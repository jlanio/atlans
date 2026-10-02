# app/services/workflow_execution_service.py
# Orquestração e despacho de execuções de workflow para executores.

import asyncio
import json
import random
import time
from app.core.utils.logger import get_logger
import uuid
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import func, select as sa_select, update as sa_update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core.authorization.workflow_access import (
    exigir_papel,
    papel_no_workspace_do_run,
)
from app.core.config import policy_routing_enabled
from app.core.rbac import ROLE_OPERATOR
from app.core.executor_connections import _capacity_is_full, executor_registry
from app.core.exceptions import (
    NoExecutorAvailableError,
    WorkflowDecryptionError,
    WorkflowInactiveError,
    WorkflowNotFoundError,
)
from app.core.job_crypto import build_job_message
from app.services.fundos_do_mapa import injetar_fundos_de_mapa
from app.services.fuso_do_agendamento import injetar_fuso_do_agendamento
from app.core.utils.encryption import decrypt_workflow_connections
from app.core.utils.workflow_nodes import node_props
from app.crud.workflow_crud import WorkflowCRUD
from app.models.executor import Executor
from app.models.models import Workflow, WorkflowRun
from app.models.workspace import Workspace
from app.services import workspace_executor_service as politica
from app.services.credential_resolver import inject_credentials
from app.services.fechamento_de_run import ABERTOS, REPETIVEL, fechar_runs
from app.services.user_executor_service import get_default_agents

_logger = get_logger(__name__)

# Tamanho do payload ja serializado a partir do qual a cifra do envelope sai do
# event loop e vai para uma thread. Abaixo disso o salto de thread custa mais do
# que a cifra em si.
_LIMIAR_CIFRA_EM_THREAD = 256 * 1024


@dataclass
class DispatchResult:
    """Resultado do despacho de um workflow para um executor."""
    id: str
    has_response_node: bool = False


class CandidateList(list):
    """Lista ordenada de executores candidatos, anotada com a política.

    É uma `list` de propósito: `_dispatch_job` e os testes existentes iteram a
    lista e passam MagicMocks; os atributos abaixo são opcionais e lidos com
    `getattr`. `tiers` mapeia executor → nível em que ele entra na cadeia
    ("primary" | "fallback" | "pool"); `allowed` é o conjunto permitido pela
    política (spec §5.3), `None` no caminho legado; `mode` e
    `exhausted_message`/`exhausted_category` alimentam a mensagem por política.
    """
    tiers: dict[str, str]
    allowed: set[str] | None
    mode: str | None
    exhausted_message: str | None
    exhausted_category: str | None

    def __init__(self, executores=(), *, tiers=None, allowed=None, mode=None,
                 exhausted_message=None, exhausted_category=None):
        super().__init__(executores)
        self.tiers = dict(tiers or {})
        self.allowed = allowed
        self.mode = mode
        self.exhausted_message = exhausted_message
        self.exhausted_category = exhausted_category


def _safe_pinned_outputs(raw: dict | None, pin_metadata: dict | None = None) -> dict:
    """Filtra `pinned_outputs` para envio ao executor.

    Passa só o nó que tem metadata correspondente. `pin_metadata` é escrito
    exclusivamente pelo pin explícito de quem está usando, então ele é a prova
    de que alguém PEDIU aquele congelamento; o que estiver em `pinned_outputs`
    sem par ali é órfão — resto de um nó apagado, de um fluxo restaurado, de um
    unpin que não limpou tudo.

    **Órfã não passa, nem quando não há metadata nenhuma.** A versão anterior
    curto-circuitava (`if meta_keys and nid not in meta_keys`), de modo que a
    coluna vazia liberava TODAS as entradas. O efeito não era teórico:

    - uma órfã com `__pin_s3_key__` faz o executor baixar o objeto e PULAR o nó
      (`flow/executor/core.py`), e a validade é lida de
      `pin_metadata[node_id]` — sem metadata não há `expires_at`, então essa
      órfã **nunca expira**. O fluxo termina verde, com dado velho, e nada na
      resposta diz que veio de cache;
    - e o caminho não dependia de dado legado: com `{A, B}` em `pinned_outputs`
      e só `A` em `pin_metadata`, B era descartada; desfixar A grava
      `pin_metadata = None` (`pin_service.py`), a coluna esvazia e **B
      ressuscitava na execução seguinte**. Desfixar um nó ressuscitava o pin de
      outro.

    O custo aceito: um fluxo que ainda dependesse de pin sem metadata passa a
    re-executar o nó. Mais lento uma vez, e correto.
    """
    if not raw:
        return {}
    meta_keys = set((pin_metadata or {}).keys())
    safe = {}
    for nid, val in raw.items():
        # Sem metadata é órfã, e órfã não vai para o executor.
        if nid not in meta_keys:
            continue
        if isinstance(val, dict) and ("__pin_s3_key__" in val or not val):
            safe[nid] = val
        else:
            # Dados brutos (legado) — marca como vazio para auto-pin na próxima execução
            safe[nid] = {}
    return safe


def _get_redis():
    """Retorna o pool Redis centralizado."""
    from app.core.redis import get_redis_pool
    return get_redis_pool()


def _validate_no_disabled_nodes(definition: dict, disabled: set[str]) -> None:
    """Bloqueia o dispatch se o workflow contem nodes desabilitados pelo admin.

    Levantado ANTES do envelope ser criado e ANTES do executor ser contatado:
    nem o servidor reserva recursos para um workflow que vai falhar no
    NodeFactory.create() no executor. O operador ve mensagem explicita citando
    quais nodes precisam de reabilitacao.
    """
    if not disabled:
        return
    from app.core.exceptions import DisabledNodesInWorkflowError

    offenders = sorted({
        n.get("name") for n in (definition.get("nodes") or [])
        if n.get("name") in disabled
    })
    if offenders:
        raise DisabledNodesInWorkflowError(
            "Workflow contém node(s) desabilitados pelo admin: "
            f"{', '.join(offenders)}. "
            "Reabilite via /admin/settings ou substitua os nodes."
        )


def _validate_trigger_inputs(definition: dict, inputs: dict | None) -> None:
    """Valida os inputs do dispatch contra o payload_schema dos triggers.

    Nesta primeira versão cobrimos WebhookTrigger, que é o único trigger com
    `payload_schema` configurado pelo usuário. Aborta o dispatch com
    WorkflowInputValidationError (422) antes de despachar para o executor,
    devolvendo uma mensagem com o caminho exato do campo e o motivo da falha.
    """
    from jsonschema import Draft7Validator
    from app.core.exceptions import WorkflowInputValidationError

    inputs = inputs or {}
    for node in definition.get("nodes", []):
        if node.get("name") != "WebhookTrigger":
            continue
        props = node_props(node)
        schema = props.get("payload_schema")
        if not (isinstance(schema, dict) and schema.get("properties")):
            continue

        field = (props.get("payloadField") or "").strip()
        # Mesma resolução do trigger:
        #   - field definido → inputs[field]
        #   - field vazio    → inputs ja eh o payload
        raw = inputs.get(field) if field else inputs
        if raw is None:
            payload: dict = {}
        elif isinstance(raw, str):
            try:
                import json as _json
                payload = _json.loads(raw)
            except Exception:
                payload = {field or "payload": raw}
        elif isinstance(raw, dict):
            payload = raw
        else:
            payload = {field or "payload": raw}

        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
        if not errors:
            continue
        parts = [f"'{err.json_path or '$'}': {err.message}" for err in errors]
        if len(parts) == 1:
            detail = f"Payload inválido em {parts[0]}"
        else:
            detail = f"Payload inválido — {len(parts)} erros: " + "; ".join(parts)
        raise WorkflowInputValidationError(detail)


async def _validate_trigger_credentials_only(
    definition: dict, request=None, *, pre_resolved: dict | None = None,
    allowed_owner_ids=None, autenticar_entrada: bool = True,
) -> None:
    """
    Valida apenas nós do tipo trigger com credencial vinculada (ex: WebhookTrigger).
    Não injeta connectionString em nós datasource — isso é feito pelo worker em runtime.

    Se pre_resolved for fornecido, usa esse dicionário em vez de ir ao banco novamente.
    Fail-closed: se um trigger declara credential_id mas a credencial não está
    presente em `resolved` (ausente/expirada/deletada), lança HTTP 403 — isso
    vale em TODOS os caminhos, e é o que pega credencial apagada.

    `autenticar_entrada=False` pula só a autenticação de quem chamou (o token do
    webhook), que não faz sentido num disparo já autenticado por sessão.
    """
    from fastapi import HTTPException
    from app.core.authorization.credential_validators import validate_credential_by_type

    trigger_nodes = [
        (n, node_props(n).get("credential_id"))
        for n in definition.get("nodes", [])
        if n.get("type") == "trigger" and node_props(n).get("credential_id")
    ]
    if not trigger_nodes:
        return

    cred_ids = [cid for _, cid in trigger_nodes]
    if pre_resolved is not None:
        resolved = {cid: pre_resolved[cid] for cid in cred_ids if cid in pre_resolved}
    else:
        from app.core.authorization.credential_loader import resolve_credentials_from_ids
        resolved = await resolve_credentials_from_ids(
            cred_ids, allowed_owner_ids=allowed_owner_ids,
        )

    for _, cred_id in trigger_nodes:
        cred = resolved.get(cred_id)
        if not cred:
            # Trigger declara credencial mas ela não pôde ser resolvida — tratar
            # como falha de autenticação (nunca fail-open silencioso).
            raise HTTPException(
                status_code=403,
                detail="Credencial do trigger não pôde ser resolvida (ausente, expirada ou removida).",
            )
        await validate_credential_by_type(
            cred, request=request, autenticar_entrada=autenticar_entrada,
        )


def _collect_credential_ids(*definitions: dict) -> list[str]:
    """Extrai IDs únicos de credenciais dos nós de uma ou mais definitions.

    Aceita várias porque a cadeia de sub-fluxos também entra no envelope: um
    nó de banco DENTRO de um sub-fluxo precisa da credencial resolvida igual
    a um do fluxo raiz. Enquanto isto só olhava a raiz, esse nó chegava ao
    executor com `credential_id` e sem `connectionString`, e falhava com
    "deve ser resolvido antes da execução" — uma mensagem que descreve um
    problema do servidor como se fosse configuração do nó.

    Usa `node_props` para garantir que coletor e validador concordem na
    extração — ver docstring de `node_props`.
    """
    return list({
        cid
        for definition in definitions
        for node in (definition or {}).get("nodes", [])
        if (cid := node_props(node).get("credential_id"))
    })


async def _load_workflow(
    crud: WorkflowCRUD,
    id_hash: str,
    request: Request | None,
    workflow: Workflow | None = None,
) -> tuple[Workflow, dict]:
    """Carrega workflow, valida estado e descriptografa a definition.

    `workflow` é o objeto que o chamador já tem em mãos. Os três disparos
    autenticados (execute, retry, webhook) passam pela dependency de
    autorização, que JÁ carregou e descriptografou o workflow; refazer o
    `SELECT` aqui transferia e desserializava a coluna `definition` inteira uma
    segunda vez (~1,7 MB e ~4,4 ms de `json.loads` num fluxo grande) para
    descartar o resultado — o identity map do SQLAlchemy devolve o mesmo objeto.
    O agendador dispara só pelo hash e continua caindo no SELECT.

    As validações valem igual nos dois caminhos: são aplicadas sobre o objeto,
    não sobre o resultado da consulta.
    """
    wf = workflow if workflow is not None else await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")
    if not wf.flag_ative:
        raise WorkflowInactiveError(f"Workflow {id_hash} está desativado.")

    try:
        definition = decrypt_workflow_connections(wf.definition)
    except Exception as e:
        raise WorkflowDecryptionError(
            f"Não foi possível descriptografar a definição do workflow {id_hash}."
        ) from e

    # Validação de trigger credentials movida para start_analysis (resolve 1 vez)
    return wf, definition


async def _disponivel(executor_id: str) -> bool:
    """Candidato a ser TENTADO: presença True ou "não sei" (spec §5.1).

    Só a presença confirmadamente ausente exclui. Um blip do Redis ou uma
    reconexão em curso não podem tirar um executor vivo da lista — o
    `send_job` real dirá se ele conecta, e o failover segue se não.
    """
    return (await executor_registry.presence_or_unknown(executor_id)) is not False


# Runs que ocupam um executor aos olhos do servidor: despachados e ainda sem
# desfecho. `pending` entra porque o INSERT já grava o host antes do envio.
_STATUS_EM_VOO = ("pending", "running")

# Padrões do executor (EXECUTOR_MAX_CONCURRENT / EXECUTOR_MAX_QUEUE_SIZE), para
# quem não declarou os seus nem tem o teto do banco legível.
_VAGAS_PADRAO = 4
_FILA_PADRAO = 50

# Sorteio da ordem (uniforme em [0, 1)). Função do módulo para os testes
# fixarem a ordem; não é segurança, só espalhamento.
_desempate = random.random


def _contagem(valor) -> int:
    """Inteiro não negativo, ou 0 — a capacidade vem de fora (executor/Redis)."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        return 0
    return max(valor, 0)


def _menor_positivo(*valores: int) -> int:
    """O menor dos valores positivos; 0 se nenhum é."""
    return min((v for v in valores if v > 0), default=0)


def _cheio_pela_declarada(cap: dict) -> bool:
    """A MESMA conta do `is_full` do `send_job`: se ela diz cheio, o envio vai
    ser recusado. Capacidade ilegível não é "cheio" — quem decide é o envio."""
    if not cap:
        return False
    try:
        return _capacity_is_full(cap)
    except TypeError:
        return False


@dataclass(frozen=True)
class _Situacao:
    """Como um executor está, para a ordem do despacho (`_situacoes`)."""
    carga: int              # jobs que ele tem (rodando + na fila local)
    vagas: int              # execuções simultâneas que ele comporta
    fila: int               # jobs que a fila local dele comporta além das vagas
    cheio_declarado: bool   # o último `capacity` dele já bate no teto

    @property
    def livres(self) -> int:
        return self.vagas - self.carga

    @property
    def cheio(self) -> bool:
        """Não cabe mais nada: pelo relatório dele (o send_job recusa) ou pela
        contagem do servidor (a fila local dele recusa, e o run FALHA — sem
        failover, porque o envio já tinha sido aceito)."""
        return self.cheio_declarado or self.carga >= self.vagas + self.fila

    @property
    def ocupacao(self) -> float:
        """Ocupação com mais este job: (carga + 1) / vagas."""
        return (self.carga + 1) / self.vagas


async def _contadas_pelo_servidor(db: AsyncSession, ids: list[str]) -> dict[str, int] | None:
    """Runs `pending`/`running` de cada executor, contados no banco; None se a
    contagem não saiu.

    É a carga que todos os workers da API enxergam igual e que muda no
    instante do despacho: o INSERT do run, com o host, é commitado antes de o
    job sair. A declarada pelo executor só chega a cada 10 s — numa rajada,
    todos os jobs iam para quem estava vazio no último relatório.

    Best-effort, num SAVEPOINT aberto na CONEXÃO da sessão:
    - no Postgres, um erro nesta consulta (lock_timeout, statement_timeout,
      cancelamento) abortaria a transação do request, e o INSERT do run logo
      adiante falharia — a ordenação derrubando o despacho. O savepoint
      reverte só o ponto aninhado;
    - na conexão, e não com `Session.begin_nested()`: aquele descarrega (flush)
      o que a sessão tem pendente antes do SAVEPOINT, e um erro desse flush
      seria engolido aqui como "contagem indisponível", com a transação já
      perdida. Aqui nada da sessão é descarregado nem expirado;
    - só erro do driver (`DBAPIError`) vira degradação, e conexão perdida não:
      o INSERT adiante falharia de todo jeito, e com um erro pior. Bug sobe.
    """
    hosts = {f"executor:{i}": i for i in ids}
    consulta = (
        sa_select(WorkflowRun.host, func.count())
        .where(
            WorkflowRun.status.in_(_STATUS_EM_VOO),
            WorkflowRun.host.in_(list(hosts)),
        )
        .group_by(WorkflowRun.host)
    )
    conexao = await db.connection()
    try:
        async with conexao.begin_nested():
            linhas = (await conexao.execute(consulta)).all()
    except DBAPIError as exc:
        if exc.connection_invalidated:
            raise
        _logger.warning(
            "Carga contada pelo servidor indisponível (%s) — ordenando pela declarada.", exc,
        )
        return None
    return {hosts[host]: int(n) for host, n in linhas if host in hosts}


async def _situacoes(db: AsyncSession, executores: list[Executor]) -> dict[str, _Situacao]:
    """Carga, vagas, fila e "cheio" de cada candidato.

    - carga = a contada pelo servidor. É fresca e a mesma em todos os workers;
      a declarada (running + queued do último `capacity`) tem até 10 s e, somada
      ou comparada a ela, fazia executor recém-liberado parecer ocupado. A
      declarada só vale quando a contagem não saiu.
    - vagas/fila = o menor entre o declarado (max_concurrent/max_queue, já
      limitados ao teto do banco) e o teto do banco — antes do primeiro
      `capacity` o worker que segura o WebSocket tem só um valor provisório, e
      os workers não podem enxergar o mesmo executor com tamanhos diferentes.
    - cheio_declarado = o `is_full` do `send_job` sobre a declarada: pega o
      executor em drenagem, que se anuncia cheio para sair da frente.
    """
    ids = [ag.id_hash for ag in executores]
    # `return_exceptions`: um erro de um lado não pode propagar com o outro
    # ainda em voo — a consulta usaria a sessão enquanto o chamador já a usa de
    # novo. Depois das duas terminarem, erro da contagem sobe; o da leitura da
    # capacidade conta como nada declarado.
    contadas, declaradas = await asyncio.gather(
        _contadas_pelo_servidor(db, ids),
        executor_registry.read_capacities(ids),
        return_exceptions=True,
    )
    if isinstance(contadas, BaseException):
        raise contadas
    if isinstance(declaradas, BaseException) or not isinstance(declaradas, dict):
        declaradas = {}
    situacoes: dict[str, _Situacao] = {}
    for ag in executores:
        cap = declaradas.get(ag.id_hash)
        cap = cap if isinstance(cap, dict) else {}
        declarada = _contagem(cap.get("running")) + _contagem(cap.get("queued"))
        situacoes[ag.id_hash] = _Situacao(
            carga=contadas.get(ag.id_hash, 0) if contadas is not None else declarada,
            vagas=_menor_positivo(
                _contagem(cap.get("max_concurrent")),
                _contagem(getattr(ag, "max_concurrent_jobs", None)),
            ) or _VAGAS_PADRAO,
            fila=_menor_positivo(
                _contagem(cap.get("max_queue")),
                _contagem(getattr(ag, "max_queue_size", None)),
            ) or _FILA_PADRAO,
            cheio_declarado=_cheio_pela_declarada(cap),
        )
    return situacoes


def _chave_de_ordem(s: _Situacao) -> tuple:
    """Três grupos, nesta ordem:

    1. Com vaga livre — o job começa na hora. Sorteio PONDERADO pelas vagas
       livres (Efraimidis–Spirakis: U^(1/peso), maior primeiro). Com o mínimo
       estrito, decisões simultâneas — os workers da API, requisições
       concorrentes — partiam do mesmo retrato e escolhiam todas o mesmo
       executor; o sorteio as espalha na proporção da folga. Em sequência, o
       banco já mostra cada despacho anterior.
    2. Sem vaga, com lugar na fila local — o job vai esperar em alguma fila: o
       de menor ocupação relativa às vagas, que é onde ele deve começar antes.
    3. Cheios — pelo relatório (o `send_job` recusa) ou pela contagem (a fila
       local recusa e o run falha). Vão por último: tentados só se não houver
       outro. É onde cai o executor em drenagem.
    """
    if s.cheio:
        return (2, s.ocupacao, _desempate())
    if s.livres > 0:
        return (0, -(_desempate() ** (1 / s.livres)))
    return (1, s.ocupacao, _desempate())


async def _elegiveis_ordenados(
    db: AsyncSession, executores: list[Executor], *, excluir: set[str] = frozenset(),
) -> list[Executor]:
    """Filtra por `active` + `public_key` + disponibilidade (em paralelo) e
    ordena por `_chave_de_ordem` sobre `_situacoes`."""
    base = [
        ag for ag in executores
        if ag.id_hash not in excluir and ag.status == "active" and ag.public_key
    ]
    if not base:
        return []
    flags = await asyncio.gather(*[_disponivel(ag.id_hash) for ag in base])
    vivos = [ag for ag, ok in zip(base, flags) if ok]
    if len(vivos) < 2:
        return vivos
    situacoes = await _situacoes(db, vivos)
    vivos.sort(key=lambda ag: _chave_de_ordem(situacoes[ag.id_hash]))
    return vivos


async def _resolve_candidates(db: AsyncSession, wf: Workflow) -> CandidateList:
    """Executores candidatos, em ordem de tentativa.

    Com `EXECUTOR_POLICY_ROUTING=on` a lista é a CADEIA da política do
    workspace (spec §5); com `off`, o caminho legado (dedicado do workspace e
    depois o pool inteiro). Após o backfill da migração 20260907_0002 os dois
    produzem a mesma cadeia para todo workspace existente — os mesmos
    executores nos mesmos níveis; dentro de um nível a ordem tem sorteio
    (`_chave_de_ordem`), então só é idêntica com o sorteio fixado, como no
    teste dourado.
    """
    if policy_routing_enabled() and wf.workspace_id:
        return await _resolve_candidates_by_policy(db, wf)
    return await _resolve_candidates_legacy(db, wf)


async def _resolve_candidates_legacy(db: AsyncSession, wf: Workflow) -> CandidateList:
    """Ordem de prioridade legada: 1. dedicado do workspace (se disponível);
    2. pool de executores default, na ordem de `_chave_de_ordem`. Lança 503 se
    a lista fica vazia."""
    candidates: list[Executor] = []
    tiers: dict[str, str] = {}

    if wf.workspace_id:
        result = await db.execute(
            sa_select(Executor)
            .join(Workspace, Workspace.target_executor_id == Executor.id_hash)
            .where(
                Workspace.id_hash == wf.workspace_id,
                Workspace.deleted_at.is_(None),
                Executor.deleted_at.is_(None),
            )
        )
        ag = result.scalar_one_or_none()
        if ag and ag.status == "active" and ag.public_key and await _disponivel(ag.id_hash):
            candidates.append(ag)
            tiers[ag.id_hash] = politica.DISPATCH_PRIMARY

    defaults = await get_default_agents(db)
    for ag in await _elegiveis_ordenados(db, defaults, excluir={c.id_hash for c in candidates}):
        candidates.append(ag)
        tiers[ag.id_hash] = politica.DISPATCH_POOL

    if not candidates:
        raise NoExecutorAvailableError(
            "Nenhum executor disponível (pool padrão vazio ou todos offline). Contate o administrador.",
            category="no_pool_executor",
        )
    return CandidateList(candidates, tiers=tiers, mode=None)


def _mensagens_da_politica(p: "politica.WorkspacePolicy") -> tuple[str, str]:
    """(mensagem detalhada para o dono, error_category) quando a cadeia se esgota."""
    n = len(p.primary) + len(p.fallback)
    if p.mode == politica.MODE_ISOLATED:
        return (
            f"Workspace isolado: nenhum dos {n} executores dedicados está disponível. "
            "O job NÃO foi enviado ao pool compartilhado.",
            "no_dedicated_executor",
        )
    if p.mode == politica.MODE_DEDICATED_POOL:
        return (
            f"Nenhum executor disponível: {n} dedicados e o pool compartilhado estão fora.",
            "no_executor_chain",
        )
    return ("Nenhum executor do pool compartilhado disponível.", "no_pool_executor")


async def _resolve_candidates_by_policy(db: AsyncSession, wf: Workflow) -> CandidateList:
    """Cadeia da política: nível 1 → nível 2 → terminal (spec §5).

    Dentro de um nível, a ordem de `_chave_de_ordem`; entre níveis, ordem
    estrita. O pool só entra se o terminal EFETIVO for `pool` (o piso do admin
    vence). Modo pool (sem nível 1) é o de sempre."""
    p = await politica.load_policy_by_id(db, wf.workspace_id)
    if p is None:
        # Workspace apagado/inexistente: o caminho legado devolve o pool — mantém.
        return await _resolve_candidates_legacy(db, wf)

    cadeia: list[Executor] = []
    tiers: dict[str, str] = {}

    if p.has_primary:
        for ag in await _elegiveis_ordenados(db, p.primary):
            cadeia.append(ag); tiers[ag.id_hash] = politica.DISPATCH_PRIMARY
        for ag in await _elegiveis_ordenados(db, p.fallback, excluir=set(tiers)):
            cadeia.append(ag); tiers[ag.id_hash] = politica.DISPATCH_FALLBACK

    if p.allows_pool:
        defaults = await get_default_agents(db)
        for ag in await _elegiveis_ordenados(db, defaults, excluir=set(tiers)):
            cadeia.append(ag); tiers[ag.id_hash] = politica.DISPATCH_POOL

    mensagem, categoria = _mensagens_da_politica(p)
    if not cadeia:
        _log_dispatch_event(
            wf=wf, mode=p.mode, candidates_total=0, chosen=None, tier=None,
            failovers=0, decision_ms=0.0, outcome="no_candidates", category=categoria,
        )
        raise NoExecutorAvailableError(mensagem, category=categoria)

    allowed = await politica.allowed_executor_ids(db, p)
    return CandidateList(
        cadeia, tiers=tiers, allowed=allowed, mode=p.mode,
        exhausted_message=mensagem, exhausted_category=categoria,
    )


def _log_dispatch_event(*, wf, mode, candidates_total, chosen, tier, failovers,
                        decision_ms, outcome, category=None, run_id=None) -> None:
    """Uma linha JSON por decisão de dispatch — substitui o `info` solto de antes
    e é a fonte das métricas por nível (spec §11)."""
    evento = {
        "event": "dispatch",
        "run_id": run_id,
        "workflow_hash": getattr(wf, "id_hash", None),
        "workspace_id": getattr(wf, "workspace_id", None),
        "mode": mode or "legacy",
        "candidates_total": candidates_total,
        "chosen_executor": chosen,
        "dispatch_tier": tier,
        "failovers": failovers,
        "decision_ms": round(decision_ms, 1),
        "outcome": outcome,
    }
    if category:
        evento["error_category"] = category
    nivel = _logger.info if outcome == "dispatched" else _logger.warning
    nivel("dispatch_event %s", json.dumps(evento, ensure_ascii=False, default=str))


@dataclass
class _Despacho:
    """O que as fases de `_dispatch_job` compartilham: o run já gravado, a
    cadeia com as anotações da política e o relógio da decisão (spec §11).
    `ultimo_erro` acumula o motivo da última recusa, que entra na mensagem do
    run quando nenhum candidato aceita."""
    db: AsyncSession
    wf: Workflow
    run: WorkflowRun
    # O id do run como string, e não `run.task_id`: um rollback no meio (a
    # contabilização do fechamento faz um) expira o objeto, e ler atributo
    # expirado numa sessão assíncrona é I/O implícito.
    job_id: str
    candidatos: list[Executor]
    tiers: dict
    allowed: set[str] | None
    mode: str | None
    inicio: float
    has_response_node: bool
    ultimo_erro: str = ""

    def resultado(self) -> DispatchResult:
        return DispatchResult(id=self.job_id, has_response_node=self.has_response_node)


async def _dispatch_job(
    wf: Workflow,
    definition: dict,
    candidates: list[Executor],
    inputs: dict | None,
    debug_mode: bool,
    *,
    db: AsyncSession,
    pre_resolved: dict | None = None,
    disabled_nodes: list[str] | None = None,
    subworkflow_definitions: dict | None = None,
    trigger_source: str | None = None,
    triggered_by: str | None = None,
    schedule_id: int | None = None,
) -> DispatchResult:
    """Persiste WorkflowRun no DB e tenta despachar para cada candidato.

    Sequencia (anti-race):
      1. INSERT WorkflowRun(status='pending', host=<primeiro candidato>) —
         garante que o run existe no DB antes de qualquer chamada de rede. WS
         /ws/workflow/<task_id> encontra o run imediatamente apos o POST
         /execute retornar.
      2. Loop pelos candidatos: cifra job + send_job ao executor.
      3. Sucesso: UPDATE status='running'. Retorna DispatchResult.
      4. Nenhum candidato aceita: UPDATE status='failed' + error_message.
         Re-raise NoExecutorAvailableError para o caller (POST retorna 5xx).

    Cada passo e uma funcao: `_criar_run` (1), `_serializar_payload` (o
    envelope, uma vez), `_tentar_candidatos` (2 e 3, com a barreira do
    isolamento e `_confirmar_entrega`) e `_fechar_sem_executor` (4). Esta
    funcao so as encadeia e segura a rede de seguranca.

    Antes essa criacao era assincrona via fila Redis 'run_creates' (consumer
    fazia o INSERT). Causava 4404 sob carga (consumer atrasado), e podia
    deixar runs orfaos se a API crashava entre send_job e lpush.

    Todo o corpo apos o INSERT roda dentro de um try/except: qualquer excecao
    inesperada (TypeError em build_job_message por chave publica invalida,
    falha do resolver de credenciais, send_job estourando) fechava o run em
    'pending' para sempre — o watchdog so reconcilia 'running' e o cancel
    respondia "Execucao sem executor associado". Agora o run e marcado como
    'failed' com a mensagem do erro antes do re-raise.

    `trigger_source`, `triggered_by` e `schedule_id` entram no INSERT junto
    com o host (docs/specs/historico-metricas.md §2): sao rotulos do run, nao
    do despacho — um UPDATE separado depois custaria mais um commit no caminho
    critico. Quem fecha o run por aqui tambem grava `error_category`
    ("isolation", "no_executor", "dispatch"), para o Historico agrupar "por que
    falhou" sem LIKE em `error_message`.
    """
    has_response_node = any(n.get("name") == "Response" for n in definition.get("nodes", []))
    job_id = str(uuid.uuid4())
    inicio = time.monotonic()
    tiers: dict = getattr(candidates, "tiers", None) or {}
    allowed = getattr(candidates, "allowed", None)
    mode = getattr(candidates, "mode", None)

    run = await _criar_run(
        db, wf, candidates, tiers, job_id,
        trigger_source=trigger_source, triggered_by=triggered_by, schedule_id=schedule_id,
    )
    despacho = _Despacho(
        db=db, wf=wf, run=run, job_id=job_id, candidatos=candidates, tiers=tiers,
        allowed=allowed, mode=mode, inicio=inicio, has_response_node=has_response_node,
    )

    try:
        plaintext = await _serializar_payload(
            wf, definition, job_id, inputs, debug_mode,
            pre_resolved=pre_resolved, disabled_nodes=disabled_nodes,
            subworkflow_definitions=subworkflow_definitions,
        )
        entregue = await _tentar_candidatos(despacho, plaintext)
        if entregue is not None:
            return entregue
        raise await _fechar_sem_executor(despacho)

    except Exception as exc:
        # Rede de seguranca: fecha o run antes de propagar. Idempotente — o
        # caminho (4) ja gravou 'failed' e nao e reescrito aqui.
        await _close_orphan_dispatch(db, run, exc)
        raise


async def _criar_run(
    db: AsyncSession,
    wf: Workflow,
    candidates: list[Executor],
    tiers: dict,
    job_id: str,
    *,
    trigger_source: str | None,
    triggered_by: str | None,
    schedule_id: int | None,
) -> WorkflowRun:
    """1) Cria run no DB ANTES de tocar a rede (resolve race WS↔consumer).

    SEG: o host do PRIMEIRO candidato ja entra no INSERT. A garantia que
    importa e "host gravado antes do envio" — e ela que faz
    `_run_belongs_to_agent` recusar um executor que reivindique run alheio —
    e o primeiro candidato ja e conhecido aqui. Gravar o host so no laco
    custava um segundo commit (mais um fsync do WAL) entre a decisao e o
    frame sair pelo WebSocket. Agora so o failover paga esse UPDATE.

    Fica FORA da rede de seguranca de `_dispatch_job`: se este commit falha,
    nao ha run para fechar.
    """
    run = WorkflowRun(
        task_id=job_id,
        workflow_hash=wf.id_hash,
        workspace_id=wf.workspace_id,
        status="pending",
        node_stats={},
        host=f"executor:{candidates[0].id_hash}" if candidates else None,
        dispatch_tier=tiers.get(candidates[0].id_hash) if candidates else None,
        trigger_source=trigger_source,
        triggered_by=triggered_by,
        schedule_id=schedule_id,
    )
    db.add(run)
    await db.commit()
    return run


async def _serializar_payload(
    wf: Workflow,
    definition: dict,
    job_id: str,
    inputs: dict | None,
    debug_mode: bool,
    *,
    pre_resolved: dict | None,
    disabled_nodes: list[str] | None,
    subworkflow_definitions: dict | None,
) -> bytes:
    """O envelope do job, com as credenciais injetadas, ja serializado."""
    # Injeta credenciais no payload (sem salvar no banco). A cadeia de
    # sub-fluxos passa pelo MESMO tratamento: ela viaja no envelope e o
    # executor não tem DB para resolver nada por conta própria.
    enriched = await inject_credentials(definition, pre_resolved=pre_resolved)
    enriched_subs = {
        hash_: await inject_credentials(sub_def, pre_resolved=pre_resolved)
        for hash_, sub_def in (subworkflow_definitions or {}).items()
    }
    # E o fundo de mapa da instalação nos nós Carta, pelo mesmo motivo: o
    # executor não tem a configuração (ver app/services/fundos_do_mapa.py).
    enriched = injetar_fundos_de_mapa(enriched)
    enriched_subs = {hash_: injetar_fundos_de_mapa(sub) for hash_, sub in enriched_subs.items()}
    # E o fuso padrão dos agendamentos no ScheduleTrigger sem fuso: o default
    # do nó é o do ambiente de quem o importa, e o executor não tem o da
    # instalação (ver app/services/fuso_do_agendamento.py).
    enriched = injetar_fuso_do_agendamento(enriched)
    enriched_subs = {hash_: injetar_fuso_do_agendamento(sub) for hash_, sub in enriched_subs.items()}

    agent_payload = {
        "workflow_definition": enriched,
        "workflow_hash":       wf.id_hash,
        "run_id":              job_id,
        "params":              inputs or {},
        "workspace_id":        wf.workspace_id,
        "debug_mode":          debug_mode,
        "pinned_outputs":      _safe_pinned_outputs(wf.pinned_outputs, wf.pin_metadata),
        "pin_metadata":        wf.pin_metadata or {},
        # Snapshot dos nodes desabilitados no momento do despacho. SubWorkflowNode
        # usa isso para validar sub-fluxos sem precisar consultar o DB do servidor.
        "disabled_nodes":      disabled_nodes or [],
        # Definitions pre-resolvidas de toda a cadeia de sub-workflows. O executor
        # nao tem acesso ao DB (so flow/ e executor/ no Docker), entao precisa
        # receber tudo aqui. Mapa {hash: definition}.
        "subworkflow_definitions": enriched_subs,
    }

    # Serializa o payload UMA vez, fora do laco de candidatos: para um
    # workflow grande sao alguns MB de json.dumps, e antes isso era refeito
    # por candidato a cada failover. Vai para thread: nao da para saber o
    # tamanho antes de serializar (o gate `_LIMIAR` do cifrar depende deste
    # resultado), e um json.dumps de megabytes inline congelava o worker que
    # atende os WebSockets de TODOS os executores. E uma vez por despacho
    # (nao por candidato), entao o salto de thread e barato — diferente do
    # cifrar, que pode repetir no failover e cujo tamanho ja e conhecido.
    return await asyncio.to_thread(
        lambda: json.dumps(agent_payload, ensure_ascii=False).encode()
    )


async def _tentar_candidatos(d: _Despacho, plaintext: bytes) -> DispatchResult | None:
    """2) Tenta despachar para cada candidato em ordem de prioridade.

    Devolve o resultado do primeiro que aceitar (3), ou None se nenhum aceitou
    — com o motivo da última recusa em `d.ultimo_erro`. Um candidato fora da
    política levanta, com o run já fechado (`_barrar_fora_da_politica`).
    """
    cifrar_em_thread = len(plaintext) >= _LIMIAR_CIFRA_EM_THREAD
    for indice, ag in enumerate(d.candidatos):
        label = f"{ag.name}@{ag.id_hash[-5:]}" if ag.name else ag.id_hash

        # Barreira do isolamento (spec §5.3): antes de CIFRAR para a chave
        # deste executor, ele tem de estar no conjunto que a política
        # permite. Um refactor que reintroduza o pool na cadeia é apanhado
        # aqui, não em produção pelo cliente — e o job nunca sai.
        if d.allowed is not None and ag.id_hash not in d.allowed:
            raise await _barrar_fora_da_politica(d, ag, indice, label)

        try:
            job_msg = await _cifrar_para(d, ag, plaintext, cifrar_em_thread)
        except RuntimeError as exc:
            _logger.warning("Falha ao cifrar job para executor '%s': %s", label, exc)
            d.ultimo_erro = f"Falha ao cifrar job para '{label}': {exc}"
            continue

        # SEG: o host tem de estar gravado ANTES do envio — e ele que
        # `_run_belongs_to_agent` usa no WS router para autorizar
        # job_result/node_event, e sem ele qualquer executor poderia
        # reivindicar o run (fail-open cross-tenant). O primeiro candidato
        # ja foi gravado no INSERT; so o failover precisa reescrever.
        if indice:
            d.run.host = f"executor:{ag.id_hash}"
            d.run.dispatch_tier = d.tiers.get(ag.id_hash)
            await d.db.commit()

        try:
            sent = await executor_registry.send_job(ag.id_hash, job_msg)
        except Exception as exc:
            # send_job toca estado em memoria da conexao (ex.: is_full() com
            # capacity malformada levanta TypeError). Isso derrubava o dispatch
            # inteiro e deixava o run em 'pending'; aqui vira recusa deste
            # candidato para que o failover continue.
            _logger.warning("Erro ao enviar job ao executor '%s': %s", label, exc)
            d.ultimo_erro = f"Erro ao enviar job para '{label}': {exc}"
            continue

        if not sent:
            _logger.warning("Executor '%s' recusou job (fila cheia ou desconectado). Tentando próximo.", label)
            d.ultimo_erro = f"Executor '{label}' não aceitou o job (fila cheia ou desconectado)."
            continue

        return await _confirmar_entrega(d, ag, indice, label)
    return None


async def _barrar_fora_da_politica(
    d: _Despacho, ag: Executor, indice: int, label: str,
) -> NoExecutorAvailableError:
    """Fecha o run e registra a violação do isolamento; devolve a exceção que
    quem chama levanta. O job NÃO sai: nada foi cifrado para este executor."""
    _logger.error(
        "VIOLAÇÃO DE ISOLAMENTO: executor '%s' fora do conjunto permitido do "
        "workspace '%s' (run %s). Job NÃO enviado.", label, d.wf.workspace_id, d.job_id,
    )
    mensagem = (
        "Barreira de isolamento: o roteamento escolheu um executor fora da "
        "política do workspace. O job não foi enviado."
    )
    # Condicional, como todo fechamento do servidor: um
    # cancelamento que chegou nesta janela vale.
    await fechar_runs(d.db, [d.run], de=ABERTOS, para="failed", mensagem=mensagem, categoria="isolation")
    _log_dispatch_event(
        wf=d.wf, mode=d.mode, candidates_total=len(d.candidatos), chosen=ag.id_hash,
        tier=d.tiers.get(ag.id_hash), failovers=indice,
        decision_ms=(time.monotonic() - d.inicio) * 1000,
        outcome="isolation_violation", category="isolation_violation", run_id=d.job_id,
    )
    return NoExecutorAvailableError(
        mensagem, category="isolation_violation", run_id=d.job_id,
    )


async def _cifrar_para(d: _Despacho, ag: Executor, plaintext: bytes, cifrar_em_thread: bool) -> dict:
    """O envelope cifrado para a chave deste executor. RuntimeError = chave
    inválida, e o candidato é pulado."""
    argumentos = dict(
        executor_id=ag.id_hash,
        workspace_id=d.wf.workspace_id or "",
        agent_x25519_pub_pem=ag.public_key,
        job_type="run_workflow",
        payload=plaintext,
        job_id=d.job_id,
    )
    # Acima do limiar o AES-GCM + base64 + assinatura vao para uma
    # thread: o `cryptography` solta o GIL nas primitivas, e este
    # worker tambem serve os WebSockets de TODOS os executores —
    # cifrar um envelope de megabytes inline congelava o processo
    # inteiro por dezenas de milissegundos a cada disparo. Abaixo do
    # limiar o salto de thread custaria mais do que economiza.
    if cifrar_em_thread:
        return await asyncio.to_thread(build_job_message, **argumentos)
    return build_job_message(**argumentos)


async def _confirmar_entrega(d: _Despacho, ag: Executor, indice: int, label: str) -> DispatchResult:
    """3) Sucesso — transiciona pending → running, mas SO se o run ainda
    nao chegou a um estado terminal. Entre o INSERT do passo (1) e este
    ponto passam segundos (inject_credentials resolve/decifra
    credenciais, cifra do envelope, send_job) e o run ja aparece na
    tela de execucoes: o usuario pode cancela-lo nessa janela. Com um
    `run.status = "running"` incondicional o UPDATE por PK apagava o
    'cancelled', a API ja tinha respondido 200/cancelled e o job rodava
    ate o fim.

    'running' entra na condicao porque o ACK do executor tambem
    promove o run (ver `_record_job_ack`) e costuma chegar ANTES deste
    commit: o executor confirma em milissegundos. So com 'pending' o
    rowcount 0 seria lido como cancelamento e o dispatch mandaria
    'cancel' para um job saudavel.
    """
    transition = await d.db.execute(
        sa_update(WorkflowRun)
        .where(
            WorkflowRun.task_id == d.job_id,
            WorkflowRun.status.in_(("pending", "running")),
        )
        .values(status="running")
        .execution_options(synchronize_session=False)
    )
    await d.db.commit()

    if not transition.rowcount:
        # Perdemos para o cancelamento. O executor JA aceitou o job, de
        # modo que o unico jeito de honrar o 'cancelled' e avisa-lo.
        _logger.warning(
            "Run '%s' saiu de 'pending' durante o despacho — pedindo ao "
            "executor '%s' que interrompa o job recem-enviado.", d.job_id, label,
        )
        try:
            await executor_registry.send_json(
                ag.id_hash, {"type": "cancel", "job_id": d.job_id}
            )
        except Exception as exc:
            _logger.error(
                "Falha ao pedir interrupcao do job '%s' ao executor '%s': %s",
                d.job_id, label, exc,
            )
        return d.resultado()

    # Sincroniza o objeto SEM suja-lo: uma atribuicao normal faria o
    # proximo flush reemitir `SET status=...` por PK, reintroduzindo o
    # escritor incondicional que o UPDATE acima acabou de eliminar.
    set_committed_value(d.run, "status", "running")

    _log_dispatch_event(
        wf=d.wf, mode=d.mode, candidates_total=len(d.candidatos), chosen=ag.id_hash,
        tier=d.tiers.get(ag.id_hash), failovers=indice,
        decision_ms=(time.monotonic() - d.inicio) * 1000, outcome="dispatched", run_id=d.job_id,
    )
    return d.resultado()


async def _fechar_sem_executor(d: _Despacho) -> NoExecutorAvailableError:
    """4) Nenhum candidato aceitou — marca como failed para evitar run
    zumbi em 'pending' para sempre. Condicional (ver `fechar_runs`): o
    usuario pode ter cancelado o run enquanto os candidatos respondiam, e
    o 'cancelled' que a API confirmou nao pode virar 'failed'.

    Devolve a exceção que quem chama levanta.
    """
    exhausted = getattr(d.candidatos, "exhausted_message", None)
    categoria = getattr(d.candidatos, "exhausted_category", None) or "no_executor"
    last_error = d.ultimo_erro
    mensagem = (
        f"{exhausted} Último motivo: {last_error}" if exhausted and last_error
        else exhausted or last_error or "Nenhum executor aceitou o job."
    )
    # Categoria FIXA, e nao `categoria`: a da excecao e a granularidade do
    # alerta ao dono ("no_dedicated_executor", "no_executor_chain"...) e nao
    # cabe na taxonomia da coluna, que resume tudo isso em "sem executor".
    # Repetir e seguro: nada rodou, e o executor pode voltar.
    await fechar_runs(
        d.db, [d.run], de=ABERTOS, para="failed", mensagem=mensagem,
        categoria="no_executor", extra=REPETIVEL,
    )
    _log_dispatch_event(
        wf=d.wf, mode=d.mode, candidates_total=len(d.candidatos), chosen=None, tier=None,
        failovers=len(d.candidatos), decision_ms=(time.monotonic() - d.inicio) * 1000,
        outcome="all_refused", category=categoria, run_id=d.job_id,
    )

    return NoExecutorAvailableError(mensagem, category=categoria, run_id=d.job_id)


async def _close_orphan_dispatch(db: AsyncSession, run: WorkflowRun, exc: Exception) -> None:
    """Marca como 'failed' um run que estourou durante o dispatch.

    Sem isso o run ficava em 'pending' indefinidamente: o watchdog de executores
    so reconcilia runs em 'running' e `cancel_run` nao tinha host para contatar.
    Idempotente: o run que o proprio dispatch ja fechou (passo 4, barreira) ou
    que o usuario cancelou no meio nao e reescrito — `fechar_runs` so fecha o
    que ainda esta aberto.
    """
    try:
        await fechar_runs(
            db, [run], de=ABERTOS, para="failed",
            mensagem=f"Falha no despacho: {exc}"[:1000], categoria="dispatch",
        )
    except Exception as commit_exc:
        _logger.error(
            "Nao foi possivel fechar o run '%s' apos falha de despacho (%s): %s",
            run.task_id, exc, commit_exc,
        )
        try:
            await db.rollback()
        except Exception:
            pass


async def _close_unassigned_run(db: AsyncSession, run: WorkflowRun) -> bool:
    """Fecha como 'cancelled' um run que nenhum executor aceitou. Retorna se venceu.

    UPDATE **condicional** de propósito, e a condição é `status='pending'` —
    exatamente a simétrica do UPDATE do dispatch (`pending → running`), de modo
    que exatamente um dos dois vence. Um ler-decidir-gravar em passos separados
    perderia a corrida: o `SET status='running'` do dispatch, sendo por PK,
    apagava o 'cancelled' que a API já tinha confirmado ao usuário.

    Antes a condição também exigia `host IS NULL`. O host passou a entrar já no
    INSERT do run (é o que evita um commit extra antes do envio), então essa
    coluna não distingue mais nada: quem separa "o executor já tem o job" de "o
    job ainda não saiu do servidor" é o STATUS — o dispatch só promove para
    'running' depois que `send_job` aceitou.

    Cuidado: 'pending' separa os dois casos só enquanto o processo que despachou
    está vivo. Por isso quem fecha aqui deve avisar o host mesmo assim — ver
    `_avisar_host_do_cancelamento`.
    """
    return bool(await fechar_runs(
        db, [run], de=("pending",), para="cancelled",
        mensagem="Cancelado antes de ser atribuído a um executor.", categoria=None,
    ))


async def _avisar_host_do_cancelamento(run: WorkflowRun) -> None:
    """Pede ao executor gravado em `run.host` que interrompa o job. Best-effort.

    Chamado TAMBÉM quando o run foi fechado localmente ainda em 'pending'.
    Motivo: 'pending' não prova que o job não saiu. O host entra já no INSERT e
    o `send_job` acontece ANTES do commit de pending→running; se o worker que
    despachou morre nessa janela (rolling restart, `docker compose restart api`,
    OOM killer, SIGKILL), o run fica 'pending' para sempre com o executor
    rodando o fluxo de verdade — mandando e-mails, fazendo INSERTs. A rede de
    proteção do dispatch (rowcount 0 → manda o 'cancel') só existe enquanto
    AQUELE processo está vivo, que é exatamente o que não vale nesse cenário, e
    o usuário receberia "cancelado" com o fluxo correndo até o fim.

    Mandar o 'cancel' é idempotente: para um job_id que o executor nunca
    recebeu, `JobQueue.cancel` responde "unknown" e não marca nada.

    Não levanta: o cancelamento local já foi confirmado no banco e falar com o
    executor é um esforço extra, não uma condição para responder ao usuário.
    """
    host = run.host or ""
    if not host.startswith("executor:"):
        return
    executor_id = host[len("executor:"):]
    try:
        await executor_registry.send_json(
            executor_id, {"type": "cancel", "job_id": run.task_id},
        )
    except Exception as exc:
        _logger.warning(
            "Falha ao avisar o executor '%s' do cancelamento do run '%s': %s",
            executor_id, run.task_id, exc,
        )


async def cancel_run(
    db: AsyncSession,
    run_id: str,
    *,
    user_id: str,
    como_admin: bool = False,
) -> str:
    """Pede ao executor que interrompa um run em andamento.

    `user_id` é obrigatório e somente-nomeado porque esta função NÃO tinha
    autorização nenhuma: o papel era conferido só na rota, e qualquer outro
    chamador — uma tool do servidor MCP, um script, um job — cancelava execução
    de qualquer workspace de qualquer conta. Agora a regra mora aqui, junto do
    SELECT que carrega o run, e quem esquecer o parâmetro quebra na chamada em
    vez de atravessar tenant em silêncio.

    A autorização é pelo workspace DO RUN, não pelo workspace atual do workflow:
    um workflow pode ter sido movido de A para B depois do disparo, e quem
    controla B não deve poder cancelar uma execução que rodou (e consumiu
    recursos) em A. `como_admin` reproduz o atalho do administrador global que a
    rota já tinha — um token pessoal nunca o recebe, porque `como_usuario()`
    devolve `role="user"` sempre.

    Retorna o "outcome": "requested" quando a mensagem chegou ao executor,
    "already_finished" quando o run já terminou (no-op idempotente) e
    "cancelled" quando o run foi fechado aqui — nunca chegou a um executor, ou
    o executor que o segura está fora do ar.

    Para um run já entregue NÃO escreve o status no banco: quem o fecha é o
    `job_result` de volta do executor (status=cancelled), o mesmo caminho de
    sempre. Ter dois escritores do status abriria corrida entre este commit e o
    resultado que chega logo em seguida — e o run poderia terminar "cancelado"
    mesmo tendo concluído no intervalo entre o pedido e a interrupção.

    A única escrita local é a de `_close_unassigned_run`, restrita por UPDATE
    condicional ao run que ainda está 'pending' — o caso em que, em condições
    normais, não existe executor a quem pedir nada. Perder essa condição
    significa que o dispatch venceu; então relemos o run e seguimos pelo caminho
    normal.

    A decisão entre "fechar aqui" e "esperar o job_result" é pelo STATUS, não
    pelo host: o host já vem preenchido desde o INSERT do run, mas 'pending'
    quer dizer que `send_job` ainda não confirmou a entrega, e sem o fechamento
    local o usuário ficaria sem nenhuma forma de limpar o run (o watchdog só
    reconcilia 'running'). O fechamento local NÃO dispensa o aviso ao host: um
    'pending' pode ser um job já entregue cujo despachante morreu antes do
    commit — ver `_avisar_host_do_cancelamento`.

    Com o executor que o segura fora do ar, o run também é fechado aqui
    ("cancelled"): sem isso não havia como limpar um run perdido pela tela.

    Levanta WorkflowNotFoundError se o run não existe.
    """
    result = await db.execute(
        sa_select(WorkflowRun).where(WorkflowRun.task_id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise WorkflowNotFoundError(f"Execução '{run_id}' não encontrada.")

    if not como_admin:
        papel = await papel_no_workspace_do_run(db, run, user_id)
        exigir_papel(
            papel,
            ROLE_OPERATOR,
            "Requer role 'operator' ou superior para cancelar execuções.",
        )

    if run.status not in ("pending", "running"):
        return "already_finished"

    if run.status == "pending":
        # Ninguém confirmou o recebimento ainda. O watchdog só reconcilia
        # 'running', então sem este fechamento local o usuário ficava sem
        # nenhuma forma de limpar o run. Se o dispatch entregar logo depois,
        # ele detecta o rowcount 0 do seu próprio UPDATE e manda o 'cancel'.
        if await _close_unassigned_run(db, run):
            _logger.info("Run '%s' cancelado localmente (ainda em 'pending').", run_id)
            # E avisa o host mesmo assim: 'pending' pode ser um job que JÁ saiu
            # e cujo despachante morreu antes do commit — ver
            # `_avisar_host_do_cancelamento`.
            await _avisar_host_do_cancelamento(run)
            return "cancelled"

        # O dispatch chegou primeiro: relê o estado real antes de decidir.
        await db.refresh(run)
        if run.status not in ("pending", "running"):
            _logger.info(
                "Run '%s': cancelamento local perdeu a corrida com o dispatch (status=%s).",
                run_id, run.status,
            )
            return "already_finished"

    # O host do run guarda quem o está executando: "executor:{id_hash}".
    host = run.host or ""
    if not host.startswith("executor:"):
        _logger.info(
            "Run '%s' em '%s' não tem executor associado — nada a interromper.",
            run_id, run.status,
        )
        return "already_finished"

    executor_id = host[len("executor:"):]

    # O servidor despacha com job_id == task_id (ver dispatch acima), então o
    # executor localiza o job pelo mesmo identificador.
    sent = await executor_registry.send_json(executor_id, {
        "type":   "cancel",
        "job_id": run_id,
    })
    if not sent:
        # `send_json` também devolve False com o executor VIVO: chave de
        # assinatura ausente, relay sem listener durante um restart, Redis com
        # erro. Fechar nesses casos daria "cancelado" com o job rodando — e um
        # executor antigo, sem inventário, o levaria até o fim. Só a ausência
        # COMPROVADA de presença fecha aqui; o resto segue sendo 503.
        if await executor_registry.presence_or_unknown(executor_id) is not False:
            raise NoExecutorAvailableError(
                "Não foi possível pedir o cancelamento ao executor agora — tente de novo."
            )
        # Executor fora do ar: antes era 503 ("não foi possível cancelar") e o
        # run ficava "Em andamento" sem nenhuma forma de ser limpo pela tela —
        # justamente o run perdido que o usuário tentava tirar do caminho. Fecha
        # aqui, condicional (um job_result que chegue no meio vence). Se o
        # executor voltar ainda rodando o job, o inventário dele manda parar
        # (ver `_parar_zumbis`) e o resultado atrasado é recusado por idempotência.
        if await _close_offline_run(db, run):
            _logger.info(
                "Run '%s' cancelado no servidor: executor '%s' fora do ar.", run_id, executor_id,
            )
            return "cancelled"
        await db.refresh(run)
        return "already_finished"

    _logger.info("Cancelamento do run '%s' solicitado ao executor '%s'.", run_id, executor_id)
    return "requested"


async def _close_offline_run(db: AsyncSession, run: WorkflowRun) -> bool:
    """Fecha como 'cancelled' um run cujo executor está fora do ar. Retorna se
    venceu.

    Condicional em 'pending'/'running', pelo mesmo motivo de
    `_close_unassigned_run`: um job_result que chegue entre a leitura e este
    UPDATE já fechou o run com o desfecho real, e ele não pode ser sobrescrito.
    """
    return bool(await fechar_runs(
        db, [run], de=ABERTOS, para="cancelled",
        mensagem="Cancelada com o executor fora do ar — a execução foi encerrada no servidor.",
        categoria=None,
    ))
