import { INodeContext } from "@/context/useFlowContext"
import { STATUS_COLOR_MAP, STATUS_LABEL } from "@/consts/NodeStatusStyles"
import { useEdges, useNodes, type Edge } from "@xyflow/react"
import { useParams } from "next/navigation"
import { TbInbox, TbCopy, TbGripVertical } from "react-icons/tb"
import { useEffect, useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { useNodeSamplesStore, type AmostraRegistrada } from "@/app/stores/nodeSamplesStore"
import { resolveNodeAlias } from "../utils/node-alias"
import { saidasDoNo } from "../utils/node-ports"
import {
  AbasDeChave, FilhosDaChave, SeletorDeVisao, SeloAnterior, SemAmostra, VisaoDaSaida,
  copiar, iniciarArrasto, useVisaoLembrada,
} from "./data-view"

interface InputInspectorProps {
  nodeFound: INodeContext
}

const SEM_AMOSTRAS: Record<string, AmostraRegistrada> = {}

/** A node whose data this node can read: a direct parent (wired by an edge) or
 *  any earlier node (reachable in an expression, `{{ Alias.key }}`). */
interface Fonte {
  id: string
  node: INodeContext
  alias: string
  direto: boolean
  /** Edges from this source into the node (empty for an earlier, unwired node). */
  connectedEdges: Edge[]
  /** Keys wired by an explicit `from_key`. */
  connectedKeys: Set<string>
  staticFields: { name: string; type?: string; description?: string }[]
}

/** Every ancestor of `nodeId` that is not a direct parent, nearest first. */
function ancestraisIndiretos(nodeId: string, edges: Edge[], diretos: Set<string>): string[] {
  const porAlvo = new Map<string, string[]>()
  for (const e of edges) {
    const lista = porAlvo.get(e.target)
    if (lista) lista.push(e.source)
    else porAlvo.set(e.target, [e.source])
  }
  const vistos = new Set<string>([nodeId, ...diretos])
  const fila = [...diretos]
  const ordem: string[] = []
  let i = 0
  while (i < fila.length) {
    const atual = fila[i++]
    for (const pai of porAlvo.get(atual) ?? []) {
      if (vistos.has(pai)) continue
      vistos.add(pai)
      ordem.push(pai)
      fila.push(pai)
    }
  }
  return ordem
}

/**
 * Left panel — the data this node can read (docs/specs/node-data-panels.md §6.3).
 *
 * A source picker (direct parents first, then every earlier node), and the
 * source's outputs in three views: Schema (keys, their columns and an example
 * value), Tabela and JSON (the sample of the last run started from the editor).
 * Keys and columns can be dragged into form fields: a key inserts
 * `{{ Alias.key }}` (or the variable name in the Python Script), a column its name.
 */
const InputInspector = ({ nodeFound }: InputInspectorProps) => {
  const workflowId = useParams<{ id?: string }>()?.id
  const edges = useEdges()
  const allNodes = useNodes<INodeContext>()
  const statusWorkflow = useWorkflowExecutionStore(s => s.statusWorkflow)
  const amostras = useNodeSamplesStore(s => (workflowId && s.workflowId === workflowId ? s.byNode : SEM_AMOSTRAS))
  const desligado = useNodeSamplesStore(s => !!workflowId && s.workflowId === workflowId && s.disabledByAdmin)

  const parentEdges = useMemo(() => edges.filter(e => e.target === nodeFound.id), [edges, nodeFound.id])

  const isPythonNode = nodeFound.data?.name === "PythonScript"

  // Ports declared by THIS node. In a node with dynamic inputs they are the ones
  // the person configured, and they are what the script variable is named after.
  const declaredPorts = ((nodeFound.data?.inputs ?? []) as { name: string }[]).map(p => p.name)

  // PERF: memoized — avoids recomputing O(n) on every canvas drag.
  const fontes = useMemo<Fonte[]>(() => {
    const porId = new Map(allNodes.map(n => [n.id, n]))
    const montar = (id: string, direto: boolean): Fonte | null => {
      const node = porId.get(id)
      if (!node) return null
      const connectedEdges = parentEdges.filter(e => e.source === id)
      return {
        id,
        node,
        direto,
        // Same rule as the executor (flow/core/aliases.py) — the panel generates
        // expressions, so the alias must be the one registered in the context.
        alias: resolveNodeAlias(node.data ?? {}) || id.slice(0, 8),
        connectedEdges,
        connectedKeys: new Set(connectedEdges.flatMap(e => {
          const fk = e.data?.from_key as string | undefined
          return fk ? [fk] : []
        })),
        staticFields: saidasDoNo(node.data),
      }
    }
    // A parent may have several edges into this node (output + metadata): once.
    const diretos = [...new Set(parentEdges.map(e => e.source))]
    const indiretos = ancestraisIndiretos(nodeFound.id, edges, new Set(diretos))
    return [
      ...diretos.map(id => montar(id, true)),
      ...indiretos.map(id => montar(id, false)),
    ].filter((f): f is Fonte => f !== null)
  }, [parentEdges, edges, allNodes, nodeFound.id])

  const [fonteId, setFonteId] = useState<string | null>(null)
  const fonte = fontes.find(f => f.id === fonteId) ?? fontes[0]
  const status = fonte ? statusWorkflow?.nodes?.find(n => n.id === fonte.id) : undefined
  const registro = fonte ? amostras[fonte.id] : undefined
  const [visao, setVisao] = useVisaoLembrada("entradas", !!registro)

  // Keys of the source: real run > sample > declared > wired > "output" fallback.
  const chaves = useMemo(() => {
    if (!fonte) return []
    const keys = new Set<string>()
    status?.output_keys?.forEach(k => keys.add(k))
    Object.keys(registro?.sample.outputs ?? {}).forEach(k => keys.add(k))
    fonte.staticFields.forEach(f => keys.add(f.name))
    fonte.connectedKeys.forEach(k => keys.add(k))
    if (keys.size === 0) keys.add("output")
    return [...keys]
  }, [fonte, status?.output_keys, registro])

  const [chave, setChave] = useState<string | null>(null)
  const chaveAtual = chave && chaves.includes(chave) ? chave : (chaves.find(k => registro?.sample.outputs[k]) ?? chaves[0])
  useEffect(() => { setChave(null) }, [fonte?.id])

  if (fontes.length === 0) {
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

  const { alias, connectedEdges, connectedKeys, direto } = fonte
  const motivoVazio = desligado ? "desligado" : (statusWorkflow || registro) ? "sem-amostra" : "nao-executado"

  // The arrival name follows the same rule as the executor
  // (`inputs[to_key if to_key else from_key]`). One row per EDGE, not per parent
  // key: the same parent can feed TWO ports of this node with the same `from_key`.
  const linhas = chaves.flatMap(key => {
    const fromKey = connectedEdges.filter(e => (e.data?.from_key as string | undefined) === key)
    // An edge without `from_key` serves any key (the executor spreads all of the
    // parent's outputs), but its `to_key`, if any, is still the arrival name.
    const withoutKey = connectedEdges.filter(e => !e.data?.from_key)
    const arestas = fromKey.length ? fromKey : withoutKey
    if (!arestas.length) return [{ key, variavel: key, linhaId: key }]
    return arestas.map(e => ({
      key,
      variavel: (e.data?.to_key as string | undefined) || key,
      linhaId: `${key}:${e.id}`,
    }))
  })

  // Visibility rule:
  // - an earlier node that is not wired: its outputs are in the expression context
  //   (`{{ Alias.key }}`), but not a Python Script variable — only edges make those;
  // - connectedKeys empty → edge without from_key: the executor spreads every key;
  // - a key observed at runtime also counts as wired (dynamic spreading).
  const ligada = (key: string) => {
    if (!direto) return !isPythonNode
    return connectedKeys.size === 0 || connectedKeys.has(key) || (status?.output_keys?.includes(key) ?? false)
  }
  // For the Python Script what you type is the VARIABLE (the arrival name); for
  // the others the Jinja expression navigates the parent's output.
  const expressao = (key: string, variavel: string) => (isPythonNode ? variavel : `{{ ${alias}.${key} }}`)
  const exprDoCaminho = (key: string, variavel: string) => (caminho: string[]) => (
    isPythonNode
      ? `${variavel}${caminho.map(p => `[${JSON.stringify(p)}]`).join("")}`
      : `{{ ${alias}.${[key, ...caminho].join(".")} }}`
  )
  const tipoDeclarado = new Map(fonte.staticFields.map(f => [f.name, f.type]))
  const saidaAtual = registro?.sample.outputs[chaveAtual]
  const variavelAtual = linhas.find(l => l.key === chaveAtual)?.variavel ?? chaveAtual

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Source and view */}
      <div className="flex flex-col gap-2 border-b px-3 pb-2 pt-1">
        <div className="flex items-center gap-2">
          <label htmlFor={`fonte-${nodeFound.id}`} className="shrink-0 text-[10px] text-muted-foreground">De</label>
          <select
            id={`fonte-${nodeFound.id}`}
            value={fonte.id}
            onChange={e => setFonteId(e.target.value)}
            className="min-w-0 flex-1 rounded-md border bg-background px-2 py-1 text-xs"
          >
            <optgroup label="Ligados a este nó">
              {fontes.filter(f => f.direto).map(f => (
                <option key={f.id} value={f.id}>{f.alias}</option>
              ))}
            </optgroup>
            {fontes.some(f => !f.direto) && (
              <optgroup label="Outros nós anteriores">
                {fontes.filter(f => !f.direto).map(f => (
                  <option key={f.id} value={f.id}>{f.alias}</option>
                ))}
              </optgroup>
            )}
          </select>
          <SeletorDeVisao visao={visao} onChange={setVisao} />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {status && (
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${STATUS_COLOR_MAP[status.status] ?? STATUS_COLOR_MAP.idle}`}>
              {STATUS_LABEL[status.status] ?? status.status}
              {status.duration !== undefined && ` · ${status.duration.toFixed(0)}ms`}
            </span>
          )}
          {registro?.stale && <SeloAnterior />}
          {!direto && (
            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                  title={isPythonNode ? "Ligue este nó para usá-lo como variável no script" : "Acessível por expressão, sem aresta"}>
              não ligado diretamente
            </span>
          )}
        </div>
        {visao !== "schema" && <AbasDeChave chaves={chaves} atual={chaveAtual} onChange={setChave} />}
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        {visao === "schema" ? (
          <div className="flex flex-col gap-1.5 text-xs">
            {/* Schema drift: the catalog's declared fields and the real output diverge. */}
            {status?.schema_drift && (status.schema_drift.missing.length > 0 || status.schema_drift.extra.length > 0) && (
              <div className="text-[10px] text-yellow-700 bg-yellow-500/10 border border-yellow-500/30 rounded px-1.5 py-1">
                <span className="font-semibold">Schema divergente:</span>
                {status.schema_drift.missing.length > 0 && (
                  <span className="ml-1">faltando {status.schema_drift.missing.join(", ")}</span>
                )}
                {status.schema_drift.extra.length > 0 && (
                  <span className="ml-1">extra {status.schema_drift.extra.join(", ")}</span>
                )}
              </div>
            )}

            {linhas.map(({ key, variavel, linhaId }) => {
              const isWired = ligada(key)
              const expression = expressao(key, variavel)
              const saida = registro?.sample.outputs[key]
              const tipo = saida?.kind === "table"
                ? `tabela · ${saida.rows_total.toLocaleString("pt-BR")} linhas`
                : saida?.kind === "json" ? "objeto" : tipoDeclarado.get(key)
              return (
                <div key={linhaId} className="flex flex-col gap-0.5">
                  <div
                    draggable={isWired}
                    onDragStart={isWired ? (e) => iniciarArrasto(e, expression) : undefined}
                    title={isWired ? undefined : (direto ? "Não conectado — adicione uma edge para usar esta chave" : "Ligue este nó para usá-lo como variável no script")}
                    className={cn(
                      "flex items-center gap-1 group rounded bg-muted/60 px-1.5 py-1 transition-colors",
                      isWired ? "cursor-grab active:cursor-grabbing hover:bg-muted" : "opacity-50 cursor-default",
                    )}
                  >
                    {isWired
                      ? <TbGripVertical className="h-3 w-3 shrink-0 text-muted-foreground/50 group-hover:text-muted-foreground" />
                      : <span className="h-3 w-3 shrink-0" />}
                    <code className="min-w-0 flex-1 truncate text-[11px] font-mono font-medium text-primary">
                      {key}
                      {variavel !== key && (
                        // The port is the name that matters to whoever writes the
                        // script; the parent's key stays as provenance.
                        <span className="ml-1 text-muted-foreground">
                          &rarr; <span className="text-foreground">{variavel}</span>
                        </span>
                      )}
                      {tipo && <span className="ml-1.5 font-normal text-[9px] text-muted-foreground">{tipo}</span>}
                    </code>
                    {isWired && (
                      <>
                        {direto && <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" title="Conectado" />}
                        <button
                          type="button"
                          onClick={() => copiar(expression)}
                          // `coarse:`: without hover the copy button simply didn't exist on a phone.
                          className="opacity-0 coarse:opacity-70 group-hover:opacity-100 transition-opacity ml-1"
                          title={`Copiar: ${expression}`}
                        >
                          <TbCopy className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                        </button>
                      </>
                    )}
                  </div>
                  <FilhosDaChave
                    saida={saida}
                    colunasConhecidas={status?.output_columns?.[key]}
                    exprDe={exprDoCaminho(key, variavel)}
                    arrastavel={isWired}
                  />
                </div>
              )
            })}

            {!registro && (
              <p className="mt-1 text-[10px] text-muted-foreground">
                {desligado
                  ? "Amostras de dados desligadas pelo administrador."
                  : "Execute o fluxo para ver as colunas e um valor de exemplo de cada saída."}
              </p>
            )}

            {status?.error && (
              <p className="text-destructive break-all text-[10px] mt-1">{status.error}</p>
            )}
          </div>
        ) : saidaAtual ? (
          <VisaoDaSaida
            saida={saidaAtual}
            visao={visao}
            exprDe={ligada(chaveAtual) ? exprDoCaminho(chaveAtual, variavelAtual) : undefined}
            onVerJson={() => setVisao("json")}
          />
        ) : (
          <SemAmostra motivo={motivoVazio} deQuem={`de ${alias}`} />
        )}

        {(() => {
          const ligadas = new Set(
            parentEdges.map(e => (e.data?.to_key as string | undefined)).filter(Boolean) as string[],
          )
          const pendentes = declaredPorts.filter(p => !ligadas.has(p))
          if (!pendentes.length) return null
          // With one port connected and another not, the missing one was invisible
          // precisely to whoever still needs to connect it.
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

        <p className="text-[10px] text-muted-foreground">
          {isPythonNode
            ? <>Arraste uma chave para inserir o nome da variável Python, ou uma coluna para inserir o nome dela.</>
            : <>Arraste uma chave para inserir a expressão Jinja, ou uma coluna para inserir o nome dela. <TbCopy className="inline h-3 w-3" /> copia.</>}
        </p>
      </div>
    </div>
  )
}

export default InputInspector
