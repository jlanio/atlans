# tests/unit/test_register_artifacts_caracterizacao.py
"""Characterization of `_register_artifacts`: sanitizes, resolves in batch, persists.

Against a real SQLite (the written rows are checked field by field) and with a
journal that records each query, HEAD to storage, `add`, `commit` and Drive
notice, in the order they happen. It pins:

- the order of the phases: retention → artifacts already known to the run → Drive
  guards (by id and by key) → HEADs → rows → ONE commit → Drive notices;
- the sanitization: an item that is not an object is dropped silently, an invalid
  name is dropped with a warning, a duplicate in the same batch or one already
  stored in the run does not become a second row;
- that HEAD only happens for a new row that has an object in storage (never for a
  local artifact nor for an already registered Drive file);
- the shape of the Artifact and WorkspaceFile rows (minio, local, catalog);
- that a redelivery does not pay for a commit, and that a failing Drive notice
  does not prevent the following ones.
"""
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import run_result_consumer as rrc
from app.models.artifact import Artifact
from app.models.base import Base
from app.models.system_config import SystemConfig
from app.models.workspace_file import WorkspaceFile

WS = "ws-1"
TASK = "task-1"
EXECUTOR = "ag-1"


def _key(nome: str) -> str:
    return f"artifacts/{WS}/{TASK}/{nome}"


def _run(**campos):
    base = {"workspace_id": WS, "task_id": TASK, "workflow_hash": "wf-1", "host": f"executor:{EXECUTOR}"}
    base.update(campos)
    return SimpleNamespace(**base)


def _consulta(stmt) -> str:
    sql = str(stmt)
    onde = sql.split("WHERE")[-1]
    if "system_config" in sql:
        return "retencao"
    if "FROM artifacts" in sql:
        return "conhecidos"
    if "workspace_files.id_hash IN" in onde:
        return "drive_por_id"
    if "workspace_files.s3_key IN" in onde:
        return "drive_por_key"
    return sql


@pytest_asyncio.fixture
async def fabrica():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[Artifact.__table__, WorkspaceFile.__table__, SystemConfig.__table__],
        )
    # The same `expire_on_commit=False` as the production AsyncSessionLocal.
    yield async_sessionmaker(eng, expire_on_commit=False)
    await eng.dispose()


@pytest.fixture
def mundo(monkeypatch):
    """Fake Storage and Drive that write to the same journal as the session."""
    estado = SimpleNamespace(
        diario=[], tamanhos={}, head_falha=set(), emit_falha=set(),
    )

    def _head(key):
        estado.diario.append(("head", key))
        if key in estado.head_falha:
            raise ConnectionError("minio fora")
        return {"size": estado.tamanhos.get(key, 100)}

    async def _emit(workspace_id, action, file_info, **_kw):
        estado.diario.append(("emit", action, file_info))
        if file_info["original_name"] in estado.emit_falha:
            raise ConnectionError("ws caiu")

    monkeypatch.setattr("app.core.storage.head", _head)
    monkeypatch.setattr("app.core.drive_events.emit_drive_event", _emit)
    monkeypatch.setattr(rrc.logger, "propagate", True)
    return estado


def _espionar(db, diario: list) -> None:
    execute, add, commit = db.execute, db.add, db.commit

    async def _execute(stmt, *a, **kw):
        diario.append(("execute", _consulta(stmt)))
        return await execute(stmt, *a, **kw)

    def _add(obj, *a, **kw):
        nome = getattr(obj, "filename", None) or getattr(obj, "original_name", None)
        diario.append(("add", type(obj).__name__, nome))
        return add(obj, *a, **kw)

    async def _commit():
        diario.append(("commit",))
        return await commit()

    db.execute, db.add, db.commit = _execute, _add, _commit


async def _registrar(fabrica, mundo, meta, run=None) -> None:
    async with fabrica() as db:
        _espionar(db, mundo.diario)
        await rrc._register_artifacts(db, run or _run(), meta)


async def _linhas(fabrica, modelo):
    async with fabrica() as db:
        return list((await db.execute(select(modelo).order_by(modelo.id))).scalars().all())


async def _semear(fabrica, *objs) -> None:
    async with fabrica() as db:
        db.add_all(objs)
        await db.commit()


def _nomes(diario) -> list:
    return [c[0] if c[0] != "execute" else c[1] for c in diario]


# ── Fases e formato ───────────────────────────────────────────────────────────


async def test_run_sem_workspace_nao_consulta_nada(fabrica, mundo, caplog):
    with caplog.at_level("WARNING"):
        await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}]}, _run(workspace_id=None))
    assert mundo.diario == []
    assert any(
        r.getMessage() == "run task-1 nao tem workspace_id — artefatos ignorados (nao ha prefixo seguro)."
        for r in caplog.records
    )


async def test_artefato_no_minio_segue_as_fases_e_grava_a_linha_completa(fabrica, mundo):
    await _semear(fabrica, SystemConfig(key="artifact_retention_days", value=7))
    mundo.tamanhos[_key("Saida_Final.geojson")] = 4321

    await _registrar(fabrica, mundo, {"n1": [{
        "output_key": "saida", "format": "geojson", "features": 12,
        "filename": "Saída Final.geojson",
        "s3_key": "artifacts/ws-vitima/run-x/segredo.geojson",
        "credential_id": "cred-1", "is_published": True, "publish_config": {"titulo": "x"},
    }]})

    assert mundo.diario == [
        ("execute", "retencao"),
        ("execute", "conhecidos"),
        ("head", _key("Saida_Final.geojson")),
        ("add", "Artifact", "Saida_Final.geojson"),
        ("commit",),
    ]
    [a] = await _linhas(fabrica, Artifact)
    assert (a.workspace_id, a.workflow_hash, a.run_id, a.node_id) == (WS, "wf-1", TASK, "n1")
    assert (a.output_key, a.filename, a.format) == ("saida", "Saida_Final.geojson", "geojson")
    assert (a.size_bytes, a.features) == (4321, 12)
    assert (a.s3_key, a.content_location, a.local_path) == (_key("Saida_Final.geojson"), "minio", None)
    assert (a.executor_id, a.credential_id) == (EXECUTOR, "cred-1")
    assert (a.is_published, a.publish_config, a.is_pinned) == (True, {"titulo": "x"}, False)
    esperado = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    assert abs((a.expires_at - esperado).total_seconds()) < 60


async def test_sem_retencao_nao_expira_e_campos_opcionais_tem_default(fabrica, mundo):
    await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}]})
    [a] = await _linhas(fabrica, Artifact)
    assert a.expires_at is None
    assert (a.output_key, a.format, a.features, a.credential_id) == ("", None, None, None)
    assert (a.is_published, a.publish_config) == (False, None)


@pytest.mark.parametrize(("host", "esperado"), [("local", None), (None, None), ("executor:", "")])
async def test_executor_id_so_sai_de_host_de_executor(fabrica, mundo, host, esperado):
    await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}]}, _run(host=host))
    [a] = await _linhas(fabrica, Artifact)
    assert a.executor_id == esperado


async def test_payload_misturado_saneia_e_deduplica_no_proprio_lote(fabrica, mundo, caplog):
    with caplog.at_level("WARNING"):
        await _registrar(fabrica, mundo, {
            "n1": [
                {"filename": "a.json"},
                "nao-sou-objeto",
                {"filename": ""},
                {"output_key": "sem-nome"},
                {"filename": "a.json", "output_key": "repetido"},
                {"filename": "b.json"},
            ],
            # A loose item, outside a list, also counts.
            "n2": {"filename": "a.json"},
        })

    linhas = await _linhas(fabrica, Artifact)
    assert [(a.node_id, a.filename, a.output_key) for a in linhas] == [
        ("n1", "a.json", ""), ("n1", "b.json", ""), ("n2", "a.json", ""),
    ]
    avisos = [r.getMessage() for r in caplog.records if r.name == rrc.logger.name]
    assert avisos.count("run task-1 / node n1: artefato com filename invalido ('') — ignorado.") == 2
    assert [c for c in mundo.diario if c[0] == "commit"] == [("commit",)]


async def test_reentrega_nao_duplica_nem_paga_commit_nem_head(fabrica, mundo):
    meta = {"n1": [{"filename": "a.json"}, {"filename": "b.json", "content_location": "executor"}]}
    await _registrar(fabrica, mundo, meta)
    mundo.diario.clear()

    await _registrar(fabrica, mundo, meta)

    assert mundo.diario == [("execute", "retencao"), ("execute", "conhecidos")]
    assert len(await _linhas(fabrica, Artifact)) == 2


async def test_nada_aproveitavel_para_antes_das_guardas_do_drive(fabrica, mundo):
    await _registrar(fabrica, mundo, {"n1": [{"filename": "..", "context": "drive"}, 7]})
    assert mundo.diario == [("execute", "retencao"), ("execute", "conhecidos")]


async def test_local_nao_consulta_o_storage_e_so_aceita_tamanho_inteiro(fabrica, mundo):
    await _registrar(fabrica, mundo, {"n1": [
        {"filename": "a.geojson", "content_location": "executor", "size_bytes": 77},
        {"filename": "b.geojson", "content_location": "executor", "size_bytes": -1},
        {"filename": "c.geojson", "content_location": "executor", "size_bytes": "12"},
        {"filename": "d.geojson", "content_location": "minio", "local_fallback": True, "size_bytes": 5},
    ]})

    assert "head" not in _nomes(mundo.diario)
    linhas = await _linhas(fabrica, Artifact)
    assert [(a.filename, a.size_bytes) for a in linhas] == [
        ("a.geojson", 77), ("b.geojson", None), ("c.geojson", None), ("d.geojson", 5),
    ]
    for a in linhas:
        assert (a.s3_key, a.content_location) == (None, "executor")
        assert a.local_path == f"{WS}/{TASK}/{a.filename}"


async def test_head_que_falha_deixa_so_aquele_sem_tamanho(fabrica, mundo, caplog):
    mundo.head_falha.add(_key("a.json"))
    mundo.tamanhos[_key("b.json")] = 9

    with caplog.at_level("WARNING"):
        await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}, {"filename": "b.json"}]})

    assert [(a.filename, a.size_bytes) for a in await _linhas(fabrica, Artifact)] == [
        ("a.json", None), ("b.json", 9),
    ]
    assert any(
        r.getMessage() == f"Falha ao obter tamanho do artefato S3 '{_key('a.json')}': minio fora"
        for r in caplog.records
    )


# ── Drive ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("nome", "extensao", "mime"),
    [
        ("limites.geojson", "geojson", "application/geo+json"),
        ("tabela.json", "json", "application/json"),
        ("LEIAME", "", "application/json"),
    ],
)
async def test_drive_novo_no_minio_cria_linha_e_avisa_depois_do_commit(fabrica, mundo, nome, extensao, mime):
    mundo.tamanhos[_key(nome)] = 321

    await _registrar(fabrica, mundo, {"n1": [{"filename": nome, "context": "drive"}]})

    [wf] = await _linhas(fabrica, WorkspaceFile)
    assert (wf.workspace_id, wf.s3_key, wf.original_name) == (WS, _key(nome), nome)
    assert (wf.extension, wf.mime_type, wf.size) == (extensao, mime, 321)
    assert (wf.uploaded_by, wf.status, wf.content_location) == (EXECUTOR, "confirmed", "minio")
    assert wf.content_executor_id is None
    assert not await _linhas(fabrica, Artifact)
    assert mundo.diario == [
        ("execute", "retencao"),
        ("execute", "conhecidos"),
        ("execute", "drive_por_key"),
        ("head", _key(nome)),
        ("add", "WorkspaceFile", nome),
        ("commit",),
        ("emit", "file_created", {
            "id_hash": wf.id_hash, "original_name": nome, "extension": extensao,
            "size": 321, "content_md5": None,
        }),
    ]


@pytest.mark.parametrize(("reusado", "acao"), [(True, "file_updated"), (False, "file_created")])
async def test_drive_com_linha_do_upload_so_avisa(fabrica, mundo, reusado, acao):
    await _semear(fabrica, WorkspaceFile(
        id_hash="file-1", workspace_id=WS, s3_key=f"artifacts/{WS}/task-antigo/imovel.geojson",
        original_name="imovel.geojson", extension="geojson", size=None, content_md5="abc",
    ))

    await _registrar(fabrica, mundo, {"n1": [{
        "filename": "imovel.geojson", "context": "drive",
        "drive_file_id": "file-1", "drive_reused": reusado,
    }]})

    assert mundo.diario == [
        ("execute", "retencao"),
        ("execute", "conhecidos"),
        ("execute", "drive_por_id"),
        ("execute", "drive_por_key"),
        ("emit", acao, {
            "id_hash": "file-1", "original_name": "imovel.geojson", "extension": "geojson",
            "size": 0, "content_md5": "abc",
        }),
    ]
    assert len(await _linhas(fabrica, WorkspaceFile)) == 1


async def test_id_do_drive_de_outro_workspace_nao_serve_de_guarda(fabrica, mundo):
    await _semear(fabrica, WorkspaceFile(
        id_hash="file-1", workspace_id="ws-2", s3_key="artifacts/ws-2/t/x.geojson",
        original_name="x.geojson", extension="geojson",
    ))

    await _registrar(fabrica, mundo, {"n1": [{
        "filename": "x.geojson", "context": "drive", "drive_file_id": "file-1",
    }]})

    novas = [wf for wf in await _linhas(fabrica, WorkspaceFile) if wf.workspace_id == WS]
    assert [wf.s3_key for wf in novas] == [_key("x.geojson")]
    assert [c[1] for c in mundo.diario if c[0] == "emit"] == ["file_created"]


async def test_drive_ja_registrado_pela_key_derivada_e_ignorado(fabrica, mundo):
    await _semear(fabrica, WorkspaceFile(
        workspace_id=WS, s3_key=_key("x.geojson"), original_name="x.geojson", extension="geojson",
    ))

    await _registrar(fabrica, mundo, {"n1": [{"filename": "x.geojson", "context": "drive"}]})

    assert mundo.diario == [
        ("execute", "retencao"), ("execute", "conhecidos"), ("execute", "drive_por_key"),
    ]


async def test_falha_ao_avisar_um_arquivo_nao_impede_os_demais(fabrica, mundo, caplog):
    mundo.emit_falha.add("a.geojson")

    with caplog.at_level("WARNING"):
        await _registrar(fabrica, mundo, {"n1": [
            {"filename": "a.geojson", "context": "drive"},
            {"filename": "b.geojson", "context": "drive"},
        ]})

    assert [c[2]["original_name"] for c in mundo.diario if c[0] == "emit"] == ["a.geojson", "b.geojson"]
    assert len(await _linhas(fabrica, WorkspaceFile)) == 2
    assert any(
        r.getMessage() == "Falha ao notificar Drive para 'a.geojson': ws caiu" for r in caplog.records
    )


async def test_lote_misturado_percorre_as_tres_fases_na_ordem(fabrica, mundo, caplog):
    """Artifact in MinIO, local artifact, Drive already uploaded, new Drive and Drive
    that fell back to local — in a single payload."""
    await _semear(fabrica, WorkspaceFile(
        id_hash="file-1", workspace_id=WS, s3_key=f"artifacts/{WS}/task-antigo/c.geojson",
        original_name="c.geojson", extension="geojson", size=8,
    ))

    with caplog.at_level(logging.DEBUG, logger=rrc.logger.name):
        await _registrar(fabrica, mundo, {
            "n1": [{"filename": "a.json"}],
            "n2": [{"filename": "b.json", "content_location": "executor", "size_bytes": 3}],
            "n3": [{"filename": "c.geojson", "context": "drive", "drive_file_id": "file-1"}],
            "n4": [{"filename": "d.geojson", "context": "drive"}],
            "n5": [{"filename": "e.geojson", "context": "drive", "local_fallback": True, "size_bytes": 4}],
        })

    nomes = _nomes(mundo.diario)
    assert nomes[:4] == ["retencao", "conhecidos", "drive_por_id", "drive_por_key"]
    # The HEADs go out in parallel: the order AMONG them is not a contract.
    assert sorted(c[1] for c in mundo.diario[4:6]) == [_key("a.json"), _key("d.geojson")]
    assert nomes[4:6] == ["head", "head"]
    assert mundo.diario[6:11] == [
        ("add", "Artifact", "a.json"),
        ("add", "Artifact", "b.json"),
        ("add", "WorkspaceFile", "d.geojson"),
        ("add", "WorkspaceFile", "e.geojson"),
        ("commit",),
    ]
    # The already existing file is notified first (decided in phase 2), the new one after.
    assert [(c[1], c[2]["original_name"]) for c in mundo.diario[11:]] == [
        ("file_created", "c.geojson"), ("file_created", "d.geojson"),
    ]
    catalogo = next(wf for wf in await _linhas(fabrica, WorkspaceFile) if wf.original_name == "e.geojson")
    assert (catalogo.s3_key, catalogo.content_location, catalogo.content_executor_id) == (None, "executor", EXECUTOR)
    assert catalogo.size == 4
    assert "run task-1: 4 artefato(s) registrado(s) (2 no Drive)." in [
        r.getMessage() for r in caplog.records if r.name == rrc.logger.name
    ]
