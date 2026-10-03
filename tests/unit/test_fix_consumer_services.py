# tests/unit/test_fix_consumer_services.py
"""
Tests for the S2 / B11 / B9 / B13 / B7 fixes on the server side.

Covers:
  - S2  : artifact/pin s3_key derived by the server (never the executor's).
  - B11 : rollback after a phase failure — the following phases keep running.
  - B9  : usage_daily ALWAYS accounted (failures included) and node_stats
          preserved when the executor sends empty stats.
  - B13 : run does not get stuck as a zombie in 'pending' and cancel_run closes a run without a host.
  - B7  : sign_csr_via_stepca fails instead of returning an empty ca_pem.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core import run_result_consumer as rrc
from app.models.artifact import Artifact
from app.models.models import WorkflowRun


# ── Helpers ───────────────────────────────────────────────────────────────────

def _end_ts() -> str:
    """Mesmo formato publicado pelo WS router (naive UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _make_run(status="running", workspace_id="ws-alvo", host="executor:ag-1") -> WorkflowRun:
    run = WorkflowRun(
        task_id=str(uuid4()),
        workflow_hash="wf-hash",
        workspace_id=workspace_id,
        status=status,
        node_stats={},
    )
    run.host = host
    run.start_time = datetime.now(timezone.utc)
    run.end_time = None
    run.duration_seconds = None
    run.error_message = None
    return run


def _result(value) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars(items: list) -> MagicMock:
    """Query result with `.scalars()`, answering both `.all()` AND `.first()`.

    Wiring only `all()` was a silent trap: a `MagicMock` accepts
    `.first()` without complaint and returns ANOTHER mock, so the code under test
    wrote to an object nobody inspects and the assertion ended up measuring
    nothing. It cost us a green test over code that did not do what it claimed.
    """
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    r.scalars.return_value.first.return_value = items[0] if items else None
    return r


def _all(rows: list) -> MagicMock:
    """Query result read directly via `.all()` (no `.scalars()`) — the artifact
    idempotency guard uses `select(Artifact.node_id, Artifact.filename)`."""
    r = MagicMock()
    r.all.return_value = rows
    return r


class _AsyncCtx:
    """Replaces AsyncSessionLocal() in the _consume_one tests."""

    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *_a):
        return False


def _rowcount(n: int) -> MagicMock:
    """Resultado de um UPDATE condicional (n=1 venceu a corrida, n=0 perdeu)."""
    r = MagicMock()
    r.rowcount = n
    return r


class _SavepointFalso:
    """`db.begin_nested()` as an async context manager.

    `AsyncMock` returns a coroutine, and `async with` on a coroutine blows up.
    `_upsert_pin_artifact` uses a savepoint to isolate the violation of the pin
    unique index when two runs race, so the double needs to enter and exit
    doing nothing.
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _mock_db(execute_results=None) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.begin_nested = MagicMock(return_value=_SavepointFalso())
    db.execute = AsyncMock(side_effect=list(execute_results or []))
    return db


# ── A corrida que o indice unico passou a expor ───────────────────────────────


class TestUpsertPinCorrida:
    """Two runs of the same workflow finishing together, with the unique index in place.

    Before the index, both inserted and the database ended up with two rows — the
    defect that the collapse remedies. With `uq_artifact_pin_por_no`, the second
    INSERT VIOLATES the constraint, and in Postgres an error like that poisons the
    whole transaction: this is the transaction that persists the run's RESULT, on
    the `job_result` path. Without the SAVEPOINT, swapping the duplicate for the
    constraint would have made the hot path worse instead of fixing it.
    """

    @pytest.mark.asyncio
    async def test_o_perdedor_da_corrida_reaponta_a_linha_vencedora(self):
        from sqlalchemy.exc import IntegrityError

        run = _make_run(workspace_id="ws-alvo")
        wf_obj = MagicMock()
        wf_obj.workspace_id = "ws-alvo"

        vencedora = MagicMock()
        vencedora.s3_key = "pin-cache/ws-alvo/run-do-outro/n1_pin.json"

        db = _mock_db([
            _scalars([]),            # 1a leitura: ninguem tinha inserido ainda
            _scalars([vencedora]),   # 2nd read, already after the violation
        ])
        db.flush = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("unique")))

        await rrc._upsert_pin_artifact(db, run, wf_obj, "n1", {
            "__pin_s3_key__": f"pin-cache/ws-alvo/{run.task_id}/n1_pin.json",
            "__pin_format__": "json",
            "__pin_filename__": "n1_pin.json",
        })

        # The other run's row is the truth; this call only repoints it to the
        # newest object — exactly what the UPDATE branch already did.
        assert vencedora.s3_key == f"pin-cache/ws-alvo/{run.task_id}/n1_pin.json"
        assert vencedora.run_id == run.task_id
        assert vencedora.workspace_id == "ws-alvo"

    @pytest.mark.asyncio
    async def test_a_violacao_nao_escapa_do_savepoint(self):
        """Sem `begin_nested`, a `IntegrityError` sobe e derruba o `job_result`."""
        from sqlalchemy.exc import IntegrityError

        run = _make_run(workspace_id="ws-alvo")
        wf_obj = MagicMock()
        wf_obj.workspace_id = "ws-alvo"
        db = _mock_db([_scalars([]), _scalars([MagicMock()])])
        db.flush = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("unique")))

        await rrc._upsert_pin_artifact(db, run, wf_obj, "n1", {
            "__pin_s3_key__": f"pin-cache/ws-alvo/{run.task_id}/n1_pin.json",
            "__pin_format__": "json",
            "__pin_filename__": "n1_pin.json",
        })

        db.begin_nested.assert_called_once()

    @pytest.mark.asyncio
    async def test_sem_corrida_o_insert_normal_acontece(self):
        """O caminho feliz continua sendo um INSERT, e nao um UPDATE disfarcado."""
        run = _make_run(workspace_id="ws-alvo")
        wf_obj = MagicMock()
        wf_obj.workspace_id = "ws-alvo"
        db = _mock_db([_scalars([])])

        await rrc._upsert_pin_artifact(db, run, wf_obj, "n1", {
            "__pin_s3_key__": f"pin-cache/ws-alvo/{run.task_id}/n1_pin.json",
            "__pin_format__": "json",
            "__pin_filename__": "n1_pin.json",
        })

        db.add.assert_called_once()
        assert db.add.call_args[0][0].node_id == "n1"


# ── S2: s3_key derivation ─────────────────────────────────────────────────────

class TestDeriveS3Key:

    def test_key_canonica(self):
        key = rrc._derive_s3_key("artifacts", "ws-1", "task-1", "saida.geojson")
        assert key == "artifacts/ws-1/task-1/saida.geojson"

    def test_path_traversal_no_filename_vira_basename(self):
        # '../../outro-ws/segredo.json' must not escape the workspace prefix.
        key = rrc._derive_s3_key("artifacts", "ws-1", "task-1", "../../outro/segredo.json")
        assert key == "artifacts/ws-1/task-1/segredo.json"

    def test_filename_vazio_rejeitado(self):
        assert rrc._derive_s3_key("artifacts", "ws-1", "task-1", "") is None
        assert rrc._derive_s3_key("artifacts", "ws-1", "task-1", "..") is None

    def test_workspace_ausente_rejeitado(self):
        assert rrc._derive_s3_key("artifacts", "", "task-1", "a.json") is None

    def test_charset_invalido_e_normalizado_nao_descartado(self):
        # A space is not in the S3-safe charset of _validate_agent_s3_key, but
        # discarding the whole artifact because of it made it vanish from the UI.
        assert (rrc._derive_s3_key("artifacts", "ws-1", "task-1", "nome com espaco.json")
                == "artifacts/ws-1/task-1/nome_com_espaco.json")

    def test_acento_vira_ascii(self):
        """Regression: a pt-BR label ('Relatorio 2026') is the common case, not the exception.

        slugify_label in the executor uses str.isalnum(), which PRESERVES accents; the
        server's S3-safe regex is pure ASCII. Rejecting here deleted the Artifact
        row and the run ended 'success' with nothing visible.
        """
        key = rrc._derive_s3_key("artifacts", "ws-1", "task-1", "Relatório_2026.geojson")
        assert key == "artifacts/ws-1/task-1/Relatorio_2026.geojson"
        assert rrc._derive_s3_key("artifacts", "ws-1", "task-1", "Parcelas_Ação.geojson") \
            == "artifacts/ws-1/task-1/Parcelas_Acao.geojson"

    def test_ponto_duplo_no_meio_do_nome_e_colapsado(self):
        # '..' em QUALQUER posicao e recusado por _validate_agent_s3_key.
        assert (rrc._derive_s3_key("artifacts", "ws-1", "task-1", "saida..final.json")
                == "artifacts/ws-1/task-1/saida.final.json")


class TestRegisterArtifactsIgnoraS3KeyDoExecutor:

    @pytest.mark.asyncio
    async def test_s3_key_forjada_e_substituida(self):
        """Executor sends a key from ANOTHER workspace — the server writes its own."""
        run = _make_run(workspace_id="ws-alvo")
        db = _mock_db([
            _result(None),      # _get_retention_days
            _scalars([]),       # keys already registered
        ])
        artifacts_meta = {
            "node-a": [{
                "filename": "resultado.geojson",
                "output_key": "res",
                "format": "geojson",
                # Attack vector: points to the victim's workspace.
                "s3_key": "artifacts/ws-vitima/run-alheio/dados-sigilosos.geojson",
                "credential_id": None,
            }],
        }

        with patch("app.core.storage.head", return_value=None), \
             patch("app.core.drive_events.emit_drive_event", new=AsyncMock()):
            await rrc._register_artifacts(db, run, artifacts_meta)

        added = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], Artifact)]
        assert len(added) == 1
        assert added[0].s3_key == f"artifacts/ws-alvo/{run.task_id}/resultado.geojson"
        assert added[0].workspace_id == "ws-alvo"

    @pytest.mark.asyncio
    async def test_nome_acentuado_ainda_gera_linha_artifact(self):
        """Regression: with an accent the artifact vanished from the UI (only a WARNING in the log)."""
        run = _make_run(workspace_id="ws-alvo")
        db = _mock_db([_result(None), _scalars([])])

        with patch("app.core.storage.head", return_value=None), \
             patch("app.core.drive_events.emit_drive_event", new=AsyncMock()):
            await rrc._register_artifacts(
                db, run, {"n1": [{"filename": "Área Útil.geojson", "format": "geojson"}]}
            )

        added = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], Artifact)]
        assert len(added) == 1
        assert added[0].s3_key == f"artifacts/ws-alvo/{run.task_id}/Area_Util.geojson"
        # the displayed filename must match the last segment of the key, otherwise the UI
        # promises a download with a name that does not exist in storage.
        assert added[0].filename == "Area_Util.geojson"

    @pytest.mark.asyncio
    async def test_key_ja_registrada_nao_duplica(self):
        run = _make_run(workspace_id="ws-alvo")
        db = _mock_db([
            _result(None),                       # _get_retention_days
            _all([("n1", "resultado.json")]),    # guard: (node_id, filename) already in the run
        ])

        with patch("app.core.storage.head", return_value=None), \
             patch("app.core.drive_events.emit_drive_event", new=AsyncMock()):
            await rrc._register_artifacts(
                db, run, {"n1": [{"filename": "resultado.json", "format": "json"}]}
            )

        assert not [c for c in db.add.call_args_list if isinstance(c.args[0], Artifact)]

    @pytest.mark.asyncio
    async def test_run_sem_workspace_nao_registra(self):
        run = _make_run(workspace_id=None)
        db = _mock_db([])
        await rrc._register_artifacts(db, run, {"n1": [{"filename": "x.json"}]})
        db.add.assert_not_called()


class TestSafePinRef:

    def test_pin_s3_key_do_executor_e_ignorada(self):
        run = _make_run(workspace_id="ws-alvo")
        ref = rrc._safe_pin_ref(run, "node-1", {
            "__pin_s3_key__": "pin-cache/ws-vitima/outro-run/node-1_pin.json",
            "__pin_format__": "json",
            "__pin_filename__": "qualquer.json",
        })
        assert ref["__pin_s3_key__"] == f"pin-cache/ws-alvo/{run.task_id}/node-1_pin.json"
        assert ref["__pin_filename__"] == "node-1_pin.json"

    def test_formato_desconhecido_rejeitado(self):
        run = _make_run()
        assert rrc._safe_pin_ref(run, "n1", {
            "__pin_s3_key__": "pin-cache/x/y/z", "__pin_format__": "../../etc",
        }) is None

    @pytest.mark.asyncio
    async def test_pinned_outputs_persistido_com_key_do_servidor(self):
        """A workspace forged in the key is neutralized — but the ref must belong to THIS
        run (current task_id in the key): pins written now are accepted and re-derived."""
        run = _make_run(workspace_id="ws-alvo")
        wf_obj = MagicMock()
        wf_obj.pinned_outputs = None
        wf_obj.workspace_id = "ws-alvo"
        db = _mock_db([
            _result(wf_obj),   # Workflow lookup
            _result(None),     # _upsert_pin_artifact: artefato de pin anterior
        ])
        stats = {"__updated_pinned_outputs__": {"n1": {
            "__pin_s3_key__": f"pin-cache/ws-vitima/{run.task_id}/n1_pin.json",
            "__pin_format__": "json",
        }}}

        with patch("sqlalchemy.orm.attributes.flag_modified"):
            await rrc._persist_pinned_outputs_if_present(db, run, stats)

        gravado = wf_obj.pinned_outputs["n1"]["__pin_s3_key__"]
        assert gravado == f"pin-cache/ws-alvo/{run.task_id}/n1_pin.json"

    @pytest.mark.asyncio
    async def test_pin_passthrough_de_run_antiga_e_ignorado(self):
        """A ref the executor merely passed along (written in a previous run) must NOT
        be re-persisted: `_safe_pin_ref` would derive the key with the CURRENT task_id,
        repointing the pin to an object that was never uploaded — a permanent 404,
        which was exactly the corruption cycle in production."""
        run = _make_run(workspace_id="ws-alvo")
        wf_obj = MagicMock()
        wf_obj.pinned_outputs = None
        wf_obj.workspace_id = "ws-alvo"
        db = _mock_db([_result(wf_obj)])
        stats = {"__updated_pinned_outputs__": {"n1": {
            "__pin_s3_key__": "pin-cache/ws-alvo/run-antiga/n1_pin.json",
            "__pin_format__": "json",
        }}}

        await rrc._persist_pinned_outputs_if_present(db, run, stats)

        assert wf_obj.pinned_outputs is None   # nada gravado
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_pin_descartado_se_o_workflow_mudou_de_workspace(self):
        """The workflow may have been moved while the run was going. The s3_keys are
        derived from `run.workspace_id` (the ORIGIN), so writing them would leave the
        workflow — already at the destination — with pins pointing to the old tenant,
        which the default executor could read on the next execution."""
        run = _make_run(workspace_id="ws-origem")
        wf_obj = MagicMock()
        wf_obj.pinned_outputs = None
        wf_obj.workspace_id = "ws-destino"          # movido durante a execucao
        db = _mock_db([_result(wf_obj)])
        stats = {"__updated_pinned_outputs__": {"n1": {
            "__pin_s3_key__": "pin-cache/ws-origem/x/n1_pin.json",
            "__pin_format__": "json",
        }}}

        await rrc._persist_pinned_outputs_if_present(db, run, stats)

        assert wf_obj.pinned_outputs is None
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_de_pin_realinha_o_workspace_do_artefato(self):
        """The lookup is by (workflow_hash, node_id) and does not filter by tenant: a row
        left over from before a move would be repointed to an object of the
        new workspace while keeping the old `workspace_id` — and the download uses the
        literal s3_key, serving destination data to someone who only reaches the origin."""
        run = _make_run(workspace_id="ws-destino")
        wf_obj = MagicMock(workspace_id="ws-destino")
        antigo = MagicMock(workspace_id="ws-origem")
        db = _mock_db([_scalars([antigo])])

        await rrc._upsert_pin_artifact(db, run, wf_obj, "n1", {
            "__pin_s3_key__": f"pin-cache/ws-destino/{run.task_id}/n1_pin.json",
            "__pin_format__": "json",
            "__pin_filename__": "n1_pin.json",
        })

        assert antigo.workspace_id == "ws-destino"
        assert antigo.s3_key == f"pin-cache/ws-destino/{run.task_id}/n1_pin.json"

    @pytest.mark.asyncio
    async def test_upsert_colapsa_linhas_de_pin_duplicadas(self):
        """`scalar_one_or_none()` here raised `MultipleResultsFound` — and it is
        THIS function that creates the second row.

        `artifacts` has no unique constraint on (workflow_hash, node_id,
        is_pinned): two runs of the same workflow finishing together find no row,
        each inserts its own, and from then on every read raised. In a route
        that is a 500; here it is worse — this is the `job_result` path, and the
        exception hangs the persistence of the run's result.

        The newest wins (the query orders by id desc) and the extras go.
        """
        run = _make_run(workspace_id="ws-1")
        wf_obj = MagicMock(workspace_id="ws-1")
        nova = MagicMock(workspace_id="ws-1")
        extra = MagicMock(workspace_id="ws-1")
        db = _mock_db([_scalars([nova, extra])])

        await rrc._upsert_pin_artifact(db, run, wf_obj, "n1", {
            "__pin_s3_key__": f"pin-cache/ws-1/{run.task_id}/n1_pin.json",
            "__pin_format__": "json",
            "__pin_filename__": "n1_pin.json",
        })

        # The first of the ordered list is the one that stays, updated.
        assert nova.s3_key == f"pin-cache/ws-1/{run.task_id}/n1_pin.json"
        # And the duplicate goes, instead of bringing down the whole phase.
        db.delete.assert_awaited_once_with(extra)
        db.add.assert_not_called()


# ── B11: rollback e isolamento de fases ───────────────────────────────────────

class TestRunPhase:

    @pytest.mark.asyncio
    async def test_falha_faz_rollback_e_refresh(self):
        run = _make_run()
        db = _mock_db([])

        async def _explode(*_a):
            raise RuntimeError("boom")

        ok = await rrc._run_phase(db, run, run.task_id, "teste", _explode)

        # Session recovered: the pipeline continues, but the phase counts as lost.
        assert ok == rrc.PHASE_FAILED
        db.rollback.assert_awaited_once()
        db.refresh.assert_awaited_once_with(run)

    @pytest.mark.asyncio
    async def test_fase_ok_nao_e_reportada_como_perda(self):
        async def _ok(*_a):
            return None

        assert await rrc._run_phase(_mock_db([]), _make_run(), "t", "teste", _ok) == rrc.PHASE_OK

    @pytest.mark.asyncio
    async def test_rollback_que_falha_interrompe_pipeline(self):
        run = _make_run()
        db = _mock_db([])
        db.rollback = AsyncMock(side_effect=RuntimeError("sessao morta"))

        async def _explode(*_a):
            raise RuntimeError("boom")

        assert await rrc._run_phase(db, run, run.task_id, "teste", _explode) == rrc.PHASE_FATAL

    @staticmethod
    def _payload_de(run) -> dict:
        return {
            "task_id": run.task_id,
            "status": "failed",
            "error_message": "erro",
            "end_time": _end_ts(),
            "stats": {},
        }

    @pytest.mark.asyncio
    async def test_falha_em_metricas_nao_impede_artefatos_nem_webhook(self):
        """B11 regression: an except without rollback brought down ALL the rest of the payload.

        The phase that failed is still REPORTED (PhaseFailure -> dead letter):
        isolating the failure must not mean consuming the item as if everything had
        gone fine.
        """
        run = _make_run(status="running")
        db = _mock_db([_result(run)])
        chamadas: list[str] = []

        async def _falha(*_a):
            chamadas.append("metricas")
            raise RuntimeError("PendingRollbackError simulado")

        def _ok_factory(nome):
            async def _fn(*_a):
                chamadas.append(nome)
            return _fn

        with patch.object(rrc, "_persist_metrics_if_present", _falha), \
             patch.object(rrc, "_upsert_usage_daily", _ok_factory("uso")), \
             patch.object(rrc, "_register_artifacts_if_present", _ok_factory("artefatos")), \
             patch.object(rrc, "_persist_pinned_outputs_if_present", _ok_factory("pins")), \
             patch.object(rrc, "_fire_notification_if_configured", _ok_factory("notificacao")):
            with pytest.raises(rrc.PhaseFailure) as exc:
                await rrc._process_result(db, self._payload_de(run))

        assert chamadas == ["uso", "metricas", "artefatos", "pins", "notificacao"]
        assert exc.value.labels == ["metricas"]
        db.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_todas_as_fases_ok_nao_levanta(self):
        run = _make_run(status="running")
        db = _mock_db([_result(run)])

        async def _ok(*_a):
            return None

        with patch.object(rrc, "_persist_metrics_if_present", _ok), \
             patch.object(rrc, "_upsert_usage_daily", _ok), \
             patch.object(rrc, "_register_artifacts_if_present", _ok), \
             patch.object(rrc, "_persist_pinned_outputs_if_present", _ok), \
             patch.object(rrc, "_fire_notification_if_configured", _ok):
            assert await rrc._process_result(db, self._payload_de(run)) is True

    @pytest.mark.asyncio
    async def test_sessao_morta_reporta_todas_as_fases_restantes(self):
        run = _make_run(status="running")
        db = _mock_db([_result(run)])
        db.rollback = AsyncMock(side_effect=RuntimeError("sessao morta"))

        async def _ok(*_a):
            return None

        async def _falha(*_a):
            raise RuntimeError("conexao derrubada")

        with patch.object(rrc, "_upsert_usage_daily", _ok), \
             patch.object(rrc, "_persist_metrics_if_present", _falha), \
             patch.object(rrc, "_register_artifacts_if_present", _ok), \
             patch.object(rrc, "_persist_pinned_outputs_if_present", _ok), \
             patch.object(rrc, "_fire_notification_if_configured", _ok):
            with pytest.raises(rrc.PhaseFailure) as exc:
                await rrc._process_result(db, self._payload_de(run))

        # Nothing ran after the session died — everything left is lost.
        assert exc.value.labels == ["metricas", "artefatos", "pins", "fontes", "notificacao"]


class TestConsumeOneDeadLetter:
    """B11: a lost phase must leave a reprocessable trail, not just a log."""

    @pytest.mark.asyncio
    async def test_phase_failure_vai_para_dead_letter_anotado(self):
        import json

        redis = AsyncMock()
        redis.brpop = AsyncMock(return_value=("run_results", json.dumps({"task_id": "t-1"})))
        redis.lpush = AsyncMock()

        async def _handler(_db, payload):
            raise rrc.PhaseFailure(payload["task_id"], ["artefatos", "notificacao"])

        with patch.object(rrc, "AsyncSessionLocal", lambda: _AsyncCtx(_mock_db([]))):
            await rrc._consume_one(redis, "run_results", _handler)

        fila, corpo = redis.lpush.await_args.args
        assert fila == rrc.QUEUE_DEAD_LETTER
        anotado = json.loads(corpo)
        assert anotado["task_id"] == "t-1"
        assert anotado["_phases_failed"] == ["artefatos", "notificacao"]

    @pytest.mark.asyncio
    async def test_sucesso_nao_gera_dead_letter(self):
        import json

        redis = AsyncMock()
        redis.brpop = AsyncMock(return_value=("run_results", json.dumps({"task_id": "t-1"})))
        redis.lpush = AsyncMock()

        async def _handler(_db, _payload):
            return True

        with patch.object(rrc, "AsyncSessionLocal", lambda: _AsyncCtx(_mock_db([]))):
            await rrc._consume_one(redis, "run_results", _handler)

        redis.lpush.assert_not_awaited()


# ── B9: usage_daily e node_stats ──────────────────────────────────────────────

class TestUsageDaily:
    # The upsert is atomic: UPDATE `coluna = coluna + delta` in SQL (rowcount decides
    # whether the day's row existed) and, when it did not exist (rowcount 0), an INSERT
    # under a savepoint. The fix for the real race (uq_usage_daily) and the increment
    # over an existing row live in the real-sqlite test `test_usage_daily_corrida.py`;
    # here, the mock covers the branch logic and the UTC date.

    @pytest.mark.asyncio
    async def test_falha_sem_metricas_conta_como_erro(self):
        """B9 regression: without metrics the upsert did not even run → error rate 0% forever.
        With no row for the day (atomic UPDATE with rowcount 0), the INSERT creates the 1st."""
        from app.models.run_metrics import UsageDaily

        run = _make_run(status="failed")
        run.duration_seconds = 2.0
        db = _mock_db([_rowcount(0)])

        await rrc._upsert_usage_daily(db, run, {}, True)

        criado = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], UsageDaily)]
        assert len(criado) == 1
        assert criado[0].total_runs == 1
        assert criado[0].failed_runs == 1
        assert criado[0].successful_runs == 0

    @pytest.mark.asyncio
    async def test_cancelado_nao_conta_como_falha(self):
        from app.models.run_metrics import UsageDaily

        run = _make_run(status="cancelled")
        db = _mock_db([_rowcount(0)])
        await rrc._upsert_usage_daily(db, run, {}, True)
        criado = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], UsageDaily)][0]
        assert criado.failed_runs == 0 and criado.successful_runs == 0 and criado.total_runs == 1

    @pytest.mark.asyncio
    async def test_reentrega_nao_reconta(self):
        run = _make_run(status="failed")
        db = _mock_db([])
        await rrc._upsert_usage_daily(db, run, {}, False)
        db.add.assert_not_called()
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_sem_workspace_nao_conta(self):
        run = _make_run(status="failed", workspace_id=None)
        db = _mock_db([])
        await rrc._upsert_usage_daily(db, run, {}, True)
        db.add.assert_not_called()
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_agregado_existente_atualiza_no_sql_sem_inserir(self):
        """The day's row already exists: the atomic UPDATE matches (rowcount 1) and NO
        INSERT runs — the increment is in SQL, no read-modify-write in Python."""
        run = _make_run(status="failed")
        db = _mock_db([_rowcount(1)])

        await rrc._upsert_usage_daily(db, run, {}, True)

        db.add.assert_not_called()
        db.begin_nested.assert_not_called()
        assert db.execute.await_count == 1  # a single UPDATE, no SELECT or INSERT

    @pytest.mark.asyncio
    async def test_usa_data_utc_e_nao_a_local(self):
        """Time zone: the row uses the UTC date (utc_now_naive), not the local `date.today()` —
        previously the count landed on the wrong day near midnight."""
        from app.models.run_metrics import UsageDaily

        run = _make_run(status="failed")
        db = _mock_db([_rowcount(0)])
        with patch.object(rrc, "utc_now_naive", return_value=datetime(2020, 6, 15, 3, 0)):
            await rrc._upsert_usage_daily(db, run, {}, True)

        criado = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], UsageDaily)][0]
        assert criado.date == datetime(2020, 6, 15, 3, 0).date()


class TestUpdateRunStatus:

    @pytest.mark.asyncio
    async def test_stats_vazio_preserva_node_stats(self):
        run = _make_run()
        run.node_stats = {"n1": {"status": "success"}}
        db = _mock_db([])
        await rrc._update_run_status(db, run, {
            "task_id": run.task_id, "status": "failed", "stats": {},
            "end_time": _end_ts(),
        })
        assert run.node_stats == {"n1": {"status": "success"}}
        assert run.status == "failed"

    @pytest.mark.asyncio
    async def test_stats_parcial_sobrescreve(self):
        run = _make_run()
        run.node_stats = {"n1": {"status": "success"}}
        db = _mock_db([])
        parcial = {"n1": {"status": "success"}, "n2": {"status": "error"}}
        await rrc._update_run_status(db, run, {
            "task_id": run.task_id, "status": "failed", "stats": parcial,
            "end_time": _end_ts(),
        })
        assert run.node_stats == parcial


# ── B13: run zumbi em 'pending' ───────────────────────────────────────────────

class TestDispatchNaoDeixaRunPendente:

    @pytest.mark.asyncio
    async def test_excecao_inesperada_marca_run_failed(self):
        from app.services import workflow_execution_service as wes

        wf = MagicMock()
        wf.id_hash = "wf-1"
        wf.workspace_id = "ws-1"
        wf.pinned_outputs = None
        wf.pin_metadata = None
        # _close_orphan_dispatch closes the run with a conditional UPDATE (won:
        # rowcount 1) and accounts it in usage_daily (B9): the atomic UPDATE of the
        # day's aggregate does not match (rowcount 0) and a new row is created.
        db = _mock_db([_rowcount(1), _rowcount(0)])
        ag = MagicMock()
        ag.id_hash = "ag-1"
        ag.name = "executor"
        ag.public_key = "PEM"

        with patch.object(wes, "inject_credentials", new=AsyncMock(side_effect=TypeError("payload invalido"))):
            with pytest.raises(TypeError):
                await wes._dispatch_job(wf, {"nodes": []}, [ag], {}, False, db=db)

        runs = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], WorkflowRun)]
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert "payload invalido" in (runs[0].error_message or "")
        assert runs[0].end_time is not None

    @pytest.mark.asyncio
    async def test_falha_de_despacho_entra_no_usage_daily(self):
        """B9: a run closed OUTSIDE the run_results queue must also be counted."""
        from app.models.run_metrics import UsageDaily
        from app.services import workflow_execution_service as wes

        wf = MagicMock()
        wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
        wf.pinned_outputs = None
        wf.pin_metadata = None
        db = _mock_db([_rowcount(1), _rowcount(0)])   # conditional close + day's aggregate
        ag = MagicMock()
        ag.id_hash, ag.name, ag.public_key = "ag-1", "executor", "PEM"

        with patch.object(wes, "inject_credentials", new=AsyncMock(side_effect=TypeError("boom"))):
            with pytest.raises(TypeError):
                await wes._dispatch_job(wf, {"nodes": []}, [ag], {}, False, db=db)

        usos = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], UsageDaily)]
        assert len(usos) == 1
        assert usos[0].total_runs == 1 and usos[0].failed_runs == 1
        assert usos[0].workspace_id == "ws-1"

    @pytest.mark.asyncio
    async def test_send_job_que_estoura_faz_failover(self):
        """A TypeError coming from send_job was fatal — now it counts as a refusal."""
        from app.services import workflow_execution_service as wes

        wf = MagicMock()
        wf.id_hash = "wf-1"
        wf.workspace_id = "ws-1"
        wf.pinned_outputs = None
        wf.pin_metadata = None
        # Unico execute do caminho feliz: o UPDATE condicional pending → running.
        db = _mock_db([_rowcount(1)])
        ag1, ag2 = MagicMock(), MagicMock()
        ag1.id_hash, ag1.name, ag1.public_key = "ag-1", "a1", "PEM"
        ag2.id_hash, ag2.name, ag2.public_key = "ag-2", "a2", "PEM"

        async def _send(executor_id, _msg):
            if executor_id == "ag-1":
                raise TypeError("is_full() quebrado")
            return True

        with patch.object(wes, "inject_credentials", new=AsyncMock(side_effect=lambda d, **k: d)), \
             patch.object(wes, "build_job_message", return_value={"ciphertext": ""}), \
             patch.object(wes, "executor_registry") as reg:
            reg.send_job = AsyncMock(side_effect=_send)
            result = await wes._dispatch_job(wf, {"nodes": []}, [ag1, ag2], {}, False, db=db)

        runs = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], WorkflowRun)]
        assert result.id == runs[0].task_id
        assert runs[0].status == "running"
        assert runs[0].host == "executor:ag-2"


class TestCancelRunPendente:

    @pytest.mark.asyncio
    async def test_run_pending_sem_host_e_cancelado_localmente(self):
        from app.services import workflow_execution_service as wes

        run = _make_run(status="pending", host=None)
        db = _mock_db([
            _result(run),     # SELECT of the run
            _rowcount(1),     # UPDATE condicional venceu
            _result(None),    # day's usage_daily (B9)
        ])

        # `como_admin=True` is not a lazy shortcut: these cases are about the MECHANICS
        # of cancellation (pending × delivered, race with the dispatch), and setting up
        # workspace membership in each one would only pull the test away from what it
        # measures. Authorization has its own coverage in test_fixes_seguranca_opcao_c.py.
        outcome = await wes.cancel_run(db, run.task_id, user_id="irrelevante", como_admin=True)

        assert outcome == "cancelled"
        assert run.status == "cancelled"
        assert run.end_time is not None
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_fechamento_local_e_condicional(self):
        """The UPDATE must carry the guard, otherwise the race with the dispatch comes back.

        The guard is just `status='pending'`: the host now goes in already in the run's
        INSERT (to save a commit before sending), so what distinguishes "the
        executor already has the job" from "the job has not left the server" is the status.
        """
        from app.services import workflow_execution_service as wes

        run = _make_run(status="pending", host="executor:ag-1")
        db = _mock_db([_result(run), _rowcount(1), _result(None)])

        assert await wes.cancel_run(db, run.task_id, user_id="irrelevante", como_admin=True) == "cancelled"

        stmt = str(db.execute.await_args_list[1].args[0])
        assert "UPDATE workflow_runs" in stmt
        assert "status = :status_1" in stmt   # WHERE status='pending'

    @pytest.mark.asyncio
    async def test_corrida_perdida_para_o_dispatch_vira_pedido_ao_executor(self):
        """Regression: the local cancel overwrote the run that the dispatch had just
        delivered — the user saw 'cancelled' and the workflow ran to the end."""
        from app.services import workflow_execution_service as wes

        run = _make_run(status="pending", host=None)

        async def _refresh(obj):
            # O dispatch venceu entre o SELECT e o UPDATE condicional.
            obj.host = "executor:ag-9"
            obj.status = "running"

        db = _mock_db([_result(run), _rowcount(0)])
        db.refresh = AsyncMock(side_effect=_refresh)

        with patch.object(wes, "executor_registry") as reg:
            reg.send_json = AsyncMock(return_value=True)
            outcome = await wes.cancel_run(db, run.task_id, user_id="irrelevante", como_admin=True)

        assert outcome == "requested"
        assert run.status == "running"  # was not overwritten to 'cancelled'
        reg.send_json.assert_awaited_once_with(
            "ag-9", {"type": "cancel", "job_id": run.task_id}
        )

    @pytest.mark.asyncio
    async def test_dispatch_aborta_running_se_run_foi_cancelado(self):
        """Symmetric: if the cancel won, the dispatch does not resurrect the run."""
        from app.services import workflow_execution_service as wes

        wf = MagicMock()
        wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
        wf.pinned_outputs = None
        wf.pin_metadata = None
        db = _mock_db([_rowcount(0)])  # UPDATE pending → running did not match
        ag = MagicMock()
        ag.id_hash, ag.name, ag.public_key = "ag-1", "a1", "PEM"

        with patch.object(wes, "inject_credentials", new=AsyncMock(side_effect=lambda d, **k: d)), \
             patch.object(wes, "build_job_message", return_value={"ciphertext": ""}), \
             patch.object(wes, "executor_registry") as reg:
            reg.send_job = AsyncMock(return_value=True)
            reg.send_json = AsyncMock(return_value=True)
            result = await wes._dispatch_job(wf, {"nodes": []}, [ag], {}, False, db=db)

        runs = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], WorkflowRun)]
        assert runs[0].status == "pending"  # never became 'running'
        reg.send_json.assert_awaited_once_with(
            "ag-1", {"type": "cancel", "job_id": result.id}
        )

    @pytest.mark.asyncio
    async def test_run_terminal_continua_idempotente(self):
        from app.services import workflow_execution_service as wes

        run = _make_run(status="success", host=None)
        db = _mock_db([_result(run)])
        assert await wes.cancel_run(db, run.task_id, user_id="irrelevante", como_admin=True) == "already_finished"


# ── B7: an empty ca_pem never leaves the server ───────────────────────────────

def _self_signed_pem() -> str:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from datetime import timedelta

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


class _FakeResp:
    status_code = 201

    def __init__(self, body):
        self._body = body
        self.text = ""

    def json(self):
        return self._body


class _FakeClient:
    def __init__(self, body):
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, *_a, **_k):
        return _FakeResp(self._body)


class TestSignCsrRootCert:

    @pytest.mark.asyncio
    async def test_root_cert_ausente_levanta_em_vez_de_ca_pem_vazio(self, tmp_path, monkeypatch):
        from app.services import executor_enrollment_service as ees

        cert_pem = _self_signed_pem()
        monkeypatch.setattr(ees, "STEPCA_ROOT_CERT_PATH", str(tmp_path / "nao-existe.crt"))
        monkeypatch.setattr(ees, "_build_stepca_token", lambda *a, **k: "tok")

        fake_httpx = MagicMock()
        fake_httpx.AsyncClient = lambda *a, **k: _FakeClient({"crt": cert_pem, "ca": cert_pem})
        fake_httpx.HTTPError = Exception
        monkeypatch.setattr(ees, "httpx", fake_httpx)

        with pytest.raises(RuntimeError, match="Root cert"):
            await ees.sign_csr_via_stepca("csr", "ag-1")

    @pytest.mark.asyncio
    async def test_root_cert_vazio_levanta(self, tmp_path, monkeypatch):
        from app.services import executor_enrollment_service as ees

        cert_pem = _self_signed_pem()
        vazio = tmp_path / "root.crt"
        vazio.write_text("")
        monkeypatch.setattr(ees, "STEPCA_ROOT_CERT_PATH", str(vazio))
        monkeypatch.setattr(ees, "_build_stepca_token", lambda *a, **k: "tok")

        fake_httpx = MagicMock()
        fake_httpx.AsyncClient = lambda *a, **k: _FakeClient({"crt": cert_pem, "ca": cert_pem})
        fake_httpx.HTTPError = Exception
        monkeypatch.setattr(ees, "httpx", fake_httpx)

        with pytest.raises(RuntimeError, match="Root cert"):
            await ees.sign_csr_via_stepca("csr", "ag-1")

    @pytest.mark.asyncio
    async def test_root_cert_valido_devolve_bundle(self, tmp_path, monkeypatch):
        from app.services import executor_enrollment_service as ees

        cert_pem = _self_signed_pem()
        root = tmp_path / "root.crt"
        root.write_text(cert_pem)
        monkeypatch.setattr(ees, "STEPCA_ROOT_CERT_PATH", str(root))
        monkeypatch.setattr(ees, "_build_stepca_token", lambda *a, **k: "tok")

        fake_httpx = MagicMock()
        fake_httpx.AsyncClient = lambda *a, **k: _FakeClient({"crt": cert_pem, "ca": cert_pem})
        fake_httpx.HTTPError = Exception
        monkeypatch.setattr(ees, "httpx", fake_httpx)

        bundle = await ees.sign_csr_via_stepca("csr", "ag-1")
        assert bundle["ca_pem"] == cert_pem
        assert bundle["cert_pem"] == cert_pem

    def test_token_e_leitura_do_root_cert_saem_do_event_loop(self):
        """B-enroll: the PBKDF2 (via _build_stepca_token) and the root cert read
        run in asyncio.to_thread, not on the event loop that serves the executors'
        WebSockets. The effect is about timing (not observable in a test; RedisFalso/
        doubles have no clock), so the proof is in the SOURCE CODE — the same pattern
        as the sandbox/timeout PR. The three tests above already run via to_thread and
        prove that behavior is preserved. Mutation: removing either of the two wraps
        breaks exactly this test."""
        import inspect

        from app.services import executor_enrollment_service as ees

        fonte = inspect.getsource(ees.sign_csr_via_stepca)
        assert "asyncio.to_thread(_build_stepca_token" in fonte
        assert "asyncio.to_thread(Path(STEPCA_ROOT_CERT_PATH).read_text" in fonte
