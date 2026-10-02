import { INodeContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useConfigNodeParams } from "@/app/hooks/workflow/useConfigNodeParams"
import { Edge, useReactFlow, useStore } from "@xyflow/react"
import { memo, useCallback, useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { createPortal } from "react-dom"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog"
import { Button } from "@/app/components/ui/button"
import NodeConfigForm from "./node-config-form"
import InputInspector from "./input-inspector"
import OutputPreview from "./output-preview"
import WebhookHelper from "../nodes-configuration/webhook-helper"
import WebhookTestTab from "../nodes-configuration/webhook-test-tab"
import DataOutputHelper from "../nodes-configuration/data-output-helper"
import PinSection from "../nodes-configuration/pin-section"
import JinjaExpressionGuide from "../nodes-configuration/jinja-expression-guide"
import { TbTerminal2, TbPlayerPlay, TbBraces } from "react-icons/tb"
import { MdClose, MdEdit } from "react-icons/md"
import { GisFlowService } from "@/service/GisFlowService"
import { NODE_ICONS } from "@/consts/WorkflowIcons"

import { TYPE_STYLES, DEFAULT_STYLE } from "@/consts/NodeTypeStyles"
import { RESERVED_ALIASES, isValidAlias } from "../utils/node-alias"

// Classes compartilhadas pelos paineis laterais (Entrada / Saida) e modal central.
// Centralizar evita drift visual entre os 3 paineis ao ajustar largura/sombra.
// Os painéis de Entrada/Saída somam 480px com o modal no meio — não cabem num
// telefone junto com nada. Somem abaixo de `lg`, onde o conjunto passaria a se
// espremer mutuamente; o modal central continua dando acesso à configuração, e
// os dados de entrada/saída continuam no painel de execução.
const SIDE_PANEL = "hidden lg:flex w-[240px] shrink-0 flex-col overflow-y-auto bg-card border border-border/60 shadow-lg pointer-events-auto h-[68vh] z-[1]"
// `max-w-[60vw]` sozinho dava 216px num telefone de 360px — mais estreito que o
// próprio card do nó. No telefone o modal ocupa a tela, descontada uma margem.
const MODAL_BOX  = "relative pointer-events-auto bg-background rounded-lg border border-border shadow-lg flex flex-col w-full max-w-[calc(100vw-1.5rem)] h-[88vh] lg:w-[600px] lg:max-w-[60vw] lg:h-[80vh] z-[2]"
// Reservados vêm de utils/node-alias, mesma lista do executor — o autocomplete
// e esta validação precisam concordar sobre o que é um alias utilizável.

/**
 * Modal de configuração de nó estilo N8N.
 * Renderizado como portal (sem overlay bloqueante) para permitir
 * drag-and-drop dos painéis laterais de Entrada/Saída.
 */
const NodeConfigModal = () => {
  const { id: workflowId } = useParams<{ id?: string }>()
  const { setNodes, getNode } = useReactFlow<INodeContext, Edge>()
  const { configNodeIdParam, removeConfigNodeParam } = useConfigNodeParams()
  // O modal é um portal SEM overlay bloqueante: o canvas continua arrastável com
  // ele aberto. Assinar `useNodes()` fazia a reconciliação abaixo (e o formulário
  // inteiro) rodar a cada pointermove. Estas duas assinaturas só mudam quando o
  // `data` do nó em edição é substituído ou quando algum nó entra/sai.
  const dadosDoNo = useStore(s => (configNodeIdParam ? s.nodeLookup.get(configNodeIdParam)?.data : undefined))
  const totalDeNos = useStore(s => s.nodeLookup.size)
  const [nodeFound, setNodeFound] = useState<INodeContext>()
  const [values, setValues] = useState<Record<string, string | number | boolean>>()
  const [showDiscardDialog, setShowDiscardDialog] = useState(false)
  const [webhookTab, setWebhookTab] = useState<"api" | "test">("api")
  const [configTab, setConfigTab] = useState<"geral" | "helper">("geral")

  const pinnedNodes = useWorkflowCatalogStore(s => s.pinnedNodes)
  const setPinnedNodes = useWorkflowCatalogStore(s => s.setPinnedNodes)

  // ── Estado do alias editável ──────────────────────────────────────────────
  const [aliasTitle, setAliasTitle] = useState<string>("")
  const [aliasError, setAliasError] = useState<string | null>(null)
  const [showGuide, setShowGuide] = useState(false)

  const nodeName = nodeFound?.data.name ?? ""
  const isWebhookTrigger = nodeName === "WebhookTrigger"
  const hasConfigTabs = isWebhookTrigger || nodeName === "DataOutput"
  const requiresCredential = !!(nodeFound?.data as { requires_credential?: boolean })?.requires_credential
  const isOpen = !!configNodeIdParam && !!nodeFound

  // Resolve nodeFound a partir do param da URL. Se a lista de nodes ja foi
  // hidratada e o id nao existe mais (ex: nó deletado), limpa o param.
  useEffect(() => {
    if (!configNodeIdParam) return
    const found = getNode(configNodeIdParam)
    if (found) {
      setNodeFound(found)
    } else if (totalDeNos > 0) {
      removeConfigNodeParam()
    }
  }, [dadosDoNo, totalDeNos, configNodeIdParam, getNode, removeConfigNodeParam])

  useEffect(() => {
    setValues(nodeFound?.data.properties)
    setConfigTab("geral")
  }, [configNodeIdParam, nodeFound])

  // Compat retroativa do nó Response: workflows antigos não têm bodyMode.
  // Deduzir uma vez ao abrir, espelhando o comportamento que o backend
  // teria para o legado (literal se customBody preenchido, senão field).
  useEffect(() => {
    if (nodeFound?.data.name !== "Response" || !values) return
    if (values.bodyMode !== undefined) return
    const cb = values.customBody
    const inferred = (typeof cb === "string" && cb.trim() !== "") ? "literal" : "field"
    setNodeField("bodyMode", inferred)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeFound?.id])

  // Sincroniza título do alias quando valores mudam
  useEffect(() => {
    setAliasTitle(
      !values || values?.alias === ""
        ? nodeFound?.data.alias ?? ""
        : String(values?.alias ?? "")
    )
    setAliasError(null)
  }, [values, nodeFound?.data.alias])

  function handleAliasBlur() {
    if (!nodeFound) return
    setNodeField("alias", aliasTitle ?? "")
  }

  function setNodeField(field: string, value: string | number | boolean) {
    if (!nodeFound) return
    const newProperties = {
      ...nodeFound.data.properties,
      ...values,
      [field]: value,
    } satisfies Record<string, string | number | boolean>
    setValues(newProperties)
  }

  function saveNodeConfig() {
    if (!nodeFound) return

    const propsChanged = JSON.stringify(nodeFound.data.properties) !== JSON.stringify(values)
    const isPinned = pinnedNodes.some(p => p.node_id === nodeFound.id && !p.expired)
    if (propsChanged && isPinned && workflowId) {
      GisFlowService.unpinNodeOutput(workflowId, nodeFound.id).then(() => {
        setPinnedNodes(pinnedNodes.filter(p => p.node_id !== nodeFound.id))
      })
    }

    // A posição vem do canvas, não da fotografia que o modal abriu com: o nó
    // pode ter sido arrastado enquanto o formulário estava aberto (não há
    // overlay bloqueante) e gravar a posição antiga o faria pular de volta.
    const noAtualizado = {
      ...nodeFound,
      position: getNode(nodeFound.id)?.position ?? nodeFound.position,
      data: {
        ...nodeFound.data,
        alias: (values?.alias as string | undefined) || nodeFound.data.alias,
        properties: values,
      },
    } as INodeContext

    // Forma funcional: aplica sobre a lista mais recente da store.
    setNodes(nds => nds.map(node => (node.id === noAtualizado.id ? noAtualizado : node)))
    setNodeFound(noAtualizado)
    removeConfigNodeParam()
  }

  function handleClosePanel() {
    const hasUnsaved = JSON.stringify(nodeFound?.data.properties) !== JSON.stringify(values)
    if (hasUnsaved) {
      setShowDiscardDialog(true)
    } else {
      removeConfigNodeParam()
    }
  }

  // Fecha ao pressionar Escape
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") handleClosePanel()
  }, [nodeFound, values]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown)
      return () => document.removeEventListener("keydown", handleKeyDown)
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen || !nodeFound) return null

  // Modal renderizado como portal — sem overlay bloqueante
  const modal = createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
      {/* Backdrop sutil — clicável para fechar, permite drag-through */}
      <div
        className="absolute inset-0 bg-black/20 pointer-events-auto"
        onClick={handleClosePanel}
      />

      {/* Wrapper dos 3 painéis. `px-3` no telefone impede o modal de encostar
          nas bordas, e `px-safe` recua do notch em paisagem. */}
      <div className="relative z-10 flex items-center pointer-events-none w-full justify-center px-3 px-safe lg:w-auto lg:px-0">

        {/* Painel esquerdo — Entrada (atrás do modal, menor) */}
        <div className={`${SIDE_PANEL} rounded-l-lg -mr-2`}>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70 px-4 pt-3 pb-1 shrink-0">
            Entrada
          </p>
          <InputInspector nodeFound={nodeFound} />
        </div>

        {/* Modal central — na frente, maior, sobrepõe as bordas dos painéis */}
        <div className={MODAL_BOX}>
        {/* Header rico com ícone e cor do tipo */}
        {(() => {
          const nodeType = nodeFound?.data.type ?? ""
          const style = TYPE_STYLES[nodeType] ?? DEFAULT_STYLE
          const IconComponent = NODE_ICONS[nodeName] ?? null
          return (
            <div className="shrink-0 border-b flex items-stretch overflow-hidden rounded-t-lg">
              {/* Stripe colorida à esquerda */}
              <div className={`w-[3px] shrink-0 ${style.stripe}`} />

              <div className="flex items-center gap-3 px-4 py-3 flex-1 min-w-0">
                {/* Ícone do nó */}
                {IconComponent && (
                  <div className={`flex items-center justify-center w-9 h-9 rounded-md shrink-0 ${style.bg}`}>
                    <IconComponent className={`text-lg ${style.icon}`} />
                  </div>
                )}

                {/* Alias + descrição */}
                <div className="flex flex-col flex-1 min-w-0">
                  <div className="group flex items-center gap-1">
                    <input
                      type="text"
                      value={aliasTitle}
                      placeholder={nodeFound?.data.alias ?? ""}
                      className={`w-full px-1 text-sm font-medium text-foreground bg-transparent border-b transition-colors outline-none ${
                        aliasError
                          ? "border-destructive"
                          : "border-transparent focus:border-primary"
                      }`}
                      onBlur={handleAliasBlur}
                      maxLength={40}
                      onChange={e => {
                        const value = e.target.value
                        if (value !== "" && RESERVED_ALIASES.has(value.toLowerCase())) {
                          setAliasTitle(value)
                          setAliasError("Nome reservado — escolha outro alias.")
                        } else if (value === "" || isValidAlias(value)) {
                          setAliasTitle(value)
                          setAliasError(null)
                        } else {
                          setAliasError("Apenas letras e numeros (usado em expressoes $Alias)")
                        }
                      }}
                    />
                    <MdEdit
                      size={14}
                      // `coarse:`: o lápis é a única pista de que o alias é
                      // editável, e sem hover ele nunca aparecia no telefone.
                      className="pointer-events-none group-hover:opacity-100 opacity-0 coarse:opacity-60 transition text-muted-foreground"
                    />
                  </div>
                  {aliasError && (
                    <p className="text-[10px] text-destructive mt-0.5 px-1">{aliasError}</p>
                  )}
                  <p className="text-xs text-muted-foreground px-1 truncate">
                    {nodeFound?.data.description}
                  </p>
                </div>
              </div>

              {/* Badge de tipo + botões */}
              <div className="flex items-center gap-1.5 px-4 shrink-0">
                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.label}`}>
                  {nodeType}
                </span>
                <TbBraces
                  onClick={() => setShowGuide(true)}
                  title="Guia de expressoes Jinja"
                  className="min-h-5 min-w-5 border rounded-sm p-0.5 hover:text-primary cursor-pointer text-muted-foreground"
                />
                <MdClose
                  onClick={handleClosePanel}
                  className="min-h-5 min-w-5 border rounded-sm p-0.5 hover:text-destructive cursor-pointer text-foreground"
                />
              </div>

              <JinjaExpressionGuide open={showGuide} onOpenChange={setShowGuide} />
            </div>
          )
        })()}

        {/* Corpo — formulário de configuração */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">

          {/* Barra de abas — apenas para nós com helper */}
          {hasConfigTabs && (
            <div className="flex gap-1 px-4 pt-3 pb-1 shrink-0 border-b">
              <button
                onClick={() => setConfigTab("geral")}
                className={`px-3 py-1 rounded text-[11px] font-medium transition-colors ${
                  configTab === "geral"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                Geral
              </button>
              <button
                onClick={() => setConfigTab("helper")}
                className={`px-3 py-1 rounded text-[11px] font-medium transition-colors ${
                  configTab === "helper"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                Helper
              </button>
            </div>
          )}

          {/* Aba "Geral" — campos de configuração */}
          {(!hasConfigTabs || configTab === "geral") && (
            <NodeConfigForm
              nodeFound={nodeFound}
              values={values}
              setNodeField={setNodeField}
              saveNodeConfig={saveNodeConfig}
              nodeName={nodeName}
              requiresCredential={requiresCredential}
              workflowId={workflowId}
            />
          )}

          {/* Aba "Helper" — DataOutput */}
          {nodeName === "DataOutput" && configTab === "helper" && (
            <div className="flex-1 overflow-y-auto">
              <DataOutputHelper label={String(values?.label ?? "")} />
            </div>
          )}

          {/* Aba "Helper" — WebhookTrigger */}
          {isWebhookTrigger && configTab === "helper" && (
            <div className="flex flex-col gap-3 px-4 pb-4 overflow-y-auto">
              <div className="flex gap-1 mt-3">
                <button
                  onClick={() => setWebhookTab("api")}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                    webhookTab === "api"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <TbTerminal2 className="h-3 w-3" />
                  API
                </button>
                <button
                  onClick={() => setWebhookTab("test")}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                    webhookTab === "test"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  <TbPlayerPlay className="h-3 w-3" />
                  Teste
                </button>
              </div>

              {webhookTab === "api" ? (
                <WebhookHelper
                  workflowId={workflowId}
                  outputKey={String(values?.payloadField ?? "")}
                  hasSecret={!!values?.credential_id}
                  payloadSchema={values?.payload_schema}
                />
              ) : (
                <WebhookTestTab
                  workflowId={workflowId}
                  outputKey={String(values?.payloadField ?? "")}
                  payloadSchema={values?.payload_schema}
                />
              )}
            </div>
          )}

          {/* Seção de Pin — sempre visível */}
          {workflowId && nodeFound && (
            <PinSection nodeId={nodeFound.id} workflowId={workflowId} />
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t flex items-center justify-between px-4 py-3">
          <div>
            {requiresCredential && !values?.credential_id && (
              <p className="text-xs text-destructive">Selecione uma credencial para continuar</p>
            )}
            {JSON.stringify(nodeFound?.data.properties) !== JSON.stringify(values) && (
              <p className="text-sm text-destructive">Há alterações não salvas!</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleClosePanel}>
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={saveNodeConfig}
              disabled={requiresCredential && !values?.credential_id}
            >
              Aplicar
            </Button>
          </div>
        </div>
        </div>{/* fim modal central */}

        {/* Painel direito — Saída (atrás do modal, menor) */}
        <div className={`${SIDE_PANEL} rounded-r-lg -ml-2`}>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70 px-4 pt-3 pb-1 shrink-0">
            Saída
          </p>
          <OutputPreview nodeFound={nodeFound} />
        </div>

      </div>{/* fim wrapper dos 3 painéis */}
    </div>,
    document.body
  )

  return (
    <>
      {modal}

      {/* Dialog de confirmação de descarte */}
      <Dialog open={showDiscardDialog} onOpenChange={setShowDiscardDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Alterações não salvas</DialogTitle>
            <DialogDescription>
              Você tem alterações que não foram aplicadas. Deseja descartá-las?
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setShowDiscardDialog(false)}>
              Continuar editando
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setShowDiscardDialog(false)
                removeConfigNodeParam()
              }}
            >
              Descartar
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

export default memo(NodeConfigModal)
