import { INodeContext } from "@/context/useFlowContext"
import { STATUS_COLOR_MAP, STATUS_LABEL } from "@/consts/NodeStatusStyles"
import { useEdges, useNodes } from "@xyflow/react"
import { TbInbox, TbCopy, TbGripVertical } from "react-icons/tb"
import { useCallback, useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { resolveNodeAlias } from "../utils/node-alias"
import { saidasDoNo } from "../utils/node-ports"

interface InputInspectorProps {
  nodeFound: INodeContext
}

/**
 * Left panel — shows the selected node's input data.
 * Output keys of the parent nodes can be dragged into form fields.
 * Dropping onto a text field inserts the Jinja expression {{ Alias.key }}.
 */
type InputTab = "campos" | "schema"

const InputInspector = ({ nodeFound }: InputInspectorProps) => {
  const edges = useEdges()
  const allNodes = useNodes<INodeContext>()
  const statusWorkflow = useWorkflowExecutionStore(s => s.statusWorkflow)
  const [tab, setTab] = useState<InputTab>("campos")

  const parentEdges = useMemo(() => edges.filter(e => e.target === nodeFound.id), [edges, nodeFound.id])

  const isPythonNode = nodeFound.data?.name === "PythonScript"

  // Ports declared by THIS node. In a node with dynamic inputs they are the ones
  // the person configured, and they are what the script variable is named after.
  const declaredPorts = ((nodeFound.data?.inputs ?? []) as { name: string }[]).map(p => p.name)

  // PERF: memoizes the parent lookup — avoids recomputing O(n) on every canvas drag
  const parentInfos = useMemo(() => {
    // Deduplicates: a parent may have multiple connected edges (e.g. output + metadata)
    const seenIds = new Set<string>()
    const parentNodeIds = parentEdges.map(e => e.source).filter(id => {
      if (seenIds.has(id)) return false
      seenIds.add(id)
      return true
    })
    return parentNodeIds.map(id => {
      const node = allNodes.find(n => n.id === id)
      const status = statusWorkflow?.nodes?.find(n => n.id === id)
      // Same rule as the executor (flow/executor/core.py::_resolve_alias), in
      // utils/node-alias — the panel generates expressions the user drags into
      // the field, so the alias here must be the one registered in the context.
      const alias = resolveNodeAlias(node?.data ?? {}) || id.slice(0, 8)
      const staticFields: string[] = saidasDoNo(node?.data).map(f => f.name)
      // All edges from this parent → which keys are actually connected
      const connectedEdges = parentEdges.filter(e => e.source === id)
      const connectedKeys = new Set<string>(
        connectedEdges.flatMap(e => {
          const fk = e.data?.from_key as string | undefined
          return fk ? [fk] : []
        })
      )
      return { id, node, status, alias, staticFields, connectedEdges, connectedKeys }
    }).filter(p => p.node !== undefined)
  }, [parentEdges, allNodes, statusWorkflow?.nodes])

  const statusColorMap = STATUS_COLOR_MAP
  const statusLabel = STATUS_LABEL

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text)
  }, [])

  // Starts a drag with the Jinja expression as text
  const handleDragStart = useCallback((e: React.DragEvent, expression: string) => {
    e.dataTransfer.setData("text/plain", expression)
    e.dataTransfer.effectAllowed = "copy"
  }, [])

  // Collects the parent node's schema for the Schema tab. Merges:
  //   - the fields declared in the catalog (name + type + description)
  //   - output_keys observed at runtime (marked "dynamic" if not declared)
  // Without the merge, the schema of a node with no declared fields stays empty
  // even if the real run delivered keys.
  const parentStaticOutputs = parentInfos.flatMap(({ alias, node, status }) => {
    const declared = saidasDoNo(node?.data).map(f => ({
      alias, name: f.name, type: f.type, description: f.description, dynamic: false,
    }))
    const declaredNames = new Set(declared.map(d => d.name))
    const runtimeOnly = (status?.output_keys ?? [])
      .filter(k => !declaredNames.has(k))
      .map(name => ({ alias, name, type: undefined, description: "Observado em runtime (não declarado no schema do nó)", dynamic: true }))
    return [...declared, ...runtimeOnly]
  })

  if (parentInfos.length === 0) {
    return (
      <div className="flex flex-col h-full gap-3 p-4">
        <div className="flex flex-col items-center justify-center gap-2 py-6 text-muted-foreground">
          <TbInbox size={28} />
          <p className="text-xs text-center">Nenhuma entrada conectada a este nó.</p>
        </div>

        {/* The ports the node DECLARES, even with nothing connected. Without this,
            whoever had just configured them had nowhere to check the names — and
            they are what become the script variables. */}
        {declaredPorts.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Entradas deste nó
            </span>
            {declaredPorts.map(porta => (
              <div key={porta} className="flex items-center gap-1.5 rounded-md border border-dashed px-2 py-1.5">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/40"
                      title="Ainda sem conexão" />
                <code className="flex-1 font-mono text-[11px] text-foreground">{porta}</code>
              </div>
            ))}
            <p className="text-[10px] leading-relaxed text-muted-foreground">
              {isPythonNode
                ? "Cada uma vira uma variável com este nome dentro do script, quando algo for ligado nela."
                : "Ligue um nó a cada uma para que este receba os dados."}
            </p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex gap-1 px-4 pt-2">
        <button
          onClick={() => setTab("campos")}
          className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
            tab === "campos" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
          }`}
        >
          Campos
        </button>
        <button
          onClick={() => setTab("schema")}
          className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
            tab === "schema" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
          }`}
        >
          Schema
        </button>
      </div>

      {/* Content of the Fields tab */}
      {tab === "campos" && (
        <div className="flex flex-col gap-3 p-4">
          {parentInfos.map(({ id, status, alias, staticFields, connectedKeys, connectedEdges }) => {
            // Combina: status real > campos declarados > connectedKeys > fallback "output"
            const keys = new Set<string>()
            if (status?.output_keys) status.output_keys.forEach(k => keys.add(k))
            if (staticFields.length > 0) staticFields.forEach(k => keys.add(k))
            connectedKeys.forEach(k => keys.add(k))
            if (keys.size === 0) keys.add("output")
            const outputKeys = Array.from(keys)

            // The arrival name follows the same rule as the executor
            // (`inputs[to_key if to_key else from_key]`). The panel used to
            // always use the PARENT's key — right while there were no named
            // ports, and a lie afterwards: it told you to use `output` when the
            // variable was called `pontos`.
            //
            // One row per EDGE, not per parent key: the same parent can feed
            // TWO different ports of this node, and then both edges carry the
            // same `from_key`. Listing by key, the second port was invisible —
            // precisely in the scenario that ports created.
            const linhas = outputKeys.flatMap(key => {
              const fromKey = connectedEdges.filter(e => (e.data?.from_key as string | undefined) === key)
              // An edge without `from_key` serves any key (the executor spreads all
              // of the parent's outputs), but its `to_key`, if any, is still the
              // arrival name.
              const withoutKey = connectedEdges.filter(e => !e.data?.from_key)
              const arestas = fromKey.length ? fromKey : withoutKey
              if (!arestas.length) return [{ key, variavel: key, linhaId: key }]
              return arestas.map(e => ({
                key,
                variavel: (e.data?.to_key as string | undefined) || key,
                linhaId: `${key}:${e.id}`,
              }))
            })

            return (
              <div key={id} className="flex flex-col gap-1.5 rounded-md border p-3 text-xs">
                {/* Header: alias + status */}
                <div className="flex items-center justify-between">
                  <span className="font-semibold truncate max-w-[160px]">{alias}</span>
                  {status && (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${statusColorMap[status.status] ?? statusColorMap.idle}`}>
                      {statusLabel[status.status] ?? status.status}
                    </span>
                  )}
                </div>

                {status?.duration !== undefined && (
                  <span className="text-muted-foreground text-[10px]">
                    {status.duration.toFixed(0)}ms
                  </span>
                )}

                {/* Schema drift warning: the backend detected a divergence between
                    the fields declared in the catalog and the node's real output. */}
                {status?.schema_drift && (status.schema_drift.missing.length > 0 || status.schema_drift.extra.length > 0) && (
                  <div className="text-[10px] text-yellow-700 bg-yellow-500/10 border border-yellow-500/30 rounded px-1.5 py-1 mt-1">
                    <span className="font-semibold">Schema divergente:</span>
                    {status.schema_drift.missing.length > 0 && (
                      <span className="ml-1">faltando {status.schema_drift.missing.join(", ")}</span>
                    )}
                    {status.schema_drift.extra.length > 0 && (
                      <span className="ml-1">extra {status.schema_drift.extra.join(", ")}</span>
                    )}
                  </div>
                )}

                {/* Output keys */}
                <div className="flex flex-col gap-1 mt-1">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Saídas</span>
                  {linhas.map(({ key, variavel, linhaId }) => {
                    // Visibility rule:
                    // - connectedKeys.size > 0 → edge with an explicit from_key: only
                    //   the connected key is marked as "wired" (green dot + draggable).
                    // - connectedKeys.size === 0 → edge without from_key (auto-connect
                    //   of a node with no declared fields): the executor spreads all
                    //   of the parent's outputs into the namespace, so every key is
                    //   accessible — isWired = true for all avoids false negatives.
                    // - A key observed at runtime via status.output_keys also counts
                    //   as wired: the executor delivered that data even if the edge
                    //   has a specific from_key on another key (dynamic spreading).
                    const isWired = (
                      connectedKeys.size === 0 ||
                      connectedKeys.has(key) ||
                      (status?.output_keys?.includes(key) ?? false)
                    )
                    // For the Python Script what you type is the VARIABLE, so
                    // it must be the arrival name. For the others the Jinja
                    // expression navigates the parent's output, and the key is the
                    // parent's.
                    const expression = isPythonNode ? variavel : `{{ ${alias}.${key} }}`
                    return (
                      <div
                        key={linhaId}
                        draggable={isWired}
                        onDragStart={isWired ? (e) => handleDragStart(e, expression) : undefined}
                        title={isWired ? undefined : "Não conectado — adicione uma edge para usar esta chave"}
                        className={cn(
                          "flex items-center gap-1 group rounded px-1.5 py-1 transition-colors",
                          isWired
                            ? "cursor-grab active:cursor-grabbing hover:bg-muted"
                            : "opacity-40 cursor-default"
                        )}
                      >
                        {isWired
                          ? <TbGripVertical className="h-3 w-3 shrink-0 text-muted-foreground/50 group-hover:text-muted-foreground" />
                          : <span className="h-3 w-3 shrink-0" />
                        }
                        <code className="flex-1 text-[11px] font-mono text-foreground">
                          {key}
                          {variavel !== key && (
                            // The port is the name that matters to whoever writes the
                            // script; the parent's key stays as provenance.
                            <span className="ml-1 text-muted-foreground">
                              &rarr; <span className="text-foreground">{variavel}</span>
                            </span>
                          )}
                        </code>
                        {isWired && (
                          <>
                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" title="Conectado" />
                            <button
                              onClick={() => copyToClipboard(expression)}
                              // `coarse:`: without hover the copy-expression button
                              // simply didn't exist on a phone.
                              className="opacity-0 coarse:opacity-70 group-hover:opacity-100 transition-opacity ml-1"
                              title={`Copiar: ${expression}`}
                            >
                              <TbCopy className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                            </button>
                          </>
                        )}
                      </div>
                    )
                  })}
                </div>

                {status?.error && (
                  <p className="text-destructive break-all text-[10px] mt-1">{status.error}</p>
                )}
              </div>
            )
          })}

          {(() => {
            const ligadas = new Set(
              parentEdges.map(e => (e.data?.to_key as string | undefined)).filter(Boolean) as string[],
            )
            const pendentes = declaredPorts.filter(p => !ligadas.has(p))
            if (!pendentes.length) return null
            // With one port connected and another not, the parent list shows only
            // the first — and the missing one was invisible precisely to whoever
            // still needs to connect it.
            return (
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                  Aguardando conexão
                </span>
                {pendentes.map(porta => (
                  <div key={porta} className="flex items-center gap-1.5 rounded-md border border-dashed px-2 py-1.5">
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/40" />
                    <code className="flex-1 font-mono text-[11px] text-muted-foreground">{porta}</code>
                  </div>
                ))}
              </div>
            )
          })()}

          <p className="text-[10px] text-muted-foreground mt-2">
            {isPythonNode
              ? <>Arraste ou clique em <TbCopy className="inline h-3 w-3" /> para copiar o nome da variável Python.</>
              : <>Arraste uma saída para um campo ou clique em <TbCopy className="inline h-3 w-3" /> para copiar a expressão Jinja.</>
            }
          </p>
        </div>
      )}

      {/* Content of the Schema tab — static fields of the parent nodes */}
      {tab === "schema" && (
        <div className="flex flex-col gap-2 p-4">
          {parentStaticOutputs.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">
              Nenhum campo estático declarado nos nós de entrada.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {parentStaticOutputs.map((field, i) => (
                <div key={`${field.alias}-${field.name}-${i}`} className="flex flex-col gap-0.5 rounded-md border p-2.5 text-xs">
                  <span className="text-[10px] text-muted-foreground/70 font-medium truncate">{field.alias}</span>
                  <div className="flex items-center gap-2">
                    <code className="px-1 py-0.5 rounded bg-muted text-foreground text-[11px] font-mono">{field.name}</code>
                    {field.type && (
                      <span className="text-muted-foreground text-[10px]">{field.type}</span>
                    )}
                    {field.dynamic && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-yellow-500/10 text-yellow-600 border border-yellow-500/30">
                        runtime
                      </span>
                    )}
                  </div>
                  {field.description && (
                    <p className="text-muted-foreground text-[10px] mt-0.5">{field.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default InputInspector
