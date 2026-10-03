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


def _query(stmt) -> str:
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


def _spy_on(db, diario: list) -> None:
    execute, add, commit = db.execute, db.add, db.commit

    async def _execute(stmt, *a, **kw):
        diario.append(("execute", _query(stmt)))
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
        _spy_on(db, mundo.diario)
        await rrc._register_artifacts(db, run or _run(), meta)


async def _lines(fabrica, modelo):
    async with fabrica() as db:
        return list((await db.execute(select(modelo).order_by(modelo.id))).scalars().all())


async def _seed(fabrica, *objs) -> None:
    async with fabrica() as db:
        db.add_all(objs)
        await db.commit()


def _names(diario) -> list:
    return [c[0] if c[0] != "execute" else c[1] for c in diario]


# ── Fases e formato ───────────────────────────────────────────────────────────


async def test_run_without_workspace_queries_nothing(fabrica, mundo, caplog):
    with caplog.at_level("WARNING"):
        await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}]}, _run(workspace_id=None))
    assert mundo.diario == []
    assert any(
        r.getMessage() == "run task-1 nao tem workspace_id — artefatos ignorados (nao ha prefixo seguro)."
        for r in caplog.records
    )


async def test_minio_artifact_follows_the_phases_and_writes_the_full_row(fabrica, mundo):
    await _seed(fabrica, SystemConfig(key="artifact_retention_days", value=7))
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
    [a] = await _lines(fabrica, Artifact)
    assert (a.workspace_id, a.workflow_hash, a.run_id, a.node_id) == (WS, "wf-1", TASK, "n1")
    assert (a.output_key, a.filename, a.format) == ("saida", "Saida_Final.geojson", "geojson")
    assert (a.size_bytes, a.features) == (4321, 12)
    assert (a.s3_key, a.content_location, a.local_path) == (_key("Saida_Final.geojson"), "minio", None)
    assert (a.executor_id, a.credential_id) == (EXECUTOR, "cred-1")
    assert (a.is_published, a.publish_config, a.is_pinned) == (True, {"titulo": "x"}, False)
    esperado = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    assert abs((a.expires_at - esperado).total_seconds()) < 60


async def test_without_retention_does_not_expire_and_optional_fields_have_defaults(fabrica, mundo):
    await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}]})
    [a] = await _lines(fabrica, Artifact)
    assert a.expires_at is None
    assert (a.output_key, a.format, a.features, a.credential_id) == ("", None, None, None)
    assert (a.is_published, a.publish_config) == (False, None)


@pytest.mark.parametrize(("host", "esperado"), [("local", None), (None, None), ("executor:", "")])
async def test_executor_id_only_comes_from_executor_host(fabrica, mundo, host, esperado):
    await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}]}, _run(host=host))
    [a] = await _lines(fabrica, Artifact)
    assert a.executor_id == esperado


async def test_mixed_payload_sanitizes_and_deduplicates_within_the_batch(fabrica, mundo, caplog):
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

    linhas = await _lines(fabrica, Artifact)
    assert [(a.node_id, a.filename, a.output_key) for a in linhas] == [
        ("n1", "a.json", ""), ("n1", "b.json", ""), ("n2", "a.json", ""),
    ]
    avisos = [r.getMessage() for r in caplog.records if r.name == rrc.logger.name]
    assert avisos.count("run task-1 / node n1: artefato com filename invalido ('') — ignorado.") == 2
    assert [c for c in mundo.diario if c[0] == "commit"] == [("commit",)]


async def test_redelivery_neither_duplicates_nor_pays_commit_or_head(fabrica, mundo):
    meta = {"n1": [{"filename": "a.json"}, {"filename": "b.json", "content_location": "executor"}]}
    await _registrar(fabrica, mundo, meta)
    mundo.diario.clear()

    await _registrar(fabrica, mundo, meta)

    assert mundo.diario == [("execute", "retencao"), ("execute", "conhecidos")]
    assert len(await _lines(fabrica, Artifact)) == 2


async def test_nothing_usable_stops_before_the_drive_guards(fabrica, mundo):
    await _registrar(fabrica, mundo, {"n1": [{"filename": "..", "context": "drive"}, 7]})
    assert mundo.diario == [("execute", "retencao"), ("execute", "conhecidos")]


async def test_local_does_not_query_storage_and_only_accepts_integer_size(fabrica, mundo):
    await _registrar(fabrica, mundo, {"n1": [
        {"filename": "a.geojson", "content_location": "executor", "size_bytes": 77},
        {"filename": "b.geojson", "content_location": "executor", "size_bytes": -1},
        {"filename": "c.geojson", "content_location": "executor", "size_bytes": "12"},
        {"filename": "d.geojson", "content_location": "minio", "local_fallback": True, "size_bytes": 5},
    ]})

    assert "head" not in _names(mundo.diario)
    linhas = await _lines(fabrica, Artifact)
    assert [(a.filename, a.size_bytes) for a in linhas] == [
        ("a.geojson", 77), ("b.geojson", None), ("c.geojson", None), ("d.geojson", 5),
    ]
    for a in linhas:
        assert (a.s3_key, a.content_location) == (None, "executor")
        assert a.local_path == f"{WS}/{TASK}/{a.filename}"


async def test_failing_head_leaves_only_that_one_without_size(fabrica, mundo, caplog):
    mundo.head_falha.add(_key("a.json"))
    mundo.tamanhos[_key("b.json")] = 9

    with caplog.at_level("WARNING"):
        await _registrar(fabrica, mundo, {"n1": [{"filename": "a.json"}, {"filename": "b.json"}]})

    assert [(a.filename, a.size_bytes) for a in await _lines(fabrica, Artifact)] == [
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
async def test_new_drive_in_minio_creates_row_and_notifies_after_commit(fabrica, mundo, nome, extensao, mime):
    mundo.tamanhos[_key(nome)] = 321

    await _registrar(fabrica, mundo, {"n1": [{"filename": nome, "context": "drive"}]})

    [wf] = await _lines(fabrica, WorkspaceFile)
    assert (wf.workspace_id, wf.s3_key, wf.original_name) == (WS, _key(nome), nome)
    assert (wf.extension, wf.mime_type, wf.size) == (extensao, mime, 321)
    assert (wf.uploaded_by, wf.status, wf.content_location) == (EXECUTOR, "confirmed", "minio")
    assert wf.content_executor_id is None
    assert not await _lines(fabrica, Artifact)
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
async def test_drive_with_upload_row_only_notifies(fabrica, mundo, reusado, acao):
    await _seed(fabrica, WorkspaceFile(
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
    assert len(await _lines(fabrica, WorkspaceFile)) == 1


async def test_drive_id_from_another_workspace_does_not_act_as_guard(fabrica, mundo):
    await _seed(fabrica, WorkspaceFile(
        id_hash="file-1", workspace_id="ws-2", s3_key="artifacts/ws-2/t/x.geojson",
        original_name="x.geojson", extension="geojson",
    ))

    await _registrar(fabrica, mundo, {"n1": [{
        "filename": "x.geojson", "context": "drive", "drive_file_id": "file-1",
    }]})

    novas = [wf for wf in await _lines(fabrica, WorkspaceFile) if wf.workspace_id == WS]
    assert [wf.s3_key for wf in novas] == [_key("x.geojson")]
    assert [c[1] for c in mundo.diario if c[0] == "emit"] == ["file_created"]


async def test_drive_already_registered_by_derived_key_is_ignored(fabrica, mundo):
    await _seed(fabrica, WorkspaceFile(
        workspace_id=WS, s3_key=_key("x.geojson"), original_name="x.geojson", extension="geojson",
    ))

    await _registrar(fabrica, mundo, {"n1": [{"filename": "x.geojson", "context": "drive"}]})

    assert mundo.diario == [
        ("execute", "retencao"), ("execute", "conhecidos"), ("execute", "drive_por_key"),
    ]


async def test_failure_notifying_one_file_does_not_stop_the_others(fabrica, mundo, caplog):
    mundo.emit_falha.add("a.geojson")

    with caplog.at_level("WARNING"):
        await _registrar(fabrica, mundo, {"n1": [
            {"filename": "a.geojson", "context": "drive"},
            {"filename": "b.geojson", "context": "drive"},
        ]})

    assert [c[2]["original_name"] for c in mundo.diario if c[0] == "emit"] == ["a.geojson", "b.geojson"]
    assert len(await _lines(fabrica, WorkspaceFile)) == 2
    assert any(
        r.getMessage() == "Falha ao notificar Drive para 'a.geojson': ws caiu" for r in caplog.records
    )


async def test_mixed_batch_goes_through_the_three_phases_in_order(fabrica, mundo, caplog):
    """Artifact in MinIO, local artifact, Drive already uploaded, new Drive and Drive
    that fell back to local — in a single payload."""
    await _seed(fabrica, WorkspaceFile(
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

    nomes = _names(mundo.diario)
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
    catalogo = next(wf for wf in await _lines(fabrica, WorkspaceFile) if wf.original_name == "e.geojson")
    assert (catalogo.s3_key, catalogo.content_location, catalogo.content_executor_id) == (None, "executor", EXECUTOR)
    assert catalogo.size == 4
    assert "run task-1: 4 artefato(s) registrado(s) (2 no Drive)." in [
        r.getMessage() for r in caplog.records if r.name == rrc.logger.name
    ]
