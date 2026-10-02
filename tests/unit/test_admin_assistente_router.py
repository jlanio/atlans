# tests/unit/test_admin_assistente_router.py
"""`/admin/assistente/modelo` — trocar o modelo com o catálogo na frente.

O que estes testes prendem:

1. **Só admin.** O router inteiro está sob `require_admin`.
2. **Provedor fora do ar não derruba a tela.** Sem catálogo, o admin ainda
   precisa ver o que está em uso e poder voltar ao padrão.
3. **Id inválido é 400 na hora**, não erro na próxima conversa de cada usuário.
4. **O modelo é sondado antes de salvar**, e o «voltar ao padrão» nunca.
5. **Uma extensão soma campos ao painel** (uma de planos soma a cota e o custo,
   com testes na pasta dela) e recebe os parâmetros da URL que o núcleo não lê.
"""
from unittest.mock import patch

import pytest
import pytest_asyncio

from app.core.config import ASSISTENTE_MODELO
from app.services import openrouter
from tests.unit._painel_do_modelo import CATALOGO, api_com_banco, com_catalogo

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api(client, mock_current_user):
    async with api_com_banco(client, mock_current_user) as par:
        yield par


async def test_usuario_comum_nao_entra(client, mock_current_user):
    mock_current_user.role = "user"
    r = await client.get("/admin/assistente/modelo")
    assert r.status_code in (401, 403)


async def test_provedor_fora_do_ar_nao_derruba_a_tela(api):
    """Sem catálogo o admin ainda precisa ver o que está em uso e poder voltar
    ao padrão — responder 500 aqui trancaria a única saída."""
    client, _ = api
    with com_catalogo(erro=openrouter.ErroDoOpenRouter("fora do ar", status=503)):
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["catalogo"] == []
    assert corpo["catalogo_indisponivel"] == "ErroDoOpenRouter"
    assert corpo["atual"]["modelo"] == ASSISTENTE_MODELO


async def test_o_catalogo_vem_da_base_configurada_com_a_chave(api):
    """Fora do OpenRouter (um gateway, um vLLM com chave), o catálogo é o do
    servidor configurado, e ele pede a mesma chave da conversa."""
    client, _ = api
    visto: dict = {}

    async def _listar(**kw):
        visto.update(kw)
        return [dict(m) for m in CATALOGO]

    with com_catalogo(), \
            patch("app.services.openrouter.listar_modelos", _listar), \
            patch("app.api.routers.admin_assistente_router.OPENROUTER_BASE_URL", "http://vllm:8000/v1"):
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    assert visto == {"base_url": "http://vllm:8000/v1", "chave": "k"}


async def test_trocar_salva_e_a_resposta_ja_reflete(api):
    client, _ = api
    with com_catalogo():
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})

    assert r.status_code == 200
    atual = r.json()["atual"]
    assert atual["modelo"] == "a/caro"
    assert atual["origem"] == "banco"
    assert atual["definido_por"] == "admin-test"
    assert atual["definido_em"]


async def test_voltar_ao_padrao_do_ambiente(api):
    client, _ = api
    with com_catalogo():
        await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
        r = await client.put("/admin/assistente/modelo", json={"modelo": None})

    assert r.json()["atual"] == {
        "modelo": ASSISTENTE_MODELO, "origem": "ambiente",
        "definido_por": None, "definido_em": None,
        "padrao_do_ambiente": ASSISTENTE_MODELO,
    }


async def test_id_invalido_e_400_e_nao_erro_na_proxima_conversa(api):
    client, _ = api
    with com_catalogo():
        r = await client.put("/admin/assistente/modelo", json={"modelo": "antropic claude"})
        depois = await client.get("/admin/assistente/modelo")

    assert r.status_code == 400
    assert depois.json()["atual"]["modelo"] == ASSISTENTE_MODELO


async def test_campo_desconhecido_e_recusado(api):
    """`extra=forbid`: preço e teto são do servidor. Aceitar um campo a mais em
    silêncio é o primeiro passo para alguém tentar mandar um deles."""
    client, _ = api
    with com_catalogo():
        r = await client.put("/admin/assistente/modelo",
                             json={"modelo": "a/caro", "preco_centavos": 1})
    assert r.status_code == 422


# ── O painel sem extensões, e com uma ────────────────────────────────────────

async def test_sem_extensoes_o_painel_e_o_modelo_e_o_catalogo(api, registro_de_teste):
    """A distribuição livre: nada de cota nem custo por plano."""
    client, _ = api
    with com_catalogo():
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    assert set(r.json()) == {"atual", "catalogo", "catalogo_indisponivel"}


async def test_uma_extensao_soma_campos_e_recebe_os_parametros_da_url(api, registro_de_teste):
    client, _ = api
    vistos: list[dict] = []

    async def contribuicao(db, *, atual, catalogo, simular, consulta):
        vistos.append({"modelo": atual["modelo"], "catalogo": [m["id"] for m in catalogo],
                       "simular": simular, "consulta": dict(consulta)})
        return {"economia": {"teto": 42}}

    registro_de_teste.painel_do_modelo.append(contribuicao)
    with com_catalogo():
        r = await client.get("/admin/assistente/modelo", params={"simular": "a/caro", "faixa": "7"})
        trocado = await client.put("/admin/assistente/modelo", json={"modelo": "a/barato"})

    assert r.json()["economia"] == {"teto": 42}
    assert vistos[0] == {"modelo": ASSISTENTE_MODELO, "catalogo": ["a/barato", "a/caro"],
                         "simular": "a/caro", "consulta": {"simular": "a/caro", "faixa": "7"}}
    # A resposta do PUT é o painel inteiro também, sem simulação.
    assert trocado.json()["economia"] == {"teto": 42}
    assert vistos[1]["simular"] is None and vistos[1]["consulta"] == {}


# ── A sonda do modelo ────────────────────────────────────────────────────────
#
# O caso real, de produção: um admin escolheu `deepseek/...:batch` no painel —
# um id que ESTÁ no catálogo do provedor mas pertence ao endpoint de batch. O
# provedor respondeu «cannot be used with the chat/completions endpoint», e o
# assistente passou a dar «não consegui falar com o modelo» para TODOS os
# usuários, enquanto quem trocou não viu nada.
#
# A tela oferecia uma escolha que não podia funcionar. A sonda é o que move a
# recusa do provedor para o momento do clique, com as palavras dele.

_RECUSA_DO_BATCH = (
    "OpenRouter respondeu 404: deepseek/deepseek-v4-flash-vision-exp:batch cannot be "
    "used with the chat/completions endpoint (adapter FireworksBatchAdapter)."
)


async def test_modelo_que_o_provedor_recusa_nao_e_salvo(api):
    """400 no clique, com a mensagem do provedor — e nada muda."""
    client, _ = api
    from app.services.openrouter import ErroDoOpenRouter

    with com_catalogo(sonda=ErroDoOpenRouter(_RECUSA_DO_BATCH, status=404)):
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
        assert r.status_code == 400
        # A mensagem do PROVEDOR chega inteira: é ela que diz o que fazer.
        assert "chat/completions" in r.json()["message"]
        assert "não foi salvo" in r.json()["message"]

        depois = await client.get("/admin/assistente/modelo")
    assert depois.json()["atual"]["modelo"] == ASSISTENTE_MODELO, "o modelo velho continua"
    assert depois.json()["atual"]["origem"] == "ambiente"


async def test_sonda_que_nao_responde_tambem_bloqueia(api):
    """O erro caro é o outro.

    Deixar passar um modelo não verificado quebra o produto para todo mundo;
    barrar uma troca legítima durante uma instabilidade custa tentar de novo.
    Mas a mensagem separa os dois casos — «recusou» e «não deu para conferir»
    pedem ações diferentes de quem está na tela.
    """
    client, _ = api
    with com_catalogo(sonda=TimeoutError("estourou")):
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
    assert r.status_code == 400
    assert "Não deu para conferir" in r.json()["message"]
    assert "TimeoutError" in r.json()["message"]


async def test_voltar_ao_padrao_NUNCA_e_sondado(api):
    """A saída de emergência não pode depender do provedor.

    Se ele estiver fora do ar com um modelo ruim salvo, sondar o «voltar ao
    padrão» trancaria a porta justamente na hora em que ela é necessária.
    """
    client, _ = api
    with com_catalogo():
        await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})

    # Agora o provedor recusa TUDO — e mesmo assim o padrão volta.
    from app.services.openrouter import ErroDoOpenRouter

    with com_catalogo(sonda=ErroDoOpenRouter("provedor fora do ar", status=503)):
        r = await client.put("/admin/assistente/modelo", json={"modelo": None})

    assert r.status_code == 200
    assert r.json()["atual"]["origem"] == "ambiente"


async def test_a_sonda_manda_a_MESMA_forma_da_conversa():
    """Sondar com uma forma diferente da real não provaria nada.

    É a forma que o provedor recusa: são as ferramentas que um modelo sem
    suporte rejeita, e é o `max_tokens` que um modelo de teto baixo recusa.
    Uma sonda «leve» aprovaria modelos que quebram na primeira conversa.
    """
    import httpx

    from app.services import openrouter
    from app.services.assistente_service import ESFORCO_DO_RACIOCINIO, MAX_TOKENS

    visto = {}

    def _responder(pedido: httpx.Request) -> httpx.Response:
        import json as _json

        visto.update(_json.loads(pedido.content))
        # Um stream realista: um pedaço de texto e o fim. O que a sonda quer
        # saber já foi respondido no 200.
        return httpx.Response(
            200, headers={"Content-Type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_responder)) as http:
        await openrouter.sondar_modelo(
            "a/qualquer", chave="k", max_tokens=MAX_TOKENS,
            esforco=ESFORCO_DO_RACIOCINIO, http=http,
        )

    assert visto["model"] == "a/qualquer"
    assert visto["max_tokens"] == MAX_TOKENS, "o teto real, senão um modelo de teto baixo passa"
    assert visto["tools"], "sem ferramentas, um modelo que não as suporta passaria"
    assert visto["reasoning"] == {"effort": ESFORCO_DO_RACIOCINIO}
    assert visto["stream"] is True


async def test_stream_esquisito_NAO_bloqueia_a_troca():
    """O provedor aceitou — é só isso que a sonda pergunta.

    Um stream que abre com 200 e termina sem quadro útil é detalhe de
    transmissão, e a conversa real lida com ele. Barrar a troca por causa disso
    seria a sonda reprovando um modelo que funciona.
    """
    import httpx

    from app.services import openrouter

    def _vazio(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                              content=b"data: [DONE]\n\n")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_vazio)) as http:
        await openrouter.sondar_modelo(
            "a/qualquer", chave="k", max_tokens=1000, esforco=None, http=http,
        )


async def test_a_sonda_levanta_o_que_o_provedor_respondeu():
    """Sem tradução no meio: a mensagem do provedor é o que ajuda a decidir."""
    import httpx

    from app.services import openrouter

    def _recusar(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"message": _RECUSA_DO_BATCH}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(_recusar)) as http:
        with pytest.raises(openrouter.ErroDoOpenRouter) as erro:
            await openrouter.sondar_modelo(
                "d/v:batch", chave="k", max_tokens=1000, esforco=None, http=http,
            )
    assert "chat/completions" in str(erro.value)
    assert erro.value.status == 404
