"""
Tokens pessoais de acesso (PAT) — o service, contra um banco de verdade.

Vale o SQLite em memória: as regras que importam (só o hash fica no banco,
escopo de workspaces, teto de tokens ativos, resolução que exige token vivo E
usuário ativo, cascata de revogação sem commit próprio) são todas sobre o que
está gravado, não sobre o código de status de uma rota.
"""
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.authorization import pat
from app.core.utils.datetime_utils import utc_now_naive
from app.models.api_token import ApiToken
from app.models.base import Base
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services import api_token_service as svc

import pytest as _pytest_seg16
from unittest.mock import AsyncMock as _AsyncMock_seg16


@_pytest_seg16.fixture(autouse=True)
def _patch_revoga_executores(monkeypatch):
    """SEG-16: isola estes testes (token/commit) da revogacao de executores,
    que faz suas proprias consultas ao banco."""
    monkeypatch.setattr(
        "app.services.executor_service.revogar_executores_do_usuario",
        _AsyncMock_seg16(return_value=[]),
    )


TABELAS = [User.__table__, Workspace.__table__, WorkspaceMember.__table__, ApiToken.__table__]


@pytest_asyncio.fixture
async def sessao():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


async def _semear(sessao):
    """ana é dona de ws-1 e membro de ws-3; ws-2 é só da bia. Os dois `ws-lixo-*`
    estão na lixeira — um dela, outro em que ela é membro."""
    ana = User(id_hash="u-ana", username="ana", email="ana@x.test", hashed_password="x")
    bia = User(id_hash="u-bia", username="bia", email="bia@x.test", hashed_password="x")
    sessao.add_all([
        ana, bia,
        Workspace(id_hash="ws-1", name="Meu", owner_id="u-ana"),
        Workspace(id_hash="ws-2", name="Alheio", owner_id="u-bia"),
        Workspace(id_hash="ws-3", name="Compartilhado", owner_id="u-bia"),
        WorkspaceMember(workspace_id="ws-3", user_id="u-ana", role="editor"),
        Workspace(id_hash="ws-lixo-dono", name="Lixo", owner_id="u-ana", deleted_at=utc_now_naive()),
        Workspace(id_hash="ws-lixo-membro", name="Lixo 2", owner_id="u-bia", deleted_at=utc_now_naive()),
        WorkspaceMember(workspace_id="ws-lixo-membro", user_id="u-ana", role="editor"),
    ])
    await sessao.commit()
    return ana, bia


@pytest_asyncio.fixture
async def fabrica_transacional():
    """Sessões sobre um SQLite que emite BEGIN de verdade.

    O driver pysqlite (e o aiosqlite por cima dele) comita sozinho ao liberar
    o SAVEPOINT mais externo: com ele, um UPDATE dentro de `begin_nested()`
    "persiste" mesmo que o chamador dê rollback depois — e um teste de commit
    não provaria nada. Este é o workaround documentado pelo SQLAlchemy
    ("Serializable isolation / Savepoints / Transactional DDL", versão asyncio).
    """
    from sqlalchemy import event

    engine = create_async_engine("sqlite+aiosqlite://")

    @event.listens_for(engine.sync_engine, "connect")
    def _sem_begin_implicito(dbapi_connection, _record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine.sync_engine, "begin")
    def _begin_explicito(conn):
        conn.exec_driver_sql("BEGIN")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


# ── criar ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_criar_devolve_o_segredo_uma_vez_e_guarda_so_o_hash(sessao):
    ana, _ = await _semear(sessao)

    token, segredo = await svc.criar(
        sessao, ana, name="  Claude Code ", scopes=["workflows:read", "runs:execute", "workflows:read"],
        workspace_ids=["ws-1", "ws-3"], expires_in_days=30,
    )

    assert pat.e_segredo_pat(segredo)
    assert token.token_hash == pat.hash_segredo(segredo)
    assert token.token_prefix == segredo[:12] and token.token_prefix.startswith("atl_pat_")
    assert token.name == "Claude Code"
    assert token.scopes == ["workflows:read", "runs:execute"]  # sem duplicata, ordem preservada
    assert token.workspace_ids == ["ws-1", "ws-3"]
    assert token.revoked_at is None and token.last_used_at is None
    assert timedelta(days=29) < token.expires_at - utc_now_naive() <= timedelta(days=30)
    # Nada na linha carrega o segredo.
    assert segredo not in {str(v) for v in vars(token).values()}
    assert pat.status_de(token.revoked_at, token.expires_at, utc_now_naive()) == "active"


@pytest.mark.asyncio
async def test_criar_recusa_escopo_desconhecido_ou_vazio(sessao):
    ana, _ = await _semear(sessao)
    with pytest.raises(svc.ApiTokenError, match="Escopo desconhecido: admin"):
        await svc.criar(sessao, ana, name="x", scopes=["workflows:read", "admin"])
    with pytest.raises(svc.ApiTokenError, match="ao menos um escopo"):
        await svc.criar(sessao, ana, name="x", scopes=[])


@pytest.mark.asyncio
async def test_criar_so_aceita_workspaces_do_usuario(sessao):
    ana, _ = await _semear(sessao)
    with pytest.raises(svc.ApiTokenError, match="não participa"):
        await svc.criar(sessao, ana, name="x", scopes=["workflows:read"], workspace_ids=["ws-1", "ws-2"])
    with pytest.raises(svc.ApiTokenError, match="ao menos um workspace"):
        await svc.criar(sessao, ana, name="x", scopes=["workflows:read"], workspace_ids=[])

    # Membro (não dono) conta; None = todos, inclusive os futuros.
    token, _ = await svc.criar(sessao, ana, name="m", scopes=["workflows:read"], workspace_ids=["ws-3"])
    assert token.workspace_ids == ["ws-3"]
    todos, _ = await svc.criar(sessao, ana, name="t", scopes=["workflows:read"], workspace_ids=None)
    assert todos.workspace_ids is None


@pytest.mark.asyncio
async def test_criar_recusa_workspace_na_lixeira_mesmo_sendo_dono_ou_membro(sessao):
    """A lixeira não é um workspace: um token com alcance nele daria acesso a
    artefatos que a tela já não mostra (mesma regra de `get_user_workspace_ids`)."""
    ana, _ = await _semear(sessao)
    for ws in ("ws-lixo-dono", "ws-lixo-membro"):
        with pytest.raises(svc.ApiTokenError, match="não participa"):
            await svc.criar(sessao, ana, name="x", scopes=["workflows:read"], workspace_ids=[ws])


@pytest.mark.asyncio
async def test_criar_limita_validade_e_nome(sessao):
    ana, _ = await _semear(sessao)
    with pytest.raises(svc.ApiTokenError, match="validade"):
        await svc.criar(sessao, ana, name="x", scopes=["workflows:read"], expires_in_days=366)
    with pytest.raises(svc.ApiTokenError, match="validade"):
        await svc.criar(sessao, ana, name="x", scopes=["workflows:read"], expires_in_days=0)
    with pytest.raises(svc.ApiTokenError, match="nome"):
        await svc.criar(sessao, ana, name="   ", scopes=["workflows:read"])
    with pytest.raises(svc.ApiTokenError, match="nome"):
        await svc.criar(sessao, ana, name="n" * 81, scopes=["workflows:read"])


def _linha(user_id, i, *, expires=None, revoked=None):
    return ApiToken(
        user_id=user_id, name=f"t{i}", token_prefix="atl_pat_xxxx",
        token_hash=pat.hash_segredo(f"seed-{user_id}-{i}"), scopes=["workflows:read"],
        workspace_ids=None, expires_at=expires or (utc_now_naive() + timedelta(days=10)),
        revoked_at=revoked,
    )


@pytest.mark.asyncio
async def test_teto_de_tokens_ativos_ignora_expirados_e_revogados(sessao):
    ana, _ = await _semear(sessao)
    sessao.add_all([_linha("u-ana", i) for i in range(pat.MAX_TOKENS_ATIVOS_POR_USUARIO)])
    # Um expirado e um revogado a mais não contam.
    sessao.add(_linha("u-ana", 98, expires=utc_now_naive() - timedelta(minutes=1)))
    sessao.add(_linha("u-ana", 99, revoked=utc_now_naive()))
    await sessao.commit()

    with pytest.raises(svc.ApiTokenLimitError):
        await svc.criar(sessao, ana, name="mais um", scopes=["workflows:read"])

    # Revogar um libera a vaga.
    um = (await sessao.execute(select(ApiToken).where(ApiToken.name == "t0"))).scalar_one()
    await svc.revogar(sessao, "u-ana", um.id_hash)
    token, _ = await svc.criar(sessao, ana, name="mais um", scopes=["workflows:read"])
    assert token.id_hash


# ── listar / status / revogar ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_listar_traz_todos_com_status_e_o_mais_recente_primeiro(sessao):
    ana, _ = await _semear(sessao)
    sessao.add(_linha("u-ana", 1, expires=utc_now_naive() - timedelta(days=1)))
    sessao.add(_linha("u-ana", 2, revoked=utc_now_naive()))
    sessao.add(_linha("u-bia", 3))
    await sessao.commit()
    novo, _ = await svc.criar(sessao, ana, name="novo", scopes=["workflows:read"])

    tokens = await svc.listar(sessao, "u-ana")

    assert [t.name for t in tokens][0] == "novo"
    assert {t.name for t in tokens} == {"novo", "t1", "t2"}  # nada da bia
    agora = utc_now_naive()
    por_nome = {t.name: pat.status_de(t.revoked_at, t.expires_at, agora) for t in tokens}
    assert por_nome == {"novo": "active", "t1": "expired", "t2": "revoked"}


@pytest.mark.asyncio
async def test_revogar_e_idempotente_e_nao_alcanca_token_alheio(sessao):
    ana, bia = await _semear(sessao)
    meu, _ = await svc.criar(sessao, ana, name="meu", scopes=["workflows:read"])
    dela, _ = await svc.criar(sessao, bia, name="dela", scopes=["workflows:read"])

    r1 = await svc.revogar(sessao, "u-ana", meu.id_hash)
    r2 = await svc.revogar(sessao, "u-ana", meu.id_hash)
    assert r1.revoked_at is not None and r1.revoked_reason == "user"
    assert r2.revoked_at == r1.revoked_at  # segunda chamada não re-carimba

    with pytest.raises(svc.ApiTokenNotFoundError):
        await svc.revogar(sessao, "u-ana", dela.id_hash)
    with pytest.raises(svc.ApiTokenNotFoundError):
        await svc.revogar(sessao, "u-ana", "nao-existe")


# ── resolver (o contrato da autenticação por PAT) ────────────────────────────


@pytest.mark.asyncio
async def test_resolver_devolve_token_e_usuario_so_para_segredo_vivo(sessao):
    ana, _ = await _semear(sessao)
    token, segredo = await svc.criar(sessao, ana, name="ok", scopes=["workflows:read"])

    achado = await svc.resolver(sessao, segredo)
    assert achado is not None
    tok, usuario = achado
    assert tok.id_hash == token.id_hash and usuario.id_hash == "u-ana"

    assert await svc.resolver(sessao, None) is None
    assert await svc.resolver(sessao, "Bearer " + segredo) is None  # formato exato, sem prefixo de header
    assert await svc.resolver(sessao, "atl_pat_" + "A" * 43) is None  # hash desconhecido
    assert await svc.resolver(sessao, segredo[:-1] + "!") is None  # fora do alfabeto


@pytest.mark.asyncio
async def test_resolver_nega_expirado_revogado_e_usuario_inativo(sessao):
    ana, _ = await _semear(sessao)

    expirado, s_exp = await svc.criar(sessao, ana, name="exp", scopes=["workflows:read"], expires_in_days=1)
    expirado.expires_at = utc_now_naive() - timedelta(seconds=1)
    revogado, s_rev = await svc.criar(sessao, ana, name="rev", scopes=["workflows:read"])
    await sessao.commit()
    await svc.revogar(sessao, "u-ana", revogado.id_hash)
    assert await svc.resolver(sessao, s_exp) is None
    assert await svc.resolver(sessao, s_rev) is None

    vivo, s_vivo = await svc.criar(sessao, ana, name="vivo", scopes=["workflows:read"])
    assert await svc.resolver(sessao, s_vivo) is not None
    ana.status = "suspended"
    await sessao.commit()
    assert await svc.resolver(sessao, s_vivo) is None


# ── marcar_uso (best-effort com throttle) ────────────────────────────────────


class _RedisFalso:
    def __init__(self, ganha=True):
        self.ganha = ganha
        self.chamadas = []
        self.apagadas = []

    async def set(self, key, value, nx=None, ex=None):
        self.chamadas.append((key, nx, ex))
        return self.ganha

    async def delete(self, key):
        self.apagadas.append(key)
        return 1


@pytest.mark.asyncio
async def test_marcar_uso_carimba_uma_vez_por_minuto(sessao):
    ana, _ = await _semear(sessao)
    token, _ = await svc.criar(sessao, ana, name="x", scopes=["workflows:read"])

    redis = _RedisFalso(ganha=True)
    assert await svc.marcar_uso(sessao, redis, token) is True
    assert redis.chamadas == [(f"pat:lu:{token.id_hash}", True, 60)]
    await sessao.refresh(token)
    primeiro = token.last_used_at
    assert primeiro is not None

    redis.ganha = False  # o lock já existe: ninguém toca no banco
    assert await svc.marcar_uso(sessao, redis, token) is False
    await sessao.refresh(token)
    assert token.last_used_at == primeiro
    assert redis.apagadas == []


@pytest.mark.asyncio
async def test_marcar_uso_persiste_mesmo_com_rollback_do_chamador_depois(fabrica_transacional):
    """O caminho real: `get_session_async` faz rollback no `finally` da request.
    Por padrão o carimbo é commitado aqui dentro — o rollback não o leva."""
    async with fabrica_transacional() as s:
        ana, _ = await _semear(s)
        criado, _ = await svc.criar(s, ana, name="x", scopes=["workflows:read"])

    async with fabrica_transacional() as s:
        token = (await s.execute(select(ApiToken).where(ApiToken.id_hash == criado.id_hash))).scalar_one()
        assert await svc.marcar_uso(s, _RedisFalso(), token) is True
        await s.rollback()

    async with fabrica_transacional() as s:
        linha = (await s.execute(select(ApiToken).where(ApiToken.id_hash == criado.id_hash))).scalar_one()
        assert linha.last_used_at is not None


@pytest.mark.asyncio
async def test_marcar_uso_sem_commit_deixa_o_carimbo_por_conta_do_chamador(fabrica_transacional):
    """Controle do harness (e do contrato): com `commit=False` e rollback
    depois, o carimbo se perde — é exatamente o que o default evita."""
    async with fabrica_transacional() as s:
        ana, _ = await _semear(s)
        criado, _ = await svc.criar(s, ana, name="x", scopes=["workflows:read"])

    async with fabrica_transacional() as s:
        token = (await s.execute(select(ApiToken).where(ApiToken.id_hash == criado.id_hash))).scalar_one()
        assert await svc.marcar_uso(s, _RedisFalso(), token, commit=False) is True
        await s.rollback()

    async with fabrica_transacional() as s:
        linha = (await s.execute(select(ApiToken).where(ApiToken.id_hash == criado.id_hash))).scalar_one()
        assert linha.last_used_at is None


@pytest.mark.asyncio
async def test_marcar_uso_nunca_levanta_e_devolve_o_lock_quando_o_banco_falha(sessao):
    ana, _ = await _semear(sessao)
    token, _ = await svc.criar(sessao, ana, name="x", scopes=["workflows:read"])

    quebrado = MagicMock()
    quebrado.set = AsyncMock(side_effect=ConnectionError("redis fora"))
    assert await svc.marcar_uso(sessao, quebrado, token) is False

    redis = _RedisFalso(ganha=True)
    db_ruim = MagicMock()
    db_ruim.begin_nested = MagicMock(side_effect=RuntimeError("sessão morta"))
    assert await svc.marcar_uso(db_ruim, redis, token) is False
    # O minuto não fica queimado sem carimbo: a próxima request tenta de novo.
    assert redis.apagadas == [f"pat:lu:{token.id_hash}"]


# ── cascata ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revogar_todos_do_usuario_so_marca_os_ativos_dos_usuarios_pedidos(sessao):
    ana, bia = await _semear(sessao)
    a1, _ = await svc.criar(sessao, ana, name="a1", scopes=["workflows:read"])
    a2, _ = await svc.criar(sessao, ana, name="a2", scopes=["workflows:read"])
    await svc.revogar(sessao, "u-ana", a2.id_hash)  # já revogado: não re-carimba
    b1, _ = await svc.criar(sessao, bia, name="b1", scopes=["workflows:read"])

    n = await svc.revogar_todos_do_usuario(sessao, ["u-ana", "u-ana", ""], motivo="user_suspended")
    await sessao.commit()

    assert n == 1
    for t in (a1, a2, b1):
        await sessao.refresh(t)
    assert a1.revoked_reason == "user_suspended"
    assert a2.revoked_reason == "user"
    assert b1.revoked_at is None
    assert await svc.revogar_todos_do_usuario(sessao, [], motivo="x") == 0


@pytest.mark.asyncio
async def test_revogar_todos_aceita_um_id_hash_so(sessao):
    """`"u-ana"` iterado como letras revogaria nada, sem erro — o reset de
    senha chama com uma string."""
    ana, _ = await _semear(sessao)
    t, _ = await svc.criar(sessao, ana, name="a", scopes=["workflows:read"])

    assert await svc.revogar_todos_do_usuario(sessao, "u-ana", motivo="password_reset") == 1
    await sessao.commit()
    await sessao.refresh(t)
    assert t.revoked_reason == "password_reset"


@pytest.mark.asyncio
async def test_revogar_todos_nao_commita_por_conta_propria():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(rowcount=2))
    db.commit = AsyncMock()

    assert await svc.revogar_todos_do_usuario(db, ["u1"], motivo="user_deleted") == 2

    db.execute.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_suspender_usuario_revoga_seus_tokens(sessao):
    from app.services import admin_user_service

    ana, _ = await _semear(sessao)
    token, segredo = await svc.criar(sessao, ana, name="x", scopes=["workflows:read"])

    await admin_user_service.suspend_user(sessao, ana, motivo="teste", por="admin-1")

    await sessao.refresh(token)
    assert token.revoked_reason == "user_suspended"
    assert await svc.resolver(sessao, segredo) is None
    # Reativar a conta NÃO ressuscita o token.
    await admin_user_service.reactivate_user(sessao, ana)
    assert await svc.resolver(sessao, segredo) is None


@pytest.mark.asyncio
async def test_excluir_usuario_em_lote_revoga_seus_tokens(sessao):
    from app.services import admin_user_service

    ana, bia = await _semear(sessao)
    ta, _ = await svc.criar(sessao, ana, name="a", scopes=["workflows:read"])
    tb, _ = await svc.criar(sessao, bia, name="b", scopes=["workflows:read"])

    await admin_user_service.bulk_soft_delete(sessao, [ana])

    await sessao.refresh(ta)
    await sessao.refresh(tb)
    assert ta.revoked_reason == "user_deleted"
    assert tb.revoked_at is None
