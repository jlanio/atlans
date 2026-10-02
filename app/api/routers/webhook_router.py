import asyncio
import json
import os
from json import JSONDecodeError

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response

from app.api.dependencies import get_workflow_service
from app.core.exceptions import NoExecutorAvailableError
from app.core.rate_limiter import _client_key, limiter
from app.core.utils.logger import get_logger
from app.core.utils.workflow_triggers import has_webhook_trigger
from app.services.workflow_service import (
    WorkflowInactiveError,
    WorkflowNotFoundError,
    WorkflowService,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/webhook",
    tags=["webhook"],
    # Sem autenticação JWT global — o controle de acesso é por credencial no nó WebhookTrigger:
    # sem credential_id → acesso livre; com credential_id → token validado em start_analysis.
)

# Segundos para aguardar resposta do ResponseNode antes de retornar 504.
# Piso de 1 s porque o valor vai direto ao BRPOP, onde 0 significa "bloqueia
# para sempre" — exatamente o que este timeout existe para evitar.
_WEBHOOK_RESPONSE_TIMEOUT = max(1, int(os.getenv("WEBHOOK_RESPONSE_TIMEOUT", "60")))
_MAX_WEBHOOK_BODY = 10 * 1024 * 1024  # 10 MB

# ── Allowlist da resposta do ResponseNode ────────────────────────────────────
#
# `/webhook/execute/{id_hash}` nao tem JWT (por desenho — o controle e a
# credencial do no WebhookTrigger), e o corpo/cabecalhos da resposta vem do
# ResponseNode, ou seja, do autor do workflow. Os cabecalhos crus permitiam
# sobrescrever o que o SecurityHeadersMiddleware acabara de aplicar.
#
# A lista abaixo espelha o dropdown `contentType` do ResponseNode
# (flow/nodes/outputs/response_node.py) MAIS os tipos que so o body_ref produz.
# Nao pode ser mais restrita que o no: rebaixar um tipo que a UI oferece
# quebraria workflows existentes em silencio, com um aviso so no log do servidor.
_CONTENT_TYPES_PERMITIDOS = {
    "application/json",
    "application/xml",
    "application/geo+json",
    "text/plain",
    "text/csv",
    "text/xml",
    "text/html",
}

# Tipos que o navegador RENDERIZA como documento. `text/html` e opcao legitima
# do no, mas o corpo pode ecoar a entrada da requisicao — XSS refletido na
# ORIGEM DA API, cuja CSP padrao traz `script-src 'unsafe-inline'`.
#
# A resposta nao e rebaixada (isso quebraria o recurso): ela e marcada em
# `request.state`, e o SecurityHeadersMiddleware troca a CSP por uma com
# `sandbox` — origem opaca, sem script e sem formulario. O HTML continua
# renderizando; o script dentro dele nao roda.
#
# A marcacao tem de ir por `request.state` porque o middleware SOBRESCREVE
# `Content-Security-Policy` em toda resposta: um header definido aqui seria
# descartado.
# Auditoria (SEG-08): não é só text/html. O navegador RENDERIZA documentos XML
# e executa `<script>` inline num XML com namespace XHTML (e SVG é XML). Como
# esses tipos estão na allowlist do nó e a resposta sai na ORIGEM da API (CSP
# padrão com `unsafe-inline`), eles TAMBÉM precisam da CSP `sandbox`.
_CONTENT_TYPES_RENDERIZAVEIS = {
    "text/html", "application/xml", "text/xml", "application/xhtml+xml",
    "image/svg+xml",
}

# Cabecalhos que o workflow NAO pode definir: os de seguranca (que o middleware
# aplica), os que fixam identidade no browser, e os que o proprio Starlette
# calcula. Content-Type sai daqui por vir de `content_type`, ja validado.
_HEADERS_BLOQUEADOS = frozenset({
    "content-security-policy", "content-security-policy-report-only",
    "x-frame-options", "x-content-type-options", "strict-transport-security",
    "referrer-policy", "permissions-policy", "x-xss-protection",
    "set-cookie", "access-control-allow-origin", "access-control-allow-credentials",
    "content-type", "content-length", "content-encoding", "transfer-encoding",
})


def _sanear_resposta_do_node(resp: dict, request: Request) -> tuple[str, dict]:
    """Devolve (content_type, headers) seguros a partir do que o ResponseNode pediu.

    Tipo fora da allowlist vira `text/plain`: o conteudo continua chegando ao
    caller — so deixa de ser interpretado como markup pelo navegador. Rebaixar
    e melhor que recusar, porque o workflow ja rodou e o dado ja existe.

    Tipo renderizavel que ESTA na allowlist (text/html) passa intacto, mas marca
    `request.state.corpo_nao_confiavel` para o middleware endurecer a CSP.
    """
    content_type = str(resp.get("content_type") or "application/json")
    base = content_type.split(";")[0].strip().lower()
    if base not in _CONTENT_TYPES_PERMITIDOS:
        logger.warning(
            "[webhook] content_type '%s' fora da allowlist — rebaixado para text/plain.",
            content_type,
        )
        content_type = "text/plain; charset=utf-8"
        base = "text/plain"

    if base in _CONTENT_TYPES_RENDERIZAVEIS:
        request.state.corpo_nao_confiavel = True

    # `headers` vem do JSON do executor e o no o expoe como campo livre do tipo
    # `object` — nao ha garantia de ser dict. Sem esta guarda, uma string ou
    # lista levantava AttributeError e virava 500 no handler generico.
    brutos = resp.get("headers")
    if not isinstance(brutos, dict):
        if brutos:
            logger.warning("[webhook] `headers` do ResponseNode nao e um objeto — ignorado.")
        brutos = {}

    headers = {
        str(k): str(v) for k, v in brutos.items()
        if str(k).lower() not in _HEADERS_BLOQUEADOS
    }
    headers["Content-Type"] = content_type
    return content_type, headers


def _webhook_rate_key(request: Request) -> str:
    """Chave de rate-limit (IP, workflow_hash).

    Antes era so o IP — botnet com 1000 IPs gerava 20000 req/min. Agora um
    par (IP, workflow) e contado isoladamente: botnet ainda pode tentar mil
    workflows distintos, mas atingir UM workflow especifico exige IP rotation
    por cada janela.

    O IP e o do cliente de verdade (`_client_key`, o X-Forwarded-For lido
    atras do Traefik). O `get_remote_address` do slowapi devolvia o IP do
    proxy para todo mundo: o balde era um so por workflow, dividido entre
    todos os chamadores — com os contadores no Redis, quem soubesse a URL
    esgotaria os 20/min do workflow para os demais.
    """
    workflow_hash = request.path_params.get("id_hash") or "unknown"
    return f"{_client_key(request)}:{workflow_hash}"


@router.post("/execute/{id_hash}", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/minute", key_func=_webhook_rate_key)
async def webhook_trigger(
    id_hash: str,
    request: Request,
    background_tasks: BackgroundTasks,
    service: WorkflowService = Depends(get_workflow_service),
):
    """
    Dispara um workflow via Webhook.

    Comportamento:
      - Workflow sem ResponseNode → retorna 202 com {"task_id": "..."} imediatamente.
      - Workflow com ResponseNode → aguarda o executor executar e retorna a resposta
        HTTP definida pelo nó (status_code, body, headers customizáveis).
        Retorna 504 se o executor não responder dentro de WEBHOOK_RESPONSE_TIMEOUT segundos.
    """
    # 1) Valida tamanho e tenta ler body JSON; se não for JSON, body = {}
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > _MAX_WEBHOOK_BODY:
                raise HTTPException(status_code=413, detail=f"Payload excede {_MAX_WEBHOOK_BODY // (1024*1024)}MB.")
        except ValueError:
            pass
    try:
        body = await request.json()
    except JSONDecodeError:
        body = {}

    debug_mode = bool(body.pop("debug_mode", False))
    # no_wait=True: retorna 202 imediatamente sem aguardar o ResponseNode.
    # O canvas sempre envia no_wait=True para manter feedback visual em tempo real.
    # Callers externos (curl, integrações) omitem o parâmetro e obtêm resposta síncrona.
    no_wait   = bool(body.pop("no_wait", False))
    logger.info("[webhook] acionando workflow %s debug_mode=%s no_wait=%s", id_hash, debug_mode, no_wait)

    # 1b) Valida que o workflow tem WebhookTrigger antes de despachar.
    # Sem isso, workflows com outros tipos de trigger (ScheduleTrigger,
    # FileTrigger, etc) seriam executados via HTTP arbitrário — comportamento
    # indevido: o endpoint de webhook só deve disparar fluxos explicitamente
    # configurados com esse gatilho.
    try:
        wf = await service.get_workflow_by_hash(id_hash)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow não encontrado",
        )
    if not wf.flag_ative:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workflow está desativado e não pode ser executado.",
        )
    if not has_webhook_trigger(wf.definition or {}):
        logger.warning(
            "[webhook] tentativa de disparo em workflow sem WebhookTrigger (id_hash=%s)",
            id_hash,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workflow não possui node WebhookTrigger — endpoint de webhook não é válido para este fluxo.",
        )

    # 2) Dispara análise
    try:
        async_result = await service.start_analysis(
            id_hash, inputs=body, request=request, debug_mode=debug_mode,
            # O workflow acabou de ser carregado e descriptografado acima para
            # a checagem do WebhookTrigger; sem repassá-lo, o dispatch refazia
            # o SELECT e desserializava a `definition` inteira uma segunda vez.
            workflow=wf,
            # Sem `triggered_by`: o chamador é um sistema externo, não um
            # usuário — inventar um dono aqui abriria credenciais privadas.
            trigger_source="webhook",
        )
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow não encontrado",
        )
    except WorkflowInactiveError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workflow está desativado e não pode ser executado.",
        )
    except NoExecutorAvailableError as exc:
        # Chamador ANÔNIMO: corpo genérico, sem nomes de executores, contagens
        # ou política (spec §6). O motivo detalhado fica no log e no histórico
        # do dono. Stateless: nenhum run foi criado neste caminho, então um
        # integrador martelando não amplifica escrita. `Retry-After` orienta o
        # backoff; a chave de idempotência NÃO foi consumida (só é gravada após
        # um dispatch bem-sucedido), então o reenvio tenta de verdade.
        logger.warning("[webhook] sem executor para %s (%s): %s", id_hash, exc.category, exc.detail)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Execução temporariamente indisponível para este workflow.",
            headers={"Retry-After": "60"},
        )

    task_id = async_result.id

    # 3) Se não há ResponseNode ou o caller pediu resposta assíncrona, retorna 202 imediatamente
    if no_wait or not getattr(async_result, "has_response_node", False):
        return JSONResponse({"task_id": task_id}, status_code=202)

    # 4) Aguarda resposta síncrona via Redis BRPOP
    from app.core.redis import get_redis_pool
    rc = get_redis_pool()
    try:
        raw = await asyncio.wait_for(
            # O timeout vai no PRÓPRIO comando. Sem ele o BRPOP era `timeout=0`
            # — bloqueio indefinido no servidor Redis — e quem desistia era só o
            # `wait_for` daqui: a conexão continuava presa até o Redis notar o
            # socket fechado. Cada webhook síncrono em voo segurava assim uma
            # conexão da pool COMPARTILHADA (idempotência, rate-limit de WS,
            # blacklist de JWT, fila run_results), que não tem teto de tamanho:
            # um pico de webhooks caminhava para o `maxclients` do Redis e
            # derrubava todo o resto junto.
            rc.brpop(f"webhook_response:{task_id}", timeout=_WEBHOOK_RESPONSE_TIMEOUT),
            # Rede de segurança para um Redis que nem responde ao próprio
            # timeout; a expiração normal agora volta como `raw is None`.
            timeout=_WEBHOOK_RESPONSE_TIMEOUT + 5,
        )
    except asyncio.TimeoutError:
        raw = None

    if raw is None:
        logger.warning("[webhook] timeout aguardando ResponseNode (task_id=%s)", task_id)
        return JSONResponse(
            {
                "error":   "timeout",
                "task_id": task_id,
                "message": "O workflow não respondeu no tempo esperado.",
            },
            status_code=504,
        )

    payload = json.loads(raw[1])

    # 5) Workflow falhou antes de atingir o ResponseNode
    if payload.get("job_status") != "ok":
        error_msg = payload.get("error") or "Workflow falhou."
        logger.error("[webhook] workflow falhou (task_id=%s): %s", task_id, error_msg)
        return JSONResponse(
            {"error": error_msg, "task_id": task_id},
            status_code=500,
        )

    # 6) Monta resposta HTTP a partir dos dados do ResponseNode
    resp = payload.get("response") or {}
    http_status  = resp.get("status_code", 200)
    _content_type, extra_headers = _sanear_resposta_do_node(resp, request)

    # 6a) Body guardado no MinIO (body grande, evita HoL no WS executor→servidor):
    # streama diretamente do MinIO para o caller e agenda remoção imediata.
    body_ref = resp.get("body_ref")
    if body_ref and body_ref.get("s3_key"):
        s3_key = body_ref["s3_key"]
        logger.info(
            "[webhook] ResponseNode retornou body_ref=%s status=%d (task_id=%s)",
            s3_key, http_status, task_id,
        )
        # A s3_key vem do executor (máquina sob controle do usuário) e aqui ela
        # seria usada para LER e depois APAGAR um objeto do MinIO — que usa um
        # bucket único para os prefixos de todos os workspaces. Sem o guard, um
        # executor devolvia `s3_key = "drive/<workspace_alheio>/<arquivo>"` e o
        # webhook servia o conteúdo de outro tenant ao caller, apagando o objeto
        # em seguida. Mesmo guard já aplicado nos demais caminhos executor→servidor.
        from app.api.routers.executor_drive_router import _validate_agent_s3_key
        # Auditoria (SEG-71): além do escopo por workspace, exige o prefixo
        # `webhook-responses/` — o corpo do ResponseNode é sempre gravado ali
        # (response_node.py). Sem isso, um `body_ref` apontando para
        # `drive/{ws}/…` ou `artifacts/{ws}/…` do MESMO workspace faria o
        # webhook servir e depois APAGAR esse objeto.
        prefixo_ok = isinstance(s3_key, str) and s3_key.startswith(
            f"webhook-responses/{wf.workspace_id}/"
        )
        try:
            _validate_agent_s3_key(s3_key, [wf.workspace_id])
            if not prefixo_ok:
                raise HTTPException(status_code=403, detail="body_ref fora de webhook-responses/")
        except HTTPException as exc:
            logger.error(
                "[webhook] s3_key rejeitada (%s) no task_id=%s: %s",
                exc.detail, task_id, s3_key,
            )
            return JSONResponse(
                {"error": "Resposta do workflow inválida.", "task_id": task_id},
                status_code=502,
            )

        from app.core import storage as s3
        # Baixa em memória (operação síncrona boto3 em threadpool). Para bodies
        # muito grandes seria possível usar streaming chunked de get_object,
        # mas requer plumbing extra de boto3.StreamingBody em async.
        try:
            content_bytes = await asyncio.to_thread(s3.download, s3_key)
        except Exception as exc:
            logger.error("[webhook] falha ao baixar body do MinIO '%s': %s", s3_key, exc)
            return JSONResponse(
                {"error": "Falha ao recuperar resposta do storage.", "task_id": task_id},
                status_code=502,
            )
        # Apaga no MinIO em background; o Artifact registrado pelo executor_ws_router
        # também é removido pelo cleanup global quando expires_at vence (rede de segurança).
        background_tasks.add_task(_delete_webhook_response_artifact, s3_key)
        return Response(
            content=content_bytes,
            status_code=http_status,
            headers=extra_headers,
        )

    body_data = resp.get("body")
    if isinstance(body_data, (dict, list)):
        content = json.dumps(body_data, ensure_ascii=False)
    else:
        content = str(body_data) if body_data is not None else ""

    logger.info("[webhook] ResponseNode retornou status=%d (task_id=%s)", http_status, task_id)
    return Response(
        content=content,
        status_code=http_status,
        headers=extra_headers,
    )


async def _delete_webhook_response_artifact(s3_key: str) -> None:
    """Remove objeto do MinIO e a linha Artifact correspondente após o caller receber o body.

    Rodado em BackgroundTasks — se falhar, o cleanup global remove pelo expires_at.
    """
    from sqlalchemy import delete as sa_delete

    from app.core import storage as s3
    from app.core.db import get_session_async
    from app.models.artifact import Artifact

    try:
        await s3.delete_async(s3_key)
    except Exception as exc:
        logger.warning("[webhook] falha ao remover objeto MinIO '%s': %s", s3_key, exc)

    try:
        async with get_session_async() as db:
            await db.execute(sa_delete(Artifact).where(Artifact.s3_key == s3_key))
            await db.commit()
    except Exception as exc:
        logger.warning("[webhook] falha ao remover linha Artifact s3_key='%s': %s", s3_key, exc)
