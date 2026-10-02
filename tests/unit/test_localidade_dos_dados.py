# tests/unit/test_localidade_dos_dados.py
"""
Localidade dos dados nos nos de saida.

A politica saiu de um booleano de UM no (`keepLocal` do DataOutput) e virou um
campo comum a todos os nos que gravam, governado pela maquina. Estes testes
travam o que faz isso significar alguma coisa:

  PROIBE        a politica da maquina nao pode ser afrouxada por um workflow. O
                campo do no nem oferece a opcao de enviar — se oferecesse, seria
                uma escolha que o executor ignora em silencio.

  NAO SAI       com localidade `executor` nao ha upload. Vale para o Drive
                tambem, que ate aqui so tinha o caminho que enviava os bytes.

  FALHA ALTO    `PublishMap` e o anexo automatico do `SendEmail` so funcionam
                enviando. Numa maquina que retem dados eles param, com mensagem
                — pular em silencio deixaria o run verde e ninguem saberia que a
                camada nunca foi publicada.

  ATOMICO       o arquivo gravado na pasta do GeoSync nao pode ser catalogado
                pela metade: o scanner passa a cada 10 s e reconhece por tamanho
                e mtime.
"""
import os

import pytest

from flow.utils import artifact_helpers
from flow.utils.artifact_helpers import EnvioBloqueadoError


@pytest.fixture
def maquina(tmp_path, monkeypatch):
    """Executor com raiz de artefatos e pasta de GeoSync temporarias."""
    raiz = tmp_path / "artifacts"
    raiz.mkdir()
    pasta = tmp_path / "geosync"
    pasta.mkdir()
    monkeypatch.setenv("EXECUTOR_ARTIFACTS_DIR", str(raiz))
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", str(pasta))
    monkeypatch.delenv("EXECUTOR_SYNC_MODE", raising=False)
    monkeypatch.delenv("EXECUTOR_WORKSPACE_ID", raising=False)
    return raiz, pasta


# ── Politica da maquina ──────────────────────────────────────────────────────

@pytest.mark.parametrize("modo,esperado", [
    ("catalog", "executor"),
    ("CATALOG", "executor"),
    ("  catalog  ", "executor"),
    ("upload", "servidor"),
    ("bidirectional", "servidor"),
    ("download", "servidor"),
    ("", "servidor"),
])
def test_politica_vem_do_modo_do_geosync(monkeypatch, modo, esperado):
    """Reusa `EXECUTOR_SYNC_MODE`, que e o que a tela do desktop ja grava sob o
    rotulo "Localidade dos dados". Uma variavel propria seria uma segunda fonte
    de verdade para a mesma decisao."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", modo)
    assert artifact_helpers.localidade_padrao() == esperado


def test_sem_a_variavel_o_padrao_e_servidor(monkeypatch):
    """E o caso do servidor, onde `flow/` tambem roda in-process: o conteudo ja
    esta la. E o comportamento de sempre para todo executor existente."""
    monkeypatch.delenv("EXECUTOR_SYNC_MODE", raising=False)
    assert artifact_helpers.localidade_padrao() == "servidor"


@pytest.mark.parametrize("escolha", [None, "", "herdar", "  HERDAR "])
def test_herdar_segue_a_maquina(monkeypatch, escolha):
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    assert artifact_helpers.resolver_localidade(escolha) == ("executor", "executor")

    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "upload")
    assert artifact_helpers.resolver_localidade(escolha) == ("servidor", "executor")


def test_no_pode_APERTAR_a_politica(monkeypatch):
    """Maquina permite enviar, no pede local → fica local. Apertar e sempre
    aceito; e o unico sentido em que a escolha do no vale."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "upload")
    assert artifact_helpers.resolver_localidade("executor") == ("executor", "nó")


def test_no_NAO_pode_afrouxar_a_politica(monkeypatch):
    """O caso central. Nem um valor inventado, nem um fluxo antigo, nem edicao
    fora da UI conseguem fazer um executor em catalogo enviar."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    for escolha in (None, "herdar", "servidor", "minio", "qualquer", "EXECUTOR"):
        efetiva, _ = artifact_helpers.resolver_localidade(escolha)
        assert efetiva == "executor", f"escolha {escolha!r} furou a política"


def test_o_schema_NAO_oferece_a_opcao_de_enviar():
    """Se oferecesse, seria a unica escolha que o executor ignora em silencio —
    a pessoa marca, acredita, e o comportamento e outro."""
    valores = [o["value"] for o in artifact_helpers.propriedade_localidade()["options"]]
    assert valores == ["herdar", "executor"]
    assert "servidor" not in valores


def test_frase_do_log_diz_o_destino_e_quem_decidiu(monkeypatch):
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    efetiva, quem = artifact_helpers.resolver_localidade("herdar")
    frase = artifact_helpers.descrever_localidade(efetiva, quem)
    assert "apenas neste executor" in frase and "executor" in frase

    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "upload")
    efetiva, quem = artifact_helpers.resolver_localidade("executor")
    frase = artifact_helpers.descrever_localidade(efetiva, quem)
    assert "apenas neste executor" in frase and "nó" in frase


# ── Nos que so funcionam enviando ────────────────────────────────────────────

def test_envio_permitido_passa_quando_a_maquina_permite(monkeypatch):
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "bidirectional")
    artifact_helpers.exigir_envio_permitido("PublishMap 'X'", "publicar exige enviar")


def test_envio_bloqueado_explica_configuracao_causa_e_saida(monkeypatch):
    """A mensagem e o unico feedback que a pessoa recebe. Tem de dizer ONDE esta
    a configuracao, POR QUE o no precisa enviar, e O QUE fazer."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    with pytest.raises(EnvioBloqueadoError) as e:
        artifact_helpers.exigir_envio_permitido(
            "PublishMap 'Lotes'", "publicar uma camada exige enviar a geometria ao portal",
        )
    msg = str(e.value)
    assert "PublishMap 'Lotes'" in msg
    assert "GeoSync" in msg and "Manter apenas no executor" in msg
    assert "publicar uma camada exige enviar" in msg
    assert "O que fazer" in msg
    # Tem de sobreviver a um console cp1252: um UnicodeEncodeError ao explicar
    # a recusa trocaria a explicacao por um traceback.
    msg.encode("cp1252")


def test_bloqueio_nao_e_erro_de_configuracao_do_no():
    """Excecao propria: quem le o log precisa distinguir "voce montou errado" de
    "esta maquina nao permite"."""
    assert issubclass(EnvioBloqueadoError, RuntimeError)
    assert not issubclass(EnvioBloqueadoError, ValueError)


@pytest.mark.parametrize("no", ["PublishMap", "SendEmail"])
def test_nos_que_enviam_chamam_a_guarda(no):
    """Ler o codigo: o defeito seria de FLUXO — a guarda existir e nao ser
    chamada — e exercitar os dois nos exigiria portal, SMTP e um GeoDataFrame."""
    import pathlib
    arquivo = {"PublishMap": "publish_map.py", "SendEmail": "send_email.py"}[no]
    src = pathlib.Path(f"flow/nodes/outputs/{arquivo}").read_text(encoding="utf-8")
    assert "exigir_envio_permitido(" in src


def test_publishmap_barra_ANTES_de_serializar():
    """Serializar um GeoDataFrame grande para depois recusar gasta CPU e memoria
    num resultado que ja se sabia que seria negado."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/publish_map.py").read_text(encoding="utf-8")
    corpo = src[src.index("async def execute"):]
    assert corpo.index("exigir_envio_permitido") < corpo.index("to_json")


# ── Despacho compartilhado ───────────────────────────────────────────────────

def test_persistir_artefato_local_nao_faz_nenhuma_chamada_http(maquina, monkeypatch):
    """O `if` que escolhe o destino vive num lugar so justamente para isto: cada
    copia dele seria um ponto novo por onde dado pessoal poderia vazar."""
    import httpx

    def explode(*a, **k):
        raise AssertionError("localidade 'executor' NAO pode falar com a rede")

    for nome in ("post", "put", "get", "request", "stream"):
        monkeypatch.setattr(httpx, nome, explode, raising=False)
    monkeypatch.setattr(httpx, "Client", explode)

    chave, meta = artifact_helpers.persistir_artefato(
        localidade="executor", content=b"x", filename="a.json",
        workspace_id="ws-1", task_id="run-1",
    )
    assert meta["content_location"] == "executor"
    assert chave == "ws-1/run-1/a.json"


def test_persistir_artefato_servidor_vai_para_o_upload(maquina, monkeypatch):
    chamados: list[str] = []

    def falso_upload(**kw):
        chamados.append(kw["filename"])
        return "artifacts/ws-1/run-1/a.json", {"content_location": "minio"}

    monkeypatch.setattr(artifact_helpers, "upload_artifact_to_minio", falso_upload)
    artifact_helpers.persistir_artefato(
        localidade="servidor", content=b"x", filename="a.json",
        workspace_id="ws-1", task_id="run-1",
    )
    assert chamados == ["a.json"]


# ── Drive local: gravar na pasta do GeoSync ──────────────────────────────────

@pytest.fixture
def retendo(maquina, monkeypatch):
    """A pasta so recebe arquivo local quando a maquina esta em catalogo."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    return maquina


@pytest.mark.parametrize("modo", ["upload", "bidirectional", "download", ""])
def test_NAO_grava_na_pasta_quando_o_geosync_ENVIARIA(maquina, monkeypatch, modo):
    """O bug que esta guarda existe para impedir.

    Em `upload`/`bidirectional` o GeoSync varre a pasta a cada 10 s e ENVIA os
    bytes de tudo que encontra — `_upload_dataset` so chama `register` quando o
    modo e `catalog`. Sem esta guarda, marcar "Manter apenas no executor" num nó
    com destino Drive publicaria o arquivo no MinIO em segundos: o oposto exato
    do que a opcao promete, e em silencio.
    """
    _, pasta = maquina
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", modo)

    with pytest.raises(ValueError) as e:
        artifact_helpers.salvar_na_pasta_do_geosync(b"sigiloso", "a.geojson", "ws-1")

    assert list(pasta.iterdir()) == [], "arquivo gravado numa pasta que sincroniza"
    msg = str(e.value)
    assert "enviaria" in msg.lower()
    assert "Artefatos" in msg, "a mensagem precisa oferecer a saída que funciona"


def test_grava_na_pasta_e_deixa_o_geosync_catalogar(retendo):
    _, pasta = retendo
    destino = artifact_helpers.salvar_na_pasta_do_geosync(
        b'{"a":1}', "cadastro.geojson", "ws-1",
    )
    assert (pasta / "cadastro.geojson").read_bytes() == b'{"a":1}'
    assert destino == str(pasta / "cadastro.geojson")


def test_escrita_e_ATOMICA_e_nao_deixa_temporario(retendo, monkeypatch):
    """O scanner varre a cada 10 s e reconhece por tamanho+mtime; pego no meio
    da escrita, cataloga um arquivo pela metade. O temporario comeca com ponto,
    que o scanner ignora, e o `os.replace` publica de uma vez."""
    _, pasta = retendo
    vistos: list[str] = []
    replace_real = os.replace

    def espiao(origem, destino):
        # Neste instante o conteudo final ainda nao existe sob o nome definitivo.
        vistos.extend(p.name for p in pasta.iterdir())
        return replace_real(origem, destino)

    monkeypatch.setattr(os, "replace", espiao)
    artifact_helpers.salvar_na_pasta_do_geosync(b"conteudo", "saida.geojson", "ws-1")

    assert all(n.startswith(".") for n in vistos), (
        f"arquivo visivel ao scanner durante a escrita: {vistos}"
    )
    # Nada de lixo depois.
    assert [p.name for p in pasta.iterdir()] == ["saida.geojson"]


def test_temporario_e_removido_quando_a_escrita_falha(retendo, monkeypatch):
    """Um `.atlans-tmp-*` orfao e invisivel ao usuario E ao scanner: ficaria
    ocupando disco para sempre sem ninguem notar."""
    _, pasta = retendo

    def replace_que_falha(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", replace_que_falha)
    with pytest.raises(OSError):
        artifact_helpers.salvar_na_pasta_do_geosync(b"x", "saida.geojson", "ws-1")

    assert list(pasta.iterdir()) == []


def test_sem_pasta_configurada_o_erro_diz_o_que_fazer(retendo, monkeypatch):
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", "")
    with pytest.raises(ValueError) as e:
        artifact_helpers.salvar_na_pasta_do_geosync(b"x", "a.geojson", "ws-1")
    assert "GeoSync" in str(e.value) and "Configure" in str(e.value)


def test_workspace_divergente_e_barrado(retendo, monkeypatch):
    """O GeoSync sincroniza contra UM workspace. Gravar aqui com outro publicaria
    o arquivo no Drive de outro cliente."""
    monkeypatch.setenv("EXECUTOR_WORKSPACE_ID", "ws-outro")
    with pytest.raises(ValueError) as e:
        artifact_helpers.salvar_na_pasta_do_geosync(b"x", "a.geojson", "ws-1")
    assert "ws-outro" in str(e.value) and "ws-1" in str(e.value)


def test_workspace_vazio_significa_auto_deteccao(retendo, monkeypatch):
    """Vazio so acontece quando ha um unico workspace acessivel
    (executor/main.py), entao coincide por construcao."""
    monkeypatch.delenv("EXECUTOR_WORKSPACE_ID", raising=False)
    artifact_helpers.salvar_na_pasta_do_geosync(b"x", "a.geojson", "ws-1")


def test_nao_sobrescreve_arquivo_do_usuario_sem_permissao(retendo):
    """E a pasta DELE. Sobrescrever em silencio destroi dado; inventar
    'saida (1).geojson' produz lixo que ninguem pediu."""
    _, pasta = retendo
    (pasta / "saida.geojson").write_bytes(b"do usuario")

    with pytest.raises(ValueError) as e:
        artifact_helpers.salvar_na_pasta_do_geosync(b"novo", "saida.geojson", "ws-1")
    assert "Sobrescrever" in str(e.value)
    assert (pasta / "saida.geojson").read_bytes() == b"do usuario", "arquivo destruído"


def test_com_overwrite_substitui(retendo):
    _, pasta = retendo
    (pasta / "saida.geojson").write_bytes(b"antigo")
    artifact_helpers.salvar_na_pasta_do_geosync(b"novo", "saida.geojson", "ws-1", overwrite=True)
    assert (pasta / "saida.geojson").read_bytes() == b"novo"


def test_formatos_dos_nos_sao_todos_visiveis_ao_scanner():
    """Um formato fora de `SUPPORTED_EXTENSIONS` seria gravado na pasta e NUNCA
    catalogado — o arquivo existiria e o Drive nunca saberia dele."""
    from executor.sync.scanner import SUPPORTED_EXTENSIONS

    for ext in (".geojson", ".json", ".parquet", ".zip"):
        assert ext in SUPPORTED_EXTENSIONS, ext


def test_drive_local_nao_devolve_caminho_absoluto():
    """`artifact_s3_key` circula pelo workflow e fica gravado no run. Devolver o
    caminho da pasta do usuario vazaria a estrutura de diretorios da maquina —
    a mesma razao pela qual `local_relative_path` e relativo."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/data_output.py").read_text(encoding="utf-8")
    trecho = src[src.index("if manter_local and create_drive_entry:"):]
    trecho = trecho[:trecho.index("if manter_local:")]
    assert '"artifact_s3_key":   filename,' in trecho
    assert "destino," not in trecho.split('"output"')[1]


def test_drive_local_nao_emite_artifact():
    """Quem cria a linha no Drive e o GeoSync. Emitir `__artifact__` faria o
    servidor derivar uma s3_key para um objeto que nunca existiu, e a UI
    ofereceria um download 404."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/data_output.py").read_text(encoding="utf-8")
    trecho = src[src.index("if manter_local and create_drive_entry:"):]
    trecho = trecho[:trecho.index("if manter_local:")]
    # A CHAVE, e nao a palavra: o comentario do bloco explica justamente por que
    # ela nao esta la.
    assert '"__artifact__":' not in trecho


# ── Guarda de download no servidor ───────────────────────────────────────────

def test_download_de_conteudo_local_e_recusado():
    from types import SimpleNamespace

    from app.core.exceptions import ConteudoNoExecutorError
    from app.services import drive_service

    with pytest.raises(ConteudoNoExecutorError):
        drive_service._recusar_se_local(
            SimpleNamespace(content_location="executor", s3_key=None, original_name="a.gpkg")
        )


def test_download_de_arquivo_normal_passa():
    from types import SimpleNamespace

    from app.services import drive_service

    drive_service._recusar_se_local(
        SimpleNamespace(content_location="minio", s3_key="drive/ws1/a.gpkg", original_name="a.gpkg")
    )


def test_guarda_vive_no_SERVICE_e_nao_no_router():
    """Regressao: `GET /drive/{id}/download` chamava `generate_download_url`
    direto e chegava ao boto3 com `s3_key=None` — ParamValidationError, que nao e
    ClientError, escapa de todo except e vira 500 mudo. A UI escondia o botao; a
    rota continuava alcancavel."""
    import inspect

    from app.services.drive_service import DriveService

    assert "_recusar_se_local" in inspect.getsource(DriveService.generate_download_url)


def test_replace_retenta_quando_o_scanner_segura_o_arquivo(retendo, monkeypatch):
    """No Windows, `os.replace` sobre um arquivo aberto por outro handle falha —
    e o scanner do GeoSync abre os arquivos da pasta, numa thread deste mesmo
    processo, para calcular MD5. Sem retry, o run morreria com um
    "[WinError 5] Acesso negado" que nao diz nada."""
    _, pasta = retendo
    tentativas = {"n": 0}
    replace_real = os.replace

    def instavel(origem, destino):
        tentativas["n"] += 1
        if tentativas["n"] < 3:
            raise PermissionError(5, "Acesso negado")
        return replace_real(origem, destino)

    monkeypatch.setattr(os, "replace", instavel)
    monkeypatch.setattr("time.sleep", lambda _s: None)

    artifact_helpers.salvar_na_pasta_do_geosync(b"x", "a.geojson", "ws-1")
    assert tentativas["n"] == 3
    assert (pasta / "a.geojson").read_bytes() == b"x"


def test_replace_desiste_e_propaga_se_nao_for_transitorio(retendo, monkeypatch):
    """Retry infinito esconderia um arquivo travado de verdade (antivirus, outro
    programa com ele aberto) e o run ficaria pendurado sem explicacao."""
    _, pasta = retendo

    def sempre_falha(origem, destino):
        raise PermissionError(5, "Acesso negado")

    monkeypatch.setattr(os, "replace", sempre_falha)
    monkeypatch.setattr("time.sleep", lambda _s: None)

    with pytest.raises(PermissionError):
        artifact_helpers.salvar_na_pasta_do_geosync(b"x", "a.geojson", "ws-1")
    # E sem deixar o temporario para tras.
    assert list(pasta.iterdir()) == []


# ── E-mail com referencia que nao tem download ───────────────────────────────

def test_email_nao_embute_link_morto():
    """`_build_artifact_html` poe o que receber num `href`. Sem presign, isso
    seria a referencia crua do no anterior — um link RELATIVO num e-mail HTML,
    que nao leva a lugar nenhum. O e-mail sairia anunciando "anexo disponivel
    para download" apontando para o nada.

    O caso comum e um artefato mantido no executor: nao ha objeto no storage,
    entao nao ha o que assinar.
    """
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/send_email.py").read_text(encoding="utf-8")
    bloco = src[src.index('if attach_mode == "link":'):]
    bloco = bloco[:bloco.index("elif attach_mode ==")]
    # A montagem do HTML tem de estar sob a guarda de "é URL", nao solta.
    guarda = bloco.index('if artifact_ref.startswith(("http://", "https://")):\n                    body +=')
    assert guarda > 0


def test_anexo_sem_presign_nem_endpoint_publico_sai_sem_link(monkeypatch):
    """O modo "auto" passa a chave crua quando o presign falha. Sem
    MINIO_EXTERNAL_ENDPOINT, ela ia num `href` relativo: um link morto."""
    from unittest.mock import MagicMock

    from flow.nodes.outputs.send_email import SendEmailNode

    no = MagicMock()
    monkeypatch.delenv("MINIO_EXTERNAL_ENDPOINT", raising=False)
    assert SendEmailNode._build_artifact_html(no, "workspaces/ws-1/x.geojson", "x.geojson") == ""
    assert "sem ele" in no.log.call_args.args[0]

    monkeypatch.setenv("MINIO_EXTERNAL_ENDPOINT", "https://s3.atlans.example.org/")
    html = SendEmailNode._build_artifact_html(no, "workspaces/ws-1/x.geojson", "x.geojson")
    assert 'href="https://s3.atlans.example.org/atlans-drive/workspaces/ws-1/x.geojson"' in html


# ── PublishMap: fallback e degradacao, nao politica ──────────────────────────

def test_publishmap_fallback_registra_que_FOI_falha():
    """`content_location` diz ONDE o conteudo esta; `local_fallback` diz POR QUE.
    Marcar False no fallback contaria uma falha do portal como se fosse uma
    decisao de privacidade."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/publish_map.py").read_text(encoding="utf-8")
    bloco = src[src.index("meta.update({"):]
    bloco = bloco[:bloco.index("})")]
    assert '"content_location": "executor"' in bloco
    assert '"local_fallback": True' in bloco
