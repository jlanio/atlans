# tests/unit/test_workflow_service.py
"""Unit tests for app/services/workflow_service.py."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.workflow import Workflow
from app.models.executor import Executor
from app.core.exceptions import (
    NoExecutorAvailableError,
    WorkflowNotFoundError,
    WorkflowInactiveError,
    WorkflowDecryptionError,
)
from app.services.workflow_service import WorkflowService, DispatchResult, _safe_pinned_outputs, _has_substantial_changes
from app.crud.workflow_crud import WorkflowCRUD


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_workflow(
    name: str = "wf-test",
    flag_ative: bool = True,
    workspace_id: str | None = None,
) -> Workflow:
    wf = Workflow(name=name, definition={"nodes": [], "edges": []}, flag_ative=flag_ative)
    wf.id_hash = str(uuid4())
    wf.workspace_id = workspace_id
    wf.pinned_outputs = None
    wf.pin_metadata = None
    return wf


def _make_agent(status: str = "active", public_key: str = "VALID_PEM") -> Executor:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    priv = X25519PrivateKey.generate()
    pub_pem = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()

    ag = Executor(
        name="executor-test", executor_type="dedicated", status=status,
        capabilities=[], max_concurrent_jobs=4, max_queue_size=50,
    )
    ag.id_hash = str(uuid4())
    ag.public_key = pub_pem if public_key == "VALID_PEM" else public_key
    return ag


def _make_db_result(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_scalars_result(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def _mock_disabled_and_subworkflow_helpers():
    """Mocks disabled_names and collect_subworkflow_definitions_recursive so the
    existing start_analysis tests do not hit the DB. The tests specific to that
    behavior live in test_workflow_service_dispatch.py."""
    with patch(
        "app.services.disabled_nodes_service.disabled_names",
        new=AsyncMock(return_value=set()),
    ):
        with patch(
            "flow.utils.workflow_contract.collect_subworkflow_definitions_recursive",
            new=AsyncMock(return_value={}),
        ):
            yield


@pytest.fixture
def service(mock_db):
    """WorkflowService com crud mockado via AsyncMock(spec=WorkflowCRUD)."""
    svc = WorkflowService(mock_db)
    svc.crud = AsyncMock(spec=WorkflowCRUD)
    svc.crud.db = mock_db
    return svc


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock(return_value=True)
    r.lpush = AsyncMock(return_value=1)
    return r


@pytest.fixture
def patched_redis(mock_redis):
    """Patcha o pool Redis centralizado."""
    with patch("app.core.redis._pool", mock_redis):
        yield mock_redis


@pytest.fixture
def sample_workflow():
    return _make_workflow()


@pytest.fixture
def sample_agent():
    return _make_agent()


# ── TestSafePinnedOutputs ─────────────────────────────────────────────────────

class TestSafePinnedOutputs:

    def test_none_returns_empty_dict(self):
        assert _safe_pinned_outputs(None) == {}

    def test_empty_returns_empty_dict(self):
        assert _safe_pinned_outputs({}) == {}

    def test_with_pin_s3_key_preserves(self):
        """A node with __pin_s3_key__ and pin_metadata should be preserved intact."""
        raw = {"n1": {"__pin_s3_key__": "s3://bucket/key"}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert result == {"n1": {"__pin_s3_key__": "s3://bucket/key"}}

    def test_empty_dict_with_metadata_preserved(self):
        """A node with an empty dict and pin_metadata should be preserved (awaiting auto-pin)."""
        raw = {"n1": {}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert result == {"n1": {}}

    def test_raw_data_with_metadata_returns_empty_dict(self):
        """Raw data with metadata should be replaced with {} for auto-pin."""
        raw = {"n1": {"column_a": [1, 2, 3], "column_b": ["x", "y"]}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert result == {"n1": {}}

    def test_without_metadata_ignores_entry(self):
        """Nodes in pinned_outputs without matching pin_metadata should be ignored."""
        raw = {"n1": {"__pin_s3_key__": "s3://key"}, "n2": {}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert "n1" in result
        assert "n2" not in result

    def test_empty_metadata_discards_every_orphan(self):
        """Without metadata NO entry gets through — not even the one with `__pin_s3_key__`.

        This test used to say the opposite (the name promised discarding and the
        assertions required preservation, under the label "backward
        compatibility"). What it locked in was a defect: the orphan with
        `__pin_s3_key__` makes the executor skip the node, and validity is read
        from `pin_metadata[node_id]` — without metadata there is no
        `expires_at`, so it **never expires**.
        """
        raw = {"n1": {}, "n2": {"__pin_s3_key__": "s3://key"}}
        assert _safe_pinned_outputs(raw, {}) == {}

    def test_metadata_none_discards_every_orphan(self):
        """`None` is the same case as `{}` — and it is the value unpin writes."""
        raw = {"n1": {"__pin_s3_key__": "s3://key"}}
        assert _safe_pinned_outputs(raw, None) == {}

    def test_unpinning_one_node_does_not_revive_another_pin(self):
        """The regression this fix exists to prevent.

        With `{A, B}` in `pinned_outputs` and only `A` in `pin_metadata`, B is an
        orphan and is left out — that already held. The problem showed up in the
        next step: unpinning A writes `pin_metadata = None`
        (`pin_service.unpin_output`), the column empties, and the previous
        version went back to sending B to the executor. Unpinning one node
        resurrected another's pin, with a cache that never expires.
        """
        raw = {"A": {"__pin_s3_key__": "s3://a"}, "B": {"__pin_s3_key__": "s3://b"}}

        antes = _safe_pinned_outputs(raw, {"A": {"pinned_at": "2026-01-01"}})
        assert set(antes) == {"A"}, "B é órfã e nunca deveria ter passado"

        # Unpinning A leaves the column like this:
        depois = _safe_pinned_outputs(raw, None)
        assert depois == {}, "B não pode voltar só porque a metadata esvaziou"


# ── TestHasSubstantialChanges ─────────────────────────────────────────────────

class TestHasSubstantialChanges:

    def _def(self, nodes=None, edges=None):
        return {"nodes": nodes or [], "edges": edges or []}

    def _node(self, nid: str, props: dict = None, position: dict = None):
        # FLAT format of the persisted/PUT definition (`properties` at the top of the
        # node), not ReactFlow's `data.properties`. It is the real production
        # shape — and the only one that exercises the bug: reading
        # `data.properties` from a flat node on each side saw {} vs {} and a
        # property-only edit never became a version.
        return {
            "id": nid,
            "properties": props or {},
            "position": position or {"x": 0, "y": 0},
        }

    def _edge(self, src: str, tgt: str, sh: str = "out", th: str = "in"):
        return {"source": src, "target": tgt, "sourceHandle": sh, "targetHandle": th}

    def test_identical_nodes_returns_false(self):
        d = self._def(nodes=[self._node("n1", {"key": "val"})])
        assert _has_substantial_changes(d, d) is False

    def test_added_node_returns_true(self):
        old = self._def(nodes=[self._node("n1")])
        new = self._def(nodes=[self._node("n1"), self._node("n2")])
        assert _has_substantial_changes(old, new) is True

    def test_removed_node_returns_true(self):
        old = self._def(nodes=[self._node("n1"), self._node("n2")])
        new = self._def(nodes=[self._node("n1")])
        assert _has_substantial_changes(old, new) is True

    def test_added_edge_returns_true(self):
        nodes = [self._node("n1"), self._node("n2")]
        old = self._def(nodes=nodes, edges=[])
        new = self._def(nodes=nodes, edges=[self._edge("n1", "n2")])
        assert _has_substantial_changes(old, new) is True

    def test_removed_edge_returns_true(self):
        nodes = [self._node("n1"), self._node("n2")]
        old = self._def(nodes=nodes, edges=[self._edge("n1", "n2")])
        new = self._def(nodes=nodes, edges=[])
        assert _has_substantial_changes(old, new) is True

    def test_changed_property_returns_true(self):
        old = self._def(nodes=[self._node("n1", props={"k": "old_value"})])
        new = self._def(nodes=[self._node("n1", props={"k": "new_value"})])
        assert _has_substantial_changes(old, new) is True

    def test_only_position_changed_returns_false(self):
        """Moving a node on the canvas (position) is not a substantial change."""
        old = self._def(nodes=[self._node("n1", props={"k": "v"}, position={"x": 0, "y": 0})])
        new = self._def(nodes=[self._node("n1", props={"k": "v"}, position={"x": 500, "y": 300})])
        assert _has_substantial_changes(old, new) is False

    def test_empty_definitions_returns_false(self):
        assert _has_substantial_changes({}, {}) is False


# ── TestCreateWorkflow ────────────────────────────────────────────────────────

class TestCreateWorkflow:

    @pytest.mark.asyncio
    async def test_success_without_schedule(self, service, sample_workflow):
        """Should encrypt and create the workflow; without a ScheduleTrigger, no schedule is created."""
        definition = {"nodes": [], "edges": []}
        service.crud.create = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.encrypt_workflow_connections", return_value=definition) as enc, \
             patch("app.services.workflow_service.extract_schedule_node", return_value=None):
            result = await service.create_workflow("my-wf", definition, created_by_id="usr-1")

        enc.assert_called_once_with(definition)
        service.crud.create.assert_called_once()
        assert result is sample_workflow

    @pytest.mark.asyncio
    async def test_stamps_author_on_create(self, service, sample_workflow):
        """The user's created_by_id/updated_by_id reach the INSERT — without that the
        listing would never show 'criado há X por Y' (created X ago by Y) (the
        POST /workflows router stopped passing them on and the fields were born
        null)."""
        definition = {"nodes": [], "edges": []}
        service.crud.create = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.encrypt_workflow_connections", return_value=definition), \
             patch("app.services.workflow_service.extract_schedule_node", return_value=None):
            await service.create_workflow(
                "wf", definition, workspace_id="ws-1",
                created_by_id="usr-1", updated_by_id="usr-1",
            )

        _, kwargs = service.crud.create.call_args
        assert kwargs.get("created_by_id") == "usr-1"
        assert kwargs.get("updated_by_id") == "usr-1"
        assert kwargs.get("workspace_id") == "ws-1"

    @pytest.mark.asyncio
    async def test_success_with_schedule_trigger(self, service, sample_workflow):
        """Should call apply_schedule_if_needed when the definition contains a ScheduleTrigger."""
        definition = {"nodes": [{"type": "trigger", "name": "ScheduleTrigger"}], "edges": []}
        service.crud.create = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.encrypt_workflow_connections", return_value=definition), \
             patch("app.services.workflow_service.extract_schedule_node", return_value={"type": "trigger"}), \
             patch("app.services.workflow_service.apply_schedule_if_needed", new_callable=AsyncMock) as apply_sched:
            await service.create_workflow("scheduled-wf", definition, created_by_id="usr-1")

        apply_sched.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_failure_logs_warning_does_not_fail(self, service, sample_workflow):
        """A scheduling failure should not prevent the workflow from being created."""
        definition = {"nodes": [{"type": "trigger"}], "edges": []}
        service.crud.create = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.encrypt_workflow_connections", return_value=definition), \
             patch("app.services.workflow_service.extract_schedule_node", return_value={"type": "trigger"}), \
             patch("app.services.workflow_service.apply_schedule_if_needed", side_effect=Exception("Redis down")):
            # Should not propagate the exception
            result = await service.create_workflow("wf", definition, created_by_id="usr-1")

        assert result is sample_workflow


# ── TestGetWorkflowByHash ─────────────────────────────────────────────────────

class TestGetWorkflowByHash:

    @pytest.mark.asyncio
    async def test_found_with_decryption(self, service, sample_workflow):
        """Should decrypt the definition when returning the workflow."""
        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)
        decrypted_def = {"nodes": [{"id": "n1"}], "edges": []}

        with patch("app.services.workflow_service.decrypt_workflow_connections", return_value=decrypted_def) as dec:
            result = await service.get_workflow_by_hash(sample_workflow.id_hash)

        dec.assert_called_once()
        assert result.definition == decrypted_def

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found_error(self, service):
        """A nonexistent workflow should raise WorkflowNotFoundError."""
        service.crud.get_by_hash = AsyncMock(return_value=None)

        with pytest.raises(WorkflowNotFoundError):
            await service.get_workflow_by_hash("nao-existe")

    @pytest.mark.asyncio
    async def test_decryption_failure_raises_decryption_error(self, service, sample_workflow):
        """A decryption failure should raise WorkflowDecryptionError."""
        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.decrypt_workflow_connections", side_effect=Exception("chave inválida")):
            with pytest.raises(WorkflowDecryptionError):
                await service.get_workflow_by_hash(sample_workflow.id_hash)


# ── TestStartAnalysis ─────────────────────────────────────────────────────────

class TestStartAnalysis:

    @pytest.mark.asyncio
    async def test_idempotency_hit_returns_without_running(self, service, patched_redis):
        """With an existing idempotency_key in Redis, it should not execute again."""
        patched_redis.get = AsyncMock(return_value="existing-job-id")
        service._load_workflow = AsyncMock()  # must not be called

        result = await service.start_analysis(
            "wf-hash", idempotency_key="key-already-used"
        )

        assert result.id == "existing-job-id"
        service._load_workflow.assert_not_called()

    @pytest.mark.asyncio
    async def test_without_idempotency_key_does_not_query_redis(self, service, patched_redis, sample_workflow, sample_agent):
        """Without an idempotency_key, Redis should not be queried for idempotency."""
        service._load_workflow = AsyncMock(return_value=(sample_workflow, {"nodes": [], "edges": []}))
        service._resolve_candidates = AsyncMock(return_value=[sample_agent])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="job-new"))

        await service.start_analysis("wf-hash")

        patched_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_workflow_not_found(self, service, patched_redis):
        """A nonexistent workflow should propagate WorkflowNotFoundError."""
        service._load_workflow = AsyncMock(side_effect=WorkflowNotFoundError("não existe"))

        with pytest.raises(WorkflowNotFoundError):
            await service.start_analysis("nao-existe")

    @pytest.mark.asyncio
    async def test_inactive_workflow(self, service, patched_redis):
        """An inactive workflow should propagate WorkflowInactiveError."""
        service._load_workflow = AsyncMock(side_effect=WorkflowInactiveError("inativo"))

        with pytest.raises(WorkflowInactiveError):
            await service.start_analysis("wf-inativo")

    @pytest.mark.asyncio
    async def test_decryption_error(self, service, patched_redis):
        """A decryption error should propagate WorkflowDecryptionError."""
        service._load_workflow = AsyncMock(side_effect=WorkflowDecryptionError("chave inválida"))

        with pytest.raises(WorkflowDecryptionError):
            await service.start_analysis("wf-bad-key")

    @pytest.mark.asyncio
    async def test_success_returns_dispatch_result_with_uuid(
        self, service, patched_redis, sample_workflow, sample_agent
    ):
        """A successful execution should return a DispatchResult with a UUID job_id and call Redis.lpush."""
        service._load_workflow = AsyncMock(return_value=(sample_workflow, {"nodes": [], "edges": []}))
        service._resolve_candidates = AsyncMock(return_value=[sample_agent])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="job-uuid-abc"))

        result = await service.start_analysis("wf-hash")

        assert result.id == "job-uuid-abc"

    @pytest.mark.asyncio
    async def test_success_with_idempotency_key_writes_to_redis(
        self, service, patched_redis, sample_workflow, sample_agent
    ):
        """With a new idempotency_key, it should write the job_id to Redis after dispatch."""
        patched_redis.get = AsyncMock(return_value=None)  # chave nova
        service._load_workflow = AsyncMock(return_value=(sample_workflow, {"nodes": [], "edges": []}))
        service._resolve_candidates = AsyncMock(return_value=[sample_agent])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="job-new-id"))

        await service.start_analysis("wf-hash", idempotency_key="new-key")

        patched_redis.set.assert_called_once()
        call_args = patched_redis.set.call_args
        assert "new-key" in call_args[0][0] or "new-key" in str(call_args)


# ── TestResolveCandidates ─────────────────────────────────────────────────────

class TestResolveCandidates:

    @pytest.mark.asyncio
    async def test_empty_pool_503(self, service, mock_db, sample_workflow):
        """With no default executors available, it should return HTTP 503."""
        sample_workflow.workspace_id = None

        with patch("app.services.workflow_execution_service.get_default_agents", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(NoExecutorAvailableError):
                await service._resolve_candidates(sample_workflow)

    @pytest.mark.asyncio
    async def test_all_offline_503(self, service, mock_db, sample_workflow):
        """All defaults offline should raise NoExecutorAvailableError."""
        sample_workflow.workspace_id = None
        ag1 = _make_agent(status="active")
        ag2 = _make_agent(status="active")

        with patch("app.services.workflow_execution_service.get_default_agents", new_callable=AsyncMock, return_value=[ag1, ag2]), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.is_online = AsyncMock(return_value=False)
            mock_registry.presence_or_unknown = AsyncMock(return_value=False)

            with pytest.raises(NoExecutorAvailableError):
                await service._resolve_candidates(sample_workflow)

    @pytest.mark.asyncio
    async def test_returns_agents_sorted_by_load(self, service, mock_db, sample_workflow):
        """Should return online executors ordered by lowest load."""
        sample_workflow.workspace_id = None
        ag_busy = _make_agent(status="active")
        ag_idle = _make_agent(status="active")

        cap = {"running": 0, "queued": 0, "max_concurrent": 4, "max_queue": 50}

        async def read_capacities(ids):
            return {i: dict(cap) for i in ids}

        # The load is the one counted in the database: 5 in-flight runs on the busy
        # one, none on the idle one. The count runs on the session's connection,
        # in a savepoint — which the fixture's AsyncMock cannot open as a
        # context manager.
        conexao = MagicMock()
        conexao.execute = AsyncMock(return_value=MagicMock(
            all=MagicMock(return_value=[(f"executor:{ag_busy.id_hash}", 5)]),
        ))
        mock_db.connection = AsyncMock(return_value=conexao)

        with patch("app.services.workflow_execution_service.get_default_agents", new_callable=AsyncMock, return_value=[ag_busy, ag_idle]), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.is_online = AsyncMock(return_value=True)
            mock_registry.presence_or_unknown = AsyncMock(return_value=True)
            mock_registry.read_capacities = read_capacities

            candidates = await service._resolve_candidates(sample_workflow)

        assert len(candidates) == 2
        assert candidates[0].id_hash == ag_idle.id_hash  # menor carga primeiro

    @pytest.mark.asyncio
    async def test_dedicated_workspace_takes_priority(self, service, mock_db, sample_workflow):
        """The workspace's dedicated executor should come before the default pool."""
        sample_workflow.workspace_id = "ws-001"
        dedicated = _make_agent(status="active")
        default = _make_agent(status="active")

        # Workspace ⋈ Executor became a single join — one query, one result.
        mock_db.execute.side_effect = [_make_db_result(dedicated)]

        with patch("app.services.workflow_execution_service.get_default_agents", new_callable=AsyncMock, return_value=[default]), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.is_online = AsyncMock(return_value=True)
            mock_registry.presence_or_unknown = AsyncMock(return_value=True)

            candidates = await service._resolve_candidates(sample_workflow)

        assert candidates[0].id_hash == dedicated.id_hash

    @pytest.mark.asyncio
    async def test_failover_dedicated_offline_uses_pool(self, service, mock_db, sample_workflow):
        """If the dedicated executor is offline, it should fall back to the default pool."""
        sample_workflow.workspace_id = "ws-001"
        dedicated = _make_agent(status="active")
        default = _make_agent(status="active")

        mock_db.execute.side_effect = [_make_db_result(dedicated)]

        async def is_online(executor_id):
            return executor_id != dedicated.id_hash  # dedicado offline, default online

        with patch("app.services.workflow_execution_service.get_default_agents", new_callable=AsyncMock, return_value=[default]), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.is_online = AsyncMock(side_effect=is_online)
            mock_registry.presence_or_unknown = AsyncMock(side_effect=is_online)

            candidates = await service._resolve_candidates(sample_workflow)

        assert len(candidates) == 1
        assert candidates[0].id_hash == default.id_hash


# ── TestDispatchJob ───────────────────────────────────────────────────────────

class TestDispatchJob:

    @pytest.mark.asyncio
    async def test_all_candidates_fail_encryption_503(self, service, patched_redis, sample_workflow, sample_agent):
        """A RuntimeError in build_job_message for all candidates should result in HTTP 503."""
        definition = {"nodes": [], "edges": []}

        with patch("app.services.workflow_execution_service.build_job_message", side_effect=RuntimeError("sem chave")), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}):
            with pytest.raises(NoExecutorAvailableError):
                await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

    @pytest.mark.asyncio
    async def test_send_job_returns_false_503(self, service, patched_redis, sample_workflow, sample_agent):
        """All candidates refuse → HTTP 503."""
        definition = {"nodes": [], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=False)

            with pytest.raises(NoExecutorAvailableError):
                await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

    @pytest.mark.asyncio
    async def test_no_candidate_accepts_marks_run_failed(self, service, patched_redis, sample_workflow, sample_agent):
        """When no candidate accepts, the run created as pending should end with
        status='failed' (not a zombie in pending).

        Guarantees the invariant: every run created by _dispatch_job has a
        defined terminal status on exit (running, failed). Without it the WS
        would open on a run that never moved out of pending.
        """
        from app.models.models import WorkflowRun
        definition = {"nodes": [], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=False)

            with pytest.raises(NoExecutorAvailableError):
                await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

        added_runs = [c.args[0] for c in service.crud.db.add.call_args_list
                      if isinstance(c.args[0], WorkflowRun)]
        assert len(added_runs) == 1
        assert added_runs[0].status == "failed"
        assert added_runs[0].error_message  # non-empty message
        assert added_runs[0].end_time is not None

    @pytest.mark.asyncio
    async def test_success_returns_dispatch_result(self, service, patched_redis, sample_workflow, sample_agent):
        """A successfully dispatched job should return a DispatchResult with job_id."""
        definition = {"nodes": [], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=True)

            result = await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

        assert isinstance(result, DispatchResult)
        assert result.id  # not empty
        # The run is now persisted to the DB synchronously instead of via the Redis queue.
        # Checks that db.add was called with a WorkflowRun and db.commit at least
        # 2x (pending on INSERT + running after send_job).
        from app.models.models import WorkflowRun
        added_runs = [c.args[0] for c in service.crud.db.add.call_args_list
                      if isinstance(c.args[0], WorkflowRun)]
        assert len(added_runs) == 1
        assert added_runs[0].task_id == result.id
        assert service.crud.db.commit.await_count >= 2

    @pytest.mark.asyncio
    async def test_has_response_node_detectado(self, service, patched_redis, sample_workflow, sample_agent):
        """A workflow with a Response node should have has_response_node=True in the result."""
        definition = {"nodes": [{"name": "Response", "id": "n1"}], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=True)

            result = await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

        assert result.has_response_node is True

    @pytest.mark.asyncio
    async def test_failover_first_rejects_second_accepts(self, service, patched_redis, sample_workflow):
        """If the first candidate rejects (queue full), it should try the second."""
        definition = {"nodes": [], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}
        ag1 = _make_agent(status="active")
        ag2 = _make_agent(status="active")

        call_count = 0
        async def send_job_side_effect(executor_id, msg):
            nonlocal call_count
            call_count += 1
            return executor_id == ag2.id_hash  # ag1 rejeita, ag2 aceita

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(side_effect=send_job_side_effect)

            result = await service._dispatch_job(sample_workflow, definition, [ag1, ag2], {}, False)

        assert isinstance(result, DispatchResult)
        assert call_count == 2  # tentou ambos
        # Run created only once in the DB (regardless of how many candidates were tried).
        from app.models.models import WorkflowRun
        added_runs = [c.args[0] for c in service.crud.db.add.call_args_list
                      if isinstance(c.args[0], WorkflowRun)]
        assert len(added_runs) == 1

    @pytest.mark.asyncio
    async def test_credentials_injected_and_credential_id_removed(
        self, service, patched_redis, sample_workflow, sample_agent
    ):
        """credential_id should be removed from the node and connectionString injected."""
        cred_id = "cred-abc"
        definition = {
            "nodes": [{
                "id": "n1",
                "data": {"properties": {"credential_id": cred_id, "other_prop": "value"}}
            }],
            "edges": [],
        }
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}
        resolved_creds = {cred_id: {"connectionString": "postgresql://user:pass@host/db"}}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg) as mock_build, \
             patch("app.services.credential_resolver.resolve_credentials_from_ids",
                   new_callable=AsyncMock, return_value=resolved_creds), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=True)

            await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

        # Inspects the payload sent to build_job_message. It arrives already
        # serialized: the dispatch does the json.dumps a single time, outside the
        # candidates loop, instead of repeating it on each failover.
        import json as _json
        sent_payload = _json.loads(mock_build.call_args[1]["payload"])
        sent_node_props = sent_payload["workflow_definition"]["nodes"][0]["data"]["properties"]
        assert "credential_id" not in sent_node_props
        assert sent_node_props.get("connectionString") == "postgresql://user:pass@host/db"
        assert sent_node_props.get("other_prop") == "value"  # outras props preservadas


# ── TestDeleteWorkflow ────────────────────────────────────────────────────────

class TestDeleteWorkflow:

    @pytest.mark.asyncio
    async def test_success_deactivates_schedules(self, service, mock_db, sample_workflow):
        """Should soft-delete the workflow and deactivate all linked schedules."""
        service.crud.soft_delete_by_hash = AsyncMock(return_value=sample_workflow)

        # Simula schedules ativos vinculados
        sched1 = MagicMock()
        sched1.active = True
        sched2 = MagicMock()
        sched2.active = True
        mock_db.execute.return_value = _make_scalars_result([sched1, sched2])

        await service.delete_workflow(sample_workflow.id_hash)

        assert sched1.active is False
        assert sched2.active is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found_error(self, service, mock_db):
        """A nonexistent workflow should raise WorkflowNotFoundError."""
        service.crud.soft_delete_by_hash = AsyncMock(return_value=None)

        with pytest.raises(WorkflowNotFoundError):
            await service.delete_workflow("nao-existe")

    @pytest.mark.asyncio
    async def test_without_schedules_does_not_fail(self, service, mock_db, sample_workflow):
        """A workflow without schedules should be deleted without error."""
        service.crud.soft_delete_by_hash = AsyncMock(return_value=sample_workflow)
        mock_db.execute.return_value = _make_scalars_result([])

        result = await service.delete_workflow(sample_workflow.id_hash)

        assert result is sample_workflow


# ── TestUpdateWorkflow ────────────────────────────────────────────────────────

class TestUpdateWorkflow:

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found_error(self, service):
        """A nonexistent workflow should raise WorkflowNotFoundError."""
        from app.schemas.workflow import WorkflowUpdate

        service.crud.get_by_hash = AsyncMock(return_value=None)

        with pytest.raises(WorkflowNotFoundError):
            await service.update_workflow("nao-existe", WorkflowUpdate(name="new-name"), updated_by_id="usr-1")

    @pytest.mark.asyncio
    async def test_without_substantial_changes_does_not_create_version(self, service, sample_workflow):
        """An update without substantial changes should not create a version snapshot."""
        from app.schemas.workflow import WorkflowUpdate

        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)
        service.crud.update = AsyncMock(return_value=sample_workflow)
        service.crud.create_version = AsyncMock()

        new_definition = {"nodes": [], "edges": []}

        with patch("app.services.workflow_service.decrypt_workflow_connections", return_value=new_definition), \
             patch("app.services.workflow_service.encrypt_workflow_connections", return_value=new_definition), \
             patch("app.services.workflow_service._has_substantial_changes", return_value=False), \
             patch("app.services.workflow_service.extract_schedule_node", return_value=None):
            await service.update_workflow(
                sample_workflow.id_hash,
                WorkflowUpdate(definition=new_definition),
                updated_by_id="usr-1",
            )

        service.crud.create_version.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_substantial_changes_creates_version(self, service, sample_workflow):
        """An update with substantial changes should create a snapshot of the previous version."""
        from app.schemas.workflow import WorkflowUpdate

        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)
        service.crud.update = AsyncMock(return_value=sample_workflow)
        service.crud.create_version = AsyncMock()

        new_definition = {"nodes": [{"id": "n_new"}], "edges": []}

        with patch("app.services.workflow_service.decrypt_workflow_connections", return_value={"nodes": [], "edges": []}), \
             patch("app.services.workflow_service.encrypt_workflow_connections", return_value=new_definition), \
             patch("app.services.workflow_service._has_substantial_changes", return_value=True), \
             patch("app.services.workflow_service.extract_schedule_node", return_value=None):
            await service.update_workflow(
                sample_workflow.id_hash,
                WorkflowUpdate(definition=new_definition),
                updated_by_id="usr-1",
            )

        service.crud.create_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_always_calls_apply_schedule_even_without_schedule_trigger(self, service, sample_workflow):
        """An update with a definition should ALWAYS call apply_schedule_if_needed.

        Regression: previously the update had a guard `if extract_schedule_node(...)`
        that skipped apply_schedule_if_needed when the user removed the ScheduleTrigger.
        Result: the old Schedule stayed active in the database and async_scheduler
        kept triggering the workflow in a loop (zombie scheduler).

        Now apply_schedule_if_needed is called unconditionally — internally it
        removes old schedules and only creates a new one if there is a ScheduleTrigger.
        """
        from app.schemas.workflow import WorkflowUpdate

        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)
        service.crud.update = AsyncMock(return_value=sample_workflow)
        service.crud.create_version = AsyncMock()

        # New definition WITHOUT ScheduleTrigger (the user removed the trigger)
        new_definition = {"nodes": [{"id": "n1", "type": "action"}], "edges": []}

        with patch("app.services.workflow_service.decrypt_workflow_connections", return_value={"nodes": [], "edges": []}), \
             patch("app.services.workflow_service.encrypt_workflow_connections", return_value=new_definition), \
             patch("app.services.workflow_service._has_substantial_changes", return_value=False), \
             patch("app.services.workflow_service.apply_schedule_if_needed", new_callable=AsyncMock) as apply_sched:
            await service.update_workflow(
                sample_workflow.id_hash,
                WorkflowUpdate(definition=new_definition),
                updated_by_id="usr-1",
            )

        # It must have been called EVEN without a ScheduleTrigger in the definition —
        # it is the function itself that decides whether to create a new schedule or just clean up.
        apply_sched.assert_called_once()


# ── TestApplyScheduleIfNeeded ─────────────────────────────────────────────────

class TestApplyScheduleIfNeeded:
    """Tests the sync behavior of the apply_schedule_if_needed function.

    Without a ScheduleTrigger in the definition, all schedules are removed —
    otherwise a workflow that lost the node would keep being triggered by cron.

    With a ScheduleTrigger, the schedule is only REPLACED when the timing
    configuration changes. Recreating it on every save reset next_run_at, which
    is recomputed to the next future occurrence: saving after the cron time
    skipped that day's trigger. See tests/unit/test_schedule_hook_preserva_disparo.py.
    """

    @pytest.mark.asyncio
    async def test_without_schedule_trigger_only_removes_schedules(self):
        """Definition without ScheduleTrigger → delete_all_schedules is called,
        create_schedule is NOT called."""
        from app.core.scheduling.hooks import apply_schedule_if_needed

        workflow = MagicMock()
        workflow.id_hash = "wf-abc"
        definition = {"nodes": [{"type": "action", "name": "HttpRequest"}], "edges": []}
        db_session = MagicMock()

        scheduler_mock = MagicMock()
        scheduler_mock.delete_all_schedules_for_workflow = AsyncMock()
        scheduler_mock.create_schedule = AsyncMock()

        with patch("app.core.scheduling.hooks.ScheduleService", return_value=scheduler_mock):
            await apply_schedule_if_needed(workflow, definition, db_session)

        scheduler_mock.delete_all_schedules_for_workflow.assert_called_once_with("wf-abc")
        scheduler_mock.create_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_schedule_trigger_creates_when_there_was_none(self):
        """Definition with ScheduleTrigger and no existing schedule → creates one."""
        from app.core.scheduling.hooks import apply_schedule_if_needed

        workflow = MagicMock()
        workflow.id_hash = "wf-xyz"
        workflow.flag_ative = True
        definition = {
            "nodes": [
                {
                    "type": "trigger",
                    "name": "ScheduleTrigger",
                    "properties": {"strategy": "cron", "cron_expression": "0 * * * *"},
                }
            ],
            "edges": [],
        }
        db_session = MagicMock()

        scheduler_mock = MagicMock()
        scheduler_mock.delete_all_schedules_for_workflow = AsyncMock()
        scheduler_mock.create_schedule = AsyncMock()
        scheduler_mock.schedule_crud = MagicMock(
            get_by_workflow_hash=AsyncMock(return_value=[]),
            delete=AsyncMock(),
            update=AsyncMock(),
        )

        with patch("app.core.scheduling.hooks.ScheduleService", return_value=scheduler_mock):
            await apply_schedule_if_needed(workflow, definition, db_session)

        scheduler_mock.create_schedule.assert_called_once()
        # Checks that the call was made with the workflow's id_hash
        args = scheduler_mock.create_schedule.call_args
        assert args[0][0] == "wf-xyz"
        # Only the "no ScheduleTrigger" path does the bulk cleanup.
        scheduler_mock.delete_all_schedules_for_workflow.assert_not_called()
