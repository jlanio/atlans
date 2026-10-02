# tests/unit/test_agent_service.py
"""
Testes unitarios para app/services/executor_service.py apos migracao para mTLS.

Cobertura:
  - create_executor (status=pending; credencial vem via enrollment OTP + cert mTLS)
  - delete_agent, revogar_executor + concluir_revogacoes (revogacao marca
    cert_serial no Redis blacklist depois do commit)

Fluxos cobertos em outro arquivo:
  - Enrollment OTP e CSR signing — tests/unit/test_agent_enrollment_service.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.executor import Executor


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_agent(
    status: str = "active",
    is_default: bool = False,
    executor_type: str = "dedicated",
    public_key: str | None = None,
    cert_serial: str | None = "abc123",
) -> Executor:
    """Constroi um objeto Executor para uso nos testes."""
    ag = Executor(
        name="test-executor",
        description="Executor de teste",
        created_by="user-001",
        capabilities=[],
        max_concurrent_jobs=4,
        max_queue_size=50,
        executor_type=executor_type,
        is_default=is_default,
        status=status,
    )
    ag.id_hash = str(uuid4())
    ag.public_key = public_key
    ag.cert_serial = cert_serial
    return ag


def _make_db_result(value) -> MagicMock:
    """Simula o resultado de db.execute com scalar_one_or_none."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
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


# ── TestCreateAgent ───────────────────────────────────────────────────────────

class TestCreateAgent:

    @pytest.mark.asyncio
    async def test_sucesso_dedicated_retorna_agent_pending(self, mock_db):
        """Apos migracao mTLS, create_executor retorna apenas Executor (sem api_key)."""
        from app.services.executor_service import create_executor

        ag = await create_executor(
            mock_db, name="my-executor", created_by="user-001", executor_type="dedicated",
        )

        assert ag.name == "my-executor"
        assert ag.executor_type == "dedicated"
        assert ag.status == "pending"
        assert ag.is_default is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sucesso_default(self, mock_db):
        from app.services.executor_service import create_executor

        ag = await create_executor(
            mock_db, name="default-executor", created_by="admin", executor_type="default",
        )
        assert ag.is_default is True
        assert ag.executor_type == "default"

    @pytest.mark.asyncio
    async def test_agent_type_invalido_lanca_value_error(self, mock_db):
        from app.services.executor_service import create_executor

        with pytest.raises(ValueError, match="executor_type"):
            await create_executor(mock_db, name="x", created_by="user", executor_type="unknown")


# ── TestCreateDedicatedForUser ────────────────────────────────────────────────

class TestCreateDedicatedForUser:

    @staticmethod
    def _user(quota: int = 1, uid: str = "user-xyz"):
        u = MagicMock()
        u.id_hash = uid
        u.agent_quota = quota
        return u

    @pytest.mark.asyncio
    async def test_sem_cota_lanca_403(self, mock_db):
        from app.services.executor_service import create_dedicated_for_user, ExecutorQuotaError

        with pytest.raises(ExecutorQuotaError) as exc:
            await create_dedicated_for_user(mock_db, self._user(quota=0), name="a")
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_limite_atingido_lanca_409(self, mock_db):
        from app.services import executor_service

        with patch("app.services.executor_service.count_user_created_executors", AsyncMock(return_value=1)):
            with pytest.raises(executor_service.ExecutorQuotaError) as exc:
                await executor_service.create_dedicated_for_user(mock_db, self._user(quota=1), name="a")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_sucesso_forca_dedicated_e_cria_assignment(self, mock_db):
        from app.services import executor_service
        from app.models.user_executor_assignment import UserExecutorAssignment

        with patch("app.services.executor_service.count_user_created_executors", AsyncMock(return_value=0)):
            ag = await executor_service.create_dedicated_for_user(
                mock_db, self._user(quota=2), name="meu",
            )

        assert ag.executor_type == "dedicated"
        assert ag.is_default is False
        assert ag.created_by == "user-xyz"
        # db.add chamado 2x: o Executor e o UserExecutorAssignment de visibilidade
        assert mock_db.add.call_count == 2
        added_types = [type(c.args[0]) for c in mock_db.add.call_args_list]
        assert UserExecutorAssignment in added_types


# ── TestCountUserCreatedAgents ────────────────────────────────────────────────

class TestCountUserCreatedAgents:
    """O contador ignora revoked + soft-deleted — executores nesses estados não
    ocupam vaga na cota e não bloqueiam criação de novos quando o admin
    restaura a cota após uma rodada de revogação."""

    @pytest.mark.asyncio
    async def test_retorna_scalar_do_execute(self, mock_db):
        from app.services.executor_service import count_user_created_executors

        result_mock = MagicMock()
        result_mock.scalar_one = MagicMock(return_value=5)
        mock_db.execute = AsyncMock(return_value=result_mock)

        n = await count_user_created_executors(mock_db, "user-xyz")
        assert n == 5
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_select_filtra_revoked_e_deleted(self, mock_db):
        """Compila o statement e verifica que os filtros corretos estão presentes."""
        from app.services.executor_service import count_user_created_executors

        captured: dict = {}

        async def capture_execute(stmt):
            captured["stmt"] = stmt
            result_mock = MagicMock()
            result_mock.scalar_one = MagicMock(return_value=0)
            return result_mock

        mock_db.execute = capture_execute

        await count_user_created_executors(mock_db, "user-xyz")

        # Compila SQL inline e procura pelos filtros — robusto a aliasing/case.
        sql = str(captured["stmt"].compile(compile_kwargs={"literal_binds": True}))
        sql_lower = sql.lower()
        assert "deleted_at is null" in sql_lower
        assert "revoked" in sql_lower
        assert "user-xyz" in sql_lower


# ── TestDeleteAgent ───────────────────────────────────────────────────────────

class TestDeleteAgent:

    @pytest.mark.asyncio
    async def test_sucesso_preenche_deleted_at(self, mock_db):
        from app.services.executor_service import delete_agent

        ag = _make_agent(status="revoked")
        ag.deleted_at = None
        with patch("app.services.executor_service.ExecutorCRUD") as crud_cls:
            crud_inst = MagicMock()
            crud_inst.get_any = AsyncMock(return_value=ag)
            crud_cls.return_value = crud_inst
            result = await delete_agent(mock_db, ag.id_hash)
        assert result.deleted_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_nao_revogado_lanca_value_error(self, mock_db):
        from app.services.executor_service import delete_agent

        ag = _make_agent(status="active")
        with patch("app.services.executor_service.ExecutorCRUD") as crud_cls:
            crud_inst = MagicMock()
            crud_inst.get_any = AsyncMock(return_value=ag)
            crud_cls.return_value = crud_inst
            with pytest.raises(ValueError, match="revogados"):
                await delete_agent(mock_db, ag.id_hash)

    @pytest.mark.asyncio
    async def test_nao_encontrado_lanca_value_error(self, mock_db):
        from app.services.executor_service import delete_agent

        with patch("app.services.executor_service.ExecutorCRUD") as crud_cls:
            crud_inst = MagicMock()
            crud_inst.get_any = AsyncMock(return_value=None)
            crud_cls.return_value = crud_inst
            with pytest.raises(ValueError, match="nao encontrado"):
                await delete_agent(mock_db, "missing")


# ── Revogação: revogar_executor + concluir_revogacoes ────────────────────────

def _revogar(ag, **kw):
    from app.services.executor_service import revogar_executor

    return revogar_executor(
        kw.pop("db"), ag, force=kw.pop("force", False), actor_id="adm-1", motivo="revoked",
        aviso="Executor revogado pelo administrador.", fechamento="Executor revogado.",
    )


class TestRevogarExecutor:

    @pytest.mark.asyncio
    async def test_muda_status_e_anula_o_cert_sem_commit_proprio(self, mock_db):
        ag = _make_agent(status="active", cert_serial="abc123")
        with patch("app.services.workspace_executor_service.detach_executor",
                   AsyncMock(return_value=[])) as detach:
            revogacao = await _revogar(ag, db=mock_db)

        assert (ag.status, ag.cert_serial) == ("revoked", None)
        assert revogacao.serial == "abc123"            # o que a blacklist recebe depois
        detach.assert_awaited_once()
        assert detach.await_args.kwargs["reason"] == "revoked"
        # O commit é de quem chama: a revogação entra na transação dele.
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_nivel_principal_que_esvaziaria_barra_a_revogacao(self, mock_db):
        """Sem `force`, o 409 da política vem ANTES de tocar no executor."""
        from app.core.exceptions import WorkspacePolicyConflictError

        ag = _make_agent(status="active", cert_serial="abc123")
        recusa = WorkspacePolicyConflictError("esvaziaria", workspaces=[])
        with patch("app.services.workspace_executor_service.detach_executor",
                   AsyncMock(side_effect=recusa)):
            with pytest.raises(WorkspacePolicyConflictError):
                await _revogar(ag, db=mock_db)

        assert (ag.status, ag.cert_serial) == ("active", "abc123")


def _registro():
    reg = MagicMock()
    reg.send_json = AsyncMock(return_value=True)
    reg.disconnect_executor = AsyncMock(return_value=True)
    return reg


class TestConcluirRevogacoes:

    @pytest.mark.asyncio
    async def test_blacklist_aviso_e_fechamento(self):
        from app.services import executor_service as svc

        revogacao = svc.Revogacao(
            executor_id="ex-1", nome="maquina", serial="abc123", serial_expira_em=None,
            aviso="Executor revogado pelo administrador.", fechamento="Executor revogado.",
        )
        reg = _registro()
        with patch.object(svc, "executor_registry", reg), \
             patch("app.services.executor_enrollment_service.revoke_cert", AsyncMock()) as blacklist:
            await svc.concluir_revogacoes([revogacao])

        # V07: revoke_cert recebe cert_expires_at para alinhar o TTL.
        blacklist.assert_awaited_once_with("abc123", cert_expires_at=None)
        reg.send_json.assert_awaited_once_with("ex-1", {
            "type": "control", "action": "revoked", "reason": "Executor revogado pelo administrador.",
        })
        reg.disconnect_executor.assert_awaited_once_with("ex-1", code=4403, reason="Executor revogado.")

    @pytest.mark.asyncio
    async def test_falha_de_um_passo_nao_impede_os_outros(self):
        """Tudo depois do commit é best-effort: a blacklist fora do ar não pode
        deixar o executor conectado, nem o de um executor impedir o do outro."""
        from app.services import executor_service as svc

        revogacoes = [
            svc.Revogacao(executor_id=e, nome=e, serial=f"serial-{e}", serial_expira_em=None,
                          aviso="a", fechamento="Operador revogado.")
            for e in ("exec-a", "exec-b")
        ]

        async def _revoke_cert(serial, cert_expires_at=None):
            if serial == "serial-exec-a":
                raise RuntimeError("Redis fora")

        reg = _registro()
        reg.send_json = AsyncMock(side_effect=[RuntimeError("relay fora"), True])
        with patch.object(svc, "executor_registry", reg), \
             patch("app.services.executor_enrollment_service.revoke_cert", new=_revoke_cert):
            await svc.concluir_revogacoes(revogacoes)

        assert [c.args[0] for c in reg.disconnect_executor.await_args_list] == ["exec-a", "exec-b"]


class TestRevogarExecutoresDoUsuario:
    """Auditoria SEG-16: suspender/excluir a conta revoga os executores dela."""

    @staticmethod
    def _db_com(executores):
        sel = MagicMock()
        sel.scalars.return_value.all.return_value = list(executores)
        db = MagicMock()
        db.execute = AsyncMock(return_value=sel)
        db.commit = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_revoga_todos_os_executores_da_conta(self):
        from app.services import executor_service as svc

        a, b = _make_agent(cert_serial="serial-a"), _make_agent(status="pending", cert_serial=None)
        db = self._db_com([a, b])
        usuario = MagicMock(id_hash="user-001", username="ana")
        with patch("app.services.workspace_executor_service.detach_executor",
                   AsyncMock(return_value=[])) as detach:
            revogacoes = await svc.revogar_executores_do_usuario(
                db, usuario, motivo="operator_revoked", desanexar=True,
            )

        assert [r.executor_id for r in revogacoes] == [a.id_hash, b.id_hash]
        assert {a.status, b.status} == {"revoked"}
        # "Revogar todos": níveis da política com força, porque é a conta inteira.
        assert [c.kwargs["force"] for c in detach.await_args_list] == [True, True]
        assert {c.kwargs["reason"] for c in detach.await_args_list} == {"operator_revoked"}
        assert revogacoes[0].fechamento == "Operador revogado."
        assert "ana" in revogacoes[0].aviso
        # Um SELECT só (fora o detach de cada um) e nenhum commit próprio.
        db.execute.assert_awaited_once()
        db.commit.assert_not_awaited()
        sql = str(db.execute.await_args.args[0])
        assert "executors.created_by" in sql and "executors.status !=" in sql

    @pytest.mark.asyncio
    async def test_suspensao_nao_tira_dos_niveis(self):
        """Suspender/excluir a conta (`desanexar=False`) revoga sem detach: o
        executor fica nos níveis dos workspaces (spec §4.4)."""
        from app.services import executor_service as svc

        a = _make_agent(cert_serial="serial-a")
        db = self._db_com([a])
        with patch("app.services.workspace_executor_service.detach_executor", AsyncMock()) as detach:
            revogacoes = await svc.revogar_executores_do_usuario(
                db, MagicMock(id_hash="user-001", username="ana"), motivo="user_suspended", desanexar=False,
            )

        detach.assert_not_awaited()
        assert a.status == "revoked" and a.cert_serial is None
        assert revogacoes[0].afetados == []

    @pytest.mark.asyncio
    async def test_sem_executores_nao_revoga_nada(self):
        from app.services import executor_service as svc

        db = self._db_com([])
        revogacoes = await svc.revogar_executores_do_usuario(
            db, MagicMock(id_hash="user-001", username="ana"), motivo="user_deleted", desanexar=False,
        )
        assert revogacoes == []
        db.execute.assert_awaited_once()
