# app/core/authorization/credential_loader.py
"""
Resolução de credenciais para execução — com escopo de autorização obrigatório.

Antes a busca era por ID puro (`WHERE id IN (...)`), sem olhar dono nem
workspace. Como o `credential_id` fica em texto puro na definition e é legível
por qualquer membro que abra o workflow, bastava copiá-lo para um workflow de
outro workspace — criado pelo próprio atacante — para usar a credencial alheia
indefinidamente. O mesmo buraco valia para `POST /workflows/validate`, que
aceita uma definition arbitrária e chega a CONECTAR ao banco pelo `simulate()`.

O escopo tem duas dimensões (basta uma casar): os `owner_id` autorizados e o
workspace de compartilhamento. Na EXECUÇÃO, resolve-se uma credencial se ela é
de QUEM DISPAROU (`triggered_by`) OU está EXPLICITAMENTE compartilhada com o
workspace do workflow (`workspace_id`). Ser apenas membro do workspace não
basta — senão um membro usaria a credencial PRIVADA de outro só copiando o
`credential_id` da definition. Disparos sem usuário (cron/webhook) alcançam
apenas as credenciais compartilhadas. Na SIMULAÇÃO/validação, o escopo é o
usuário autenticado e, quando a validação informa um workspace, as credenciais
compartilhadas com ele — a MESMA cláusula, aplicada antes de conectar
(`assert_credentials_accessible`) e durante o `simulate()` (`credential_scope`).
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Collection, Iterable, List
from uuid import UUID

from sqlalchemy.future import select

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger

from app.models.credential import Credential
from app.core.db import get_session_async
from app.core.utils.encryption import decrypt_credential_data

logger = get_logger(__name__)


class CredentialScopeMissing(RuntimeError):
    """Resolução tentada sem escopo de autorização.

    Erro de programação, não de dados: sinaliza um call site novo que não
    declarou de quem as credenciais podem ser. Falhar alto aqui é o que impede
    a regressão silenciosa para o comportamento antigo.
    """


@dataclass(frozen=True)
class EscopoDeCredenciais:
    """O que um `credential_scope` delimita: donos autorizados e, opcionalmente,
    o workspace cujas credenciais compartilhadas também valem.

    São as MESMAS duas dimensões dos kwargs de `resolve_credentials_from_ids`.
    O ContextVar carregava só a de dono, e a validação com workspace ficava
    incoerente: a guarda (`assert_credentials_accessible`) aceitava a credencial
    compartilhada, mas o `simulate()` — que não recebe parâmetros — não a
    resolvia, porque o escopo implícito não sabia do workspace.
    """
    owner_ids: frozenset[str]
    shared_workspace_id: str | None = None


# Escopo implícito para código que não recebe parâmetros — hoje só o `simulate()`
# dos nós, invocado genericamente por `simulate_runner`.
_scope: ContextVar[EscopoDeCredenciais | None] = ContextVar("credential_scope", default=None)


@contextmanager
def credential_scope(owner_ids: Iterable[str], shared_workspace_id: str | None = None):
    """Delimita de quem as credenciais podem ser resolvidas no bloco.

    `shared_workspace_id` estende o escopo às credenciais EXPLICITAMENTE
    compartilhadas com esse workspace (a mesma regra do dispatch). Só o passe
    quando o chamador já verificou que o usuário pertence ao workspace — o
    resolver confia no que recebe aqui.
    """
    token = _scope.set(EscopoDeCredenciais(frozenset(owner_ids), shared_workspace_id))
    try:
        yield
    finally:
        _scope.reset(token)


async def workspace_credential_owners(db, workspace_id: str | None) -> set[str]:
    """Usuários com acesso ao workspace: o dono mais os membros.

    Serve a checagens de PERTENCIMENTO — hoje, o relatório de mudança de
    workspace, que avisa quais donos de credencial deixam de alcançar o destino.
    NÃO é escopo de credenciais: passá-lo como `allowed_owner_ids` (ou usá-lo
    numa guarda) entregaria a credencial PRIVADA de cada membro a qualquer outro
    membro que copiasse o `credential_id` da definition. O escopo de resolução é
    {quem disparou} + `shared_workspace_id` — ver `resolve_credentials_from_ids`
    e `assert_credentials_accessible`.

    Um workspace inexistente/deletado devolve conjunto vazio, e o chamador
    decide se isso é erro.
    """
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    if not workspace_id:
        return set()

    # Dono e membros numa consulta so. Eram dois SELECTs sequenciais dentro do
    # caminho quente do POST /execute — e o segundo nem filtrava o workspace por
    # `deleted_at`, de modo que um workspace na lixeira continuava autorizando
    # suas credenciais pela lista de membros. O outerjoin parte do Workspace,
    # entao workspace inexistente ou deletado nao devolve linha nenhuma.
    rows = (await db.execute(
        select(Workspace.owner_id, WorkspaceMember.user_id)
        .outerjoin(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id_hash)
        .where(
            Workspace.id_hash == workspace_id,
            Workspace.deleted_at.is_(None),
        )
    )).all()

    return {uid for row in rows for uid in row if uid}


async def assert_credentials_accessible(
    db, credential_ids: Iterable[str], owner_id: str, shared_workspace_id: str | None = None,
) -> None:
    """Recusa se algum id não for de `owner_id` nem estiver compartilhado com o workspace.

    Guarda da validação (`validate_service`), que aceita uma definition
    arbitrária: o `simulate()` de nós dinâmicos chega a CONECTAR ao banco,
    então um credential_id alheio ali significava executar SQL na
    infraestrutura de outro usuário. Barrar aqui dá 403 claro antes de
    qualquer conexão. As escritas do `WorkflowService` usam a mesma guarda.

    A cláusula é a MESMA do dispatch (`_resolver_na_sessao`): (id pedido) AND
    (owner_id IS NOT NULL) AND (owner_id == usuário OR workspace_id ==
    shared_workspace_id). Manter as duas iguais garante que o validate aceite
    exatamente o que o Executar resolveria — nem mais (conectaria a uma
    credencial que a execução recusaria) nem menos (403 numa credencial que a
    execução usa). `owner_id IS NOT NULL` é fail-closed: uma órfã compartilhada
    não passa. A cláusula de workspace só entra quando `shared_workspace_id` é
    informado; sem ele a guarda é "só dono".

    Nunca troque o workspace por `workspace_credential_owners`: ser membro do
    workspace não dá direito à credencial PRIVADA de outro membro.
    """
    from sqlalchemy import or_

    from app.core.exceptions import CredentialAccessDeniedError

    uuid_ids: List[UUID] = []
    for cid in credential_ids:
        try:
            uuid_ids.append(UUID(str(cid)))
        except Exception:
            raise CredentialAccessDeniedError(f"credential_id inválido: {cid!r}")
    if not uuid_ids:
        return

    escopo = [Credential.owner_id == owner_id]
    if shared_workspace_id:
        escopo.append(Credential.workspace_id == shared_workspace_id)

    acessiveis = {
        str(cid) for (cid,) in (await db.execute(
            select(Credential.id).where(
                Credential.id.in_(uuid_ids),
                Credential.owner_id.isnot(None),
                or_(*escopo),
            )
        )).all()
    }

    recusadas = sorted(str(uid) for uid in uuid_ids if str(uid) not in acessiveis)
    if recusadas:
        logger.warning(
            "Usuário '%s' referenciou credencial(is) fora do seu escopo "
            "(dono, ou compartilhada com o workspace %r): %s",
            owner_id, shared_workspace_id, recusadas,
        )
        raise CredentialAccessDeniedError(
            "A definição referencia credenciais que não pertencem a você"
            + (" nem estão compartilhadas com o workspace informado" if shared_workspace_id else "")
            + f": {', '.join(recusadas)}."
        )


def validade_da_credencial(expires_at_raw) -> str:
    """O que o `expires_at` gravado no `data` da credencial diz dela:
    `"valida"` (ainda vale, ou não tem validade), `"expirada"` ou
    `"invalida"` (não é uma data — ignorada por segurança na resolução).

    É a regra da resolução (`_resolver_na_sessao`); a validação a usa para
    avisar ANTES do Executar que a credencial do nó não vai ser resolvida.
    """
    if not expires_at_raw:
        return "valida"
    try:
        expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
    except ValueError:
        return "invalida"
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return "expirada" if expires_at < datetime.now(timezone.utc) else "valida"


async def tipos_e_validades(db, credential_ids: Iterable[str]) -> dict:
    """`{id: (tipo, validade, expires_at)}` das credenciais pedidas — só o
    tipo e a validade, nunca o `data` decifrado.

    Para a validação dizer o que a resolução faria em silêncio: deixar de fora
    uma credencial vencida, ou de um tipo que o nó não aceita. Chame DEPOIS de
    `assert_credentials_accessible` — aqui não há escopo.
    """
    uuid_ids: List[UUID] = []
    for cid in credential_ids:
        try:
            uuid_ids.append(UUID(str(cid)))
        except Exception:
            continue
    if not uuid_ids:
        return {}
    rows = (await db.execute(
        select(Credential.id, Credential.type, Credential.data).where(Credential.id.in_(uuid_ids))
    )).all()
    saida = {}
    for cid, tipo, data in rows:
        expires_at_raw = (data or {}).get("expires_at") if isinstance(data, dict) else None
        saida[str(cid)] = (tipo, validade_da_credencial(expires_at_raw), expires_at_raw)
    return saida


async def _explain_missing(session, uuid_ids: List[UUID], resolvidos: set[str],
                           allowed: Collection[str],
                           shared_workspace_id: str | None = None) -> None:
    """Loga por que cada credencial pedida não foi resolvida.

    Sem isto o sintoma chega ao operador como "o workflow parou de funcionar".
    Consulta apenas id/owner_id/workspace_id — nunca toca em `data`.
    """
    faltando = [uid for uid in uuid_ids if str(uid) not in resolvidos]
    if not faltando:
        return

    rows = (await session.execute(
        select(Credential.id, Credential.owner_id, Credential.workspace_id)
        .where(Credential.id.in_(faltando))
    )).all()
    encontrados = {str(cid): (owner, ws) for cid, owner, ws in rows}

    for uid in faltando:
        cid = str(uid)
        if cid not in encontrados:
            logger.warning("Credencial %s não existe (ou foi removida).", cid)
            continue
        owner, ws = encontrados[cid]
        if owner is None:
            logger.warning(
                "Credencial %s não tem dono (owner_id nulo) e por isso não é resolvida. "
                "Atribua um dono: UPDATE credentials SET owner_id = '<user_id_hash>' WHERE id = '%s';",
                cid, cid,
            )
        elif owner not in allowed and not (shared_workspace_id and ws == shared_workspace_id):
            # Escopo D: não é de quem disparou e não está compartilhada com o
            # workspace do workflow. A saída é o dono compartilhar a credencial
            # com o workspace (ou disparar quem é dono dela).
            logger.warning(
                "Credencial %s pertence a '%s' e não está compartilhada com o workspace "
                "deste workflow — não resolvida. Compartilhe-a com o workspace ou execute "
                "como o dono dela.",
                cid, owner,
            )
        # Restante: existe, no escopo, mas expirada — já logado no laço principal.


async def resolve_credentials_from_ids(
    credential_ids: list[str],
    *,
    allowed_owner_ids: Collection[str] | None = None,
    shared_workspace_id: str | None = None,
    db=None,
) -> dict:
    """Resolve e descriptografa credenciais, restrito ao escopo de autorização.

    Uma credencial é resolvida quando (id pedido) E (dono NÃO nulo) E
    (`owner_id ∈ allowed_owner_ids` OU `workspace_id == shared_workspace_id`):

    - `allowed_owner_ids` — donos autorizados. Na execução é {quem disparou}
      (ver workflow_service); na simulação/validação, o próprio usuário.
    - `shared_workspace_id` — o workspace do workflow em execução (ou o que o
      a validação informou). Casa com credenciais EXPLICITAMENTE compartilhadas
      com ele (workspace_id preenchido), de qualquer dono. É o que permite um
      disparo sem usuário (cron/webhook) alcançar as credenciais compartilhadas
      do workspace.

    Os dois kwargs são o escopo INTEIRO assim que qualquer um deles é passado.
    Só na ausência de AMBOS vale o `credential_scope` ativo — que carrega as
    mesmas duas dimensões (`EscopoDeCredenciais`). Não há mistura: um kwarg
    explícito nunca é completado pelo ContextVar, para que o escopo de um call
    site seja sempre o que está escrito nele.

    Sem NENHUM dos dois escopos (nem kwargs, nem credential_scope) levanta
    `CredentialScopeMissing` — nunca resolve "aberto". Dono nulo (órfã) nunca
    resolve, mesmo compartilhada: fail-closed.

    `db` é a sessão do chamador, quando ele já tem uma. Sem esse parâmetro esta
    função abria a SUA própria sessão mesmo rodando dentro do request — uma
    espera aninhada por conexão do MESMO pool (8 + 5 por worker), com a primeira
    conexão retida enquanto a segunda era aguardada. A partir de ~7 disparos
    simultâneos no mesmo worker o botão Executar ficava pendurado no
    `pool_timeout` de 30 s. Quem não tem sessão (simulate/credential_scope)
    continua caindo no `get_session_async()`.
    """
    if allowed_owner_ids is None and shared_workspace_id is None:
        # Só sem NENHUM kwarg de escopo é que o ContextVar entra — e entra com as
        # duas dimensões de uma vez.
        escopo = _scope.get()
        if escopo is None:
            raise CredentialScopeMissing(
                "resolve_credentials_from_ids exige allowed_owner_ids, shared_workspace_id "
                "ou um credential_scope ativo."
            )
        allowed = escopo.owner_ids
        shared_workspace_id = escopo.shared_workspace_id
    else:
        # Kwargs explícitos são o escopo INTEIRO: o ContextVar nunca completa a
        # dimensão ausente. Senão um `allowed_owner_ids` passado dentro de um
        # `credential_scope(..., shared_workspace_id=...)` herdaria o workspace
        # sem o chamador saber — e vice-versa.
        allowed = allowed_owner_ids

    # Converte strings para UUID objects — asyncpg não faz cast automático para colunas UUID
    uuid_ids: List[UUID] = []
    for cid in credential_ids:
        try:
            uuid_ids.append(UUID(str(cid)))
        except Exception as exc:
            logger.warning("Falha ao converter credential_id '%s' para UUID: %s", cid, exc)
    if not uuid_ids:
        return {}

    allowed = list(allowed) if allowed is not None else []
    if not allowed and not shared_workspace_id:
        logger.warning(
            "Escopo de credenciais vazio — %d credencial(is) não serão resolvidas.",
            len(uuid_ids),
        )
        return {}

    if db is not None:
        # Sessão do request: quem commita é o chamador. Não commitamos aqui para
        # não gravar por engano trabalho pendente dele.
        return await _resolver_na_sessao(
            db, uuid_ids, allowed, shared_workspace_id=shared_workspace_id, own_session=False
        )

    async with get_session_async() as session:
        # Sessão própria (simulate): o get_session_async faz rollback na saída,
        # então o carimbo de last_used_at só persiste se commitarmos aqui.
        return await _resolver_na_sessao(
            session, uuid_ids, allowed, shared_workspace_id=shared_workspace_id, own_session=True
        )


async def _marcar_last_used(session, usados: List[UUID], now, *, own_session: bool) -> None:
    """Carimba last_used_at nas credenciais efetivamente resolvidas — best-effort.

    Roda no caminho MAIS quente (POST /execute). Regras de segurança:
    - Usa a MESMA sessão já em mãos (nunca abre conexão nova — foi por causa de
      esgotamento de pool que o parâmetro `db` existe).
    - Nunca é fatal: qualquer falha aqui é engolida e logada; a execução do
      workflow não pode cair porque um carimbo de auditoria falhou.
    - Só commita quando a sessão é NOSSA; na do request, o chamador commita.
    """
    if not usados:
        return
    from sqlalchemy import update
    try:
        # SAVEPOINT (begin_nested) isola a falha do carimbo. Sem ele, um erro no
        # UPDATE (lock, statement_timeout, deadlock entre dois dispatches na mesma
        # credencial) deixaria a transação COMPARTILHADA do request em
        # PendingRollback — e o commit seguinte do WorkflowRun explodiria,
        # derrubando o dispatch com 500. Exatamente o "jamais derruba a execução"
        # que este bloco promete. Com o savepoint, a falha reverte só o ponto
        # aninhado; a transação do chamador segue íntegra e ele commita normal.
        async with session.begin_nested():
            await session.execute(
                update(Credential).where(Credential.id.in_(usados)).values(last_used_at=now)
            )
        if own_session:
            await session.commit()
    except Exception as exc:  # best-effort — jamais derruba a execução
        logger.warning("Falha best-effort ao marcar last_used_at (%d cred): %s", len(usados), exc)
        # No caminho do request NÃO tocamos na transação do chamador: o savepoint
        # já reverteu o que era nosso. Na sessão própria, desfazemos o que abrimos.
        if own_session:
            try:
                await session.rollback()
            except Exception:
                pass


async def _resolver_na_sessao(
    session, uuid_ids: List[UUID], allowed: list,
    *, shared_workspace_id: str | None = None, own_session: bool = False,
) -> dict:
    """Corpo da resolução, já com uma sessão em mãos (própria ou do request)."""
    from sqlalchemy import or_

    # Naive, em UTC: `Credential.last_used_at` é `DateTime` SEM fuso, e o
    # asyncpg recusa um datetime com fuso para essa coluna ("can't subtract
    # offset-naive and offset-aware datetimes"). O savepoint do carimbo engolia
    # o erro, e no Postgres o last_used_at nunca era gravado. Mesmo helper do
    # carimbo dos tokens de API (api_token_service).
    now = utc_now_naive()

    # Escopo: dono autorizado (quem disparou) OU compartilhada com o workspace
    # do workflow. `owner_id IS NOT NULL` é fail-closed: uma credencial órfã
    # nunca resolve, nem que casasse pela cláusula de workspace — o mesmo
    # comportamento que o antigo `owner_id.in_(...)` tinha por consequência (IN
    # nunca casa NULL), agora explícito porque a cláusula de workspace poderia
    # alcançar uma órfã compartilhada.
    escopo = []
    if allowed:
        escopo.append(Credential.owner_id.in_(allowed))
    if shared_workspace_id:
        escopo.append(Credential.workspace_id == shared_workspace_id)
    if not escopo:
        # Guardado pelos chamadores, mas defensivo: sem escopo, não resolve nada.
        return {}

    result = await session.execute(
        select(Credential).where(
            Credential.id.in_(uuid_ids),
            Credential.owner_id.isnot(None),
            or_(*escopo),
        )
    )
    credentials = result.scalars().all()

    auth = {}
    usados: List[UUID] = []
    for cred in credentials:
        # Ignora credenciais expiradas (expires_at está dentro do JSONB data, não como coluna)
        expires_at_raw = (cred.data or {}).get("expires_at")
        validade = validade_da_credencial(expires_at_raw)
        if validade == "expirada":
            logger.warning("Credencial %s expirada em %s — ignorada.", cred.id, expires_at_raw)
            continue
        if validade == "invalida":
            logger.warning(
                "Credencial %s com expires_at inválido: %r — ignorada por segurança.",
                cred.id, expires_at_raw,
            )
            continue
        # `decrypt_credential_data` devolve um dict NOVO: nada é atribuído de
        # volta ao objeto ORM, então rodar na sessão do request não faz o commit
        # seguinte gravar credencial descriptografada no banco.
        decrypted = decrypt_credential_data(cred.data)
        decrypted["type"] = cred.type
        auth[str(cred.id)] = decrypted
        usados.append(cred.id)

    await _explain_missing(session, uuid_ids, set(auth), allowed, shared_workspace_id)
    await _marcar_last_used(session, usados, now, own_session=own_session)

    return auth
