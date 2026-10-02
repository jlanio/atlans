# tests/unit/test_credential_authorization.py
"""Autorizacao na resolucao de credenciais.

Antes a busca era `WHERE id IN (...)`, sem dono nem workspace. Como o
credential_id fica em texto puro na definition e e legivel por qualquer membro
que abra o workflow, bastava copia-lo para um workflow de OUTRO workspace —
criado pelo proprio atacante — para usar a credencial alheia indefinidamente.

Estes testes falham no instante em que o filtro de dono sair da query.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.authorization.credential_loader import (
    CredentialScopeMissing,
    assert_credentials_accessible,
    credential_scope,
    resolve_credentials_from_ids,
    workspace_credential_owners,
)
from app.core.exceptions import CredentialAccessDeniedError

DONO = "user-dono"
MEMBRO = "user-membro"
ESTRANHO = "user-de-outro-workspace"


def _cred(owner_id: str, cid=None) -> MagicMock:
    c = MagicMock()
    c.id = cid or uuid4()
    c.owner_id = owner_id
    c.type = "postgresql"
    c.data = {"connectionString": "postgres://x"}
    return c


def _session_com(credenciais: list) -> MagicMock:
    """Sessao que devolve apenas o que o WHERE da query deixaria passar.

    O filtro real e SQL; aqui o teste inspeciona o statement para garantir que
    o owner_id entrou nele — ver test_query_filtra_por_owner_id.
    """
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = credenciais
    result.all.return_value = []          # _explain_missing
    session.execute = AsyncMock(return_value=result)
    # commit/rollback async: o resolver commita o carimbo de last_used_at quando
    # abre a própria sessão. Sem estes AsyncMock, `await session.commit()` cairia
    # no ramo best-effort e o teste não exerceria o caminho de sucesso.
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    # begin_nested: o carimbo de last_used_at roda dentro de um SAVEPOINT para
    # não envenenar a transação do chamador. O mock devolve um CM assíncrono
    # no-op (não suprime exceção — __aexit__ → False), como o savepoint real.
    session.begin_nested = MagicMock(side_effect=lambda: _AsyncNoop())
    return session


class _AsyncNoop:
    """Context manager assíncrono no-op para simular session.begin_nested()."""
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False   # não suprime a exceção — igual ao savepoint real


def _patch_session(session):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake():
        yield session

    return patch("app.core.authorization.credential_loader.get_session_async", _fake)


def _sql(session) -> str:
    """Primeiro statement que passou por session.execute, compilado com literais.

    Compilar e o unico jeito de checar o filtro: a sessao e falsa, entao o
    WHERE real nunca roda — e e justamente ele que este arquivo protege.
    """
    return str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    ))


def _where(session) -> str:
    """So a clausula WHERE — `select(Credential)` lista owner_id/workspace_id
    entre as colunas, entao procurar no statement inteiro passaria sem filtro."""
    return _sql(session).split("WHERE", 1)[1]


def _db_com_linhas(linhas: list) -> MagicMock:
    """Sessao do request para as guardas do /validate: `.all()` devolve `linhas`,
    isto e, apenas os ids que o WHERE deixaria passar."""
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = linhas
    db.execute = AsyncMock(return_value=res)
    return db


@pytest.fixture(autouse=True)
def _decrypt():
    with patch(
        "app.core.authorization.credential_loader.decrypt_credential_data",
        side_effect=lambda d: dict(d),
    ):
        yield


# ── Escopo obrigatorio ───────────────────────────────────────────────────────

async def test_sem_escopo_levanta_em_vez_de_resolver():
    """Fail-closed: call site novo que esquecer o escopo quebra em teste."""
    with pytest.raises(CredentialScopeMissing):
        await resolve_credentials_from_ids([str(uuid4())])


async def test_escopo_vazio_nao_resolve_nada():
    """Workflow sem workspace cai aqui — nao pode virar resolucao aberta."""
    with _patch_session(_session_com([])):
        assert await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids=set()) == {}


async def test_contextvar_serve_de_escopo():
    """Caminho da simulacao: o `simulate()` nao recebe parametros de contexto."""
    cred = _cred(DONO)
    with _patch_session(_session_com([cred])), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    assert str(cred.id) in out


async def test_contextvar_carrega_shared_workspace_id():
    """/validate com workspace: o `simulate()` nao recebe parametros, entao o
    ContextVar tem de levar as DUAS dimensoes — dono E workspace compartilhado.
    Senao a guarda aceitaria a credencial compartilhada e a simulacao nao a
    resolveria."""
    session = _session_com([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())])

    where = _where(session)
    assert "owner_id IN" in where and DONO in where
    assert "workspace_id" in where and "ws-1" in where
    assert " OR " in where


async def test_kwargs_explicitos_nao_se_misturam_com_o_contextvar():
    """Kwargs explicitos sao o escopo INTEIRO: o ContextVar nunca completa a
    dimensao que faltou. Senao um call site que passasse so `allowed_owner_ids`
    dentro de um `credential_scope(..., shared_workspace_id=...)` herdaria o
    workspace sem saber — e vice-versa."""
    # Dono explicito dentro de um ctx com dono E workspace: so o explicito vale.
    session = _session_com([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={MEMBRO})

    where = _where(session)
    assert MEMBRO in where
    assert DONO not in where
    assert "ws-1" not in where

    # Workspace explicito sozinho: sem clausula de dono, mesmo com ctx ativo.
    session = _session_com([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())], shared_workspace_id="ws-2")

    where = _where(session)
    assert "owner_id IN" not in where
    assert "ws-2" in where
    assert DONO not in where
    assert "ws-1" not in where


# ── Filtro por dono ──────────────────────────────────────────────────────────

async def test_query_filtra_por_owner_id():
    """O cerco tem de estar no SQL, nao so no chamador.

    Checa o WHERE especificamente: `select(Credential)` ja lista owner_id entre
    as colunas selecionadas, entao procurar no statement inteiro passaria mesmo
    sem filtro nenhum.
    """
    session = _session_com([])
    with _patch_session(session):
        await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={DONO, MEMBRO})

    stmt = str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    ))
    where = stmt.split("WHERE", 1)[1]
    assert "owner_id" in where
    assert DONO in where


async def test_credencial_de_membro_do_workspace_resolve():
    """B executa o workflow de A: a credencial de A continua valendo."""
    cred = _cred(DONO)
    with _patch_session(_session_com([cred])):
        out = await resolve_credentials_from_ids(
            [str(cred.id)], allowed_owner_ids={DONO, MEMBRO},
        )

    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_credencial_sem_dono_nao_resolve():
    """owner_id NULL nunca casa com IN — e o comportamento desejado.

    Hoje essas credenciais sao legiveis por QUALQUER usuario autenticado,
    inclusive os segredos via GET /credentials/{id}/data.
    """
    session = _session_com([])   # o WHERE do banco nao a devolveria
    with _patch_session(session):
        out = await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={DONO})

    assert out == {}


# ── Escopo D: dono (quem disparou) OU compartilhado com o workspace ──────────

async def test_escopo_d_no_sql_e_dono_ou_workspace_sem_orfa():
    """A cláusula é (owner IS NOT NULL) AND (owner IN allowed OR workspace_id == ws)."""
    session = _session_com([])
    with _patch_session(session):
        await resolve_credentials_from_ids(
            [str(uuid4())], allowed_owner_ids={DONO}, shared_workspace_id="ws-1",
        )
    where = str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    )).split("WHERE", 1)[1]
    assert "owner_id IS NOT NULL" in where          # órfã nunca resolve
    assert "owner_id IN" in where and DONO in where  # de quem disparou
    assert "workspace_id" in where and "ws-1" in where  # compartilhada
    assert " OR " in where


async def test_escopo_d_sem_usuario_so_compartilhadas_no_sql():
    """triggered_by=None (cron/webhook): sem cláusula de dono, só a de workspace."""
    session = _session_com([])
    with _patch_session(session):
        await resolve_credentials_from_ids(
            [str(uuid4())], allowed_owner_ids=set(), shared_workspace_id="ws-1",
        )
    where = str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    )).split("WHERE", 1)[1]
    assert "workspace_id" in where and "ws-1" in where
    assert "owner_id IN" not in where               # sem usuário → sem cláusula de dono
    assert "owner_id IS NOT NULL" in where           # mas órfã segue barrada


async def test_credencial_compartilhada_resolve_mesmo_nao_sendo_de_quem_disparou():
    """Compartilhada com o workspace resolve para quem disparou, mesmo sendo de
    outro dono (o banco a devolve pela cláusula de workspace_id)."""
    cred = _cred("outro-dono")
    with _patch_session(_session_com([cred])):
        out = await resolve_credentials_from_ids(
            [str(cred.id)], allowed_owner_ids={MEMBRO}, shared_workspace_id="ws-1",
        )
    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_credencial_privada_de_outro_nao_resolve():
    """Sem compartilhamento e não sendo de quem disparou, o banco não a devolve —
    o WHERE a exclui. Simulamos com a sessão que só entrega o que o filtro deixaria."""
    with _patch_session(_session_com([])):    # o WHERE (dono/ws) não a devolveria
        out = await resolve_credentials_from_ids(
            [str(uuid4())], allowed_owner_ids={MEMBRO}, shared_workspace_id="ws-1",
        )
    assert out == {}


# ── last_used_at (F6): carimbo best-effort ───────────────────────────────────

def _statements(session):
    """Statements SQL que passaram por session.execute, como objetos."""
    return [c.args[0] for c in session.execute.await_args_list]


async def test_last_used_carimbado_e_commitado_na_sessao_propria():
    """Sessao propria (simulate): emite UPDATE em last_used_at e COMMITA.

    get_session_async faz rollback na saida — sem commit explicito o carimbo
    nao persistiria.
    """
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    with _patch_session(session), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    assert str(cred.id) in out
    updates = [s for s in _statements(session) if isinstance(s, Update)]
    assert len(updates) == 1, "esperado exatamente um UPDATE de last_used_at"
    session.commit.assert_awaited_once()


async def test_last_used_grava_horario_utc_sem_fuso():
    """`Credential.last_used_at` é `DateTime` sem fuso: o asyncpg recusa um
    datetime COM fuso ("can't subtract offset-naive and offset-aware
    datetimes"), e o savepoint do carimbo engolia o erro — no Postgres o
    last_used_at nunca era gravado. Os mocks daqui não têm driver, então a
    garantia é o valor que vai no UPDATE: naive e em UTC."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    await resolve_credentials_from_ids([str(cred.id)], allowed_owner_ids={DONO}, db=session)

    (update,) = [s for s in _statements(session) if isinstance(s, Update)]
    carimbo = update.compile().params["last_used_at"]
    assert carimbo.tzinfo is None
    agora_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs(agora_utc - carimbo) < timedelta(seconds=5)


async def test_last_used_nao_commita_na_sessao_do_request():
    """Sessao do request (db=): emite o UPDATE mas NAO commita — quem commita e
    o chamador, para nao gravar por engano o trabalho pendente dele."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    out = await resolve_credentials_from_ids(
        [str(cred.id)], allowed_owner_ids={DONO}, db=session,
    )

    assert str(cred.id) in out
    assert any(isinstance(s, Update) for s in _statements(session))
    session.commit.assert_not_awaited()


async def test_last_used_falha_nao_derruba_resolucao():
    """Se o UPDATE de auditoria falhar, a resolucao ainda entrega as credenciais."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    result = session.execute.return_value

    async def _execute(stmt, *a, **k):
        if isinstance(stmt, Update):
            raise RuntimeError("banco indisponivel para o carimbo")
        return result

    session.execute = AsyncMock(side_effect=_execute)
    with _patch_session(session), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    # O segredo foi resolvido apesar da falha best-effort no carimbo.
    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_last_used_falha_na_sessao_do_request_nao_faz_rollback():
    """Na sessão COMPARTILHADA do request, a falha do carimbo não pode chamar
    rollback — isso descartaria o trabalho pendente do chamador. O SAVEPOINT já
    reverteu o que era nosso; a resolução ainda entrega as credenciais e o
    chamador segue livre para commitar (evita o 500 no dispatch)."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    result = session.execute.return_value

    async def _execute(stmt, *a, **k):
        if isinstance(stmt, Update):
            raise RuntimeError("deadlock no carimbo")
        return result

    session.execute = AsyncMock(side_effect=_execute)
    out = await resolve_credentials_from_ids(
        [str(cred.id)], allowed_owner_ids={DONO}, db=session,
    )

    assert str(cred.id) in out
    session.rollback.assert_not_awaited()   # transação do chamador intocada


# ── Helper de escopo por workspace ───────────────────────────────────────────

async def test_workspace_credential_owners_une_dono_e_membros():
    """Dono e membros saem de uma consulta so (outerjoin), nao de dois SELECTs."""
    db = MagicMock()
    res = MagicMock()
    # Uma linha por membro; o dono se repete em todas.
    res.all.return_value = [(DONO, MEMBRO), (DONO, None)]
    db.execute = AsyncMock(return_value=res)

    assert await workspace_credential_owners(db, "ws-1") == {DONO, MEMBRO}
    assert db.execute.await_count == 1


async def test_workspace_credential_owners_sem_workspace():
    """Workflow legado sem workspace: escopo vazio, sem ir ao banco."""
    db = MagicMock(execute=AsyncMock())

    assert await workspace_credential_owners(db, None) == set()
    db.execute.assert_not_awaited()


# ── Guarda de credenciais da validação (assert_credentials_accessible) ──────

async def test_assert_recusa_credencial_alheia():
    """IDOR: a definition vem do corpo e o simulate() conecta ao banco."""
    alheia = uuid4()
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = []            # nenhuma pertence ao usuario
    db.execute = AsyncMock(return_value=res)

    with pytest.raises(CredentialAccessDeniedError, match=str(alheia)):
        await assert_credentials_accessible(db, [str(alheia)], MEMBRO)


async def test_assert_aceita_credencial_propria():
    minha = uuid4()
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = [(minha,)]
    db.execute = AsyncMock(return_value=res)

    await assert_credentials_accessible(db, [str(minha)], MEMBRO)


async def test_assert_recusa_uuid_invalido():
    db = MagicMock(execute=AsyncMock())

    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(db, ["nao-e-uuid"], MEMBRO)


# ── Guarda da validação com workspace: mesma clausula do dispatch ───────────
#
# O validate com workspace tem de aceitar EXATAMENTE o que o Executar resolveria:
# (owner IS NOT NULL) AND (owner == usuario OR workspace_id == ws). Nunca a lista
# de membros — senao um membro validaria (e o simulate() CONECTARIA) com a
# credencial PRIVADA de outro membro.

async def test_assert_accessible_sql_e_dono_ou_workspace_sem_orfa_e_sem_membros():
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(
            db, [str(uuid4())], MEMBRO, shared_workspace_id="ws-1",
        )

    where = _where(db)
    assert "owner_id IS NOT NULL" in where             # orfa compartilhada nao passa
    assert MEMBRO in where                             # o proprio usuario
    assert "workspace_id" in where and "ws-1" in where  # ou compartilhada com o ws
    assert " OR " in where
    assert "workspace_members" not in _sql(db)         # membros nao entram, nem por join


async def test_assert_accessible_sem_workspace_so_dono():
    """Sem workspace a clausula nem entra no SQL — nao vira `workspace_id = NULL`
    (nunca casaria) nem `IS NULL` (casaria a privada de qualquer dono)."""
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(db, [str(uuid4())], MEMBRO)

    where = _where(db)
    assert MEMBRO in where
    assert "owner_id IS NOT NULL" in where
    assert "workspace_id" not in where


async def test_assert_accessible_aceita_o_que_o_banco_devolve():
    """A decisao e do SQL: se o WHERE devolveu todos os ids (proprios ou
    compartilhados), passa em silencio, sem segunda checagem em Python."""
    minha, compartilhada = uuid4(), uuid4()
    db = _db_com_linhas([(minha,), (compartilhada,)])

    await assert_credentials_accessible(
        db, [str(minha), str(compartilhada)], MEMBRO, shared_workspace_id="ws-1",
    )


async def test_assert_accessible_mensagem_cita_o_workspace_e_o_uuid():
    """Quem recebe o 403 precisa saber O QUE foi recusado (o UUID, para achar o
    no) e que o compartilhamento com o workspace ja foi considerado — a saida e
    compartilhar a credencial, nao pedir a senha ao dono."""
    alheia = uuid4()
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError) as exc:
        await assert_credentials_accessible(
            db, [str(alheia)], MEMBRO, shared_workspace_id="ws-1",
        )

    msg = str(exc.value)
    assert str(alheia) in msg
    assert "workspace" in msg


async def test_assert_accessible_sem_workspace_nao_cita_workspace():
    """Sem workspace a guarda e "so dono": a dimensao de workspace nao aparece
    nem no SQL nem na mensagem de recusa."""
    alheia = uuid4()
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError) as exc:
        await assert_credentials_accessible(db, [str(alheia)], MEMBRO)

    msg = str(exc.value)
    assert str(alheia) in msg
    assert "workspace" not in msg
    assert "workspace_id" not in _where(db)


# ── Integracao: start_analysis monta o escopo (opção D) ──────────────────────
#
# Escopo de execução = {quem disparou (triggered_by)} + credenciais
# compartilhadas com o workspace do workflow. Ser MEMBRO do workspace não basta.

def _svc_com_workflow(workspace_id):
    from app.services.workflow_service import WorkflowService

    wf = MagicMock(id_hash="wf-1", workspace_id=workspace_id, flag_ative=True)
    svc = WorkflowService(MagicMock())
    return svc, wf


def _patches_do_dispatch(wf, resolve_fn):
    """Silencia tudo que start_analysis toca antes e depois do bloco de credencial."""
    return [
        patch("app.services.workflow_service._load_workflow",
              new=AsyncMock(return_value=(wf, {"nodes": [], "edges": []}))),
        patch("app.services.workflow_service._validate_trigger_inputs"),
        patch("app.services.workflow_service._collect_credential_ids", return_value=["cred-1"]),
        patch("app.services.workflow_service.resolve_credentials_from_ids", new=resolve_fn),
        patch("app.services.workflow_service._validate_trigger_credentials_only", new=AsyncMock()),
        patch("app.services.disabled_nodes_service.disabled_names",
              new=AsyncMock(return_value=set())),
        patch("app.services.workflow_execution_service._validate_no_disabled_nodes"),
        patch("flow.utils.workflow_contract.collect_subworkflow_definitions_recursive",
              new=AsyncMock(return_value={})),
        patch("app.services.workflow_service.WorkflowService._resolve_candidates",
              new=AsyncMock(return_value=[MagicMock()])),
        patch("app.services.workflow_service.WorkflowService._dispatch_job",
              new=AsyncMock(return_value=MagicMock(id="run-1"))),
    ]


async def test_start_analysis_escopo_e_quem_disparou_mais_compartilhadas():
    """Opção D: escopo = {quem disparou} + shared_workspace_id do workflow —
    NÃO o conjunto de membros do workspace."""
    from contextlib import ExitStack

    svc, wf = _svc_com_workflow("ws-1")
    capturado = {}

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):
        capturado["allowed"] = set(allowed_owner_ids or [])
        capturado["shared_ws"] = shared_workspace_id
        capturado["db"] = db
        return {}

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        await svc.start_analysis("wf-1", triggered_by=MEMBRO)

    # Só quem disparou entra como dono; DONO (outro membro) NÃO.
    assert capturado["allowed"] == {MEMBRO}
    assert DONO not in capturado["allowed"]
    assert capturado["shared_ws"] == "ws-1"
    # A sessao do request vai junto: sem ela o resolver abria uma segunda
    # conexao do mesmo pool sem soltar a primeira.
    assert capturado["db"] is svc.crud.db


async def test_start_analysis_cron_sem_usuario_so_alcanca_compartilhadas():
    """Disparo sem usuário (triggered_by=None): dono vazio, só resolvem as
    credenciais compartilhadas com o workspace."""
    from contextlib import ExitStack

    svc, wf = _svc_com_workflow("ws-1")
    capturado = {}

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):
        capturado["allowed"] = set(allowed_owner_ids or [])
        capturado["shared_ws"] = shared_workspace_id
        return {}

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        await svc.start_analysis("wf-1")   # sem triggered_by

    assert capturado["allowed"] == set()
    assert capturado["shared_ws"] == "ws-1"


async def test_start_analysis_recusa_workflow_sem_workspace():
    """Sem workspace nao ha a quem confiar — falha em vez de resolver aberto."""
    from contextlib import ExitStack

    svc, wf = _svc_com_workflow(None)

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):  # pragma: no cover
        raise AssertionError("não deveria resolver credencial sem workspace")

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        with pytest.raises(CredentialAccessDeniedError):
            await svc.start_analysis("wf-1", triggered_by=MEMBRO)
