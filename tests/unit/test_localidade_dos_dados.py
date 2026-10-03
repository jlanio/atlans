# tests/unit/test_localidade_dos_dados.py
"""
Data locality in the output nodes.

The policy went from a boolean on ONE node (DataOutput's `keepLocal`) to a
field common to all nodes that write, governed by the machine. These tests
lock down what makes that mean something:

  PROIBE        (forbids) the machine's policy cannot be loosened by a workflow. The
                node's field does not even offer the option to send — if it did, it
                would be a choice the executor silently ignores.

  NAO SAI       (does not leave) with `executor` locality there is no upload. This holds
                for the Drive too, which until now only had the path that sent the bytes.

  FALHA ALTO    (fails loudly) `PublishMap` and `SendEmail`'s automatic attachment only work
                by sending. On a machine that retains data they stop, with a message
                — skipping silently would leave the run green and nobody would know the
                layer was never published.

  ATOMICO       (atomic) the file written to the GeoSync folder must not be cataloged
                half-written: the scanner passes every 10 s and recognizes by size
                and mtime.
"""
import os

import pytest

from flow.utils import artifact_helpers
from flow.utils.artifact_helpers import EnvioBloqueadoError


@pytest.fixture
def maquina(tmp_path, monkeypatch):
    """Executor with temporary artifact root and GeoSync folder."""
    raiz = tmp_path / "artifacts"
    raiz.mkdir()
    pasta = tmp_path / "geosync"
    pasta.mkdir()
    monkeypatch.setenv("EXECUTOR_ARTIFACTS_DIR", str(raiz))
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", str(pasta))
    monkeypatch.delenv("EXECUTOR_SYNC_MODE", raising=False)
    monkeypatch.delenv("EXECUTOR_WORKSPACE_ID", raising=False)
    return raiz, pasta


# ── The machine's policy ─────────────────────────────────────────────────────

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
    """Reuses `EXECUTOR_SYNC_MODE`, which is what the desktop screen already writes under
    the label "Localidade dos dados" (data locality). A variable of its own would be a
    second source of truth for the same decision."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", modo)
    assert artifact_helpers.localidade_padrao() == esperado


def test_sem_a_variavel_o_padrao_e_servidor(monkeypatch):
    """This is the server's case, where `flow/` also runs in-process: the content is
    already there. It is the long-standing behavior for every existing executor."""
    monkeypatch.delenv("EXECUTOR_SYNC_MODE", raising=False)
    assert artifact_helpers.localidade_padrao() == "servidor"


@pytest.mark.parametrize("escolha", [None, "", "herdar", "  HERDAR "])
def test_herdar_segue_a_maquina(monkeypatch, escolha):
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    assert artifact_helpers.resolver_localidade(escolha) == ("executor", "executor")

    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "upload")
    assert artifact_helpers.resolver_localidade(escolha) == ("servidor", "executor")


def test_no_pode_APERTAR_a_politica(monkeypatch):
    """Machine allows sending, node asks for local → it stays local. Tightening is always
    accepted; it is the only direction in which the node's choice counts."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "upload")
    assert artifact_helpers.resolver_localidade("executor") == ("executor", "nó")


def test_no_NAO_pode_afrouxar_a_politica(monkeypatch):
    """The central case. Neither an invented value, nor an old workflow, nor an edit
    outside the UI can make an executor in catalog mode send."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    for escolha in (None, "herdar", "servidor", "minio", "qualquer", "EXECUTOR"):
        efetiva, _ = artifact_helpers.resolver_localidade(escolha)
        assert efetiva == "executor", f"escolha {escolha!r} furou a política"


def test_o_schema_NAO_oferece_a_opcao_de_enviar():
    """If it offered it, it would be the only choice the executor silently ignores —
    the person ticks it, believes it, and the behavior is something else."""
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


# ── Nodes that only work by sending ──────────────────────────────────────────

def test_envio_permitido_passa_quando_a_maquina_permite(monkeypatch):
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "bidirectional")
    artifact_helpers.exigir_envio_permitido("PublishMap 'X'", "publicar exige enviar")


def test_envio_bloqueado_explica_configuracao_causa_e_saida(monkeypatch):
    """The message is the only feedback the person gets. It has to say WHERE the
    setting is, WHY the node needs to send, and WHAT to do."""
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
    # It has to survive a cp1252 console: a UnicodeEncodeError while explaining
    # the refusal would replace the explanation with a traceback.
    msg.encode("cp1252")


def test_bloqueio_nao_e_erro_de_configuracao_do_no():
    """A dedicated exception: whoever reads the log needs to distinguish "you set it up wrong"
    from "this machine does not allow it"."""
    assert issubclass(EnvioBloqueadoError, RuntimeError)
    assert not issubclass(EnvioBloqueadoError, ValueError)


@pytest.mark.parametrize("no", ["PublishMap", "SendEmail"])
def test_nos_que_enviam_chamam_a_guarda(no):
    """Reads the code: the defect would be one of FLOW — the guard existing and not being
    called — and exercising the two nodes would require a portal, SMTP and a GeoDataFrame."""
    import pathlib
    arquivo = {"PublishMap": "publish_map.py", "SendEmail": "send_email.py"}[no]
    src = pathlib.Path(f"flow/nodes/outputs/{arquivo}").read_text(encoding="utf-8")
    assert "exigir_envio_permitido(" in src


def test_publishmap_barra_ANTES_de_serializar():
    """Serializing a large GeoDataFrame only to refuse it afterwards wastes CPU and memory
    on a result already known to be denied."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/publish_map.py").read_text(encoding="utf-8")
    corpo = src[src.index("async def execute"):]
    assert corpo.index("exigir_envio_permitido") < corpo.index("to_json")


# ── Despacho compartilhado ───────────────────────────────────────────────────

def test_persistir_artefato_local_nao_faz_nenhuma_chamada_http(maquina, monkeypatch):
    """The `if` that chooses the destination lives in a single place precisely for this:
    each copy of it would be a new point through which personal data could leak."""
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


# ── Local Drive: write to the GeoSync folder ─────────────────────────────────

@pytest.fixture
def retendo(maquina, monkeypatch):
    """The folder only receives a local file when the machine is in catalog mode."""
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    return maquina


@pytest.mark.parametrize("modo", ["upload", "bidirectional", "download", ""])
def test_NAO_grava_na_pasta_quando_o_geosync_ENVIARIA(maquina, monkeypatch, modo):
    """The bug this guard exists to prevent.

    In `upload`/`bidirectional` GeoSync scans the folder every 10 s and SENDS the
    bytes of everything it finds — `_upload_dataset` only calls `register` when the
    mode is `catalog`. Without this guard, ticking "Manter apenas no executor" (keep
    only on the executor) on a node with a Drive destination would publish the file to
    MinIO within seconds: the exact opposite of what the option promises, and silently.
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
    """The scanner scans every 10 s and recognizes by size+mtime; caught in the middle
    of the write, it catalogs a half-written file. The temporary file starts with a dot,
    which the scanner ignores, and `os.replace` publishes it all at once."""
    _, pasta = retendo
    vistos: list[str] = []
    replace_real = os.replace

    def espiao(origem, destino):
        # At this instant the final content does not yet exist under the definitive name.
        vistos.extend(p.name for p in pasta.iterdir())
        return replace_real(origem, destino)

    monkeypatch.setattr(os, "replace", espiao)
    artifact_helpers.salvar_na_pasta_do_geosync(b"conteudo", "saida.geojson", "ws-1")

    assert all(n.startswith(".") for n in vistos), (
        f"arquivo visivel ao scanner durante a escrita: {vistos}"
    )
    # No leftovers afterwards.
    assert [p.name for p in pasta.iterdir()] == ["saida.geojson"]


def test_temporario_e_removido_quando_a_escrita_falha(retendo, monkeypatch):
    """An orphaned `.atlans-tmp-*` is invisible to the user AND to the scanner: it would
    keep taking up disk forever without anyone noticing."""
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
    """GeoSync syncs against ONE workspace. Writing here with another would publish
    the file to another customer's Drive."""
    monkeypatch.setenv("EXECUTOR_WORKSPACE_ID", "ws-outro")
    with pytest.raises(ValueError) as e:
        artifact_helpers.salvar_na_pasta_do_geosync(b"x", "a.geojson", "ws-1")
    assert "ws-outro" in str(e.value) and "ws-1" in str(e.value)


def test_workspace_vazio_significa_auto_deteccao(retendo, monkeypatch):
    """Empty only happens when there is a single accessible workspace
    (executor/main.py), so it matches by construction."""
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
    """A format outside `SUPPORTED_EXTENSIONS` would be written to the folder and NEVER
    cataloged — the file would exist and the Drive would never know about it."""
    from executor.sync.scanner import SUPPORTED_EXTENSIONS

    for ext in (".geojson", ".json", ".parquet", ".zip"):
        assert ext in SUPPORTED_EXTENSIONS, ext


def test_drive_local_nao_devolve_caminho_absoluto():
    """`artifact_s3_key` circulates through the workflow and is stored in the run. Returning
    the path of the user's folder would leak the machine's directory structure —
    the same reason `local_relative_path` is relative."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/data_output.py").read_text(encoding="utf-8")
    trecho = src[src.index("if manter_local and create_drive_entry:"):]
    trecho = trecho[:trecho.index("if manter_local:")]
    assert '"artifact_s3_key":   filename,' in trecho
    assert "destino," not in trecho.split('"output"')[1]


def test_drive_local_nao_emite_artifact():
    """The one that creates the row in the Drive is GeoSync. Emitting `__artifact__` would
    make the server derive an s3_key for an object that never existed, and the UI
    would offer a 404 download."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/data_output.py").read_text(encoding="utf-8")
    trecho = src[src.index("if manter_local and create_drive_entry:"):]
    trecho = trecho[:trecho.index("if manter_local:")]
    # The KEY, not the word: the block's comment explains precisely why
    # it is not there.
    assert '"__artifact__":' not in trecho


# ── Download guard on the server ─────────────────────────────────────────────

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
    """Regression: `GET /drive/{id}/download` called `generate_download_url`
    directly and reached boto3 with `s3_key=None` — ParamValidationError, which is not
    a ClientError, escapes every except and becomes a silent 500. The UI hid the button;
    the route was still reachable."""
    import inspect

    from app.services.drive_service import DriveService

    assert "_recusar_se_local" in inspect.getsource(DriveService.generate_download_url)


def test_replace_retenta_quando_o_scanner_segura_o_arquivo(retendo, monkeypatch):
    """On Windows, `os.replace` over a file opened by another handle fails —
    and the GeoSync scanner opens the folder's files, in a thread of this same
    process, to compute MD5. Without a retry, the run would die with a
    "[WinError 5] Acesso negado" (access denied) that says nothing."""
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
    """An infinite retry would hide a genuinely locked file (antivirus, another
    program with it open) and the run would hang without explanation."""
    _, pasta = retendo

    def sempre_falha(origem, destino):
        raise PermissionError(5, "Acesso negado")

    monkeypatch.setattr(os, "replace", sempre_falha)
    monkeypatch.setattr("time.sleep", lambda _s: None)

    with pytest.raises(PermissionError):
        artifact_helpers.salvar_na_pasta_do_geosync(b"x", "a.geojson", "ws-1")
    # And without leaving the temporary file behind.
    assert list(pasta.iterdir()) == []


# ── E-mail with a reference that has no download ─────────────────────────────

def test_email_nao_embute_link_morto():
    """`_build_artifact_html` puts whatever it receives into an `href`. Without presign, that
    would be the previous node's raw reference — a RELATIVE link in an HTML e-mail,
    which leads nowhere. The e-mail would go out announcing "anexo disponivel
    para download" (attachment available for download) pointing at nothing.

    The common case is an artifact kept on the executor: there is no object in storage,
    so there is nothing to sign.
    """
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/send_email.py").read_text(encoding="utf-8")
    bloco = src[src.index('if attach_mode == "link":'):]
    bloco = bloco[:bloco.index("elif attach_mode ==")]
    # Building the HTML has to be under the "is a URL" guard, not loose.
    guarda = bloco.index('if artifact_ref.startswith(("http://", "https://")):\n                    body +=')
    assert guarda > 0


def test_anexo_sem_presign_nem_endpoint_publico_sai_sem_link(monkeypatch):
    """The "auto" mode passes the raw key when the presign fails. Without
    MINIO_EXTERNAL_ENDPOINT, it went into a relative `href`: a dead link."""
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
    """`content_location` says WHERE the content is; `local_fallback` says WHY.
    Setting False on the fallback would count a portal failure as if it were a
    privacy decision."""
    import pathlib
    src = pathlib.Path("flow/nodes/outputs/publish_map.py").read_text(encoding="utf-8")
    bloco = src[src.index("meta.update({"):]
    bloco = bloco[:bloco.index("})")]
    assert '"content_location": "executor"' in bloco
    assert '"local_fallback": True' in bloco
