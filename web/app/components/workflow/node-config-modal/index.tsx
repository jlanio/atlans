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

// Classes shared by the side panels (Input / Output) and the central modal.
// Centralizing them avoids visual drift among the 3 panels when adjusting width/shadow.
// The Input/Output panels add up to 480px with the modal in the middle — they
// don't fit on a phone alongside anything. They are hidden below `lg`, where the
// set would start squeezing each other; the central modal still gives access to
// the configuration, and the input/output data is still in the run panel.
const SIDE_PANEL = "hidden lg:flex w-[240px] shrink-0 flex-col overflow-y-auto bg-card border border-border/60 shadow-lg pointer-events-auto h-[68vh] z-[1]"
// `max-w-[60vw]` alone gave 216px on a 360px phone — narrower than the node
// card itself. On a phone the modal takes the screen, minus a margin.
const MODAL_BOX  = "relative pointer-events-auto bg-background rounded-lg border border-border shadow-lg flex flex-col w-full max-w-[calc(100vw-1.5rem)] h-[88vh] lg:w-[600px] lg:max-w-[60vw] lg:h-[80vh] z-[2]"
// Reserved names come from utils/node-alias, the same list as the executor — the
// autocomplete and this validation must agree on what a usable alias is.

/**
 * N8N-style node configuration modal.
 * Rendered as a portal (no blocking overlay) to allow
 * drag-and-drop from the Input/Output side panels.
 */
const NodeConfigModal = () => {
  const { id: workflowId } = useParams<{ id?: string }>()
  const { setNodes, getNode } = useReactFlow<INodeContext, Edge>()
  const { configNodeIdParam, removeConfigNodeParam } = useConfigNodeParams()
  // The modal is a portal WITHOUT a blocking overlay: the canvas stays draggable
  // while it is open. Subscribing to `useNodes()` made the reconciliation below
  // (and the whole form) run on every pointermove. These two subscriptions only
  // change when the `data` of the node being edited is replaced or when some
  // node enters/leaves.
  const nodeData = useStore(s => (configNodeIdParam ? s.nodeLookup.get(configNodeIdParam)?.data : undefined))
  const totalNodes = useStore(s => s.nodeLookup.size)
  const [nodeFound, setNodeFound] = useState<INodeContext>()
  const [values, setValues] = useState<Record<string, string | number | boolean>>()
  const [showDiscardDialog, setShowDiscardDialog] = useState(false)
  const [webhookTab, setWebhookTab] = useState<"api" | "test">("api")
  const [configTab, setConfigTab] = useState<"geral" | "helper">("geral")

  const pinnedNodes = useWorkflowCatalogStore(s => s.pinnedNodes)
  const setPinnedNodes = useWorkflowCatalogStore(s => s.setPinnedNodes)

  // ── Editable alias state ──────────────────────────────────────────────────
  const [aliasTitle, setAliasTitle] = useState<string>("")
  const [aliasError, setAliasError] = useState<string | null>(null)
  const [showGuide, setShowGuide] = useState(false)

  const nodeName = nodeFound?.data.name ?? ""
  const isWebhookTrigger = nodeName === "WebhookTrigger"
  const hasConfigTabs = isWebhookTrigger || nodeName === "DataOutput"
  const requiresCredential = !!(nodeFound?.data as { requires_credential?: boolean })?.requires_credential
  const isOpen = !!configNodeIdParam && !!nodeFound

  // Resolves nodeFound from the URL param. If the node list has already been
  // hydrated and the id no longer exists (e.g. deleted node), clears the param.
  useEffect(() => {
    if (!configNodeIdParam) return
    const found = getNode(configNodeIdParam)
    if (found) {
      setNodeFound(found)
    } else if (totalNodes > 0) {
      removeConfigNodeParam()
    }
  }, [nodeData, totalNodes, configNodeIdParam, getNode, removeConfigNodeParam])

  useEffect(() => {
    setValues(nodeFound?.data.properties)
    setConfigTab("geral")
  }, [configNodeIdParam, nodeFound])

  // Backward compat for the Response node: old workflows have no bodyMode.
  // Deduce it once on open, mirroring the behavior the backend would have
  // for legacy (literal if customBody is filled, otherwise field).
  useEffect(() => {
    if (nodeFound?.data.name !== "Response" || !values) return
    if (values.bodyMode !== undefined) return
    const cb = values.customBody
    const inferred = (typeof cb === "string" && cb.trim() !== "") ? "literal" : "field"
    setNodeField("bodyMode", inferred)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeFound?.id])

  // Syncs the alias title when values change
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

    // The position comes from the canvas, not from the snapshot the modal opened
    // with: the node may have been dragged while the form was open (there is no
    // blocking overlay) and writing the old position would make it jump back.
    const updatedNode = {
      ...nodeFound,
      position: getNode(nodeFound.id)?.position ?? nodeFound.position,
      data: {
        ...nodeFound.data,
        alias: (values?.alias as string | undefined) || nodeFound.data.alias,
        properties: values,
      },
    } as INodeContext

    // Functional form: applies on top of the store's latest list.
    setNodes(nds => nds.map(node => (node.id === updatedNode.id ? updatedNode : node)))
    setNodeFound(updatedNode)
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

  // Closes when Escape is pressed
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

  // Modal rendered as a portal — no blocking overlay
  const modal = createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
      {/* Subtle backdrop — clickable to close, allows drag-through */}
      <div
        className="absolute inset-0 bg-black/20 pointer-events-auto"
        onClick={handleClosePanel}
      />

      {/* Wrapper of the 3 panels. `px-3` on a phone keeps the modal from touching
          the edges, and `px-safe` backs off from the notch in landscape. */}
      <div className="relative z-10 flex items-center pointer-events-none w-full justify-center px-3 px-safe lg:w-auto lg:px-0">

        {/* Left panel — Input (behind the modal, smaller) */}
        <div className={`${SIDE_PANEL} rounded-l-lg -mr-2`}>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70 px-4 pt-3 pb-1 shrink-0">
            Entrada
          </p>
          <InputInspector nodeFound={nodeFound} />
        </div>

        {/* Central modal — in front, larger, overlaps the panels' edges */}
        <div className={MODAL_BOX}>
        {/* Rich header with the type's icon and color */}
        {(() => {
          const nodeType = nodeFound?.data.type ?? ""
          const style = TYPE_STYLES[nodeType] ?? DEFAULT_STYLE
          const IconComponent = NODE_ICONS[nodeName] ?? null
          return (
            <div className="shrink-0 border-b flex items-stretch overflow-hidden rounded-t-lg">
              {/* Colored stripe on the left */}
              <div className={`w-[3px] shrink-0 ${style.stripe}`} />

              <div className="flex items-center gap-3 px-4 py-3 flex-1 min-w-0">
                {/* Node icon */}
                {IconComponent && (
                  <div className={`flex items-center justify-center w-9 h-9 rounded-md shrink-0 ${style.bg}`}>
                    <IconComponent className={`text-lg ${style.icon}`} />
                  </div>
                )}

                {/* Alias + description */}
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
                      // `coarse:`: the pencil is the only cue that the alias is
                      // editable, and without hover it never showed up on a phone.
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

              {/* Type badge + buttons */}
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

        {/* Body — configuration form */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">

          {/* Tab bar — only for nodes with a helper */}
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

          {/* "Geral" (General) tab — configuration fields */}
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

          {/* Tab "Helper" — DataOutput */}
          {nodeName === "DataOutput" && configTab === "helper" && (
            <div className="flex-1 overflow-y-auto">
              <DataOutputHelper label={String(values?.label ?? "")} />
            </div>
          )}

          {/* Tab "Helper" — WebhookTrigger */}
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

          {/* Pin section — always visible */}
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

        {/* Right panel — Output (behind the modal, smaller) */}
        <div className={`${SIDE_PANEL} rounded-r-lg -ml-2`}>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70 px-4 pt-3 pb-1 shrink-0">
            Saída
          </p>
          <OutputPreview nodeFound={nodeFound} />
        </div>

      </div>{/* end of the 3-panel wrapper */}
    </div>,
    document.body
  )

  return (
    <>
      {modal}

      {/* Discard confirmation dialog */}
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
