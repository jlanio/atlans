from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.workflow import (
    WorkflowRead, WorkflowUpdate, WorkflowCreate,
    WorkflowVersionMeta, WorkflowListItem, WorkflowDuplicate,
    WorkflowMove, WorkflowMoveResult,
)

from app.core.exceptions import AtlasBaseError, CredentialAccessDeniedError
from app.services.workflow_service import WorkflowService, WorkflowInactiveError
from app.core.exceptions import WorkflowNameConflictError
from app.api.dependencies import (
    get_workflow_service, get_current_user, get_user_workspace_ids,
    verify_workspace_access, workflow_com_papel, exigir_papel_no_workspace,
    get_db,
)
from app.core.rate_limiter import limiter
from app.core.rbac import ROLE_ADMIN, ROLE_EDITOR, ROLE_OPERATOR, ROLE_VIEWER
from app.core.utils.logger import get_logger
from app.core.utils.redacao import definition_contem_segredo, params_schema_contem_segredo
from app.services import pin_service
from app.services.pin_service import TTL_MAXIMO_HORAS

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])

class ExecutePayload(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Initial inputs for trigger nodes")
    debug_mode: bool = Field(default=False, description="Se true, o executor pausa em cada nó e emite dados intermediários no WebSocket")

class PortalSettingsSchema(BaseModel):
    portal_access: str = Field(..., pattern="^(disabled|public|private)$")
    portal_shared_with: Optional[List[str]] = None

def _recusar_segredo(definition: Any, *, schema: bool = False) -> None:
    """Recusa definition que traga segredo LITERAL gravado.

    Credencial mora em `credentials`, cifrada; a definition guarda o
    `credential_id` e o servidor injeta o valor numa CÓPIA no despacho
    (`credential_resolver`). Um segredo escrito aqui ficaria cifrado no banco,
    mas já teria viajado por transporte e log — e a redação da saída o
    apagaria depois, dando a falsa impressão de que ele não está lá.

    A borda do servidor MCP já recusava (`app/mcp/tools/construcao.py`); a REST,
    que é por onde o editor grava, não. Levantamento em produção (2026-09-14):
    286 nós, 56 com `credential_id`, ZERO segredos gravados — a recusa torna
    invariante um estado que já era verdade por convenção.

    Cita o CAMINHO do campo e nunca o valor: a mensagem de recusa não pode ser
    o vazamento que ela evita.
    """
    caminhos = (
        params_schema_contem_segredo(definition) if schema
        else definition_contem_segredo(definition or {})
    )
    if caminhos:
        raise HTTPException(
            status_code=422,
            detail=(
                "Segredo gravado na definição. Use uma credencial (`credential_id`) "
                "em vez do valor literal. Um valor `<REDACTED>` veio de uma leitura redigida: "
                "restaure o original ou não envie o campo.\nCampos:\n- " + "\n- ".join(caminhos)
            ),
        )


@router.post("", status_code=201, summary="Create a new workflow definition")
@limiter.limit("30/minute")
async def create_workflow(
    request: Request,
    payload: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # O workspace vem do corpo, não do path: por isso a checagem é aqui, e não
    # na dependência `workflow_com_papel` das rotas `/{id_hash}`.
    await exigir_papel_no_workspace(
        db, payload.workspace_id, current_user.id_hash, ROLE_EDITOR,
        "Requer role 'editor' ou superior para criar workflows.",
    )

    _recusar_segredo(payload.definition)
    # `params_schema` e coluna irma, gravavel no mesmo corpo, e — diferente da
    # definition — NAO passa por `encrypt_workflow_connections`: vai crua para o
    # banco. A saida do MCP ja redige `params_schema.token`, entao deixa-la fora
    # da guarda quebraria a regra do proprio modulo de redacao: a deteccao nao
    # pode ser mais estreita que a entrega.
    _recusar_segredo(payload.params_schema, schema=True)

    # As credenciais da definition (SEG-12) o serviço confere no
    # `create_workflow`, pelo `created_by_id` — mesma guarda do MCP.

    # Validacao cross-workflow: SubWorkflows referenciados precisam existir,
    # estar ativos, no mesmo workspace e com contrato compativel com o mapping.
    from flow.utils.workflow_contract import validate_subworkflow_references_against_db
    cross_errors = await validate_subworkflow_references_against_db(
        payload.definition or {}, db, workspace_id=payload.workspace_id,
    )
    if cross_errors:
        # detail como string para o front mostrar no toast (resolveAxiosError
        # le `detail`). Lista de erros concatenada — uma por linha.
        raise HTTPException(
            status_code=422,
            detail="Sub-workflows invalidos:\n- " + "\n- ".join(cross_errors),
        )

    try:
        # Carimba o autor no INSERT: sem isso `created_by_id`/`updated_by_id`
        # nasciam nulos e "criado há X por Y" na listagem nunca mostrava o nome
        # (o campo só era preenchido na primeira edição, via update_workflow).
        wf = await service.create_workflow(
            payload.name,
            payload.definition,
            workspace_id=payload.workspace_id,
            created_by_id=current_user.id_hash,
            updated_by_id=current_user.id_hash,
        )
        logger.info(f"Workflow '{payload.name}' criado por '{current_user.id_hash}'.")
        return {"id": wf.id_hash, "name": wf.name}
    except ValueError as e:
        logger.error(f"Erro ao criar workflow: {e}")
        raise HTTPException(status_code=400, detail="Não foi possível criar o workflow. Verifique os dados informados.")

@router.get("", summary="List all registered workflows", response_model=List[WorkflowListItem])
async def list_workflows(
    workspace_id: str | None = None,
    assistente: bool = False,
    service: WorkflowService = Depends(get_workflow_service),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """Retorna listagem leve de workflows (sem definition e outros campos JSON pesados).

    `assistente=1` inclui os fluxos criados pelo assistente da Home (escondidos
    por padrao): o interruptor "mostrar os do assistente" da tela de Projetos e
    o `ActiveRunsContext` passam esse parametro."""
    if workspace_id:
        verify_workspace_access(workspace_id, workspace_ids)
        return await service.list_workflows_metadata(
            workspace_id=workspace_id, incluir_do_assistente=assistente,
        )
    # Sem workspace_id: retorna workflows de todos os workspaces do usuário numa única query
    return await service.list_workflows_metadata_by_ids(
        workspace_ids, incluir_do_assistente=assistente,
    )

@router.get(
    "/{id_hash}",
    response_model=WorkflowRead,
    summary="Get Workflow by id_hash",
    description="Retorna todos os campos de um workflow existente a partir do seu id_hash.",
    responses={
        200: {"description": "Workflow encontrado"},
        403: {"description": "Acesso negado"},
        404: {"description": "Workflow não encontrado"},
        422: {"description": "Validation Error"},
    },
)
async def read_workflow(
    wf=Depends(workflow_com_papel(None)),   # leitura: basta pertencer ao workspace
):
    # Auditoria (SEG-67): a definition vem com a connectionString legada JÁ
    # descriptografada, e a rota é acessível a viewer. Redige os segredos numa
    # CÓPIA (redigir_definition) antes de responder — sem tocar no objeto do ORM,
    # para o marcador "<REDACTED>" nunca ser gravado por um flush do GET. Fluxos
    # modernos usam credential_id (resolvido só no dispatch) e não expõem nada.
    from app.core.utils.redacao import redigir_definition
    dados = WorkflowRead.model_validate(wf)
    if isinstance(dados.definition, dict) and dados.definition:
        return dados.model_copy(update={"definition": redigir_definition(dados.definition)})
    return dados

@router.get(
    "/{id_hash}/contract",
    summary="Contrato (API publica) do workflow para uso como sub-fluxo",
    description=(
        "Retorna as chaves declaradas via SubWorkflowInput (entradas) e "
        "SubWorkflowOutput (saidas). Usado pelo canvas para renderizar portas "
        "nomeadas no node SubWorkflow e validar inputsMapping em design-time."
    ),
    responses={
        200: {"description": "Contrato extraido."},
        403: {"description": "Acesso negado."},
        404: {"description": "Workflow nao encontrado."},
    },
)
async def get_workflow_contract(wf=Depends(workflow_com_papel(None))):
    from flow.utils.workflow_contract import extract_contract
    from app.core.utils.encryption import decrypt_workflow_connections

    # decrypt_workflow_connections so toca credenciais — nodes/edges
    # ficam expostos como estao. extract_contract le apenas o grafo.
    try:
        definition = decrypt_workflow_connections(wf.definition or {})
    except Exception:
        definition = wf.definition or {}
    contract = extract_contract(definition)
    # is_active permite o canvas marcar SubWorkflow apontando para alvo
    # desativado com badge visual antes mesmo de tentar salvar.
    contract["is_active"] = bool(wf.flag_ative)
    return contract


@router.delete("/{id_hash}", status_code=200)
@limiter.limit("20/minute")
async def delete_workflow(
    request: Request,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
):
    await service.delete_workflow(wf.id_hash)
    return {"message": f"Workflow '{wf.name}' desativado com sucesso."}

@router.post("/{id_hash}/duplicate", status_code=201, summary="Duplica um workflow no mesmo workspace")
@limiter.limit("20/minute")
async def duplicate_workflow(
    request: Request,
    payload: WorkflowDuplicate | None = None,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(
        ROLE_EDITOR, "Requer role 'editor' ou superior para duplicar workflows.",
    )),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """A cópia fica no MESMO workspace do original.

    `workflow_com_papel` já barra quem não alcança o workflow, e como o destino
    é o workspace dele, o acesso ao original mais `editor` cobrem a operação —
    não há como usar esta rota para plantar um workflow em workspace alheio.
    """
    # Mesma checagem do POST / e do PUT: um SubWorkflow referenciado pode ter
    # sido desativado ou removido depois que o original foi salvo. Sem isto, a
    # cópia nasceria quebrada e só falharia na execução, com erro bem menos
    # claro do que a lista de referências inválidas.
    from flow.utils.workflow_contract import validate_subworkflow_references_against_db
    cross_errors = await validate_subworkflow_references_against_db(
        wf.definition or {}, db, workspace_id=wf.workspace_id,
    )
    if cross_errors:
        raise HTTPException(
            status_code=422,
            detail="Sub-workflows invalidos:\n- " + "\n- ".join(cross_errors),
        )

    # Auditoria (SEG-12): a cópia não pode carregar credencial que o duplicador
    # não acessa — o serviço confere, pelo `duplicated_by`.
    try:
        copia = await service.duplicate_workflow(
            wf.id_hash, payload.name if payload else None,
            duplicated_by=current_user.id_hash,
        )
    except WorkflowNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info("Workflow '%s' duplicado como '%s'.", wf.name, copia.name)
    return {"id": copia.id_hash, "name": copia.name}


# ── Mover entre workspaces ───────────────────────────────────────────────────
#
# Exige admin (ou owner) nos DOIS workspaces. Mover atravessa a fronteira de
# tenant: leva a definition — que traz `credential_id` em texto puro e ids de
# arquivos do Drive — para dentro de outro workspace, e passa a produzir dados
# lá. Papel de editor, que basta para criar e duplicar dentro do próprio
# workspace, não cobre isso.
#
# Exigir nos dois lados fecha os dois abusos simétricos: tirar um workflow de um
# workspace onde só se tem acesso parcial, e plantar um workflow dentro de um
# workspace alheio. É exatamente a lacuna que o comentário de `WorkflowUpdate`
# descreve ao recusar `workspace_id` no PUT.
#
# A origem é conferida pela dependência da rota (`workflow_com_papel`), o
# destino — que vem do corpo — em `_move`. A mensagem do destino é a mesma para
# "não sou membro", "workspace não existe" e "workspace na lixeira":
# `get_workspace_member_role` devolve None nos três, e distinguir permitiria
# enumerar workspaces alheios pelo id.
_MOVER_ORIGEM = "Requer role 'admin' ou 'owner' no workspace de origem para mover workflows."
_MOVER_DESTINO = "Requer role 'admin' ou 'owner' no workspace de destino para mover workflows."


async def _move(
    payload: WorkflowMove,
    service: WorkflowService,
    wf,
    db: AsyncSession,
    current_user,
    *,
    dry_run: bool,
) -> WorkflowMoveResult:
    """Corpo comum de /move e /move/preview — só muda o `dry_run`."""
    # Só autorização e serialização vivem aqui: "destino ≠ origem" é invariante
    # da operação e mora no serviço (WorkflowMoveTargetError → 400).
    await exigir_papel_no_workspace(
        db, payload.target_workspace_id, current_user.id_hash, ROLE_ADMIN, _MOVER_DESTINO,
    )

    resultado = await service.move_workflow(
        wf.id_hash,
        payload.target_workspace_id,
        new_name=payload.name,
        moved_by_id=current_user.id_hash,
        dry_run=dry_run,
    )
    if not dry_run:
        logger.info(
            "Workflow '%s' movido de '%s' para '%s' por '%s' (%d aviso(s)).",
            wf.id_hash, resultado["from_workspace_id"], resultado["to_workspace_id"],
            current_user.id_hash, len(resultado["warnings"]),
        )
    return WorkflowMoveResult(**resultado)


@router.post(
    "/{id_hash}/move",
    response_model=WorkflowMoveResult,
    summary="Move um workflow para outro workspace",
)
@limiter.limit("10/minute")
async def move_workflow(
    request: Request,
    payload: WorkflowMove,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_ADMIN, _MOVER_ORIGEM)),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowMoveResult:
    """Troca o workspace do workflow, preservando o `id_hash`.

    A operação NÃO falha por dependência quebrada: o que deixa de funcionar no
    destino volta em `warnings` — credenciais que não resolvem mais,
    sub-fluxos e arquivos do Drive que ficaram para trás, troca de executor.

    O que muda sempre: agendamento chega desligado, portal volta a "disabled",
    grupo e pins são limpos. Histórico (execuções, artefatos, métricas)
    permanece no workspace de origem.
    """
    return await _move(payload, service, wf, db, current_user, dry_run=False)


@router.post(
    "/{id_hash}/move/preview",
    response_model=WorkflowMoveResult,
    summary="Simula a movimentação e devolve os impactos, sem gravar",
)
@limiter.limit("30/minute")
async def preview_move_workflow(
    request: Request,
    payload: WorkflowMove,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_ADMIN, _MOVER_ORIGEM)),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowMoveResult:
    """Mesmo relatório do move, sem escrever nada.

    Alimenta o diálogo antes de confirmar. Exige a mesma permissão do move real
    para não virar um oráculo sobre o conteúdo de workspaces alheios.
    """
    return await _move(payload, service, wf, db, current_user, dry_run=True)


@router.put("/{id_hash}", response_model=WorkflowRead, summary="Atualiza um workflow existente")
@limiter.limit("30/minute")
async def update_workflow(
    request: Request,
    workflow_in: WorkflowUpdate,
    change_note: str | None = None,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Atualiza campos de um workflow já existente.
    Só os campos enviados no payload serão alterados.
    Se `definition` for alterada, a versão atual é salva automaticamente como snapshot.
    """
    # Se definition mudou, valida referencias cross-workflow contra DB.
    # `WorkflowUpdate` e parcial: `definition` ausente significa "nao mexe nela",
    # e recusar ai barraria ate renomear um workflow.
    novo_schema = getattr(workflow_in, "params_schema", None)
    if novo_schema is not None:
        _recusar_segredo(novo_schema, schema=True)   # mesma razao do POST

    new_def = getattr(workflow_in, "definition", None)
    if new_def is not None:
        _recusar_segredo(new_def)
        # As credenciais (SEG-12) o serviço confere no `update_workflow`.

        from flow.utils.workflow_contract import validate_subworkflow_references_against_db
        cross_errors = await validate_subworkflow_references_against_db(
            new_def, db, workspace_id=wf.workspace_id,
        )
        if cross_errors:
            raise HTTPException(
                status_code=422,
                detail="Sub-workflows invalidos:\n- " + "\n- ".join(cross_errors),
            )

    try:
        return await service.update_workflow(
            wf.id_hash, workflow_in, change_note=change_note,
            updated_by_id=current_user.id_hash,
        )
    except (HTTPException, CredentialAccessDeniedError):
        raise
    except Exception as e:
        logger.error("Erro ao atualizar workflow '%s': %s", wf.id_hash, e)
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o workflow.")


# ------------------------------------------------------------------ #
# Execução direta                                                      #
# ------------------------------------------------------------------ #

@router.post(
    "/{id_hash}/execute",
    status_code=202,
    summary="Executa um workflow imediatamente",
)
@limiter.limit("20/minute")
async def execute_workflow(
    request: Request,
    payload: ExecutePayload,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(
        ROLE_OPERATOR, "Requer role 'operator' ou superior para executar workflows.",
    )),
    current_user=Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Despacha o workflow para execução imediata via executor.

    **Idempotência**: envie o header `Idempotency-Key: <uuid>` para garantir
    que requisições duplicadas (ex: retry de rede) não disparem execuções extras.
    A mesma chave, para o MESMO usuário e o MESMO workflow, retorna o `task_id`
    da execução original por 24h (a chave não colide entre usuários).
    """
    try:
        async_result = await service.start_analysis(
            wf.id_hash,
            inputs=payload.inputs,
            request=request,
            debug_mode=payload.debug_mode,
            idempotency_key=idempotency_key,
            # A dependency de autorização já carregou e descriptografou este
            # workflow: sem repassar o objeto, o dispatch refazia o SELECT e
            # desserializava a `definition` inteira de novo (~1,7 MB num fluxo
            # grande) só para descartar o resultado.
            workflow=wf,
            # Escopo de credenciais (opção D): quem disparou é uma das duas
            # dimensões — resolvem-se as credenciais DESTE usuário mais as
            # compartilhadas com o workspace do workflow.
            triggered_by=current_user.id_hash,
            trigger_source="manual",
            # Quem chega aqui já passou pela sessão e tem papel de operator. O
            # token do gatilho autentica CHAMADA EXTERNA ao endpoint de webhook;
            # exigi-lo aqui só comparava o JWT do usuário com o token e
            # respondia "Token inválido", sem impedir nada.
            autenticar_entrada=False,
        )
        return {"task_id": async_result.id, "workflow": wf.id_hash}
    except (HTTPException, AtlasBaseError):
        raise
    except Exception as e:
        logger.error("Erro ao executar workflow '%s': %s", wf.id_hash, e)
        raise HTTPException(status_code=400, detail="Não foi possível executar o workflow.")


@router.post(
    "/runs/{run_id}/cancel",
    summary="Cancela uma execução em andamento",
)
@limiter.limit("30/minute")
async def cancel_run(
    request: Request,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Interrompe um run em andamento.

    Até então um workflow disparado só terminava sozinho ou por timeout do
    executor — o usuário não tinha como parar um job caro ou travado.

    Exige role `operator` ou superior no workspace DO RUN, o mesmo necessário
    para tê-lo iniciado.
    """
    from app.services.workflow_execution_service import cancel_run as _cancel

    # A autorização (papel `operator` no workspace DO RUN, com atalho de
    # administrador global) mora agora dentro de `cancel_run`, junto do SELECT
    # que carrega o run: era regra só de rota, então o serviço cancelava
    # execução de qualquer conta para quem o chamasse direto. Nenhum chamador
    # assim existe hoje — a rota é o único —, mas as ferramentas do servidor
    # MCP não passam por aqui, e é para elas que a guarda tinha de descer.
    # Esta rota deixou de repeti-la para que não existam duas versões da mesma
    # regra divergindo com o tempo.
    #
    # Erros de domínio sobem para o handler global (app/main.py), que já mapeia
    # cada um ao seu status: 404 para run inexistente, 403 para papel
    # insuficiente. Capturar aqui colapsaria os dois num código genérico.
    # Executor fora do ar não é mais erro: o run é fechado no servidor e o
    # outcome volta "cancelled".
    outcome = await _cancel(
        db,
        run_id,
        user_id=current_user.id_hash,
        como_admin=getattr(current_user, "role", None) == ROLE_ADMIN,
    )
    return {"run_id": run_id, "outcome": outcome}


# ------------------------------------------------------------------ #
# Workflow Versioning                                                  #
# ------------------------------------------------------------------ #

@router.get(
    "/{id_hash}/versions",
    response_model=List[WorkflowVersionMeta],
    summary="Lista o histórico de versões de um workflow (somente metadados)",
)
async def list_versions(
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(None)),   # leitura: basta pertencer ao workspace
):
    return await service.list_versions(wf.id_hash)


@router.post(
    "/{id_hash}/versions/{version_number}/restore",
    response_model=WorkflowRead,
    summary="Restaura o workflow para uma versão anterior",
)
@limiter.limit("10/minute")
async def restore_version(
    request: Request,
    version_number: int,
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    current_user=Depends(get_current_user),
):
    # Auditoria (SEG-12): restaurar uma versão antiga não pode reintroduzir uma
    # credencial que o autor da restauração não acessa — o serviço confere.
    return await service.restore_version(
        wf.id_hash, version_number, restored_by=current_user.id_hash,
    )

# ------------------------------------------------------------------ #
# Retry de execução                                                    #
# ------------------------------------------------------------------ #

@router.post(
    "/{id_hash}/runs/{run_id}/retry",
    status_code=202,
    summary="Dispara uma nova execução do workflow que produziu esta run",
)
@limiter.limit("10/minute")
async def retry_run(
    request: Request,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
    wf=Depends(workflow_com_papel(
        ROLE_OPERATOR, "Requer role 'operator' ou superior para executar workflows.",
    )),
    current_user=Depends(get_current_user),
):
    """
    Despacha uma execução NOVA do workflow, com a definição ATUAL dele.

    Importante, porque o nome sugere outra coisa: não é um replay da run
    apontada. `WorkflowRun` não guarda os parâmetros de entrada, então
    reexecutar exatamente aquela run não é possível hoje — e prometer isso na
    resposta seria mentir para quem depende do resultado.

    O `run_id` do path é VALIDADO, e não decorativo: ele precisa existir e
    pertencer a este workflow. Antes era recebido e ignorado, então qualquer
    string passava e a rota disparava a execução do mesmo jeito, inclusive com
    o id de uma run de outro workflow — o chamador achava estar reexecutando uma
    coisa e estava disparando outra.
    """
    from app.models.models import WorkflowRun as _Run

    run = (await db.execute(
        select(_Run.task_id).where(
            _Run.task_id == run_id,
            _Run.workflow_hash == wf.id_hash,
        )
    )).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Execução não encontrada para este workflow.",
        )

    try:
        # Mesmo caso do POST /execute: já autenticado, já com papel checado.
        async_result = await service.start_analysis(
            wf.id_hash, autenticar_entrada=False, workflow=wf,
            triggered_by=current_user.id_hash,
            # "retry" e nao "manual": no Historico, uma sequencia de reexecucoes
            # do mesmo fluxo conta uma historia diferente de disparos avulsos.
            trigger_source="retry",
        )
        return {"task_id": async_result.id, "message": "Execução reenfileirada com sucesso."}
    except WorkflowInactiveError:
        raise HTTPException(status_code=403, detail="Workflow está desativado.")


# ------------------------------------------------------------------ #
# Portal de compartilhamento                                           #
# ------------------------------------------------------------------ #

@router.patch("/{id_hash}/portal", summary="Configura acesso ao portal público do workflow")
@limiter.limit("30/minute")
async def update_portal_settings(
    request: Request,
    body: PortalSettingsSchema,
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Define portal_access (disabled/public/private) e lista de usuários permitidos."""
    wf.portal_access = body.portal_access
    wf.portal_shared_with = body.portal_shared_with if body.portal_access == "private" else None
    await db.commit()
    share_url = f"/share/{wf.id_hash}" if body.portal_access != "disabled" else None
    return {
        "portal_access": wf.portal_access,
        "portal_shared_with": wf.portal_shared_with,
        "share_url": share_url,
    }


# ── Pin Data ─────────────────────────────────────────────────────────────────

class PinOutputPayload(BaseModel):
    # `node_id` continua aceito e continua IGNORADO — o path sempre venceu, e
    # `PUT /pin/A` com `{"node_id": "B"}` gravava em A, calado. Deixou de ser
    # obrigatório (nenhum chamador precisa repetir o que já está na URL) e não
    # pode simplesmente sumir: com `extra="forbid"`, um cliente que ainda o
    # envie passaria a receber 422 numa chamada que funcionava.
    node_id: Optional[str] = Field(
        None, description="Ignorado — o nó é o do caminho da URL. Mantido por compatibilidade.",
    )
    outputs: Dict[str, Any]
    ttl_hours: Optional[int] = Field(
        None,
        ge=1,
        le=TTL_MAXIMO_HORAS,
        description=(
            "Validade do pin em horas, de 1 a 8760 (um ano). Nulo = sem expiração. "
            "O 0 é recusado de propósito: antes ele virava 'sem expiração', o "
            "oposto do que quem o digita está pedindo."
        ),
    )

    model_config = ConfigDict(extra="forbid")


@router.put("/{id_hash}/pin/{node_id}", summary="Pin (fix) output of a node")
async def pin_node_output(
    id_hash: str,
    node_id: str,
    body: PinOutputPayload,
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Fixa o output de um nó para reutilização em execuções futuras."""
    try:
        # `exigir_no_existente=False`: fixar um id que a definition não tem é
        # inútil, mas recusá-lo mudaria o contrato de uma rota que a tela usa.
        # O portão do nó de SAÍDA é outra história e vale aqui — o pin que ele
        # recusa nunca funcionou.
        return await pin_service.fixar_saida(
            db, wf, node_id,
            outputs=body.outputs,
            ttl_hours=body.ttl_hours,
            user_id=getattr(user, "id_hash", None),
            exigir_no_existente=False,
        )
    except pin_service.PinEmNoDeSaidaError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{id_hash}/pin/{node_id}", summary="Unpin output of a node")
async def unpin_node_output(
    id_hash: str,
    node_id: str,
    wf=Depends(workflow_com_papel(ROLE_EDITOR)),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Remove o output fixado de um nó e deleta o artefato de cache do MinIO."""
    return await pin_service.desfixar_saida(db, wf, node_id)


@router.get("/{id_hash}/pins", summary="List pinned nodes")
async def list_pinned_nodes(
    id_hash: str,
    wf=Depends(workflow_com_papel(
        ROLE_VIEWER, "Requer role 'viewer' ou superior para ver os pins.",
    )),
    _user=Depends(get_current_user),
):
    """Lista os nós com output fixado e seus metadados.

    Exige `viewer`, e não apenas pertencimento ao workspace. Era a única das
    três rotas de pin sem papel nenhum — as irmãs `PUT`/`DELETE` pedem `editor`
    —, e a tool `list_pins` do MCP já exigia `viewer` (`app/mcp/guardas.py`).
    A mesma leitura respondia com duas réguas conforme a porta de entrada.
    """
    # Sem `node_ids_existentes`: a rota continua listando tudo o que está
    # gravado, inclusive pin de nó já apagado. É o MCP que filtra pelos nós que
    # a definition ainda tem — a tela precisa enxergar o órfão para limpá-lo.
    pins = pin_service.listar_pins(wf.pin_metadata, wf.pinned_outputs)
    return {"pinned_nodes": pins, "total": len(pins)}
