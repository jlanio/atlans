"""
Validação de uma definição de workflow sem executar — o núcleo por trás da
tool `validate_workflow` do servidor MCP e da validação que as tools de
construção rodam antes de gravar. Existia também a casca REST
`POST /workflows/validate`; saiu por não ter chamador (a web nunca a usou, e a
skill que a chamava foi absorvida pelo MCP).

Ordem, e o porquê dela:

1. Corpo (Pydantic) — `properties` é sinônimo de `parameters` (a definição
   persistida usa um nome, o corpo do validate usa o outro), `alias` chega ao
   executor, `position` é ignorado, `workspace_id` é opcional.
2. Lint puro (`flow/utils/definition_lint.py`), ANTES de construir o executor:
   nó inexistente e ciclo estouravam dentro de `WorkflowExecutor.__init__` e
   viravam um 500 genérico com a causa mascarada; id duplicado sobrescrevia o
   nó em silêncio. Agora os três viram **422** com o relatório no corpo
   (`DefinicaoInvalidaError`) — e `credential_id` que não é UUID também (era
   403; fatal por contrato, para quem só olha o status HTTP seguir reprovando).
3. Sessão de banco só quando há o que checar — credencial ou `workspace_id`.
   O caso comum (definição solta, sem credencial) continua sem abrir sessão
   própria: o CI não tem Postgres e a validação não deve pagar por uma
   conexão que não usa. Referências de sub-fluxo só são conferidas COM
   `workspace_id`: sem a filiação provada, a consulta por hash seria um
   oráculo de existência, estado e portas de workflows de outros workspaces.
4. Com `workspace_id`: primeiro a filiação (403 antes de olhar credenciais,
   para não revelar a existência de uma credencial a quem não é do
   workspace); as credenciais compartilhadas com o workspace só entram no
   escopo para quem tem papel `operator` ou superior — o mesmo exigido para
   executar, porque a simulação do DatabaseSpatialQuery CONECTA ao banco da
   credencial; abaixo disso vale só o escopo do próprio usuário. Depois, as
   checagens que precisam de banco (nós desabilitados pelo admin, referências
   de sub-fluxo).
5. Executor → simulação → diagnósticos de aresta; o resultado é
   `{node_id: {...}}` + `__edge_diagnostics__` (só quando há) + `__report__`
   (sempre; consumidores pulam as chaves `__*`).

O cerco de credenciais é o que impede alguém que conheça o UUID de uma
credencial alheia de executar SQL na infraestrutura de outro usuário.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, model_validator

from app.core.authorization.credential_loader import (
    assert_credentials_accessible,
    credential_scope,
    tipos_e_validades,
)
from app.core.authorization.workflow_access import get_workspace_member_role, tem_papel_minimo
from app.core.db import get_session_async
from app.core.exceptions import CredentialAccessDeniedError, DefinicaoInvalidaError
from app.core.rbac import ROLE_OPERATOR
from app.services import fontes_service
from app.services.credential_resolver import propriedade_que_recebe, tipos_aceitos_do_descriptor
from app.services.disabled_nodes_service import disabled_names
from flow.utils.definition_lint import FATAIS, RelatorioLint, lint_definition
from flow.utils.workflow_contract import validate_subworkflow_references_against_db

HINT_WORKSPACE = (
    "Informe workspace_id para checar nós desabilitados, referências de sub-fluxo "
    "e credenciais compartilhadas com o workspace."
)
HINT_PAPEL_OPERATOR = (
    "Credenciais compartilhadas com o workspace só entram na validação com papel "
    "operator ou superior (o mesmo exigido para executar); o escopo ficou só nas suas."
)
HINT_PARAMS_SCHEMA = (
    "suggested_params_schema é heurístico (referências inputs.<nome> em nós trigger e "
    "ports de SubWorkflowInput); revise antes de gravar em params_schema."
)
HINT_FONTES = (
    "Fontes externas (WFS) não são sondadas aqui — a validação não toca a rede. "
    "unknown_source/failing_source dizem o que o catálogo sabe: use search_sources/"
    "describe_source para uma fonte já mapeada, ou probe_source/register_source para "
    "sondar e registrar esta."
)


# --- MODELOS ---
class NodeParameter(BaseModel):
    id: str
    name: str
    type: str
    parameters: Dict[str, Any] = {}
    # O alias vive no topo do nó na definição persistida e é o que o executor lê
    # (`flow/core/aliases.py`); sem ele aqui, o lint de alias não teria o que ver.
    alias: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _fundir_properties(cls, data: Any) -> Any:
        # A definição persistida usa `properties`; o corpo do validate, `parameters`.
        # Colar uma na outra perdia todos os valores em silêncio (extra='ignore').
        # Em conflito, `parameters` (o formato deste corpo) vence. Um `parameters`
        # que não é objeto fica como está, para o Pydantic acusar 422 — um
        # TypeError aqui dentro viraria 500.
        if isinstance(data, dict) and isinstance(data.get("properties"), dict):
            atuais = data.get("parameters")
            if atuais is None or isinstance(atuais, dict):
                data = dict(data)
                data["parameters"] = {**data["properties"], **(atuais or {})}
        return data


class EdgeDefinition(BaseModel):
    source: str
    target: str
    # O Pydantic descarta o que nao esta declarado, e `payload = definition.dict()`
    # ia direto para o WorkflowExecutor. Sem estes campos a simulacao caia sempre
    # no ramo "sem from_key" (core.py:765) e nomeava as entradas com o parent_id:
    # o schema do preview divergia do que o run produzia de fato. Um painel que
    # discorda do runtime e pior que painel nenhum.
    from_key: Optional[str] = None
    to_key: Optional[str] = None
    condition: Optional[bool] = None


class WorkflowDefinition(BaseModel):
    nodes: List[NodeParameter]
    edges: List[EdgeDefinition]
    # Opcional de propósito: sem ele a validação continua funcionando sem banco;
    # com ele, entram as checagens que dependem do workspace (§4 do módulo).
    workspace_id: Optional[str] = None


# --- HELPERS ---
def _payload_para_o_executor(definition: WorkflowDefinition) -> dict:
    """Definição no formato que o executor e os helpers do servidor leem.

    `parameters` e `properties` apontam para o MESMO dict: `simulate_runner` lê
    `parameters`, `node_props` (servidor) e `collect_subworkflow_references` leem
    `properties`. Um dict só, para não haver como divergirem.
    """
    nos = []
    for n in definition.nodes:
        params = dict(n.parameters)
        no: dict = {"id": n.id, "name": n.name, "type": n.type, "parameters": params, "properties": params}
        if n.alias:
            no["alias"] = n.alias
        nos.append(no)
    return {"nodes": nos, "edges": [e.model_dump() for e in definition.edges]}


def _credential_ids_validos(nodes: list) -> set:
    """UUIDs de `credential_id` que vão à guarda de banco. Os malformados não
    referenciam credencial nenhuma e já reprovaram a definição com 422
    (`invalid_credential_id` é fatal no lint) antes de chegar aqui — em vez do
    403 de antes, que mascarava um typo; o filtro fica como cinto e suspensório."""
    ids: set = set()
    for n in nodes:
        cid = (n.get("parameters") or {}).get("credential_id")
        if not cid:
            continue
        try:
            UUID(str(cid))
        except (ValueError, AttributeError, TypeError):
            continue
        ids.add(str(cid))
    return ids


def _conferir_credenciais(lint: RelatorioLint, nodes: list, descriptors: Dict[str, dict], credenciais: dict) -> None:
    """Diagnósticos para a credencial que a resolução NÃO vai entregar ao nó:
    de um tipo que ele não aceita, ou que não tem onde entrar nele
    (`credential_type_mismatch`), ou vencida (`credential_expired`).

    Só a tela filtra a credencial pelo tipo; pela API e pelo assistente chega
    qualquer uma, e a resolução a deixa de fora em silêncio. Onde o nó CONSOME
    o segredo injetado (WFS, HttpRequest, os de banco — declaram `http_auth`
    ou `connectionString`) isso é execução recusada: erro (não fatal). Onde o
    nó usa o próprio id (DataOutput e os SaveTo*, com `webhook_token`) a
    execução segue e só o download do artefato é recusado: aviso — um erro
    aqui impediria o assistente de gravar uma edição em outro nó.
    `credenciais` é o que `tipos_e_validades` devolveu para os ids acessíveis.
    """
    for n in nodes:
        cid = (n.get("parameters") or {}).get("credential_id")
        try:
            chave = str(UUID(str(cid))) if cid else None
        except (ValueError, AttributeError, TypeError):
            chave = None
        if chave is None or chave not in credenciais:
            continue
        tipo, validade, expires_at = credenciais[chave]
        descriptor = descriptors.get(n.get("name")) or {}
        declaradas = {p.get("name") for p in descriptor.get("properties") or [] if isinstance(p, dict)}
        recebe = propriedade_que_recebe(tipo)
        # O SaveToS3 declara `s3_auth` e também aceita o Webhook Token do uso
        # antigo (protege a cópia): consome o segredo só quando é a do S3.
        consome = bool(declaradas & {"http_auth", "connectionString"}) or (
            recebe == "s3_auth" and recebe in declaradas
        )
        registrar = lint.erro if consome else lint.aviso
        desfecho = (
            "o Executar não a resolve e o nó recusa" if consome
            else "o download do artefato protegido por ela será recusado"
        )
        onde = f"nó '{n.get('name')}' (id={n.get('id')})"
        aceitos = tipos_aceitos_do_descriptor(descriptor)
        if aceitos is not None and tipo not in aceitos:
            registrar(
                "credential_type_mismatch",
                f"{onde} aponta uma credencial do tipo '{tipo}', que ele não aceita "
                f"({', '.join(sorted(aceitos))}) — {desfecho}.",
                node_id=n.get("id"),
            )
        elif recebe is not None and declaradas and recebe not in declaradas:
            # Sem `credential_types` declarados (os nós de banco), a FORMA da
            # credencial decide: uma HTTP não tem onde entrar num nó que só
            # recebe `connectionString` — a resolução deixa o id e nada mais.
            registrar(
                "credential_type_mismatch",
                f"{onde} aponta uma credencial do tipo '{tipo}', que ele não tem onde receber "
                f"(o nó não declara `{recebe}`) — {desfecho}.",
                node_id=n.get("id"),
            )
        # O SaveToS3 usa o MESMO `credential_id` para as duas coisas: com a
        # credencial S3 escolhida, a cópia registrada como artefato fica sem o
        # Webhook Token que a protegia — download pelo link, como no nó sem
        # credencial. É uma escolha possível, mas não pode ser silenciosa.
        if (
            tipo == "s3" and "s3_auth" in declaradas
            and (n.get("parameters") or {}).get("registerArtifact") in (True, "true", "True", 1, "1")
        ):
            lint.aviso(
                "artifact_copy_unprotected",
                f"{onde} usa a credencial S3 e registra a cópia como artefato: a cópia fica "
                "sem token de proteção (download público pelo link). Para protegê-la, use a "
                "cadeia padrão do executor no lugar da credencial S3 e escolha um Webhook Token.",
                node_id=n.get("id"),
            )
        if validade == "expirada":
            registrar(
                "credential_expired",
                f"{onde} aponta uma credencial vencida em {expires_at} — {desfecho}.",
                node_id=n.get("id"),
            )
        elif validade == "invalida":
            registrar(
                "credential_expired",
                f"{onde} aponta uma credencial com validade (expires_at) ilegível: {expires_at!r} — "
                f"ignorada por segurança; {desfecho}.",
                node_id=n.get("id"),
            )


def _item(code: str, severity: str, message: str, *, node_id: Optional[str] = None,
          edge: Optional[dict] = None) -> dict:
    return {"code": code, "severity": severity, "node_id": node_id, "edge": edge, "message": message}


def _montar_report(
    lint: RelatorioLint,
    nodes: list,
    *,
    disabled_nodes: Optional[list],
    subworkflow_errors: Optional[list],
    edge_diagnostics: list,
    simulated_outputs: dict,
    hints: list,
    source_warnings: Optional[list] = None,
) -> dict:
    """`__report__`: tudo o que a validação achou, num formato só.

    `errors` junta o lint com o que depende de banco (nó desabilitado, sub-fluxo)
    e com o que a simulação produziu (aresta com `from_key` inexistente, nó com
    `status: error`). `ok` é "sem erros" — avisos não derrubam. `source_warnings`
    são os avisos do catálogo de fontes (`unknown_source`, `failing_source`):
    também avisos, porque a validação não sonda a fonte — só diz o que sabe.
    """
    errors = [d.as_dict() for d in lint.errors]
    warnings = [d.as_dict() for d in lint.warnings]
    warnings.extend(source_warnings or [])

    if disabled_nodes:
        desabilitados = set(disabled_nodes)
        for n in nodes:
            if n.get("name") in desabilitados:
                errors.append(_item(
                    "disabled_node", "error",
                    f"nó '{n['name']}' (id={n.get('id')}) está desabilitado pelo admin — "
                    "o run recusa com 422 workflow_has_disabled_nodes.",
                    node_id=n.get("id"),
                ))
    for msg in subworkflow_errors or []:
        errors.append(_item("subworkflow_reference", "error", str(msg)))

    for d in edge_diagnostics:
        edge = {"source": d.get("source"), "target": d.get("target")}
        if d.get("from_key") is not None:
            edge["from_key"] = d["from_key"]
        if d.get("severity") == "error":
            errors.append(_item("edge_from_key_unknown", "error", str(d.get("message", "")), edge=edge))
        else:
            warnings.append(_item("edge_spread_ambiguous", "warning", str(d.get("message", "")), edge=edge))

    for node_id, saida in simulated_outputs.items():
        if str(node_id).startswith("__") or not isinstance(saida, dict):
            continue
        if saida.get("status") == "error":
            errors.append(_item("simulate_error", "error", str(saida.get("error", "")), node_id=node_id))

    sugestao = dict(lint.suggested_params_schema)
    dicas = list(hints)
    if sugestao:
        dicas.append(HINT_PARAMS_SCHEMA)
    if source_warnings:
        dicas.append(HINT_FONTES)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "disabled_nodes": disabled_nodes,
        "subworkflow_errors": subworkflow_errors,
        "suggested_params_schema": sugestao,
        "hints": dicas,
    }


def _mensagem_fatal(lint: RelatorioLint) -> str:
    fatais = [d.message for d in lint.errors if d.code in FATAIS]
    mensagem = "Definição inválida: " + "; ".join(fatais[:3])
    if len(fatais) > 3:
        mensagem += f" (+{len(fatais) - 3})"
    return mensagem


# --- NÚCLEO ---
async def validar_definicao(
    definition: Union[dict, WorkflowDefinition],
    *,
    user_id: str,
    workspace_id: Optional[str],
) -> dict:
    """Lint da definição, schema de saída de cada nó e diagnósticos de aresta.

    Devolve `{node_id: {status, schema, schema_source} | {status: "error", error}}`
    + `__edge_diagnostics__` (só quando há) + `__report__` (sempre; `ok` = sem
    erros). Um `dict` passa por `WorkflowDefinition.model_validate`, com
    `properties` fundido em `parameters`; um corpo mal formado sobe como
    `pydantic.ValidationError` para o chamador traduzir.

    `workspace_id` explícito vence o do corpo: o chamador é quem sabe em que
    workspace está validando (o MCP resolve id-ou-nome antes de chegar aqui);
    `None` deixa valer o do corpo, onde o campo é opcional.

    Levanta `DefinicaoInvalidaError` (com `.report`) quando o executor nem
    construiria — nó inexistente, id duplicado, ciclo, `credential_id` que não é
    UUID, erro de construção; `HTTPException(403)` quando o usuário não é membro
    do workspace; `HTTPException(503)` com registry vazio (falha de boot, não
    da definição); `CredentialAccessDeniedError` quando alguma credencial está
    fora do escopo (com a dica de `workspace_id` quando não houve workspace).
    """
    from flow.executor import WorkflowExecutor
    from flow.registry import NODE_REGISTRY

    if not isinstance(definition, WorkflowDefinition):
        definition = WorkflowDefinition.model_validate(definition)
    if workspace_id is None:
        workspace_id = definition.workspace_id

    if not NODE_REGISTRY:
        # Registry vazio é falha de boot do servidor, não da definição: acusar
        # "nó inexistente" aqui mandaria o cliente corrigir um nome certo.
        raise HTTPException(status_code=503, detail="Catálogo de nós indisponível neste servidor.")

    payload = _payload_para_o_executor(definition)
    nodes = payload["nodes"]
    nomes = {n["name"] for n in nodes}
    hints: list = [] if workspace_id else [HINT_WORKSPACE]

    descriptors: Dict[str, dict] = {}
    for nome in nomes:
        cls = NODE_REGISTRY.get(nome)
        if cls is None:
            continue
        try:
            descriptors[nome] = cls.description()
        except Exception:  # descriptor quebrado não pode derrubar a validação
            continue

    lint = lint_definition(nodes, payload["edges"], registry_names=NODE_REGISTRY.keys(), descriptors=descriptors)
    if lint.fatal:
        raise DefinicaoInvalidaError(_mensagem_fatal(lint), report=_montar_report(
            lint, nodes, disabled_nodes=None, subworkflow_errors=None,
            edge_diagnostics=[], simulated_outputs={}, hints=hints,
        ))

    cred_ids = _credential_ids_validos(nodes)
    disabled_nodes: Optional[list] = None
    subworkflow_errors: Optional[list] = None
    escopo_compartilhado: Optional[str] = None
    avisos_de_fonte: list = []
    if cred_ids or workspace_id:
        # UMA sessão, e só aqui — sem Depends(get_db): a maioria das validações
        # não referencia credencial nem workspace e não deve pagar por uma conexão.
        async with get_session_async() as db:
            if workspace_id:
                papel = await get_workspace_member_role(db, workspace_id, user_id)
                if papel is None:
                    raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
                if tem_papel_minimo(papel, ROLE_OPERATOR):
                    escopo_compartilhado = workspace_id
                elif cred_ids:
                    hints.append(HINT_PAPEL_OPERATOR)
            if cred_ids:
                try:
                    await assert_credentials_accessible(
                        db, cred_ids, user_id, shared_workspace_id=escopo_compartilhado,
                    )
                except CredentialAccessDeniedError as exc:
                    if workspace_id:
                        raise
                    # Sem workspace o escopo é só o do usuário: a credencial pode
                    # ser compartilhada e a pessoa só não sabe que precisa dizer onde.
                    raise CredentialAccessDeniedError(f"{exc.detail} {HINT_WORKSPACE}") from exc
                # Acessível não é usável: o tipo e a validade decidem se o
                # Executar a resolve — e é aqui, e não no run, que se avisa.
                _conferir_credenciais(lint, nodes, descriptors, await tipos_e_validades(db, cred_ids))
            desabilitados = await disabled_names(db)
            disabled_nodes = sorted(nomes & set(desabilitados))
            if workspace_id:
                subworkflow_errors = list(
                    await validate_subworkflow_references_against_db(payload, db, workspace_id=workspace_id)
                )
                # O catálogo de fontes: sem rede, uma consulta por definição. Falha
                # ABERTA aqui também — a validação não depende do catálogo.
                try:
                    avisos_de_fonte = await fontes_service.conferir_fontes_da_definicao(
                        db, nodes, descriptors, workspace_id,
                    )
                except Exception:  # pragma: no cover - o serviço já falha aberto
                    avisos_de_fonte = []

    try:
        executor = WorkflowExecutor(payload)
    except ValueError as exc:
        # Rede de segurança: o lint cobre o que se conhece; qualquer outro erro
        # de construção também é da definição, não do servidor.
        lint.erro("construction_error", str(exc))
        raise DefinicaoInvalidaError(f"Definição inválida: {exc}", report=_montar_report(
            lint, nodes, disabled_nodes=disabled_nodes, subworkflow_errors=subworkflow_errors,
            edge_diagnostics=[], simulated_outputs={}, hints=hints, source_warnings=avisos_de_fonte,
        ))

    # Mesmo escopo do despacho: as credenciais do usuário mais as compartilhadas
    # com o workspace informado (para quem pode executar) — e nada além disso,
    # mesmo que um `simulate()` novo apareça.
    with credential_scope({user_id}, shared_workspace_id=escopo_compartilhado):
        await executor.simulate_runner()

    # Diagnósticos de aresta (from_key defasado = erro; spread ambíguo = aviso).
    # Sob uma chave reservada, no mesmo padrão de __artifacts__/__response__, para
    # não se confundir com os schemas por node_id. Só aparece quando há algo.
    diagnostics = executor.validate_edges()
    saida = executor.simulated_outputs
    if diagnostics:
        saida["__edge_diagnostics__"] = diagnostics
    saida["__report__"] = _montar_report(
        lint, nodes, disabled_nodes=disabled_nodes, subworkflow_errors=subworkflow_errors,
        edge_diagnostics=diagnostics, simulated_outputs=saida, hints=hints,
        source_warnings=avisos_de_fonte,
    )
    return saida
