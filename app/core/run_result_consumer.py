# app/core/run_result_consumer.py
"""
Consumer assíncrono da fila Redis run_results.

Fluxo:
  Worker  →  LPUSH run_results  { task_id, status, error_message, stats, end_time, duration_seconds }
  API     ←  BRPOP run_results  →  atualiza WorkflowRun no PostgreSQL

O run e criado SINCRONAMENTE no endpoint POST /execute (via _dispatch_job
em workflow_execution_service) com status='pending', atualizado para
'running' apos send_job, e finalmente atualizado pelo consumer com o
resultado real (status=ok/error + stats + metricas + artefatos).

Antes existia tambem uma fila run_creates onde o consumer criava o run.
Isso causava 4404 no WS quando o run_create demorava (consumer ocupado
ou Redis lento). Migrado para criacao sincrona no dispatch para eliminar
o race entre POST /execute e processamento do consumer.

Itens nao processaveis vao para run_dead_letter para analise manual — assim como
os processados PELA METADE (status gravado mas alguma fase acessoria perdida),
que vao anotados com '_phases_failed'. A fila e forense: ninguem a consome
automaticamente, entao ela e o unico registro de perda alem do log.
"""

import asyncio
import hashlib
import hmac
import ipaddress
import json
import math
from flow.utils.backoff import com_jitter
from app.core.utils.logger import get_logger
import os
import re
import time as _time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.utils.datetime_utils import utc_now_naive

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import REDIS_URL
from app.core.constants import NODE_STATS_RUN_META_KEY
from app.core.db import AsyncSessionLocal
from app.core.utils.allowlist import hostname_matches_allowlist
from app.models.models import Workflow, WorkflowRun
from app.models.artifact import Artifact
from app.models.system_config import SystemConfig

logger = get_logger(__name__)

QUEUE_RESULTS     = "run_results"
QUEUE_DEAD_LETTER = "run_dead_letter"

# Acima deste tamanho de payload, o json.loads sai do event loop (espelha o
# limiar do dumps no produtor). Abaixo, o overhead do to_thread não compensa.
_JSON_OFFLOAD_THRESHOLD = 256 * 1024

# Máximo de tentativas para run_results cujo run ainda não foi criado
_MAX_RESULT_RETRIES = 20


_NOTIFY_DELAYS = [5, 30, 120]  # segundos entre tentativas


class PhaseFailure(Exception):
    """Uma ou mais fases pos-fechamento do run falharam.

    O status do run JA foi gravado por _update_run_status; o que ficou faltando
    sao efeitos acessorios (uso, metricas, artefatos, pins, webhook). Levantada
    por _process_result para que _consume_one mande o payload para
    run_dead_letter — sem isso o unico rastro da perda era uma linha de log.
    """

    def __init__(self, task_id: str, labels: list[str]):
        super().__init__(f"run {task_id}: fase(s) nao concluida(s): {', '.join(labels)}")
        self.labels = labels

# Set de tasks em background para webhook notifications — evita que o GC
# colete-as enquanto rodam e permite rastreamento em shutdown se necessário.
# Referência em: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
_webhook_tasks: set[asyncio.Task] = set()



# Vocabulario de `workflow_runs.error_category` (docs/specs/metrics-history.md
# §2): a taxonomia do flow mais as categorias do servidor. Um valor fora dele
# nao e gravado — cortado em 16 caracteres viraria "no_executor_chai", uma
# categoria que ninguem mapeia e que a tela agruparia como se fosse outra.
_CATEGORIAS_DE_ERRO = frozenset({
    "user", "validation", "timeout", "resource", "transient", "internal",
    "no_executor", "executor_lost", "isolation", "dispatch",
})


def _categoria_conhecida(valor) -> "str | None":
    texto = str(valor).strip().lower() if valor is not None else ""
    if texto in _CATEGORIAS_DE_ERRO:
        return texto
    logger.debug("error_category fora do vocabulario ignorada: %r", valor)
    return None


def _schedule_webhook_notification(url: str, body: dict) -> None:
    """Cria task de notificação e a registra para não virar órfã."""
    task = asyncio.create_task(_send_notification_with_retry(url, body))
    _webhook_tasks.add(task)
    # Log exceções silenciosas e limpa do set quando termina.
    def _done(t: asyncio.Task) -> None:
        _webhook_tasks.discard(t)
        exc = t.exception()
        if exc is not None:
            logger.error("Webhook notification task falhou com exception não-tratada: %s", exc, exc_info=exc)
    task.add_done_callback(_done)


async def _send_notification_with_retry(url: str, body: dict) -> None:
    """Dispara webhook POST de conclusão de run com até 3 tentativas e backoff.

    Usa safe_httpx_request: pin de IP apos validacao SSRF, previne DNS
    rebinding entre validacao e POST. follow_redirects=False evita que
    servidor responda 302 para URL interna (proxy attack).
    """
    from flow.utils.geo_helpers import safe_httpx_request

    # Serializa uma vez e assina com HMAC para que o receptor possa validar
    payload_bytes = json.dumps(body, sort_keys=True).encode()
    timestamp = str(int(_time.time()))
    signature = hmac.new(
        os.getenv("APP_SECRET", "").encode(),
        f"{timestamp}.".encode() + payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    webhook_headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": timestamp,
    }

    for attempt, delay in enumerate(_NOTIFY_DELAYS, start=1):
        try:
            resp = await safe_httpx_request(
                "POST", url,
                timeout=15,
                follow_redirects=False,
                headers=webhook_headers,
                content=payload_bytes,
            )
            if resp.status_code < 500:
                logger.debug("Notificação enviada para %s (HTTP %d).", url, resp.status_code)
                return
            logger.warning(
                "Notificação para %s retornou HTTP %d (tentativa %d/%d).",
                url, resp.status_code, attempt, len(_NOTIFY_DELAYS),
            )
        except ValueError as exc:
            # safe_httpx_request raise ValueError em SSRF block — nao re-tentar.
            logger.warning("Webhook bloqueado por SSRF: %s → %s", url, exc)
            return
        except Exception as exc:
            logger.warning(
                "Falha ao enviar notificação para %s (tentativa %d/%d): %s",
                url, attempt, len(_NOTIFY_DELAYS), exc,
            )
        if attempt < len(_NOTIFY_DELAYS):
            await asyncio.sleep(com_jitter(delay))

    logger.error("Notificação para %s falhou após %d tentativas.", url, len(_NOTIFY_DELAYS))


async def _recover_session(db, run: WorkflowRun, task_id: str) -> bool:
    """Recupera a sessao apos uma fase falhar. Retorna False se nao der.

    O rollback e OBRIGATORIO: sem ele a AsyncSession fica em estado de erro e
    todas as fases seguintes estouram PendingRollbackError antes mesmo de tocar
    o banco (era exatamente esse o efeito do except silencioso de _persist_metrics
    — o run terminava "concluido" sem artefatos, sem pins e sem webhook).

    Como o rollback EXPIRA os objetos ja carregados, precisamos re-hidratar o
    `run`: caso contrario o proximo acesso a run.status dispararia IO lazy
    (MissingGreenlet) dentro do loop async.
    """
    try:
        await db.rollback()
        await db.refresh(run)
        return True
    except Exception as exc:
        logger.error("run %s: sessao irrecuperavel apos falha de fase: %s", task_id, exc)
        return False


PHASE_OK     = "ok"      # fase concluiu
PHASE_FAILED = "failed"  # fase estourou, mas a sessao voltou — pode continuar
PHASE_FATAL  = "fatal"   # sessao irrecuperavel — nada mais roda


async def _run_phase(db, run: WorkflowRun, task_id: str, label: str, fn, *args) -> str:
    """Executa uma fase do pipeline isolando a falha das demais.

    Antes, qualquer excecao aqui abortava o payload INTEIRO e o run ficava sem
    artefatos/pins/notificacao. Agora a falha e logada, a sessao e recuperada e
    as fases seguintes continuam.

    Devolve PHASE_FATAL quando a sessao ficou irrecuperavel — nesse caso o
    chamador INTERROMPE o pipeline, porque toda fase seguinte estouraria
    PendingRollbackError. O retorno distingue PHASE_FAILED de PHASE_OK porque
    quem registra a perda e _process_result, que levanta PhaseFailure no fim:
    log sozinho nao da ao operador nada para reprocessar.
    """
    try:
        await fn(*args)
        return PHASE_OK
    except Exception as exc:
        logger.error("run %s: fase '%s' falhou: %s", task_id, label, exc, exc_info=exc)
        return PHASE_FAILED if await _recover_session(db, run, task_id) else PHASE_FATAL


async def _process_result(db, payload: dict) -> bool:
    """
    Pipeline de processamento de resultado de execução.

    Retorna False se o run ainda nao existe — agora improvavel porque
    _dispatch_job cria o run SINCRONAMENTE antes de despachar. Pode
    ocorrer em cenarios degradados: payload manual via redis-cli, run
    apagado, ou crash da API entre _dispatch_job e commit. _consume_one
    faz retry com backoff antes de descartar.

    Levanta PhaseFailure quando o status foi gravado mas alguma fase acessoria
    falhou: o item vai para run_dead_letter anotado com as fases perdidas. Antes
    de B11 a excecao subia crua e produzia o mesmo dead-letter; o isolamento por
    fase nao pode custar a observabilidade da perda.
    """
    task_id = payload["task_id"]
    # FOR UPDATE: dois workers com resultados do MESMO run (o verdadeiro e um
    # tardio) liam os dois 'running', os dois contavam o uso e o ultimo a gravar
    # vencia. Com a trava o segundo espera o commit do primeiro e ve o desfecho.
    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.task_id == task_id).with_for_update()
    )
    run = result.scalar_one_or_none()
    if not run:
        return False

    stats = payload.get("stats") or {}

    # Snapshot ANTES do update: guarda de idempotencia do agregado de uso.
    # Se o run ja estava terminal, este payload e uma reentrega (dead letter
    # reprocessado, replay do outbox do executor) e nao pode contar duas vezes.
    first_close = run.status in ("pending", "running")

    if (
        not first_close
        and payload.get("status") != run.status
        and not _desfecho_inferido_pelo_servidor(run)
    ):
        # Um desfecho DIFERENTE para um run ja fechado: o resultado passou pela
        # checagem de idempotencia do WS antes de o primeiro ser gravado (os dois
        # estavam na fila ao mesmo tempo). O primeiro desfecho vale — a mesma
        # regra do WS: um 'cancelled' tardio nao apaga um sucesso, nem o
        # contrario, nem um cancelamento pedido pelo usuario. A excecao e o
        # desfecho que o proprio servidor DEDUZIU (executor sumiu, run perdido
        # na reconciliacao): o resultado de verdade que ja estava na fila corrige
        # o palpite, como sempre corrigiu. Reentrega do MESMO desfecho segue
        # abaixo (dead letter).
        logger.warning(
            "run %s: ja fechado como '%s' — resultado '%s' que chegou depois ignorado.",
            task_id, run.status, payload.get("status"),
        )
        await db.commit()  # solta a trava do FOR UPDATE
        return True

    await _update_run_status(db, run, payload)

    # Contabilizacao de uso vem PRIMEIRO: e o unico dado de billing e nao pode
    # depender de metricas (que o caminho de erro pode nao produzir).
    phases = (
        ("uso diario",  _upsert_usage_daily,                (db, run, stats, first_close)),
        ("metricas",    _persist_metrics_if_present,        (db, run, stats, payload)),
        ("artefatos",   _register_artifacts_if_present,     (db, run, stats)),
        ("pins",        _persist_pinned_outputs_if_present, (db, run, stats)),
        # O catalogo de fontes aprende com a execucao: os nos WFS que leram com
        # sucesso viram (ou atualizam) fontes do workspace. Depois das metricas
        # (le o esquema que elas trazem) e antes da notificacao (que e o fim).
        ("fontes",      _aprender_fontes_if_present,        (db, run, stats, first_close)),
        ("notificacao", _fire_notification_if_configured,   (db, run)),
    )
    failed: list[str] = []
    for idx, (label, fn, args) in enumerate(phases):
        outcome = await _run_phase(db, run, task_id, label, fn, *args)
        if outcome == PHASE_FATAL:
            # Sessao irrecuperavel: as fases restantes nem chegam a rodar, entao
            # TODAS elas entram no relato de perda que vai para o dead letter.
            failed.extend(p[0] for p in phases[idx:])
            break
        if outcome == PHASE_FAILED:
            failed.append(label)

    if failed:
        raise PhaseFailure(task_id, failed)
    return True


def _json_seguro(valor):
    """Troca NaN/Infinity por None, recursivamente.

    `json.dumps` do Python emite NaN e Infinity — extensão que a spec JSON não
    tem — e `json.loads` os aceita de volta, então eles atravessam a fila Redis
    intactos. Ao chegarem numa coluna JSONB o Postgres recusa o INSERT, a
    exceção sobe antes do commit e o run inteiro vai para run_dead_letter com o
    status preso em 'running', mesmo tendo concluído.

    A origem conhecida era o bbox de GeoDataFrame vazio (ver
    flow/metrics/collector._bbox_finito), mas a fila é um contrato externo:
    sanear aqui é o que impede um NaN de qualquer outra métrica derrubar a
    gravação do resultado.
    """
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if isinstance(valor, dict):
        return {k: _json_seguro(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_seguro(v) for v in valor]
    return valor


# Categorias de um 'failed' que o SERVIDOR deduziu sem resultado do executor:
# `executor_lost` (desconectou, ou a reconciliacao nao achou o job) e `dispatch`
# (o envio nunca foi confirmado). Um resultado verdadeiro que chegue depois
# substitui esse desfecho — ver `_process_result`.
_CATEGORIAS_INFERIDAS = frozenset({"executor_lost", "dispatch"})


def _desfecho_inferido_pelo_servidor(run: WorkflowRun) -> bool:
    return run.status == "failed" and run.error_category in _CATEGORIAS_INFERIDAS


def _numero_finito(valor):
    """O número, ou 0 se não for um número finito.

    Para os incrementos do usage_daily, onde o `_json_seguro` não basta: o
    None que ele devolve para NaN viraria NULL na soma do SQL (`coluna + NULL`
    zera a linha do dia), e o NaN cru pior — `NaN or 0` é NaN, e NaN + x = NaN
    contamina o agregado do workspace para sempre.
    """
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and math.isfinite(valor):
        return valor
    return 0


def _stats_para_coluna(stats: dict) -> dict:
    """Fica so com o que a coluna node_stats existe para guardar.

    O executor manda, dentro de `stats`, chaves de controle que NAO sao
    estatistica por no: `__metrics__` (ja normalizado em workflow_run_metrics e
    node_run_metrics), `__artifacts__` (ja em artifacts), `__response__` (o body
    inline do ResponseNode, que o webhook le do Redis) e
    `__updated_pinned_outputs__` (consumido aqui mesmo, a partir do payload da
    fila, e persistido em workflows.pinned_outputs).

    Gravar tudo isso de volta no JSON inflava a coluna em uma ordem de grandeza
    — o executor so trunca o payload acima de 16 MB — e o preco era cobrado em
    TODA listagem de execucoes, que trazia a linha inteira do Postgres para ler
    um unico inteiro. Sobra `__run_meta__`, que so existe aqui.
    """
    return {
        k: v for k, v in stats.items()
        if not k.startswith("__") or k == NODE_STATS_RUN_META_KEY
    }


async def _update_run_status(db, run: WorkflowRun, payload: dict) -> None:
    run.status           = payload["status"]
    run.error_message    = payload.get("error_message")
    # So no desfecho 'failed': o WS router ja zera a categoria em sucesso e
    # cancelamento, mas a fila e contrato externo — um payload antigo (ou
    # forjado) nao pode carimbar categoria num run que deu certo. Corte em 16
    # por ser o tamanho da coluna: um executor que mande algo fora da taxonomia
    # nao pode derrubar o commit do fechamento inteiro.
    _categoria = payload.get("error_category")
    run.error_category   = (
        _categoria_conhecida(_categoria) if run.status == "failed" and _categoria else None
    )
    # node_stats so e sobrescrito quando vem conteudo. No caminho de erro,
    # timeout ou cancelamento o executor pode mandar stats vazio/ausente —
    # gravar {} apagaria os stats parciais ja acumulados no run e o painel
    # perderia o historico dos nos que chegaram a rodar.
    stats = payload.get("stats") or {}
    if stats:
        run.node_stats = _json_seguro(_stats_para_coluna(stats))
    # end_time chega da fila e vai para uma coluna timestamptz. Um valor naive
    # seria interpretado pelo Postgres no fuso da sessao (TZ dos containers) e
    # gravado deslocado — 4h no futuro em America/Cuiaba. O produtor ja manda
    # aware, mas payloads antigos podem estar na fila e a fila e um contrato
    # externo: assumir UTC quando o offset nao vier.
    _end = datetime.fromisoformat(payload["end_time"])
    if _end.tzinfo is None:
        _end = _end.replace(tzinfo=timezone.utc)
    run.end_time         = _end
    run.duration_seconds = payload.get("duration_seconds")
    await db.commit()
    logger.debug("run atualizado: task_id=%s status=%s", payload["task_id"], run.status)


async def _persist_metrics_if_present(db, run: WorkflowRun, stats: dict, payload: dict) -> None:
    metrics_data = stats.get("__metrics__")
    if metrics_data:
        await _persist_metrics(db, run, metrics_data, payload)


async def _register_artifacts_if_present(db, run: WorkflowRun, stats: dict) -> None:
    artifacts_meta = stats.get("__artifacts__", {})
    if artifacts_meta:
        await _register_artifacts(db, run, artifacts_meta)


# ── Derivacao de s3_key no servidor (SEG cross-tenant) ───────────────────────
#
# O executor manda 's3_key' / '__pin_s3_key__' junto com os metadados, mas esses
# campos sao ATACAVEIS: um executor comprometido apontava para
# 'artifacts/<outro-workspace>/...' e o consumer gravava a linha Artifact com
# credential_id=None — download PUBLICO, sem token, de um objeto de outro tenant.
# No caso do pin era pior: /workflows/{id}/pin/{node} deleta o objeto apontado
# pelo '__pin_s3_key__' salvo, entao a key forjada virava delete cross-tenant.
#
# Todo endpoint HTTP equivalente ja passa por `_validate_agent_s3_key`; o caminho
# WS -> fila run_results nao passava por nada. Aqui invertemos o fluxo: o SERVIDOR
# deriva a key a partir de (prefixo, workspace do run, task_id, nome do arquivo) —
# exatamente o formato que o executor usa em flow/utils/artifact_helpers.py e
# flow/executor/pin.py — e ainda revalida com o mesmo guard dos endpoints HTTP,
# restrito ao workspace do run.
_PIN_FORMATS = ("json", "geojson", "parquet")

# Charset de _S3_KEY_RE (drive_router) menos a barra: tudo que sobrar vira '_'.
_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]")
_DOT_RUN = re.compile(r"\.{2,}")
_MAX_STEM_LEN = 160
_MAX_EXT_LEN = 16


def _sanitize_filename(filename: str) -> str:
    """Reduz o nome recebido do executor a um basename S3-safe.

    NORMALIZA em vez de rejeitar. O nome sai de `slugify_label` no executor, que
    usa `str.isalnum()` — Unicode-aware, portanto PRESERVA acento. Num produto
    pt-BR o label do no ('Relatorio 2026', 'Area Util') e a fonte do nome, entao
    o caso acentuado e o comum, nao a excecao: rejeitar fazia `_derive_s3_key`
    devolver None e o artefato sumia da UI deixando so um WARNING no servidor.

    NFKD + descarte de combinantes converte 'ó'→'o'; o que sobrar fora do
    charset (espaco, 'ç' isolado, ':') vira '_'. Sequencias de ponto sao
    colapsadas porque `_validate_agent_s3_key` recusa qualquer key com '..'.
    """
    name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if name in ("", ".", ".."):
        return ""

    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = _UNSAFE_NAME_CHARS.sub("_", name)
    name = _DOT_RUN.sub(".", name).strip(".")
    if not name:
        return ""

    # S3 limita a key a 1024 bytes e nomes patologicos chegam do executor sem
    # limite; corta o stem preservando a extensao (o mime do Drive vem dela).
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return name[:_MAX_STEM_LEN]
    return f"{stem[:_MAX_STEM_LEN]}.{ext[:_MAX_EXT_LEN]}"


def _derive_s3_key(prefix: str, workspace_id: str, task_id: str, filename: str) -> str | None:
    """Monta a key canonica e a valida com o mesmo guard dos endpoints HTTP.

    Retorna None so quando nao sobra nome nenhum apos o saneamento ou quando
    falta workspace/task — o charset ja foi normalizado por _sanitize_filename,
    entao a rejeicao aqui e a rede de seguranca, nao o caminho comum.
    """
    from fastapi import HTTPException
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    safe_name = _sanitize_filename(filename)
    if not safe_name or not workspace_id or not task_id:
        return None

    key = f"{prefix}/{workspace_id}/{task_id}/{safe_name}"
    try:
        _validate_agent_s3_key(key, [workspace_id])
    except HTTPException as exc:
        logger.warning("s3_key derivada rejeitada (%s): %s", exc.detail, key)
        return None
    return key


def _safe_pin_ref(run: WorkflowRun, nid: str, ref: dict) -> dict | None:
    """Reescreve a referencia de pin com a s3_key derivada pelo servidor.

    O executor monta o nome como '{node_id}_pin.{fmt}' e a key como
    'pin-cache/{workspace_id or "default"}/{task_id or "no-task"}/{nome}'
    (flow/executor/pin.py) — reproduzimos isso aqui para nao quebrar o caminho
    legitimo, ignorando o que veio no payload.
    """
    fmt = ref.get("__pin_format__") or "json"
    if fmt not in _PIN_FORMATS:
        return None

    filename = f"{nid}_pin.{fmt}"
    s3_key = _derive_s3_key(
        "pin-cache",
        run.workspace_id or "default",
        run.task_id or "no-task",
        filename,
    )
    if not s3_key:
        return None

    safe = dict(ref)
    safe["__pin_s3_key__"]  = s3_key
    safe["__pin_format__"]  = fmt
    safe["__pin_filename__"] = filename
    return safe


async def _aprender_fontes_if_present(db, run: WorkflowRun, stats: dict, first_close: bool) -> None:
    """Fase "fontes": registra no catalogo as fontes WFS que esta execucao leu.

    So execucao `success`, so nos `WFS` com status `completed` (quem falhou nao
    ensina nada), e so quando a flag esta ligada. A definition vem do Workflow
    ATUAL — a mesma limitacao aceita pelos pins: url/typeName ficam em claro
    (`encrypt_workflow_connections` so cifra `connectionString`). `first_close`
    e a guarda de reentrega: uma reentrega nao conta o uso duas vezes, e o
    upsert por chave nao duplica a linha.
    """
    from app.core.config import FONTES_APRENDER_DAS_EXECUCOES

    if not FONTES_APRENDER_DAS_EXECUCOES or run.status != "success" or not run.workspace_id:
        return
    if not isinstance(stats, dict) or not any(
        isinstance(v, dict) and v.get("node_name") == "WFS"
        for k, v in stats.items() if not str(k).startswith("__")
    ):
        return

    wf_result = await db.execute(select(Workflow).where(Workflow.id_hash == run.workflow_hash))
    wf_obj = wf_result.scalar_one_or_none()
    if not wf_obj or not isinstance(wf_obj.definition, dict):
        return

    from app.services import fontes_service

    aprendidas = await fontes_service.aprender_de_execucao(
        db, run, stats, wf_obj.definition, first_close=first_close,
    )
    if aprendidas:
        await db.commit()
        logger.info("run %s: %d fonte(s) WFS registrada(s) no catalogo.", run.task_id, aprendidas)


async def _persist_pinned_outputs_if_present(db, run: WorkflowRun, stats: dict) -> None:
    updated_pins = stats.get("__updated_pinned_outputs__")
    if not updated_pins or not isinstance(updated_pins, dict):
        return

    from sqlalchemy.orm.attributes import flag_modified
    wf_result = await db.execute(
        select(Workflow).where(Workflow.id_hash == run.workflow_hash)
    )
    wf_obj = wf_result.scalar_one_or_none()
    if not wf_obj:
        return

    # SEG: o workflow pode ter sido movido de workspace enquanto este run corria
    # (POST /workflows/{id}/move). As s3_keys sao derivadas de `run.workspace_id`
    # — o workspace de ORIGEM —, entao grava-las agora deixaria o workflow, ja no
    # destino, com pins apontando para pin-cache/{ws_origem}/. Na proxima
    # execucao o executor pediria esses objetos e, sendo o executor default (que
    # enxerga todos os workspaces), leria dados do tenant antigo.
    #
    # Descartar e o lado seguro: o pin e cache, nao dado primario, e a proxima
    # execucao no destino o recria sob o prefixo correto.
    if run.workspace_id != wf_obj.workspace_id:
        logger.warning(
            "run %s: auto-pin descartado — o workflow %s mudou do workspace '%s' "
            "para '%s' durante a execucao.",
            run.task_id, run.workflow_hash, run.workspace_id, wf_obj.workspace_id,
        )
        return

    # Sanitiza ANTES de gravar: o que entra em pinned_outputs e reenviado ao
    # executor no proximo dispatch e alimenta o delete do unpin.
    #
    # So refs DESTA run: `_safe_pin_ref` deriva a s3_key com o task_id atual,
    # entao aceitar uma ref que o executor apenas repassou (gravada numa run
    # antiga) a repontaria para um objeto que nunca foi enviado — 404 permanente
    # no pin. Executores atualizados ja mandam apenas o que regravaram
    # (updated_pin_refs); este filtro protege contra executores antigos, que
    # reportavam pinned_outputs inteiro. A chave declarada e atacavel, mas
    # usa-la para DESCARTAR e fail-safe: mentir o task_id atual so leva a ref
    # a mesma derivacao canonica que ela ja teria.
    task_atual = run.task_id or "no-task"
    accepted: dict[str, dict] = {}
    for nid, ref in updated_pins.items():
        if not isinstance(ref, dict) or "__pin_s3_key__" not in ref:
            continue
        if f"/{task_atual}/" not in str(ref.get("__pin_s3_key__", "")):
            logger.debug(
                "run %s: pin do node '%s' ignorado — ref de uma run anterior (passthrough).",
                run.task_id, nid,
            )
            continue
        safe_ref = _safe_pin_ref(run, nid, ref)
        if safe_ref is None:
            logger.warning(
                "run %s: pin do node '%s' descartado — nao foi possivel derivar uma s3_key valida.",
                run.task_id, nid,
            )
            continue
        accepted[nid] = safe_ref

    if not accepted:
        return

    current_pins = dict(wf_obj.pinned_outputs or {})
    current_pins.update(accepted)
    wf_obj.pinned_outputs = current_pins
    flag_modified(wf_obj, "pinned_outputs")

    for nid, ref in accepted.items():
        await _upsert_pin_artifact(db, run, wf_obj, nid, ref)

    await db.commit()
    logger.debug("Auto-pin persistido para workflow %s: %s", run.workflow_hash, list(accepted.keys()))


async def _upsert_pin_artifact(db, run: WorkflowRun, wf_obj, nid: str, ref: dict) -> None:
    # ref ja passou por _safe_pin_ref — s3_key/format/filename sao do servidor.
    s3_key = ref["__pin_s3_key__"]
    fmt = ref["__pin_format__"]
    filename = ref["__pin_filename__"]

    # `scalar_one_or_none()` aqui levantava `MultipleResultsFound` com duas
    # linhas — e é ESTA função que cria a segunda: `artifacts` não tem
    # constraint única em (workflow_hash, node_id, is_pinned)
    # (`models/artifact.py`), então dois runs do mesmo fluxo terminando juntos
    # não acham nada, cada um insere a sua, e a partir daí toda leitura
    # levantava. Numa rota isso é um 500; aqui é pior — este caminho é o do
    # `job_result`, e a exceção pendura a persistência do resultado da execução.
    #
    # A mais nova vence e as LINHAS extras são apagadas, o que limpa o dado com
    # o uso. Os objetos delas ficam para o reconcile: apagar no storage aqui
    # seria uma ida à rede no caminho quente do `job_result`, e um órfão no
    # MinIO custa bytes, não correção.
    #
    # O colapso continua aqui mesmo depois do índice único parcial
    # (`uq_artifact_pin_por_no`, migração de 2026-09-15): ele é o que limpa uma
    # base que ainda não migrou, e é o caminho do SQLite dos testes, que nasce
    # do `create_all`. Com o índice, a corrida deixa de criar a duplicata e
    # passa a levantar no INSERT — tratado no SAVEPOINT abaixo.
    existing = await db.execute(
        select(Artifact)
        .where(
            Artifact.workflow_hash == run.workflow_hash,
            Artifact.node_id == nid,
            Artifact.is_pinned.is_(True),
        )
        .order_by(Artifact.id.desc())
    )
    linhas = list(existing.scalars().all())
    old_art = linhas[0] if linhas else None
    for extra in linhas[1:]:
        logger.warning(
            "run %s: linha de pin-cache duplicada para o node '%s' (id=%s) removida.",
            run.task_id, nid, extra.id,
        )
        await db.delete(extra)
    if old_art:
        old_art.s3_key = s3_key
        old_art.filename = filename
        old_art.format = fmt
        old_art.run_id = run.task_id
        # O workspace acompanha a s3_key. A busca acima e por
        # (workflow_hash, node_id) e nao filtra tenant, entao uma linha remanescente
        # de antes de um move seria repontada para um objeto do workspace novo
        # mantendo o `workspace_id` antigo — e o download usa a s3_key literal,
        # servindo dados do destino a quem so tem acesso a origem.
        old_art.workspace_id = run.workspace_id or wf_obj.workspace_id or ""
    else:
        novo = Artifact(
            # Mesmo workspace usado para derivar a s3_key — o registro nunca pode
            # apontar para um tenant diferente do dono do objeto.
            workspace_id=run.workspace_id or wf_obj.workspace_id or "",
            workflow_hash=run.workflow_hash,
            run_id=run.task_id,
            node_id=nid,
            output_key=f"pin-cache-{nid}",
            filename=filename,
            format=fmt,
            s3_key=s3_key,
            is_pinned=True,
        )
        # SAVEPOINT, e não um `try` solto: com o índice único parcial, dois runs
        # do mesmo fluxo terminando juntos leem "não existe" ao mesmo tempo e o
        # segundo INSERT viola a constraint. No Postgres um erro assim envenena
        # a transação inteira — e esta é a transação que persiste o RESULTADO da
        # execução, no caminho do `job_result`. O savepoint isola a falha; o
        # padrão é o de `api_token_service.marcar_uso` e `credential_loader`.
        try:
            async with db.begin_nested():
                db.add(novo)
                await db.flush()
        except IntegrityError:
            # O outro run ganhou a corrida. A linha dele é a verdade; esta
            # chamada só a repontou para o objeto mais novo, que é exatamente o
            # que o ramo de cima faz.
            logger.info(
                "run %s: outro run criou a linha de pin-cache do node '%s' primeiro; "
                "repontando a existente.",
                run.task_id, nid,
            )
            vencedora = (await db.execute(
                select(Artifact)
                .where(
                    Artifact.workflow_hash == run.workflow_hash,
                    Artifact.node_id == nid,
                    Artifact.is_pinned.is_(True),
                )
                .order_by(Artifact.id.desc())
            )).scalars().first()
            if vencedora is None:  # pragma: no cover - só se a linha sumir no meio
                raise
            vencedora.s3_key = s3_key
            vencedora.filename = filename
            vencedora.format = fmt
            vencedora.run_id = run.task_id
            vencedora.workspace_id = run.workspace_id or wf_obj.workspace_id or ""


async def _fire_notification_if_configured(db, run: WorkflowRun) -> None:
    from urllib.parse import urlparse
    from app.models.workspace import Workspace

    wf_result = await db.execute(
        select(Workflow.notification_url, Workflow.workspace_id).where(
            Workflow.id_hash == run.workflow_hash
        )
    )
    row = wf_result.first()
    if not row:
        return
    notification_url, workspace_id = row
    if not notification_url:
        return

    try:
        target_host = urlparse(notification_url).hostname or ""
    except Exception:
        target_host = ""

    # Whitelist GLOBAL (admin → Configurações). Era gravada e exibida — a tela
    # avisa quando está vazia —, mas nenhum disparo a consultava: a restrição
    # que o admin configurava não restringia nada. Vazia = sem restrição; com
    # itens, o host precisa estar nela E na allowlist do workspace (abaixo).
    # O que foi gravado antes desta regra (um `*`, uma URL com caminho) passa
    # pela mesma validação da gravação: o que o matcher não casaria é ignorado.
    from app.core.system_config import get_config
    from app.core.utils.allowlist import padroes_validos

    global_list = padroes_validos(await get_config(db, "webhook_whitelist", default=[]) or [])
    if global_list and not hostname_matches_allowlist(target_host, global_list):
        logger.warning(
            "Webhook bloqueado pela whitelist global: host '%s' nao esta em %s.",
            target_host, global_list,
        )
        return

    # V13: allowlist de hosts por workspace. Sem essa lista, qualquer URL que
    # passe no SSRF check e aceita — incluindo intranet do operador que
    # configurou o webhook, vazando resultado de runs entre tenants.
    if workspace_id:
        ws_result = await db.execute(
            select(Workspace.notification_url_allowlist).where(
                Workspace.id_hash == workspace_id
            )
        )
        allowlist = ws_result.scalar_one_or_none() or []
        if allowlist:
            if not hostname_matches_allowlist(target_host, allowlist):
                logger.warning(
                    "Webhook bloqueado por allowlist do workspace '%s': host '%s' "
                    "nao esta em %s.",
                    workspace_id, target_host, allowlist,
                )
                return

    notify_body = {
        "task_id":          run.task_id,
        "workflow_hash":    run.workflow_hash,
        "status":           run.status,
        "duration_seconds": run.duration_seconds,
        "error_message":    run.error_message,
    }
    _schedule_webhook_notification(notification_url, notify_body)


async def _get_retention_days(db) -> int | None:
    """Lê dias de retenção de artefatos da configuração do sistema. None = sem expiração."""
    try:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == "artifact_retention_days")
        )
        cfg = result.scalar_one_or_none()
        if cfg and cfg.value is not None:
            return int(cfg.value)
    except Exception as exc:
        logger.warning("Falha ao ler artifact_retention_days: %s", exc)
        # Um SELECT que falha tambem invalida a sessao — sem o rollback o INSERT
        # dos artefatos logo abaixo estouraria PendingRollbackError.
        try:
            await db.rollback()
        except Exception as rb_exc:
            logger.debug("Rollback apos falha em artifact_retention_days: %s", rb_exc)
    return None


# Quantos HEAD simultaneos ao MinIO. `storage.head` e boto3 sincrono, entao
# cada um ocupa uma thread do executor padrao do asyncio (default: 32); 8 da
# vazao suficiente para um run com dezenas de saidas sem monopolizar o pool,
# que e compartilhado com o resto da API neste worker.
_HEAD_CONCURRENCY = 8


async def _head_sizes(keys: list[str]) -> dict[str, int]:
    """Consulta o tamanho de varias keys no storage de uma vez.

    Era um HEAD por artefato, em serie, dentro do laco de registro: um run com
    20 saidas pagava 20 round-trips de rede enfileirados com o consumer parado,
    e a fila inteira atrasava atras dele.

    `return_exceptions=True` preserva o comportamento antigo de falha parcial —
    uma key que falha vira um WARNING e fica sem tamanho, sem derrubar as
    demais.
    """
    if not keys:
        return {}

    from app.core import storage as _s3

    sem = asyncio.Semaphore(_HEAD_CONCURRENCY)

    async def _one(key: str):
        async with sem:
            # storage.head e boto3 sincrono. Este consumer roda como UNICA task
            # de background no event loop — sem to_thread, cada HEAD congelava
            # TODO o trafego da API neste worker durante o round-trip.
            return await asyncio.to_thread(_s3.head, key)

    resultados = await asyncio.gather(*(_one(k) for k in keys), return_exceptions=True)

    tamanhos: dict[str, int] = {}
    for key, obj in zip(keys, resultados):
        if isinstance(obj, BaseException):
            logger.warning("Falha ao obter tamanho do artefato S3 '%s': %s", key, obj)
            continue
        if obj:
            tamanhos[key] = obj["size"]
    return tamanhos


@dataclass(frozen=True)
class _Resolucao:
    """O destino de cada item saneado, decidido ANTES de ir ao storage (fase 2)."""

    a_criar: list[dict]             # vira linha nova: Artifact ou WorkspaceFile
    drive_existentes: list[tuple]   # (WorkspaceFile, acao): a linha ja existe, so avisar
    tamanhos: dict[str, int]        # HEAD de quem vira linha e tem objeto no storage


async def _register_artifacts(db, run: WorkflowRun, artifacts_meta: dict) -> None:
    """
    Registra artefatos produzidos no run.

    - context="artifacts" (padrao): cria registro na tabela Artifact.
    - context="drive": cria registro na tabela WorkspaceFile (Drive),
      permitindo sincronizacao automatica com executores. Nao duplica no Artifact.

    artifacts_meta: { node_id: [ {output_key, format, features, filename, ...} ] }

    SEG: o campo 's3_key' enviado pelo executor e IGNORADO — a key e derivada
    aqui a partir do workspace/task do run (ver _derive_s3_key).

    Estruturado em tres fases sem IO dentro do laco: (1) saneia o payload
    (`_sanear_artefatos`), (2) resolve banco e storage EM LOTE
    (`_resolver_em_lote`), (3) monta as linhas e persiste com um commit
    (`_persistir_artefatos`) — e so entao avisa o Drive (`_avisar_drive`). A
    versao anterior fazia duas queries por item de Drive (N+1) e um HEAD
    serial por artefato, tudo no processamento de um unico item da fila.
    """
    if not run.workspace_id:
        logger.warning(
            "run %s nao tem workspace_id — artefatos ignorados (nao ha prefixo seguro).",
            run.task_id,
        )
        return

    retention_days = await _get_retention_days(db)
    # Coluna expires_at é TIMESTAMP WITHOUT TIME ZONE — usar datetime naive (UTC)
    expires_at = (utc_now_naive() + timedelta(days=retention_days)) if retention_days else None

    executor_id = None
    if run.host and run.host.startswith("executor:"):
        executor_id = run.host[len("executor:"):]

    known = await _artefatos_ja_registrados(db, run)
    pendentes = _sanear_artefatos(run, artifacts_meta, known)
    if not pendentes:
        return

    resolucao = await _resolver_em_lote(db, run, pendentes)
    novos_no_drive = await _persistir_artefatos(
        db, run, resolucao, expires_at=expires_at, executor_id=executor_id,
    )
    # O arquivo que ja existia e avisado antes do novo: e a ordem em que cada
    # destino foi decidido (fase 2, depois fase 3).
    drive_files = resolucao.drive_existentes + novos_no_drive

    logger.debug("run %s: %d artefato(s) registrado(s) (%d no Drive).",
                 run.task_id, len(resolucao.a_criar), len(drive_files))

    await _avisar_drive(drive_files)


async def _artefatos_ja_registrados(db, run: WorkflowRun) -> set[tuple]:
    """Pares (node_id, filename) que este run ja gravou em Artifact.

    Idempotencia: se este payload for reentregue (dead letter reprocessado,
    replay do outbox) nao queremos duplicar linhas.

    Chave de dedup ESTAVEL (node_id, filename) no run, NAO a s3_key: artefato
    local grava s3_key=None (keepLocal / local_fallback), entao a s3_key
    derivada nunca casava com known e a reentrega recriava a linha. filename e
    node_id existem em toda linha, local ou nao. Dentro de um run (ws/task
    fixos) a s3_key derivada e 1:1 com o filename, entao a granularidade de
    dedup do caso NAO-local nao muda.
    """
    known_result = await db.execute(
        select(Artifact.node_id, Artifact.filename).where(Artifact.run_id == run.task_id)
    )
    return {(nid, fn) for nid, fn in known_result.all()}


def _sanear_artefatos(run: WorkflowRun, artifacts_meta: dict, known: set[tuple]) -> list[dict]:
    """Fase 1: saneia o payload. Nenhum IO aqui.

    Devolve um dict por item que vira registro — node_id, item cru, s3_key
    DERIVADA, filename saneado, se e local e o contexto —, sem o que nao e
    objeto, sem nome invalido e sem repetido (no proprio lote ou ja em `known`).
    """
    # Copia: o lote tambem deduplica contra si mesmo, e `known` e de quem chama.
    known = set(known)
    pendentes: list[dict] = []
    for node_id, items in artifacts_meta.items():
        for item in (items if isinstance(items, list) else [items]):
            if not isinstance(item, dict):
                continue

            # Artefato mantido no disco do executor. Dois caminhos chegam aqui:
            #   * keepLocal (no de saida com localidade=executor): politica LGPD,
            #     content_location='executor';
            #   * local_fallback: o upload ao MinIO FALHOU e o fallback gravou os
            #     bytes no MESMO lugar de um keepLocal
            #     (artifacts_root()/{ws}/{task}/{arquivo}). O executor reporta
            #     content_location='minio' de proposito (o destino ERA a nuvem),
            #     mas o objeto nunca chegou la — registrar como 'minio' com a
            #     s3_key derivada dava um download que respondia 404 para sempre.
            #     Os bytes estao no executor, entao e como executor-local que este
            #     artefato e servido (o download da plataforma nao busca conteudo
            #     local — a UI mostra "Sem download", que e honesto, em vez de um
            #     botao que quebra).
            #
            # Nao ha objeto no storage em nenhum dos dois: nada de derivar s3_key
            # nem de HEAD.
            #
            # A FLAG e aceita do executor, mas o CAMINHO nao. Como a s3_key, o
            # `local_path` e derivado aqui a partir de (workspace do run, task do
            # run, nome saneado) — um caminho vindo pela rede voltaria depois
            # para o executor na ordem de limpeza por retencao, e um `../` ali
            # transformaria a retencao em delete arbitrario no disco do usuario.
            #
            # Aceitar a flag em si e seguro: um executor comprometido que mentisse
            # 'executor' apenas deixaria um objeto orfao no storage, e mentindo
            # 'minio' geraria um download quebrado. Nenhum dos dois expoe dado de
            # outro tenant, que e o que _derive_s3_key existe para impedir.
            local = (
                item.get("content_location") == "executor"
                or bool(item.get("local_fallback"))
            )

            s3_key = _derive_s3_key(
                "artifacts", run.workspace_id, run.task_id, item.get("filename", "")
            )
            if not s3_key:
                logger.warning(
                    "run %s / node %s: artefato com filename invalido ('%s') — ignorado.",
                    run.task_id, node_id, item.get("filename", ""),
                )
                continue
            # O nome exibido tem de ser o MESMO do ultimo segmento da key: se
            # o saneamento trocou algo, mostrar o nome cru faria a UI prometer
            # um download que nao existe com aquele nome.
            filename = s3_key.rsplit("/", 1)[-1]
            if (node_id, filename) in known:
                continue
            known.add((node_id, filename))

            pendentes.append({
                "node_id":  node_id,
                "item":     item,
                "s3_key":   s3_key,
                "filename": filename,
                "local":    local,
                "context":  item.get("context") or "artifacts",
            })
    return pendentes


async def _resolver_em_lote(db, run: WorkflowRun, pendentes: list[dict]) -> _Resolucao:
    """Fase 2: resolve banco e storage em lote.

    O executor devolve o id_hash da linha que /drive/executor-upload-url criou
    OU reaproveitou. Ele e a guarda confiavel; a busca por s3_key nao serve
    para o caso de sobrescrita.

    A key usada aqui e DERIVADA do task_id do run (ver _derive_s3_key, e o SEG
    na docstring de _register_artifacts: a key vinda do executor e ignorada de
    proposito). Quando o upload sobrescreveu um arquivo existente, a linha
    manteve a s3_key ORIGINAL — de um run antigo — e a derivada nao casa com
    ela. A guarda entao nao encontrava nada e nascia uma linha nova a cada
    execucao, apontando para uma key onde o PUT nunca escreveu. No run seguinte
    essa orfa era a mais recente do workspace, virava alvo da sobrescrita, e o
    ciclo se repetia.
    """
    from app.models.workspace_file import WorkspaceFile

    drive_pendentes = [p for p in pendentes if p["context"] == "drive"]
    drive_ids = {
        p["item"]["drive_file_id"] for p in drive_pendentes if p["item"].get("drive_file_id")
    }

    linhas_por_id: dict[str, WorkspaceFile] = {}
    if drive_ids:
        res = await db.execute(
            select(WorkspaceFile).where(
                WorkspaceFile.id_hash.in_(drive_ids),
                # Confirma no BANCO que a linha existe e e deste workspace: o id
                # vem do executor, entao nao vale por si so. Se nao casar, segue
                # o fluxo normal.
                WorkspaceFile.workspace_id == run.workspace_id,
            )
        )
        linhas_por_id = {linha.id_hash: linha for linha in res.scalars().all()}

    keys_ja_no_drive: set[str] = set()
    if drive_pendentes:
        # Rede para caminhos que nao passaram pelo executor-upload-url.
        res = await db.execute(
            select(WorkspaceFile.s3_key).where(
                WorkspaceFile.s3_key.in_([p["s3_key"] for p in drive_pendentes])
            )
        )
        keys_ja_no_drive = set(res.scalars().all())

    # Decide o destino de cada item ANTES de ir ao storage: assim os HEADs so
    # acontecem para o que de fato vira linha nova.
    a_criar: list[dict] = []
    # (linha, acao) — a acao distingue arquivo novo de sobrescrita.
    drive_existentes: list[tuple[WorkspaceFile, str]] = []
    for p in pendentes:
        if p["context"] != "drive":
            a_criar.append(p)
            continue
        linha = linhas_por_id.get(p["item"].get("drive_file_id"))
        if linha is not None:
            # A linha ja existe, mas o executor ainda precisa ser avisado:
            # `agent_confirm_upload` emite o evento com exclude_agent_id=<executor
            # que subiu>, e ha um unico target_executor_id por workspace —
            # normalmente o mesmo. O evento morre ali. Isso e correto para o
            # GeoSync, que sobe o que ja tem em disco (uploader.py usa o MESMO
            # endpoint, entao o servidor nao distingue as origens), mas nao para
            # um artefato de run: o DataOutput produziu o arquivo em memoria e o
            # executor nao o tem localmente. Sem esta emissao, um workspace com
            # SYNC_MODE download/bidirectional deixa de receber o arquivo.
            drive_existentes.append(
                (linha, "file_updated" if p["item"].get("drive_reused") else "file_created")
            )
            continue
        if p["s3_key"] in keys_ja_no_drive:
            continue  # Já registrado pelo executor-upload-url/confirm
        a_criar.append(p)

    tamanhos = await _head_sizes([p["s3_key"] for p in a_criar if not p["local"]])
    return _Resolucao(a_criar=a_criar, drive_existentes=drive_existentes, tamanhos=tamanhos)


async def _persistir_artefatos(
    db, run: WorkflowRun, resolucao: _Resolucao, *, expires_at, executor_id: str | None,
) -> list[tuple]:
    """Fase 3: monta as linhas e persiste com um unico commit.

    Devolve os arquivos NOVOS do Drive que tem objeto no storage, como
    (WorkspaceFile, "file_created"), para o aviso aos executores.
    """
    from app.models.workspace_file import WorkspaceFile

    novos_no_drive: list[tuple[WorkspaceFile, str]] = []
    for p in resolucao.a_criar:
        item, s3_key, filename = p["item"], p["s3_key"], p["filename"]

        if p["local"]:
            # O executor informa o tamanho: nao ha objeto para consultar, e um
            # HEAD aqui falharia a cada artefato local, poluindo o log com um
            # WARNING por execucao.
            bruto = item.get("size_bytes")
            size_bytes = bruto if isinstance(bruto, int) and bruto >= 0 else None
        else:
            size_bytes = resolucao.tamanhos.get(s3_key)

        if p["context"] == "drive":
            # Destino: Drive do Workspace (sincroniza com executores)
            ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
            mime = "application/geo+json" if ext == "geojson" else "application/json"
            if p["local"]:
                # Upload ao Drive falhou e caiu no fallback local: os bytes estao
                # no disco do executor, nunca chegaram ao MinIO. Um WorkspaceFile
                # 'confirmed' com a s3_key derivada daria um download 404 — e o
                # size_bytes o faria parecer ainda mais real. Registra-se como
                # CATALOGO (content_location='executor', sem s3_key), a mesma
                # representacao de /drive/executor-register: aparece no Drive com
                # o selo local e sem download, em vez de um botao que quebra. NAO
                # entra nos avisos — nao ha objeto para outro executor baixar.
                wf = WorkspaceFile(
                    workspace_id        = run.workspace_id,
                    s3_key              = None,
                    original_name       = filename,
                    extension           = ext,
                    mime_type           = mime,
                    size                = size_bytes,
                    uploaded_by         = executor_id,
                    status              = "confirmed",
                    content_location    = "executor",
                    content_executor_id = executor_id,
                )
                db.add(wf)
            else:
                wf = WorkspaceFile(
                    workspace_id  = run.workspace_id,
                    s3_key        = s3_key,
                    original_name = filename,
                    extension     = ext,
                    mime_type     = mime,
                    size          = size_bytes,
                    uploaded_by   = executor_id,
                    status        = "confirmed",
                )
                db.add(wf)
                novos_no_drive.append((wf, "file_created"))
        else:
            # Destino: tabela Artifact (disponivel via API de artefatos)
            db.add(Artifact(
                workspace_id     = run.workspace_id,
                workflow_hash    = run.workflow_hash,
                run_id           = run.task_id,
                node_id          = p["node_id"],
                output_key       = item.get("output_key", ""),
                filename         = filename,
                format           = item.get("format"),
                size_bytes       = size_bytes,
                features         = item.get("features"),
                # Artefato local nao tem objeto: gravar a key derivada faria
                # a UI oferecer um download que responderia 404 no MinIO.
                s3_key           = None if p["local"] else s3_key,
                content_location = "executor" if p["local"] else "minio",
                # Derivado, nunca o que o executor mandou — ver a nota acima.
                local_path       = (
                    f"{run.workspace_id}/{run.task_id}/{filename}" if p["local"] else None
                ),
                executor_id      = executor_id,
                credential_id    = item.get("credential_id") or None,
                is_published     = item.get("is_published", False),
                publish_config   = item.get("publish_config"),
                expires_at       = expires_at,
            ))

    # Sem linha nova nao ha o que commitar — o caso da reentrega, em que tudo ja
    # estava registrado, deixa de pagar uma transacao a toa.
    if resolucao.a_criar:
        await db.commit()
    return novos_no_drive


async def _avisar_drive(drive_files: list[tuple]) -> None:
    """Notifica executores sobre arquivos adicionados ao Drive.

    Roda depois do commit: um aviso que falha vira WARNING e nao impede os
    seguintes — as linhas ja estao gravadas.
    """
    from app.core.drive_events import emit_drive_event

    for wf, acao in drive_files:
        try:
            await emit_drive_event(
                workspace_id=wf.workspace_id,
                action=acao,
                file_info={
                    "id_hash": wf.id_hash,
                    "original_name": wf.original_name,
                    "extension": wf.extension,
                    "size": wf.size or 0,
                    # O GeoSync usa o md5 para decidir se precisa rebaixar o
                    # arquivo; sem ele, toda sobrescrita forca um download.
                    "content_md5": wf.content_md5,
                },
            )
        except Exception as exc:
            logger.warning("Falha ao notificar Drive para '%s': %s", wf.original_name, exc)


async def account_terminal_run(
    db, run: WorkflowRun, stats: dict | None = None, *, first_close: bool = True
) -> None:
    """Contabiliza no usage_daily um run fechado FORA do consumer.

    A fila run_results e alimentada por um unico ponto (`_handle_job_result` no
    WS router), mas ha caminhos que gravam status terminal direto no Postgres e
    nunca passam por ela: falha de despacho, run cancelado antes de chegar a um
    executor e o watchdog de executor desconectado. Sem este helper esses runs
    ficavam fora de `total_runs`/`failed_runs` — o dashboard mostrava o
    workspace mais saudavel do que ele e, e o billing subfaturava.

    Chame DEPOIS de gravar o status terminal (a classificacao le `run.status`) e
    so quando a transicao foi mesmo pending/running -> terminal. Falhar aqui nao
    pode derrubar o chamador: o fechamento do run e mais importante que o
    agregado, e engolir a excecao aqui evita mascarar o erro original que levou
    o run a ser fechado.
    """
    try:
        await _upsert_usage_daily(db, run, stats or {}, first_close)
    except Exception as exc:
        logger.error(
            "run %s: falha ao contabilizar usage_daily fora do consumer: %s",
            run.task_id, exc, exc_info=exc,
        )
        try:
            await db.rollback()
        except Exception as rb_exc:
            logger.debug("Rollback apos falha de usage_daily: %s", rb_exc)


async def _upsert_usage_daily(db, run: WorkflowRun, stats: dict, first_close: bool) -> None:
    """Contabiliza o run no agregado diario de uso do workspace.

    Antes este upsert vivia DENTRO de _persist_metrics, que so roda quando o
    executor manda '__metrics__'. Como o caminho de falha nao produzia metricas,
    NENHUMA falha era contabilizada e o dashboard mostrava 0% de erro para
    sempre. Agora roda para todo item da fila run_results, com o status real do
    run (success/failed/cancelled), mesmo sem metricas — nesse caso os
    contadores de recurso entram zerados, mas o run aparece no total e na taxa
    de erro.

    Fila NAO e sinonimo de "todo run que termina": os fechamentos feitos direto
    no Postgres entram por `account_terminal_run`, nao por aqui.

    `first_close` e a guarda de idempotencia: so contabiliza na primeira
    transicao pending/running -> terminal. Reentregas nao inflam o billing.
    """
    from app.models.run_metrics import UsageDaily
    from sqlalchemy import update as sa_update

    if not first_close:
        logger.debug("run %s: resultado reentregue — usage_daily nao recontado.", run.task_id)
        return
    if not run.workspace_id:
        # usage_daily.workspace_id e NOT NULL — run sem workspace nao tem a quem
        # ser atribuido no agregado.
        return

    run_data = ((stats or {}).get("__metrics__") or {}).get("run") or {}

    duration_ms = (
        _numero_finito(run_data.get("duration_ms"))
        or _numero_finito((run.duration_seconds or 0) * 1000)
    )
    cpu_avg = _numero_finito(run_data.get("cpu_avg_pct"))
    mem_avg = _numero_finito(run_data.get("mem_avg_mb"))
    duration_s = duration_ms / 1000

    # Um run cancelado pelo usuário não é sucesso nem falha: contá-lo como
    # falha inflaria a taxa de erro do workspace com uma decisão deliberada.
    _success = run.status == "success"
    _cancelled = run.status == "cancelled"

    # A data em UTC, como o resto do pipeline (`run.end_time`, métricas). Antes
    # `date.today()` usava o fuso local do container, deslocando a contagem para o
    # dia errado perto da meia-noite.
    today = utc_now_naive().date()

    # A contribuição deste run, como um mapa coluna -> incremento. Serve tanto ao
    # UPDATE atômico (soma no SQL) quanto aos valores da 1ª linha (INSERT).
    incrementos = {
        "total_runs": 1,
        "successful_runs": 1 if _success else 0,
        "failed_runs": 0 if (_success or _cancelled) else 1,
        "total_cpu_seconds": cpu_avg * duration_s / 100,
        "total_mem_mb_seconds": mem_avg * duration_s,
        "total_duration_ms": duration_ms,
        "total_input_bytes": _numero_finito(run_data.get("input_bytes")),
        "total_output_bytes": _numero_finito(run_data.get("output_bytes")),
        "total_features": _numero_finito(run_data.get("total_features")),
        "total_nodes_executed": _numero_finito(run_data.get("nodes_executed")),
    }

    async def _incrementar() -> int:
        # UPDATE atômico (`coluna = coluna + delta` no SQL), não o
        # ler-modificar-gravar em Python de antes: o incremento não se perde
        # quando o consumer e um `account_terminal_run` concorrente (sessões
        # separadas) fecham runs do mesmo workspace/dia ao mesmo tempo.
        result = await db.execute(
            sa_update(UsageDaily)
            .where(
                UsageDaily.date == today,
                UsageDaily.workspace_id == run.workspace_id,
            )
            .values({
                getattr(UsageDaily, coluna): getattr(UsageDaily, coluna) + delta
                for coluna, delta in incrementos.items()
            })
        )
        return result.rowcount or 0

    if await _incrementar() == 0:
        # A linha do dia ainda não existe: cria. SAVEPOINT (não um `try` solto):
        # com a UniqueConstraint(date, workspace_id), duas sessões leem "não
        # existe" ao mesmo tempo e o 2º INSERT viola a constraint — no Postgres
        # isso envenenaria a transação inteira. O savepoint isola a falha (mesmo
        # padrão de `_upsert_pin_artifact`); quem perde a corrida do INSERT
        # re-tenta o UPDATE atômico sobre a linha que o vencedor criou.
        try:
            async with db.begin_nested():
                db.add(UsageDaily(date=today, workspace_id=run.workspace_id, **incrementos))
                await db.flush()
        except IntegrityError:
            if await _incrementar() == 0:  # pragma: no cover - a linha vencedora sumiu no meio
                raise

    await db.commit()
    logger.debug("run %s: usage_daily atualizado (status=%s).", run.task_id, run.status)


def _ip_do_payload(payload: dict) -> str | None:
    """`executor_ip` do resultado, só se for um IP que cabe na coluna (45)."""
    return _ip_valido(payload.get("executor_ip"))


def _ip_valido(valor) -> str | None:
    """IP na forma canônica, ou None.

    A fila `run_results` também recebe payloads de fora do WebSocket (dead
    letter reprocessado, redis-cli): o que não for IP vira None. IPv6 com
    zona (`fe80::1%eth0`) também: a zona é texto livre, de qualquer tamanho,
    e estouraria o VARCHAR(45) — o INSERT falharia e o run perderia as
    métricas.
    """
    if not isinstance(valor, str):
        return None
    try:
        endereco = ipaddress.ip_address(valor.strip())
    except ValueError:
        return None
    if getattr(endereco, "scope_id", None):
        return None
    texto = str(endereco)
    return texto if len(texto) <= 45 else None


async def _persist_metrics(db, run: WorkflowRun, metrics: dict, payload: dict) -> None:
    """Persiste metricas de execucao nas tabelas workflow_run_metrics e node_run_metrics.

    O agregado usage_daily NAO e escrito aqui — foi extraido para
    _upsert_usage_daily, que roda sempre (com ou sem metricas).

    Excecoes sobem para _run_phase, que loga e faz o rollback: engoli-las aqui
    (como era antes) deixava a sessao invalida e derrubava artefatos, pins e
    webhook em cascata.
    """
    from app.models.run_metrics import WorkflowRunMetrics, NodeRunMetrics

    # O mesmo saneamento do node_stats, agora no dicionário inteiro: o bbox de
    # node_run_metrics e o spatial_summary/operation_types de
    # workflow_run_metrics são colunas JSON, e um NaN vindo de QUALQUER métrica
    # fazia o Postgres recusar o INSERT ("Token NaN is invalid") — 37 resultados
    # foram parar na fila morta por isso antes do `_bbox_finito` do collector.
    # Aqui não depende de o executor estar atualizado.
    metrics = _json_seguro(metrics or {})
    run_data = metrics.get("run", {})
    nodes_data = metrics.get("nodes", {})
    spatial_summary = metrics.get("spatial_summary")

    if not run.workspace_id:
        # workflow_run_metrics.workspace_id e NOT NULL.
        logger.warning("run %s sem workspace_id — metricas nao persistidas.", run.task_id)
        return

    # Idempotencia: run_id tem UNIQUE em workflow_run_metrics; uma reentrega
    # estouraria IntegrityError e mataria as fases seguintes.
    exists = await db.execute(
        select(WorkflowRunMetrics.id).where(WorkflowRunMetrics.run_id == run.task_id)
    )
    if exists.scalar_one_or_none() is not None:
        logger.debug("run %s: metricas ja persistidas — ignorando reentrega.", run.task_id)
        return

    # Busca dados do executor (nome e IP)
    _agent_id = run.host.replace("executor:", "") if run.host and run.host.startswith("executor:") else None
    _agent_name = None
    _agent_ip = None
    if _agent_id:
        from app.models.executor import Executor
        _ag_result = await db.execute(
            select(Executor.name).where(Executor.id_hash == _agent_id)
        )
        _agent_name = _ag_result.scalar_one_or_none()
        # O IP vem no payload, escrito pelo worker que segura o WebSocket.
        # Este consumer roda em qualquer um dos quatro workers: o registro
        # local só serve quando o payload não traz um IP válido (resultado
        # enfileirado antes deste campo existir, dead letter reprocessado) —
        # e só acerta quando este worker segura a conexão do executor.
        _agent_ip = _ip_do_payload(payload)
        if _agent_ip is None:
            try:
                from app.core.executor_connections import executor_registry
                _conn = executor_registry.get(_agent_id)
                if _conn:
                    _agent_ip = _ip_valido(_conn.executor_ip)
            except Exception as exc:
                # Registro em memoria: falhar aqui nao justifica perder a metrica.
                logger.warning("Falha ao obter IP do executor '%s': %s", _agent_id, exc)

    # ── workflow_run_metrics ─────────────────────────────────────────────────
    wrm = WorkflowRunMetrics(
        run_id=run.task_id,
        workflow_hash=run.workflow_hash,
        workspace_id=run.workspace_id,
        executor_id=_agent_id,
        executor_name=_agent_name,
        executor_ip=_agent_ip,
        user_id=None,
        started_at=run.start_time,
        ended_at=run.end_time,
        duration_ms=run_data.get("duration_ms") or (run.duration_seconds * 1000 if run.duration_seconds else None),
        cpu_avg_pct=run_data.get("cpu_avg_pct"),
        cpu_peak_pct=run_data.get("cpu_peak_pct"),
        mem_avg_mb=run_data.get("mem_avg_mb"),
        mem_peak_mb=run_data.get("mem_peak_mb"),
        input_bytes=run_data.get("input_bytes", 0),
        output_bytes=run_data.get("output_bytes", 0),
        total_features=run_data.get("total_features", 0),
        nodes_executed=run_data.get("nodes_executed", 0),
        nodes_failed=run_data.get("nodes_failed", 0),
        nodes_cached=run_data.get("nodes_cached", 0),
        operation_types=run_data.get("operation_types"),
        spatial_summary=spatial_summary,
        status=run.status,
        # error_category vem da taxonomia de erro do flow (publicada pelo WS
        # router). O codigo anterior gravava type(str).__name__ — sempre "str",
        # o que tornava a coluna inutil para agrupar falhas.
        error_type=payload.get("error_category") or ("error" if run.error_message else None),
    )
    db.add(wrm)

    # ── node_run_metrics ─────────────────────────────────────────────────────
    for nid, nm in nodes_data.items():
        nrm = NodeRunMetrics(
            run_id=run.task_id,
            node_id=nid,
            node_name=nm.get("node_name", ""),
            node_type=nm.get("node_type"),
            duration_ms=nm.get("duration_ms"),
            cpu_avg_pct=nm.get("cpu_avg_pct"),
            mem_peak_mb=nm.get("mem_peak_mb"),
            input_bytes=nm.get("input_bytes", 0),
            output_bytes=nm.get("output_bytes", 0),
            input_features=nm.get("input_features"),
            output_features=nm.get("output_features"),
            geometry_type=next(iter((nm.get("spatial") or {}).get("geometry_types", {}).keys()), None),
            crs=(nm.get("spatial") or {}).get("crs"),
            bbox=(nm.get("spatial") or {}).get("bbox"),
            vertex_count=(nm.get("spatial") or {}).get("vertex_count"),
            status=nm.get("status", "unknown"),
            cache_hit=nm.get("cache_hit", False),
            error_message=nm.get("error"),
        )
        db.add(nrm)

    await db.commit()
    logger.debug("run %s: metricas persistidas.", run.task_id)


async def _consume_one(r: aioredis.Redis, queue: str, handler) -> None:
    """Lê um item da fila e chama o handler. Gerencia retry e dead letter."""
    item = await r.brpop(queue, timeout=2)
    if not item:
        return

    raw = item[1]
    try:
        # `stats` do job_result vai até ~4MB; o dumps já é offloadado no
        # produtor, e o loads de um payload grande também congela o event loop
        # (o consumer roda no mesmo loop do worker). Acima do limiar, para thread.
        if len(raw) > _JSON_OFFLOAD_THRESHOLD:
            payload = await asyncio.to_thread(json.loads, raw)
        else:
            payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Payload inválido na fila %s: %s — %s", queue, raw[:200], exc)
        await r.lpush(QUEUE_DEAD_LETTER, raw)
        return

    try:
        async with AsyncSessionLocal() as db:
            ok = await handler(db, payload)

        if ok is False:
            # run_result chegou antes do run_create ser processado
            retries = payload.get("_retry", 0) + 1
            if retries > _MAX_RESULT_RETRIES:
                logger.error(
                    "run_result descartado após %d tentativas: task_id=%s",
                    _MAX_RESULT_RETRIES, payload.get("task_id"),
                )
                await r.lpush(QUEUE_DEAD_LETTER, json.dumps(payload))
            else:
                payload["_retry"] = retries
                await asyncio.sleep(0.5)
                await r.lpush(queue, json.dumps(payload))

    except PhaseFailure as exc:
        # O run principal ja foi fechado; o que faltou foram efeitos acessorios.
        # Nao ha o que re-tentar automaticamente (o status ja e terminal), mas o
        # payload anotado precisa sobrar em algum lugar: e a unica pista de que
        # aquele run ficou sem artefato/metrica/webhook. O reprocesso manual e
        # seguro — usage_daily tem a guarda first_close e as demais fases sao
        # idempotentes por chave.
        logger.error("Item da fila %s parcialmente processado: %s", queue, exc)
        await r.lpush(
            QUEUE_DEAD_LETTER,
            json.dumps({**payload, "_phases_failed": exc.labels}),
        )

    except Exception as exc:
        logger.error(
            "Falha ao processar item da fila %s (task_id=%s): %s",
            queue, payload.get("task_id"), exc,
        )
        await r.lpush(QUEUE_DEAD_LETTER, raw)


# Backoff exponencial para reconnect ao Redis: 1s, 2s, 4s, 8s, 16s, 30s (cap)
_RECONNECT_DELAYS = [1, 2, 4, 8, 16, 30]


async def run_consumer_loop() -> None:
    """
    Loop principal — iniciado como background task no lifespan da API.
    Processa run_results (fila run_creates foi eliminada — runs sao criados
    sincronamente no _dispatch_job).

    Resiliencia a falhas de Redis: se a conexao cai, faz reconnect com
    backoff exponencial em vez de morrer e exigir restart manual da API.
    Cancelamento propaga normalmente via CancelledError.
    """
    attempt = 0
    while True:
        r = None
        try:
            r = aioredis.from_url(REDIS_URL, decode_responses=True)
            # Ping para validar conexao antes de logar 'iniciado'
            await r.ping()
            logger.info("Consumer run_results iniciado." if attempt == 0
                        else "Consumer run_results reconectado (tentativa %d)." % attempt)
            attempt = 0
            while True:
                await _consume_one(r, QUEUE_RESULTS, _process_result)
        except asyncio.CancelledError:
            # Shutdown da API — propaga sem reconectar
            logger.info("Consumer run_results encerrado (cancelado).")
            return
        except RedisConnectionError as exc:
            delay = com_jitter(_RECONNECT_DELAYS[min(attempt, len(_RECONNECT_DELAYS) - 1)])
            attempt += 1
            logger.warning(
                "Consumer: conexao Redis perdida (%s). Reconectando em %.1fs (tentativa %d).",
                exc, delay, attempt,
            )
            await asyncio.sleep(delay)
        except Exception as exc:
            # Erro inesperado: loga e reconecta. Nao mata o loop.
            delay = com_jitter(_RECONNECT_DELAYS[min(attempt, len(_RECONNECT_DELAYS) - 1)])
            attempt += 1
            logger.error(
                "Consumer: erro inesperado (%s). Reiniciando em %.1fs.", exc, delay,
            )
            await asyncio.sleep(delay)
        finally:
            if r is not None:
                try:
                    await r.aclose()
                except Exception as exc:
                    logger.debug("Falha ao fechar conexao Redis do consumer: %s", exc)
