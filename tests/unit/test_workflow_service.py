# tests/unit/test_workflow_service.py
"""Testes unitários para app/services/workflow_service.py."""
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
    """Mocka disabled_names e collect_subworkflow_definitions_recursive para
    nao bater no DB nos testes existentes de start_analysis. Os testes
    especificos desse comportamento ficam em test_workflow_service_dispatch.py."""
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

    def test_none_retorna_dict_vazio(self):
        assert _safe_pinned_outputs(None) == {}

    def test_vazio_retorna_dict_vazio(self):
        assert _safe_pinned_outputs({}) == {}

    def test_com_pin_s3_key_preserva(self):
        """Nó com __pin_s3_key__ e pin_metadata deve ser preservado intacto."""
        raw = {"n1": {"__pin_s3_key__": "s3://bucket/key"}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert result == {"n1": {"__pin_s3_key__": "s3://bucket/key"}}

    def test_dict_vazio_com_metadata_preservado(self):
        """Nó com dict vazio e pin_metadata deve ser preservado (aguarda auto-pin)."""
        raw = {"n1": {}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert result == {"n1": {}}

    def test_dados_brutos_com_metadata_retorna_dict_vazio(self):
        """Dados brutos com metadata devem ser substituídos por {} para auto-pin."""
        raw = {"n1": {"column_a": [1, 2, 3], "column_b": ["x", "y"]}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert result == {"n1": {}}

    def test_sem_metadata_ignora_entrada(self):
        """Nós em pinned_outputs sem pin_metadata correspondente devem ser ignorados."""
        raw = {"n1": {"__pin_s3_key__": "s3://key"}, "n2": {}}
        meta = {"n1": {"pinned_at": "2026-01-01"}}
        result = _safe_pinned_outputs(raw, meta)
        assert "n1" in result
        assert "n2" not in result

    def test_metadata_vazia_descarta_toda_orfa(self):
        """Sem metadata NENHUMA entrada passa — nem a que tem `__pin_s3_key__`.

        Este teste dizia o contrário (o nome prometia descarte e as asserções
        exigiam preservação, sob o rótulo "retrocompatibilidade"). O que ele
        travava era um defeito: a órfã com `__pin_s3_key__` faz o executor pular
        o nó, e a validade é lida de `pin_metadata[node_id]` — sem metadata não
        há `expires_at`, então ela **nunca expira**.
        """
        raw = {"n1": {}, "n2": {"__pin_s3_key__": "s3://key"}}
        assert _safe_pinned_outputs(raw, {}) == {}

    def test_metadata_none_descarta_toda_orfa(self):
        """`None` é o mesmo caso de `{}` — e é o valor que o unpin grava."""
        raw = {"n1": {"__pin_s3_key__": "s3://key"}}
        assert _safe_pinned_outputs(raw, None) == {}

    def test_desfixar_um_no_nao_ressuscita_o_pin_de_outro(self):
        """A regressão que este conserto existe para impedir.

        Com `{A, B}` em `pinned_outputs` e só `A` em `pin_metadata`, B é órfã e
        fica de fora — isso já valia. O problema aparecia no passo seguinte:
        desfixar A grava `pin_metadata = None` (`pin_service.desfixar_saida`), a
        coluna esvazia, e a versão anterior voltava a mandar B ao executor.
        Desfixar um nó ressuscitava o pin de outro, com cache que nunca expira.
        """
        raw = {"A": {"__pin_s3_key__": "s3://a"}, "B": {"__pin_s3_key__": "s3://b"}}

        antes = _safe_pinned_outputs(raw, {"A": {"pinned_at": "2026-01-01"}})
        assert set(antes) == {"A"}, "B é órfã e nunca deveria ter passado"

        # O unpin de A deixa a coluna assim:
        depois = _safe_pinned_outputs(raw, None)
        assert depois == {}, "B não pode voltar só porque a metadata esvaziou"


# ── TestHasSubstantialChanges ─────────────────────────────────────────────────

class TestHasSubstantialChanges:

    def _def(self, nodes=None, edges=None):
        return {"nodes": nodes or [], "edges": edges or []}

    def _node(self, nid: str, props: dict = None, position: dict = None):
        # Formato PLANO da definition persistida/PUT (`properties` no topo do nó),
        # não o `data.properties` do ReactFlow. É o shape real de produção — e o
        # único que exercita o bug: ler `data.properties` de um nó plano via cada
        # lado enxergava {} vs {} e uma edição só-de-propriedade nunca virava versão.
        return {
            "id": nid,
            "properties": props or {},
            "position": position or {"x": 0, "y": 0},
        }

    def _edge(self, src: str, tgt: str, sh: str = "out", th: str = "in"):
        return {"source": src, "target": tgt, "sourceHandle": sh, "targetHandle": th}

    def test_nos_identicos_retorna_false(self):
        d = self._def(nodes=[self._node("n1", {"key": "val"})])
        assert _has_substantial_changes(d, d) is False

    def test_no_adicionado_retorna_true(self):
        old = self._def(nodes=[self._node("n1")])
        new = self._def(nodes=[self._node("n1"), self._node("n2")])
        assert _has_substantial_changes(old, new) is True

    def test_no_removido_retorna_true(self):
        old = self._def(nodes=[self._node("n1"), self._node("n2")])
        new = self._def(nodes=[self._node("n1")])
        assert _has_substantial_changes(old, new) is True

    def test_edge_adicionada_retorna_true(self):
        nodes = [self._node("n1"), self._node("n2")]
        old = self._def(nodes=nodes, edges=[])
        new = self._def(nodes=nodes, edges=[self._edge("n1", "n2")])
        assert _has_substantial_changes(old, new) is True

    def test_edge_removida_retorna_true(self):
        nodes = [self._node("n1"), self._node("n2")]
        old = self._def(nodes=nodes, edges=[self._edge("n1", "n2")])
        new = self._def(nodes=nodes, edges=[])
        assert _has_substantial_changes(old, new) is True

    def test_propriedade_alterada_retorna_true(self):
        old = self._def(nodes=[self._node("n1", props={"k": "old_value"})])
        new = self._def(nodes=[self._node("n1", props={"k": "new_value"})])
        assert _has_substantial_changes(old, new) is True

    def test_apenas_posicao_alterada_retorna_false(self):
        """Mover nó no canvas (position) não é mudança substancial."""
        old = self._def(nodes=[self._node("n1", props={"k": "v"}, position={"x": 0, "y": 0})])
        new = self._def(nodes=[self._node("n1", props={"k": "v"}, position={"x": 500, "y": 300})])
        assert _has_substantial_changes(old, new) is False

    def test_definicoes_vazias_retorna_false(self):
        assert _has_substantial_changes({}, {}) is False


# ── TestCreateWorkflow ────────────────────────────────────────────────────────

class TestCreateWorkflow:

    @pytest.mark.asyncio
    async def test_sucesso_sem_schedule(self, service, sample_workflow):
        """Deve criptografar e criar o workflow; sem ScheduleTrigger, não cria schedule."""
        definition = {"nodes": [], "edges": []}
        service.crud.create = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.encrypt_workflow_connections", return_value=definition) as enc, \
             patch("app.services.workflow_service.extract_schedule_node", return_value=None):
            result = await service.create_workflow("my-wf", definition, created_by_id="usr-1")

        enc.assert_called_once_with(definition)
        service.crud.create.assert_called_once()
        assert result is sample_workflow

    @pytest.mark.asyncio
    async def test_carimba_autor_no_create(self, service, sample_workflow):
        """created_by_id/updated_by_id do usuário chegam ao INSERT — sem isso a
        listagem nunca mostraria 'criado há X por Y' (o router POST /workflows
        deixava de repassá-los e os campos nasciam nulos)."""
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
    async def test_sucesso_com_schedule_trigger(self, service, sample_workflow):
        """Deve chamar apply_schedule_if_needed quando definição contém ScheduleTrigger."""
        definition = {"nodes": [{"type": "trigger", "name": "ScheduleTrigger"}], "edges": []}
        service.crud.create = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.encrypt_workflow_connections", return_value=definition), \
             patch("app.services.workflow_service.extract_schedule_node", return_value={"type": "trigger"}), \
             patch("app.services.workflow_service.apply_schedule_if_needed", new_callable=AsyncMock) as apply_sched:
            await service.create_workflow("scheduled-wf", definition, created_by_id="usr-1")

        apply_sched.assert_called_once()

    @pytest.mark.asyncio
    async def test_falha_agendamento_loga_warning_nao_falha(self, service, sample_workflow):
        """Falha no agendamento não deve impedir a criação do workflow."""
        definition = {"nodes": [{"type": "trigger"}], "edges": []}
        service.crud.create = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.encrypt_workflow_connections", return_value=definition), \
             patch("app.services.workflow_service.extract_schedule_node", return_value={"type": "trigger"}), \
             patch("app.services.workflow_service.apply_schedule_if_needed", side_effect=Exception("Redis down")):
            # Não deve propagar a exceção
            result = await service.create_workflow("wf", definition, created_by_id="usr-1")

        assert result is sample_workflow


# ── TestGetWorkflowByHash ─────────────────────────────────────────────────────

class TestGetWorkflowByHash:

    @pytest.mark.asyncio
    async def test_encontrado_com_decriptografia(self, service, sample_workflow):
        """Deve descriptografar definition ao retornar o workflow."""
        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)
        decrypted_def = {"nodes": [{"id": "n1"}], "edges": []}

        with patch("app.services.workflow_service.decrypt_workflow_connections", return_value=decrypted_def) as dec:
            result = await service.get_workflow_by_hash(sample_workflow.id_hash)

        dec.assert_called_once()
        assert result.definition == decrypted_def

    @pytest.mark.asyncio
    async def test_nao_encontrado_lanca_not_found_error(self, service):
        """Workflow inexistente deve lançar WorkflowNotFoundError."""
        service.crud.get_by_hash = AsyncMock(return_value=None)

        with pytest.raises(WorkflowNotFoundError):
            await service.get_workflow_by_hash("nao-existe")

    @pytest.mark.asyncio
    async def test_erro_decriptografia_lanca_decryption_error(self, service, sample_workflow):
        """Falha na descriptografia deve lançar WorkflowDecryptionError."""
        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)

        with patch("app.services.workflow_service.decrypt_workflow_connections", side_effect=Exception("chave inválida")):
            with pytest.raises(WorkflowDecryptionError):
                await service.get_workflow_by_hash(sample_workflow.id_hash)


# ── TestStartAnalysis ─────────────────────────────────────────────────────────

class TestStartAnalysis:

    @pytest.mark.asyncio
    async def test_idempotency_hit_retorna_sem_executar(self, service, patched_redis):
        """Com idempotency_key existente no Redis, não deve executar novamente."""
        patched_redis.get = AsyncMock(return_value="existing-job-id")
        service._load_workflow = AsyncMock()  # não deve ser chamado

        result = await service.start_analysis(
            "wf-hash", idempotency_key="key-already-used"
        )

        assert result.id == "existing-job-id"
        service._load_workflow.assert_not_called()

    @pytest.mark.asyncio
    async def test_sem_idempotency_key_nao_consulta_redis(self, service, patched_redis, sample_workflow, sample_agent):
        """Sem idempotency_key, Redis não deve ser consultado para idempotência."""
        service._load_workflow = AsyncMock(return_value=(sample_workflow, {"nodes": [], "edges": []}))
        service._resolve_candidates = AsyncMock(return_value=[sample_agent])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="job-new"))

        await service.start_analysis("wf-hash")

        patched_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_workflow_nao_encontrado(self, service, patched_redis):
        """Workflow inexistente deve propagar WorkflowNotFoundError."""
        service._load_workflow = AsyncMock(side_effect=WorkflowNotFoundError("não existe"))

        with pytest.raises(WorkflowNotFoundError):
            await service.start_analysis("nao-existe")

    @pytest.mark.asyncio
    async def test_workflow_inativo(self, service, patched_redis):
        """Workflow inativo deve propagar WorkflowInactiveError."""
        service._load_workflow = AsyncMock(side_effect=WorkflowInactiveError("inativo"))

        with pytest.raises(WorkflowInactiveError):
            await service.start_analysis("wf-inativo")

    @pytest.mark.asyncio
    async def test_decryption_error(self, service, patched_redis):
        """Erro de descriptografia deve propagar WorkflowDecryptionError."""
        service._load_workflow = AsyncMock(side_effect=WorkflowDecryptionError("chave inválida"))

        with pytest.raises(WorkflowDecryptionError):
            await service.start_analysis("wf-bad-key")

    @pytest.mark.asyncio
    async def test_sucesso_retorna_dispatch_result_com_uuid(
        self, service, patched_redis, sample_workflow, sample_agent
    ):
        """Execução bem-sucedida deve retornar DispatchResult com job_id UUID e acionar Redis.lpush."""
        service._load_workflow = AsyncMock(return_value=(sample_workflow, {"nodes": [], "edges": []}))
        service._resolve_candidates = AsyncMock(return_value=[sample_agent])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="job-uuid-abc"))

        result = await service.start_analysis("wf-hash")

        assert result.id == "job-uuid-abc"

    @pytest.mark.asyncio
    async def test_sucesso_com_idempotency_key_grava_no_redis(
        self, service, patched_redis, sample_workflow, sample_agent
    ):
        """Com idempotency_key nova, deve gravar o job_id no Redis após dispatch."""
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
    async def test_pool_vazio_503(self, service, mock_db, sample_workflow):
        """Sem executores default disponíveis, deve retornar HTTP 503."""
        sample_workflow.workspace_id = None

        with patch("app.services.workflow_execution_service.get_default_agents", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(NoExecutorAvailableError):
                await service._resolve_candidates(sample_workflow)

    @pytest.mark.asyncio
    async def test_todos_offline_503(self, service, mock_db, sample_workflow):
        """Todos os defaults offline deve levantar NoExecutorAvailableError."""
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
    async def test_retorna_agents_ordenados_por_carga(self, service, mock_db, sample_workflow):
        """Deve retornar executores online ordenados por menor carga."""
        sample_workflow.workspace_id = None
        ag_busy = _make_agent(status="active")
        ag_idle = _make_agent(status="active")

        cap = {"running": 0, "queued": 0, "max_concurrent": 4, "max_queue": 50}

        async def read_capacities(ids):
            return {i: dict(cap) for i in ids}

        # A carga é a contada no banco: 5 runs em voo no ocupado, nenhum no
        # ocioso. A contagem roda na conexão da sessão, num savepoint — que o
        # AsyncMock da fixture não sabe abrir como context manager.
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
    async def test_workspace_dedicado_tem_prioridade(self, service, mock_db, sample_workflow):
        """Executor dedicado do workspace deve vir antes do pool default."""
        sample_workflow.workspace_id = "ws-001"
        dedicated = _make_agent(status="active")
        default = _make_agent(status="active")

        # Workspace ⋈ Executor viraram um join só — uma consulta, um resultado.
        mock_db.execute.side_effect = [_make_db_result(dedicated)]

        with patch("app.services.workflow_execution_service.get_default_agents", new_callable=AsyncMock, return_value=[default]), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.is_online = AsyncMock(return_value=True)
            mock_registry.presence_or_unknown = AsyncMock(return_value=True)

            candidates = await service._resolve_candidates(sample_workflow)

        assert candidates[0].id_hash == dedicated.id_hash

    @pytest.mark.asyncio
    async def test_failover_dedicado_offline_usa_pool(self, service, mock_db, sample_workflow):
        """Se o executor dedicado está offline, deve cair para o pool default."""
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
    async def test_todos_candidatos_falham_cifra_503(self, service, patched_redis, sample_workflow, sample_agent):
        """RuntimeError no build_job_message para todos os candidatos deve resultar em HTTP 503."""
        definition = {"nodes": [], "edges": []}

        with patch("app.services.workflow_execution_service.build_job_message", side_effect=RuntimeError("sem chave")), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}):
            with pytest.raises(NoExecutorAvailableError):
                await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

    @pytest.mark.asyncio
    async def test_send_job_retorna_false_503(self, service, patched_redis, sample_workflow, sample_agent):
        """Todos os candidatos recusam → HTTP 503."""
        definition = {"nodes": [], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=False)

            with pytest.raises(NoExecutorAvailableError):
                await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

    @pytest.mark.asyncio
    async def test_nenhum_candidato_aceita_marca_run_failed(self, service, patched_redis, sample_workflow, sample_agent):
        """Quando nenhum candidato aceita, o run criado em pending deve
        terminar com status='failed' (nao zumbi em pending).

        Garante o invariant: todo run criado pelo _dispatch_job tem status
        terminal definido na saida (running, failed). Sem isso o WS abriria
        em um run que nunca se moveu de pending.
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
        assert added_runs[0].error_message  # mensagem nao vazia
        assert added_runs[0].end_time is not None

    @pytest.mark.asyncio
    async def test_sucesso_retorna_dispatch_result(self, service, patched_redis, sample_workflow, sample_agent):
        """Job despachado com sucesso deve retornar DispatchResult com job_id."""
        definition = {"nodes": [], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=True)

            result = await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

        assert isinstance(result, DispatchResult)
        assert result.id  # não vazio
        # Run agora e persistido no DB sincronamente em vez de via fila Redis.
        # Verifica que db.add foi chamado com WorkflowRun e db.commit pelo menos
        # 2x (pending no INSERT + running apos send_job).
        from app.models.models import WorkflowRun
        added_runs = [c.args[0] for c in service.crud.db.add.call_args_list
                      if isinstance(c.args[0], WorkflowRun)]
        assert len(added_runs) == 1
        assert added_runs[0].task_id == result.id
        assert service.crud.db.commit.await_count >= 2

    @pytest.mark.asyncio
    async def test_has_response_node_detectado(self, service, patched_redis, sample_workflow, sample_agent):
        """Workflow com nó Response deve ter has_response_node=True no resultado."""
        definition = {"nodes": [{"name": "Response", "id": "n1"}], "edges": []}
        mock_msg = {"envelope": {}, "ephemeral_public": "", "ciphertext": "", "signature": ""}

        with patch("app.services.workflow_execution_service.build_job_message", return_value=mock_msg), \
             patch("app.services.credential_resolver.resolve_credentials_from_ids", new_callable=AsyncMock, return_value={}), \
             patch("app.services.workflow_execution_service.executor_registry") as mock_registry:
            mock_registry.send_job = AsyncMock(return_value=True)

            result = await service._dispatch_job(sample_workflow, definition, [sample_agent], {}, False)

        assert result.has_response_node is True

    @pytest.mark.asyncio
    async def test_failover_primeiro_rejeita_segundo_aceita(self, service, patched_redis, sample_workflow):
        """Se o primeiro candidato rejeita (fila cheia), deve tentar o segundo."""
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
        # Run criado uma unica vez no DB (independente de quantos candidatos tentados).
        from app.models.models import WorkflowRun
        added_runs = [c.args[0] for c in service.crud.db.add.call_args_list
                      if isinstance(c.args[0], WorkflowRun)]
        assert len(added_runs) == 1

    @pytest.mark.asyncio
    async def test_credenciais_injetadas_e_credential_id_removido(
        self, service, patched_redis, sample_workflow, sample_agent
    ):
        """credential_id deve ser removido do nó e connectionString injetada."""
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

        # Inspeciona o payload enviado ao build_job_message. Ele chega ja
        # serializado: o dispatch faz o json.dumps uma unica vez, fora do laco
        # de candidatos, em vez de repeti-lo a cada failover.
        import json as _json
        sent_payload = _json.loads(mock_build.call_args[1]["payload"])
        sent_node_props = sent_payload["workflow_definition"]["nodes"][0]["data"]["properties"]
        assert "credential_id" not in sent_node_props
        assert sent_node_props.get("connectionString") == "postgresql://user:pass@host/db"
        assert sent_node_props.get("other_prop") == "value"  # outras props preservadas


# ── TestDeleteWorkflow ────────────────────────────────────────────────────────

class TestDeleteWorkflow:

    @pytest.mark.asyncio
    async def test_sucesso_desativa_schedules(self, service, mock_db, sample_workflow):
        """Deve soft-deletar workflow e desativar todos os schedules vinculados."""
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
    async def test_nao_encontrado_lanca_not_found_error(self, service, mock_db):
        """Workflow inexistente deve lançar WorkflowNotFoundError."""
        service.crud.soft_delete_by_hash = AsyncMock(return_value=None)

        with pytest.raises(WorkflowNotFoundError):
            await service.delete_workflow("nao-existe")

    @pytest.mark.asyncio
    async def test_sem_schedules_nao_falha(self, service, mock_db, sample_workflow):
        """Workflow sem schedules deve ser deletado sem erro."""
        service.crud.soft_delete_by_hash = AsyncMock(return_value=sample_workflow)
        mock_db.execute.return_value = _make_scalars_result([])

        result = await service.delete_workflow(sample_workflow.id_hash)

        assert result is sample_workflow


# ── TestUpdateWorkflow ────────────────────────────────────────────────────────

class TestUpdateWorkflow:

    @pytest.mark.asyncio
    async def test_nao_encontrado_lanca_not_found_error(self, service):
        """Workflow inexistente deve lançar WorkflowNotFoundError."""
        from app.schemas.workflow import WorkflowUpdate

        service.crud.get_by_hash = AsyncMock(return_value=None)

        with pytest.raises(WorkflowNotFoundError):
            await service.update_workflow("nao-existe", WorkflowUpdate(name="new-name"), updated_by_id="usr-1")

    @pytest.mark.asyncio
    async def test_sem_mudancas_substanciais_nao_cria_versao(self, service, sample_workflow):
        """Update sem mudanças substanciais não deve criar snapshot de versão."""
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
    async def test_com_mudancas_substanciais_cria_versao(self, service, sample_workflow):
        """Update com mudanças substanciais deve criar snapshot da versão anterior."""
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
    async def test_update_sempre_chama_apply_schedule_mesmo_sem_schedule_trigger(self, service, sample_workflow):
        """Update com definition deve SEMPRE chamar apply_schedule_if_needed.

        Regression: anteriormente o update tinha um guard `if extract_schedule_node(...)`
        que pulava apply_schedule_if_needed quando o usuário removia o ScheduleTrigger.
        Resultado: o Schedule antigo permanecia ativo no banco e o async_scheduler
        continuava disparando o workflow em loop (scheduler zumbi).

        Agora apply_schedule_if_needed é chamado incondicionalmente — ela internamente
        remove agendamentos antigos e só cria novo se houver ScheduleTrigger.
        """
        from app.schemas.workflow import WorkflowUpdate

        service.crud.get_by_hash = AsyncMock(return_value=sample_workflow)
        service.crud.update = AsyncMock(return_value=sample_workflow)
        service.crud.create_version = AsyncMock()

        # Nova definition SEM ScheduleTrigger (usuário removeu o trigger)
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

        # Deve ter sido chamado MESMO sem ScheduleTrigger na definição — é a
        # própria função que decide se cria novo schedule ou só limpa.
        apply_sched.assert_called_once()


# ── TestApplyScheduleIfNeeded ─────────────────────────────────────────────────

class TestApplyScheduleIfNeeded:
    """Testa o comportamento de sync da função apply_schedule_if_needed.

    Sem ScheduleTrigger na definição, todos os schedules são removidos — senão
    um workflow que perdeu o nó continuaria sendo disparado por cron.

    Com ScheduleTrigger, o schedule só é SUBSTITUÍDO quando a configuração de
    tempo muda. Recriar a cada save zerava o next_run_at, que é recalculado para
    a próxima ocorrência futura: salvar depois do horário do cron pulava o
    disparo do dia. Ver tests/unit/test_schedule_hook_preserva_disparo.py.
    """

    @pytest.mark.asyncio
    async def test_sem_schedule_trigger_apenas_remove_agendamentos(self):
        """Definição sem ScheduleTrigger → delete_all_schedules é chamado,
        create_schedule NÃO é chamado."""
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
    async def test_com_schedule_trigger_cria_quando_nao_havia_nenhum(self):
        """Definição com ScheduleTrigger e nenhum schedule existente → cria."""
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
        # Valida que a chamada foi com o id_hash do workflow
        args = scheduler_mock.create_schedule.call_args
        assert args[0][0] == "wf-xyz"
        # Só o caminho "sem ScheduleTrigger" faz o cleanup em bloco.
        scheduler_mock.delete_all_schedules_for_workflow.assert_not_called()
