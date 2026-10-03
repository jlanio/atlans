"use client"

/**
 * SubWorkflowHelper — configuration of the SubWorkflow node.
 *
 * Replaces the raw inputsMapping JsonEditor with:
 *   1. A combo of the workspace's active workflows (with search)
 *   2. A preview of the target workflow's contract (SubWorkflowInput / SubWorkflowOutput)
 *   3. A mapping table: each input expected by the child → pick, in a
 *      dropdown, one of the keys that actually arrive at this node (derived from
 *      the incoming edges). It used to be free text: getting the name wrong gave
 *      no error, it gave a silent absence at runtime.
 *   4. An "inativo" (inactive) badge if the target is deactivated
 *
 * Replaces what used to be 3 raw JSON fields.
 */
import { useEffect, useMemo, useState } from "react"
import { useReactFlow } from "@xyflow/react"
import { useParams } from "next/navigation"
import { Label } from "@/app/components/ui/label"
import { Input } from "@/app/components/ui/input"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"
import { TbAlertTriangle, TbRefresh } from "react-icons/tb"
import { SeloAssistente } from "@/app/components/shared/selo-assistente"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflowContract } from "@/service/types"


interface Props {
  values: Record<string, string | number | boolean> | undefined
  setNodeField: (field: string, value: string | number | boolean) => void
  hasUnsaved: boolean
  /** This node's id on the canvas — used to find the keys that arrive at it. */
  nodeId?: string
}

/** A key available at the point of the graph where this SubWorkflow sits. */
interface AvailableKey {
  key: string
  fromLabel: string
}

/**
 * Derives the keys that actually arrive at this node, from the incoming
 * edges — the same rule as the executor (flow/executor/core.py):
 *   from_key + to_key -> to_key
 *   from_key only     -> from_key
 *   to_key only       -> to_key
 *   neither           -> spreads the previous node's outputs (not enumerable here)
 *
 * The operator used to type that name from memory; getting it wrong gave no
 * error, it gave a silent absence (the executor only emits a warning and goes
 * on without the data).
 */
function useAvailableInputKeys(nodeId?: string): {
  keys: AvailableKey[]
  hasUnnamedEdge: boolean
} {
  const { getEdges, getNodes } = useReactFlow()

  return useMemo(() => {
    if (!nodeId) return { keys: [], hasUnnamedEdge: false }

    const nodes = getNodes()
    const labelOf = (id: string) => {
      const n = nodes.find((x) => x.id === id)
      const data = (n?.data ?? {}) as { alias?: string; name?: string }
      return data.alias || data.name || id
    }

    const found = new Map<string, string>()
    let unnamed = false

    for (const edge of getEdges()) {
      if (edge.target !== nodeId) continue
      const data = (edge.data ?? {}) as { from_key?: string; to_key?: string }
      const key = data.to_key || data.from_key
      if (key) {
        if (!found.has(key)) found.set(key, labelOf(edge.source))
      } else {
        // An edge without a key spreads all of the previous node's outputs: the names
        // depend on the catalog and aren't known here.
        unnamed = true
      }
    }

    return {
      keys: [...found].map(([key, fromLabel]) => ({ key, fromLabel })),
      hasUnnamedEdge: unnamed,
    }
  }, [nodeId, getEdges, getNodes])
}

/** Radix doesn't accept a SelectItem with an empty value — sentinel for "don't map". */
const _NONE = "__none__"

interface WorkflowListItem {
  id_hash: string
  name: string
  workspace_id?: string | null
  flag_ative?: boolean
  /** "usuario" | "assistente" — who created the workflow (marks the option with the sparkle). */
  origem?: string | null
}


export default function SubWorkflowHelper({ values, setNodeField, nodeId }: Props) {
  const { keys: availableKeys, hasUnnamedEdge } = useAvailableInputKeys(nodeId)
  const { id: currentWorkflowId } = useParams<{ id?: string }>()

  // ── State ───────────────────────────────────────────────────────────────
  const workflowHash = String(values?.workflowHash ?? "").trim()
  const timeoutSeconds = Number(values?.timeoutSeconds ?? 300)

  const inputsMapping: Record<string, string> = useMemo(() => {
    const raw = values?.inputsMapping
    if (typeof raw === "string") {
      try {
        const parsed = JSON.parse(raw)
        return typeof parsed === "object" && parsed !== null ? parsed : {}
      } catch {
        return {}
      }
    }
    if (typeof raw === "object" && raw !== null) return raw as Record<string, string>
    return {}
  }, [values?.inputsMapping])

  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([])
  const [contract, setContract] = useState<IWorkflowContract | null>(null)
  const [loadingContract, setLoadingContract] = useState(false)
  const [contractError, setContractError] = useState<string | null>(null)
  // Nonce incremented by the "Recarregar contrato" (reload contract) button to
  // force a refetch even with an unchanged workflowHash.
  const [reloadNonce, setReloadNonce] = useState(0)

  // ── Loads the workflow list ─────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false
    // Including the assistant's: they are complete workflows and can be called as
    // a sub-workflow like any other; hiding them here was arbitrary.
    GisFlowService.getWorkflows(undefined, { incluirDoAssistente: true }).then((res) => {
      if (cancelled || res?.error || !res?.data) return
      const list = (res.data as unknown as WorkflowListItem[])
        .filter((w) => w.id_hash !== currentWorkflowId) // don't list self
        .sort((a, b) => a.name.localeCompare(b.name))
      setWorkflows(list)
    })
    return () => { cancelled = true }
  }, [currentWorkflowId])

  // ── Loads the selected workflow's contract ──────────────────────────────
  useEffect(() => {
    if (!workflowHash) {
      setContract(null)
      setContractError(null)
      return
    }
    let cancelled = false
    setLoadingContract(true)
    setContractError(null)
    GisFlowService.getWorkflowContract(workflowHash).then((res) => {
      if (cancelled) return
      setLoadingContract(false)
      if (res?.error) {
        setContractError(res.error.message ?? "Erro ao carregar contrato.")
        setContract(null)
        return
      }
      setContract(res.data ?? null)
    })
    return () => { cancelled = true }
  }, [workflowHash, reloadNonce])

  // ── Helpers ─────────────────────────────────────────────────────────────
  const declaredInputs = contract?.inputs ?? []
  const declaredOutputs = contract?.outputs ?? []

  function updateMapping(childKey: string, parentKey: string) {
    const next = { ...inputsMapping }
    if (parentKey === "" || parentKey === "__none__") {
      delete next[childKey]
    } else {
      next[childKey] = parentKey
    }
    setNodeField("inputsMapping", JSON.stringify(next))
  }

  const targetWorkflow = workflows.find((w) => w.id_hash === workflowHash)
  const isTargetInactive = contract && contract.is_active === false
  // Only the output is required: SubWorkflowOutput defines the return value.
  // SubWorkflowInput is optional — a sub-workflow may receive nothing.
  const missingContract = contract && !contract.has_output_node
  // Mapping inputs to a child without an entry point would have no effect at runtime.
  const mappingWithoutEntryPoint =
    contract && contract.has_output_node && !contract.has_input_node &&
    Object.keys(inputsMapping).length > 0

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-5">
      {/* 1. Target workflow selection */}
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs">Workflow alvo</Label>
        <Select
          value={workflowHash || "__none__"}
          onValueChange={(v) => setNodeField("workflowHash", v === "__none__" ? "" : v)}
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Selecione um workflow" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">— Nenhum —</SelectItem>
            {workflows.map((w) => (
              <SelectItem key={w.id_hash} value={w.id_hash}>
                <span className="flex min-w-0 items-center gap-1.5">
                  <SeloAssistente origem={w.origem} compacto />
                  <span className="truncate">{w.name}</span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {workflowHash && !targetWorkflow && (
          <p className="text-[10px] text-muted-foreground italic">
            Hash: <code>{workflowHash}</code> (fora do workspace ou já apagado)
          </p>
        )}
      </div>

      {/* 2. Contract status */}
      {workflowHash && (
        <div className="rounded-md border border-border bg-muted/30 p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium">Contrato do alvo</Label>
            {loadingContract && (
              <TbRefresh className="text-xs animate-spin text-muted-foreground" />
            )}
          </div>

          {contractError && (
            <div className="text-xs text-destructive flex items-start gap-1.5">
              <TbAlertTriangle className="shrink-0 mt-0.5" />
              {contractError}
            </div>
          )}

          {isTargetInactive && (
            <Badge variant="secondary" className="self-start text-[10px] bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20">
              Desativado
            </Badge>
          )}

          {missingContract && (
            <div className="text-xs text-amber-700 dark:text-amber-300 flex items-start gap-1.5">
              <TbAlertTriangle className="shrink-0 mt-0.5" />
              Falta o node <strong className="mx-1">SubWorkflowOutput</strong> no workflow
              alvo — sem ele não há saída para consumir. Edite-o e adicione o node.
            </div>
          )}

          {mappingWithoutEntryPoint && (
            <div className="text-xs text-amber-700 dark:text-amber-300 flex items-start gap-1.5">
              <TbAlertTriangle className="shrink-0 mt-0.5" />
              O workflow alvo não tem <strong className="mx-1">SubWorkflowInput</strong>:
              as entradas mapeadas não chegariam ao sub-fluxo.
            </div>
          )}

          {contract && !missingContract && (
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <div className="text-muted-foreground mb-1">Inputs ({declaredInputs.length})</div>
                {declaredInputs.length === 0 ? (
                  <div className="text-muted-foreground italic">— vazio —</div>
                ) : (
                  <ul className="flex flex-wrap gap-1">
                    {declaredInputs.map((p) => (
                      <Badge key={p.name} variant="outline" className="text-[10px]">{p.name}</Badge>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <div className="text-muted-foreground mb-1">Outputs ({declaredOutputs.length})</div>
                {declaredOutputs.length === 0 ? (
                  <div className="text-muted-foreground italic">— vazio —</div>
                ) : (
                  <ul className="flex flex-wrap gap-1">
                    {declaredOutputs.map((p) => (
                      <Badge key={p.name} variant="outline" className="text-[10px]">{p.name}</Badge>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3. Sub-workflow without declared ports: passthrough mode.
          With the opt-in contract, empty `ports` is valid — the child receives
          all the keys that arrive at this node. The table below only lists
          declared ports, so without this explanation the operator saw
          "Inputs (0)" and no way to configure anything, without knowing it was
          already working. */}
      {workflowHash && contract && !missingContract && declaredInputs.length === 0 && (
        <div className="flex flex-col gap-2">
          <Label className="text-xs">Mapeamento de entradas</Label>
          <div className="rounded-md border border-border bg-muted/30 p-2.5 text-[11px] text-muted-foreground">
            {contract.has_input_node ? (
              <>
                O sub-fluxo <strong className="text-foreground">não declara portas de entrada</strong>,
                então recebe <strong className="text-foreground">todas as chaves</strong> que chegam
                neste node ({availableKeys.length > 0
                  ? availableKeys.map((k) => k.key).join(", ")
                  : "nenhuma no momento"}).
                {" "}Para fixar a interface, declare portas no node{" "}
                <em>Entrada do Sub-Workflow</em> dentro do workflow alvo.
              </>
            ) : (
              <>
                O sub-fluxo <strong className="text-foreground">não recebe entradas</strong> —
                não há node <em>Entrada do Sub-Workflow</em> no workflow alvo.
              </>
            )}
          </div>
        </div>
      )}

      {/* 4. Mapping table (declared ports) */}
      {workflowHash && declaredInputs.length > 0 && (
        <div className="flex flex-col gap-2">
          <Label className="text-xs">Mapeamento de entradas</Label>
          <p className="text-[11px] text-muted-foreground">
            Para cada entrada esperada pelo sub-fluxo, escolha a chave que chega
            neste ponto do fluxo. Deixe em &quot;não mapear&quot; para não enviar.
          </p>
          {availableKeys.length === 0 && !hasUnnamedEdge && (
            <p className="text-[11px] text-amber-600 dark:text-amber-400">
              Nenhuma conexão chega neste node — ligue a saída de um node anterior
              para ter chaves disponíveis.
            </p>
          )}
          {hasUnnamedEdge && (
            <p className="text-[11px] text-muted-foreground">
              Há conexão sem chave nomeada: ela repassa todas as saídas do node
              anterior, cujos nomes não aparecem na lista.
            </p>
          )}
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-muted/40">
                <tr>
                  <th className="text-left px-2 py-1.5 font-medium text-muted-foreground">Chave no sub-fluxo</th>
                  <th className="text-left px-2 py-1.5 font-medium text-muted-foreground">Chave do input atual</th>
                </tr>
              </thead>
              <tbody>
                {declaredInputs.map((p) => {
                  const current = inputsMapping[p.name] ?? ""
                  // Mapped to a key that doesn't arrive at this point of the graph.
                  // At runtime the node FAILS saying which keys were missing —
                  // before, it went on silently and the child received null.
                  const isOrphan =
                    current !== "" &&
                    !availableKeys.some((k) => k.key === current) &&
                    !hasUnnamedEdge
                  return (
                    <tr key={p.name} className="border-t border-border">
                      <td className="px-2 py-1.5 font-medium align-top pt-2.5">{p.name}</td>
                      <td className="px-2 py-1.5">
                        <Select
                          value={current === "" ? _NONE : current}
                          onValueChange={(v) => updateMapping(p.name, v === _NONE ? "" : v)}
                        >
                          <SelectTrigger
                            className={`h-7 text-xs ${isOrphan ? "border-destructive" : ""}`}
                          >
                            <SelectValue placeholder="(não mapear)" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={_NONE} className="text-xs">
                              (não mapear)
                            </SelectItem>
                            {availableKeys.map((k) => (
                              <SelectItem key={k.key} value={k.key} className="text-xs">
                                <span className="font-mono">{k.key}</span>
                                <span className="text-muted-foreground ml-2">← {k.fromLabel}</span>
                              </SelectItem>
                            ))}
                            {/* Keeps the current value selectable even if the edge
                                that produced it has been removed. */}
                            {isOrphan && (
                              <SelectItem value={current} className="text-xs">
                                <span className="font-mono">{current}</span>
                                <span className="text-destructive ml-2">← não chega mais</span>
                              </SelectItem>
                            )}
                          </SelectContent>
                        </Select>
                        {isOrphan && (
                          <p className="text-[10px] text-destructive mt-0.5">
                            Nenhuma conexão entrega esta chave — a execução vai falhar aqui.
                          </p>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-muted-foreground italic">
            Chaves não mapeadas chegam ao filho como undefined (filho deve ter default).
          </p>
        </div>
      )}

      {/* 4. Timeout */}
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs">Timeout (segundos)</Label>
        <Input
          type="number"
          min={1}
          value={timeoutSeconds}
          onChange={(e) => setNodeField("timeoutSeconds", Math.max(1, Number(e.target.value) || 1))}
          className="h-9"
        />
        <p className="text-[10px] text-muted-foreground italic">
          Se o sub-fluxo demorar mais que isso, é cancelado e o node falha.
        </p>
      </div>

      {/* 5. Aviso geral */}
      {!workflowHash && (
        <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2.5 text-xs flex items-start gap-2">
          <TbAlertTriangle className="text-amber-500 shrink-0 mt-0.5" />
          Selecione um workflow alvo para configurar este SubWorkflow.
        </div>
      )}

      {/* Contract refetch button */}
      {workflowHash && (
        <Button
          variant="ghost"
          size="sm"
          className="self-end text-[10px] h-6"
          disabled={loadingContract}
          onClick={() => setReloadNonce((n) => n + 1)}
        >
          <TbRefresh className={`mr-1 ${loadingContract ? "animate-spin" : ""}`} />
          Recarregar contrato
        </Button>
      )}
    </div>
  )
}
