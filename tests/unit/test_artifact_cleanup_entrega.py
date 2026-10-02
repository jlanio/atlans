# tests/unit/test_artifact_cleanup_entrega.py
"""
A linha do banco so cai quando a ordem de remocao FOI ENTREGUE.

Um artefato local vive no disco do executor; o servidor guarda so o catalogo.
Apagar a linha sem que o executor tenha recebido a ordem deixa o arquivo orfao:
dado pessoal vencido, retido indefinidamente, e sem NADA no sistema que registre
que ele existe. Para LGPD esse e o pior desfecho — pior que nao ter apagado,
porque ninguem consegue nem saber que ha o que apagar.

O bug que estes testes travam era sutil: `_ordenar_remocao_local` envolvia o
envio num `try/except`, mas `executor_registry.send_json` **devolve False sem
levantar** quando o executor esta offline (e quando o relay Redis nao tem
ouvinte, e quando a assinatura Ed25519 falha). O `except` cobria so o caso raro
e deixava passar o caso comum — executor desligado — tratando a ordem como
entregue.
"""
import pytest

from app.core import artifact_cleanup


def _itens(n=2):
    return {
        "exec-1": [
            {"id_hash": f"h{i}", "local_path": f"a/{i}.gpkg", "_id": 100 + i}
            for i in range(n)
        ]
    }


class _Registry:
    """Dubla `executor_registry.send_json` com o retorno que o teste quer."""

    def __init__(self, retorno):
        self.retorno = retorno
        self.enviados = []

    async def send_json(self, executor_id, data):
        self.enviados.append((executor_id, data))
        if isinstance(self.retorno, Exception):
            raise self.retorno
        return self.retorno


@pytest.fixture
def registry(monkeypatch):
    def instalar(retorno):
        r = _Registry(retorno)
        import app.core.executor_connections as ec
        monkeypatch.setattr(ec, "executor_registry", r, raising=False)
        return r
    return instalar


@pytest.mark.asyncio
async def test_entrega_confirmada_libera_a_linha_do_banco(registry):
    registry(True)
    entregues = await artifact_cleanup._ordenar_remocao_local(_itens())
    assert entregues == [100, 101]


@pytest.mark.asyncio
async def test_executor_OFFLINE_nao_libera_a_linha(registry):
    # O caso do bug: send_json devolve False, sem excecao. Antes, os ids eram
    # tratados como entregues e a linha era apagada — arquivo orfao no disco.
    registry(False)
    entregues = await artifact_cleanup._ordenar_remocao_local(_itens())
    assert entregues == [], (
        "ordem NAO entregue nao pode liberar a remocao da linha: o arquivo "
        "continua no disco do executor e a linha e o unico rastro dele"
    )


@pytest.mark.asyncio
async def test_excecao_no_envio_tambem_nao_libera(registry):
    registry(RuntimeError("websocket fechado"))
    assert await artifact_cleanup._ordenar_remocao_local(_itens()) == []


@pytest.mark.asyncio
async def test_um_executor_offline_nao_impede_os_outros(registry, monkeypatch):
    # Falha por executor, e nao em lote: uma maquina desligada nao pode adiar a
    # retencao das outras.
    class _Parcial(_Registry):
        async def send_json(self, executor_id, data):
            self.enviados.append((executor_id, data))
            return executor_id != "exec-offline"

    import app.core.executor_connections as ec
    r = _Parcial(None)
    # Via monkeypatch, para o dublê sumir ao final: atribuido direto no modulo,
    # ele sobrevivia ao teste e quebrava quem usa o registro depois (o bloco
    # "agora" das metricas do Historico chamava `list_pending_acks` nele).
    monkeypatch.setattr(ec, "executor_registry", r)

    entregues = await artifact_cleanup._ordenar_remocao_local({
        "exec-offline": [{"id_hash": "a", "local_path": "x", "_id": 1}],
        "exec-online": [{"id_hash": "b", "local_path": "y", "_id": 2}],
    })
    assert entregues == [2]


@pytest.mark.asyncio
async def test_a_ordem_vai_como_control_assinavel(registry):
    # `purge_artifacts` precisa sair como `type: control` — e o que faz o
    # servidor assina-la com Ed25519 (sign_if_needed) e o executor exigi-la
    # assinada. Uma ordem de apagar arquivo sem assinatura seria um canal de
    # destruicao de dados para quem vencesse a conexao.
    r = registry(True)
    await artifact_cleanup._ordenar_remocao_local(_itens(1))

    _, msg = r.enviados[0]
    assert msg["type"] == "control"
    assert msg["action"] == "purge_artifacts"
    assert msg["artifacts"] == [{"id_hash": "h0", "local_path": "a/0.gpkg"}]
