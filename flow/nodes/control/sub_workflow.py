import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.nodes.outputs.sub_workflow_output import _parse_ports
from flow.utils.workflow_contract import MAX_PROFUNDIDADE
from flow.utils.logger import get_logger
from flow.utils.publisher.events import KIND_LIFECYCLE, LEVEL_INFO

logger = get_logger(__name__)

_CTX_ANCESTORS_KEY = "_subflow_ancestors"
_CTX_DISABLED_NODES_KEY = "_disabled_nodes"
_CTX_DEFINITIONS_KEY = "_subworkflow_definitions"

# Nome do involucro devolvido ao pai. Reservado: uma porta de saida com este
# nome sobreviveria ao `**public` do return e apagaria o dict inteiro.
RESULTADO = "subWorkflowResult"


def _onde_falhou(child: Any) -> str:
    """Sufixo com o no do sub-fluxo que falhou, quando da para saber.

    `node_stats` e preenchido no `finally` de cada no, entao esta disponivel
    mesmo depois de a excecao subir.
    """
    stats = getattr(child, "node_stats", None) or {}
    quebrados = [
        (nid, info.get("node_name") or nid)
        for nid, info in stats.items()
        if isinstance(info, dict) and info.get("status") == "failed"
    ]
    if not quebrados:
        return ""
    nid, nome = quebrados[0]
    return f", no nó '{nome}' ({nid})"


class _SubWorkflowEventPublisher:
    """Repassa eventos do sub-fluxo ao publisher do pai, com namespace.

    Os node_ids do filho nao existem no canvas do pai — publicados crus, o
    frontend recebe eventos de nos desconhecidos e os descarta (ou pior, pinta
    o no errado). Prefixando com o id do node SubWorkflow, o evento fica
    rastreavel ate o ponto do grafo que o originou e o canvas pode, no futuro,
    fazer drill-down para dentro do sub-fluxo.

    `__workflow_complete__` do filho NAO e repassado: encerraria o run do pai
    no frontend. O termino do sub-fluxo ja e sinalizado pelo evento do proprio
    node SubWorkflow.
    """

    _TERMINAL_NODE = "__workflow_complete__"

    def __init__(self, parent_publisher: Any, parent_node_id: str):
        self._parent = parent_publisher
        self._prefix = parent_node_id

    def publish_event(
        self,
        run_id: str,
        node: str,
        status: str,
        timestamp: Any = None,
        duration_ms: Any = None,
        error: Any = None,
        extra: Any = None,
        kind: str = KIND_LIFECYCLE,
        level: str = LEVEL_INFO,
    ) -> None:
        if node == self._TERMINAL_NODE:
            return
        meta = dict(extra or {})
        meta["subworkflow_parent_node"] = self._prefix
        # `nodes_total` e o denominador do progresso ("no 7 de 12") do fluxo que
        # emitiu o evento. Republicado, faria o painel do pai trocar o
        # denominador pelo do filho no meio do run.
        meta.pop("nodes_total", None)
        try:
            self._parent.publish_event(
                run_id=run_id,
                node=f"{self._prefix}::{node}",
                status=status,
                timestamp=timestamp,
                duration_ms=duration_ms,
                error=error,
                extra=meta,
                kind=kind,
                level=level,
            )
        except Exception as exc:  # publicar evento nunca derruba a execucao
            logger.debug("Falha ao republicar evento do sub-fluxo: %s", exc)


@register_node
class SubWorkflowNode(BaseNode):
    """
    Nó de controle que executa outro workflow como um nó aninhado.
    Permite compor workflows complexos reutilizando workflows existentes.

    Propriedades:
      - workflowHash:     id_hash do sub-workflow a executar
      - inputsMapping:    {"chave_sub_workflow": "chave_input_atual"}
      - timeoutSeconds:   tempo maximo de execucao (default 300)

    Hardening:
      - Loop detection via context["_subflow_ancestors"] (set de hashes)
      - Timeout via asyncio.timeout (so o prazo do proprio sub-fluxo)
      - CancelledError propagado (cancelamento cascata)
      - Mensagens especificas (nao existe / desativado / fora do workspace)
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SubWorkflow',
            'alias': 'Sub-Workflow',
            'description': (
                'Executa outro workflow como nó aninhado. '
                'Permite compor fluxos complexos reutilizando workflows existentes.'
            ),
            'type': 'control',
            'properties': [
                {
                    'name': 'workflowHash', 'required': True,
                    'label': 'Sub-workflow',
                    'type': 'string',
                    'default': '',
                    'description': 'id_hash do sub-workflow a ser executado.'
                },
                {
                    'name': 'inputsMapping',
                    'label': 'Mapeamento de entradas',
                    'type': 'object',
                    'default': {},
                    'description': (
                        'Mapeamento das entradas: '
                        '{"chave_sub_workflow": "chave_input_atual"}. '
                        'Se vazio, todos os inputs são repassados diretamente.'
                    )
                },
                {
                    'name': 'timeoutSeconds',
                    'label': 'Tempo limite (s)',
                    'type': 'integer',
                    'default': 300,
                    'description': (
                        'Tempo máximo de execução do sub-workflow em segundos. '
                        'Se exceder, o sub-fluxo é cancelado e o node falha.'
                    ),
                },
            ],
            'outputs': [
                {'name': 'subWorkflowResult', 'type': 'object', 'description': 'Resultado completo do sub-workflow executado'},
            ],
        }

    # ── Helpers internos ──────────────────────────────────────────────────

    def _check_subworkflow_contract(
        self, workflow_hash: str, definition: Dict[str, Any]
    ) -> None:
        """Garante que o sub-fluxo declara seu contrato via SubWorkflowInput
        (entry point) e SubWorkflowOutput (saida publica).

        Sem esses dois nodes, o caller nao tem como mapear inputs nomeados nem
        consumir outputs nomeados — o que tornava sub-fluxos efetivamente
        inusaveis no canvas (resultados indexados por UUID de node).
        """
        inputs = [n for n in (definition.get("nodes") or []) if n.get("name") == "SubWorkflowInput"]
        outputs = [n for n in (definition.get("nodes") or []) if n.get("name") == "SubWorkflowOutput"]

        # SubWorkflowOutput e obrigatorio: e o que define o valor de retorno.
        # Nao adotamos o "ultimo node executado" do n8n — implicito e ambiguo
        # quando o grafo tem ramos.
        if not outputs:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' nao declara saida: falta o node "
                "SubWorkflowOutput. Adicione-o e conecte o que deve ser devolvido "
                "ao workflow chamador."
            )

        # SubWorkflowInput e OPCIONAL: um sub-fluxo pode nao receber nada
        # (fonte fixa, parametros internos). Exigi-lo era burocracia.

        # No maximo um de cada: `extract_contract` UNE as portas de todos os
        # nodes do tipo, mas `collect_subworkflow_output` devolve o PRIMEIRO
        # encontrado — com dois, o contrato anuncia portas que o runtime nunca
        # entrega.
        if len(outputs) > 1:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' tem {len(outputs)} nodes "
                "SubWorkflowOutput. Apenas um e permitido — o contrato de saida "
                "precisa ser unico."
            )
        if len(inputs) > 1:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' tem {len(inputs)} nodes "
                "SubWorkflowInput. Apenas um e permitido."
            )

        # `subWorkflowResult` e o INVOLUCRO que este no devolve ao pai. Uma porta
        # com esse nome sobreviveria ao `**public` do return e apagaria o dict
        # inteiro: quem lesse `subWorkflowResult` esperando as chaves publicas
        # receberia um valor cru, sem nada explicando.
        conflitantes = [
            p for p in _parse_ports((outputs[0].get("properties") or {}).get("ports"))
            if p == RESULTADO
        ] if outputs else []
        if conflitantes:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' declara uma saida chamada "
                f"'{RESULTADO}', que e o nome reservado do resultado devolvido ao "
                "workflow chamador. Renomeie essa porta no node SubWorkflowOutput."
            )

    def _check_disabled_nodes_in_definition(
        self, workflow_hash: str, definition: Dict[str, Any]
    ) -> None:
        """Bloqueia o sub-fluxo se algum node nele esta na blacklist do admin.

        O snapshot `_disabled_nodes` vem do envelope do job (servidor → executor)
        — propagado via WorkflowExecutor.context para todos os nodes. Permite
        bloquear cadeias inteiras sem precisar consultar o DB do servidor a
        cada nivel.
        """
        ctx = self.context or {}
        disabled: set[str] = ctx.get(_CTX_DISABLED_NODES_KEY) or set()
        if not disabled:
            return

        offenders = sorted({
            n.get("name") for n in (definition.get("nodes") or [])
            if n.get("name") in disabled
        })
        if offenders:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' contem node(s) desabilitados "
                f"pelo admin: {', '.join(offenders)}. Reabilite via "
                "/admin/settings ou substitua os nodes."
            )

    def _check_loop(self, workflow_hash: str) -> set[str]:
        """Verifica se o workflow alvo cria um ciclo. Retorna o novo set de
        ancestrais (atual + hash) que sera injetado no context do filho."""
        ctx = self.context or {}
        ancestors_raw = ctx.get(_CTX_ANCESTORS_KEY) or set()
        ancestors: set[str] = set(ancestors_raw) if not isinstance(ancestors_raw, set) else ancestors_raw

        if workflow_hash in ancestors:
            chain = " > ".join(list(ancestors) + [workflow_hash])
            raise ValueError(
                f"Loop detectado: workflow '{workflow_hash}' ja esta na cadeia "
                f"de execucao ({chain}). Sub-fluxos nao podem se chamar "
                "recursivamente, direta ou indiretamente."
            )

        return ancestors | {workflow_hash}

    def _fetch_definition_from_snapshot(self, workflow_hash: str) -> Dict[str, Any]:
        """Busca a definition do sub-workflow no snapshot enviado pelo servidor
        no envelope do job.

        O executor NAO tem acesso ao DB (so flow/ e executor/ no Docker). Toda a
        cadeia de sub-workflows e pre-resolvida pelo servidor em
        workflow_execution_service.collect_subworkflow_definitions_recursive
        e enviada via payload do job. Acessamos aqui via context.

        Levanta ValueError quando o hash nao esta no snapshot — pode ser:
        - Workflow nao existe / desativado / outro workspace (servidor nao
          incluiu)
        - Cadeia ultrapassou max_depth (10) — improvavel
        - Operador alterou workflowHash em runtime (impossivel em workflows
          persistidos, mas defesa em profundidade)
        """
        ctx = self.context or {}
        definitions: Dict[str, Dict[str, Any]] = ctx.get(_CTX_DEFINITIONS_KEY) or {}
        if workflow_hash in definitions:
            return definitions[workflow_hash]

        raise ValueError(
            f"Sub-workflow '{workflow_hash}' nao foi pre-resolvido pelo servidor. "
            "Causas comuns: workflow nao existe, esta desativado, ou pertence a "
            "outro workspace. Reabra o workflow chamador e re-salve para forcar "
            "uma revalidacao."
        )

    # ── Execucao ─────────────────────────────────────────────────────────

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # 1) Validacao e extracao de parametros
        self.validate()

        workflow_hash = self.parameters.get('workflowHash', '').strip()
        inputs_mapping = self.parameters.get('inputsMapping', {})
        timeout = self.get_param_int("timeoutSeconds", 300)

        if not workflow_hash:
            raise ValueError("Parametro 'workflowHash' e obrigatorio e nao pode ser vazio.")

        if not isinstance(inputs_mapping, dict):
            raise TypeError(
                f"Parametro 'inputsMapping' deve ser um dicionario. "
                f"Tipo recebido: {type(inputs_mapping).__name__}"
            )
        if timeout <= 0:
            raise ValueError(
                f"Parametro 'timeoutSeconds' deve ser positivo (recebido: {timeout})."
            )

        logger.info(
            "SubWorkflowNode: iniciando sub-workflow '%s' (timeout=%ds, mapping=%s)",
            workflow_hash, timeout, list(inputs_mapping.keys()) or 'todos',
        )

        # 2) Loop detection — antes de qualquer I/O do filho.
        child_ancestors = self._check_loop(workflow_hash)

        # 2b) Profundidade. O servidor para de pre-resolver em MAX_PROFUNDIDADE
        # niveis, e sem esta checagem o estouro chegava ao operador como
        # "workflow nao encontrado — nao existe, esta desativado, ou e de outro
        # workspace". Nenhuma das tres era verdade, e o conselho (re-salvar) nao
        # resolvia: ele iria conferir tres coisas que estavam certas.
        if len(child_ancestors) > MAX_PROFUNDIDADE:
            cadeia = " > ".join(list(child_ancestors)[:4]) + " > ..."
            raise ValueError(
                f"A cadeia de sub-fluxos passou de {MAX_PROFUNDIDADE} níveis ao "
                f"chamar '{workflow_hash}' ({cadeia}). O servidor só pré-resolve "
                f"até esse limite. Achate a cadeia — um sub-fluxo intermediário "
                "geralmente pode ser absorvido pelo chamador."
            )

        # 3) Resolve definicao do filho no snapshot do envelope (servidor
        # ja pre-resolveu toda a cadeia). Sem I/O, sem DB, sem app.* import.
        definition = self._fetch_definition_from_snapshot(workflow_hash)

        # 3.5) Valida que o sub-fluxo nao usa nodes desabilitados pelo admin.
        # Roda DEPOIS de resolver a definicao (precisa do conteudo do filho).
        self._check_disabled_nodes_in_definition(workflow_hash, definition)

        # 3.6) Valida que o sub-fluxo tem contrato declarado: SubWorkflowInput
        # como entry point + SubWorkflowOutput como saida publica. Sem isso,
        # caller nao consegue passar dados nomeados nem ler chaves utilizaveis.
        self._check_subworkflow_contract(workflow_hash, definition)

        # 4) Constroi inputs do sub-workflow
        if inputs_mapping:
            # Chave de origem ausente INTERROMPE, e nao apenas avisa.
            #
            # Antes o sub-fluxo rodava inteiro e devolvia None naquela chave: o
            # run terminava verde, o pai seguia com um nulo e o unico sinal era
            # um warning perdido no log. E o caso comum nao e erro de digitacao
            # — e a aresta de cima ser removida ou ter o `to_key` renomeado
            # DEPOIS que o mapeamento foi feito, quando ninguem esta olhando
            # para este no.
            faltando = [
                (sub_key, src_key)
                for sub_key, src_key in inputs_mapping.items()
                if src_key not in inputs
            ]
            if faltando:
                detalhe = "; ".join(f"'{s}' (para '{d}')" for d, s in faltando)
                raise ValueError(
                    f"O mapeamento de entradas aponta para chave(s) que não chegaram "
                    f"a este nó: {detalhe}. Chegaram: "
                    f"{sorted(inputs) or '<nenhuma>'}. Corrija o mapeamento ou "
                    "reconecte a origem — o sub-fluxo receberia nulo no lugar."
                )
            sub_inputs: Dict[str, Any] = {
                sub_key: inputs[src_key] for sub_key, src_key in inputs_mapping.items()
            }
        else:
            sub_inputs = dict(inputs)

        logger.info(
            "SubWorkflowNode: executando sub-workflow '%s' com inputs: %s",
            workflow_hash, list(sub_inputs.keys()),
        )

        # 5) Executa o sub-workflow NO MESMO event loop, com timeout.
        #
        # Antes: asyncio.to_thread(run_sync) -> run_sync fazia asyncio.run(), ou seja,
        # um event loop NOVO dentro de uma thread. Isso trazia tres problemas:
        #   a) wait_for cancelava a espera, nao a thread — no timeout o sub-fluxo
        #      seguia rodando, consumindo CPU/RAM/conexoes e podendo gravar
        #      artefatos depois de o node ja ter falhado;
        #   b) CancelledError do pai nao cascateava pelo mesmo motivo;
        #   c) pools asyncpg cacheados globalmente sao atrelados ao loop que os
        #      criou — reusar no loop do filho quebra com "attached to a
        #      different loop".
        # Rodando na mesma corrotina, o prazo cancela de verdade e o loop e um so.
        #
        # Propaga o ESCOPO DE EXECUCAO (task_id, workspace_id, publisher, debug):
        # sem isso o filho instanciava WorkflowExecutor(definition) puro e todo
        # node que chama require_scope() — DataOutput, PublishMap, SaveToS3,
        # SaveToShapefile, SaveToGeoparquet, SendEmail — falhava com
        # "workspace_id nao injetado pelo executor".
        #
        # E os TRES snapshots do envelope, sem os quais a cadeia A→B→C falha em B:
        # _subflow_ancestors (loop detection), _disabled_nodes, _subworkflow_definitions.
        inherited_disabled = (self.context or {}).get(_CTX_DISABLED_NODES_KEY) or set()
        inherited_defs = (self.context or {}).get(_CTX_DEFINITIONS_KEY) or {}

        from flow.executor import WorkflowExecutor

        child = WorkflowExecutor(
            definition,
            task_id=self._task_id,
            workspace_id=self._workspace_id,
            # workflow_hash do FILHO: artefatos e metricas do sub-fluxo devem
            # ser atribuidos a ele, nao ao pai.
            workflow_hash=workflow_hash,
            publisher=_SubWorkflowEventPublisher(self._publisher, self.node_id)
            if self._publisher else None,
            debug_mode=self._debug_mode,
            # Compartilha task_id com o pai (necessario para require_scope nos
            # nodes de saida), entao NAO pode limpar recursos indexados por ele:
            # o spill-to-disk vive em /tmp/atlans_spill/<task_id> e seria
            # apagado no fim do sub-fluxo, levando junto os dados do pai.
            is_nested=True,
        )
        child.context[_CTX_ANCESTORS_KEY] = child_ancestors
        child.context[_CTX_DISABLED_NODES_KEY] = set(inherited_disabled)
        child.context[_CTX_DEFINITIONS_KEY] = dict(inherited_defs)

        def _erro_do_filho(e: BaseException) -> RuntimeError:
            logger.error(
                "SubWorkflowNode: erro durante execucao do sub-workflow '%s': %s",
                workflow_hash, e,
            )
            # Nomear o no que quebrou. Sem isto a mensagem era só a causa crua
            # ("division by zero") — num sub-fluxo de quinze nos ela nao localiza
            # nada, e o interior do filho nao aparece no painel de execucao.
            return RuntimeError(
                f"Erro ao executar o sub-workflow '{workflow_hash}'"
                f"{_onde_falhou(child)}: {e}"
            )

        # `asyncio.timeout` e não `wait_for`: do 3.11 em diante
        # `asyncio.TimeoutError` É o TimeoutError embutido, e o de um nó do
        # filho (o prazo do PythonScript) viraria "excedeu o timeout de 300s,
        # aumente timeoutSeconds" — o conselho errado. Só é o prazo do
        # sub-fluxo se ele expirou.
        prazo = asyncio.timeout(timeout)
        try:
            async with prazo:
                result = await child.run(initial_inputs=sub_inputs)
        except asyncio.CancelledError:
            # Cancelamento do pai propaga para o filho — nao engolir.
            logger.info("SubWorkflowNode: sub-workflow '%s' cancelado.", workflow_hash)
            raise
        except TimeoutError as exc:
            if not prazo.expired():
                raise _erro_do_filho(exc) from exc
            raise RuntimeError(
                f"Sub-workflow '{workflow_hash}' excedeu o timeout de {timeout}s. "
                "Aumente 'timeoutSeconds' ou investigue por que o sub-fluxo trava."
            ) from exc
        except ValueError:
            # Erros de validacao do filho (ex: loop detectado em nivel mais profundo)
            # devem propagar sem reembrulhar.
            raise
        except Exception as e:
            raise _erro_do_filho(e) from e

        logger.info(
            "SubWorkflowNode: sub-workflow '%s' concluido. Chaves de resultado: %s",
            workflow_hash, list(result.keys()) if result else [],
        )

        # 6) Resolve outputs publicos do filho via SubWorkflowOutput.
        # O contrato foi validado em (3.6) — se nao houver
        # __subworkflow_output__ aqui, e bug do executor (node nao executou).
        from flow.executor.result_helpers import collect_subworkflow_output

        public = collect_subworkflow_output(result)
        if public is None:
            raise RuntimeError(
                f"Sub-workflow '{workflow_hash}' concluiu mas o node "
                "SubWorkflowOutput nao foi executado nesta rodada. Verifique "
                "se ele esta conectado ao grafo ativo (algum branch pode estar "
                "isolando-o do fluxo)."
            )

        logger.info(
            "SubWorkflowNode: sub-workflow '%s' expos %d chave(s) publica(s) via "
            "SubWorkflowOutput: %s",
            workflow_hash, len(public), list(public.keys()),
        )
        return {RESULTADO: public, **public}
