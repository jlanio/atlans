"use client"

import { useState, useRef, useEffect, useCallback, useMemo } from "react"
import { Edge, useReactFlow } from "@xyflow/react"
import { Input } from "@/app/components/ui/input"
import { INodeContext } from "@/context/useFlowContext"
import { TbVariable, TbFunction, TbFilter, TbLink } from "react-icons/tb"
import { resolveNodeAlias, IDENTIFIER_SOURCE } from "../../utils/node-alias"
import { saidasDoNo } from "../../utils/node-ports"

// `Alias.campo.sub` as it appears in the text. Derived from the same identifier
// rule as the alias — using \w here left accented aliases out of the trigger.
const ALIAS_PATH = `${IDENTIFIER_SOURCE}(?:\\.[\\p{ID_Continue}]*)*`
const ALIAS_TRIGGER = new RegExp(`\\$(${ALIAS_PATH})$`, "u")
const ALIAS_PREFIX = new RegExp(`^${ALIAS_PATH}`, "u")

/** Popup ceiling — enough to scroll without turning into an endless list. */
const LIMITE_SUGESTOES = 12

// ── Tipos ────────────────────────────────────────────────────────────────────

interface Suggestion {
  label: string
  type: "alias" | "alias-field" | "input-port" | "input-field" | "variable" | "function" | "filter"
  description?: string
  connected?: boolean
}

interface ExpressionInputProps {
  value: string
  onChange: (value: string) => void
  nodeFound: INodeContext
  placeholder?: string
  id?: string
}

// ── Available Jinja filters ──────────────────────────────────────────────────

const JINJA_FILTERS: Suggestion[] = [
  { label: "upper", type: "filter", description: "Maiúsculas" },
  { label: "lower", type: "filter", description: "Minúsculas" },
  { label: "title", type: "filter", description: "Primeira letra maiúscula" },
  { label: "trim", type: "filter", description: "Remove espaços" },
  { label: "round", type: "filter", description: "Arredonda número" },
  { label: "int", type: "filter", description: "Converte para inteiro" },
  { label: "float", type: "filter", description: "Converte para decimal" },
  { label: "default('')", type: "filter", description: "Valor padrão se vazio" },
  { label: "length", type: "filter", description: "Tamanho da lista/string" },
  { label: "join(',')", type: "filter", description: "Junta lista em string" },
  { label: "first", type: "filter", description: "Primeiro elemento" },
  { label: "last", type: "filter", description: "Último elemento" },
  { label: "replace('a','b')", type: "filter", description: "Substituir texto" },
]

// ── Colors and icons by type ─────────────────────────────────────────────────

const TYPE_STYLES: Record<string, { bg: string; text: string; icon: typeof TbLink }> = {
  "alias":       { bg: "bg-green-500/10", text: "text-green-600 dark:text-green-400", icon: TbLink },
  "alias-field": { bg: "bg-green-500/10", text: "text-green-600 dark:text-green-400", icon: TbLink },
  "input-port":  { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", icon: TbVariable },
  "input-field": { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", icon: TbVariable },
  "variable":    { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", icon: TbVariable },
  "function":    { bg: "bg-amber-500/10", text: "text-amber-600 dark:text-amber-400", icon: TbFunction },
  "filter":      { bg: "bg-purple-500/10", text: "text-purple-600 dark:text-purple-400", icon: TbFilter },
}

// ── Trigger detection ────────────────────────────────────────────────────────

type TriggerKind = "alias" | "jinja" | "inputs" | "filter" | null

interface TriggerInfo {
  kind: TriggerKind
  start: number  // position of the trigger in the text
  query: string  // text typed after the trigger (for filtering)
}

function detectTrigger(text: string, cursorPos: number): TriggerInfo | null {
  const before = text.slice(0, cursorPos)

  // Filter: detects | inside {{ }}
  const pipeMatch = before.match(/\{\{[^}]*\|\s*(\w*)$/)
  if (pipeMatch) {
    return { kind: "filter", start: before.lastIndexOf("|") + 1, query: pipeMatch[1] }
  }

  // Inputs: detects {{ inputs. or {{ inputs
  const inputsMatch = before.match(/\{\{\s*inputs\.(\w*)$/)
  if (inputsMatch) {
    return { kind: "inputs", start: before.lastIndexOf("inputs.") + 7, query: inputsMatch[1] }
  }

  // Jinja: detects {{ followed by text
  const jinjaMatch = before.match(/\{\{\s*(\w*)$/)
  if (jinjaMatch) {
    return { kind: "jinja", start: before.lastIndexOf("{{") + 2, query: jinjaMatch[1].trim() }
  }

  // Alias: detects $ followed by text
  const aliasMatch = before.match(ALIAS_TRIGGER)
  if (aliasMatch) {
    return { kind: "alias", start: before.lastIndexOf("$") + 1, query: aliasMatch[1] }
  }
  // $ was just typed
  if (before.endsWith("$")) {
    return { kind: "alias", start: cursorPos, query: "" }
  }

  return null
}

// ── Componente ───────────────────────────────────────────────────────────────

export default function ExpressionInput({ value, onChange, nodeFound, placeholder, id }: ExpressionInputProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const [showPopup, setShowPopup] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [trigger, setTrigger] = useState<TriggerInfo | null>(null)

  const { getNodes, getEdges } = useReactFlow<INodeContext, Edge>()

  // A snapshot of the graph taken when the trigger appears, not a subscription.
  // The form stays open over a canvas that is still editable: subscribing to
  // `useNodes()/useEdges()`, the three suggestion lists were recomputed on every
  // pointermove of a drag — per expression field on screen. And there is nothing
  // to gain by following the drag: suggestions don't change with position.
  const [grafo, setGrafo] = useState<{ nodes: INodeContext[]; edges: Edge[] }>(
    () => ({ nodes: [], edges: [] }),
  )
  const { nodes: allNodes, edges } = grafo

  // Builds the base suggestions (aliases, variables, functions, inputs)
  const baseSuggestions = useMemo(() => {
    const connectedIds = edges
      .filter(e => e.target === nodeFound.id)
      .map(e => e.source)

    const suggestions: Suggestion[] = []

    // The label is what goes into the text: it must be the alias the EXECUTOR
    // registers in the context, not the display label. See utils/node-alias.
    // The description carries the friendly name, when it differs.
    const descricaoDe = (n: INodeContext, alias: string) => {
      const rotulo = typeof n.data.alias === "string" ? n.data.alias : ""
      // Without a label of its own, the alias already is the node name — repeating it only clutters the row.
      return rotulo && rotulo !== alias ? rotulo : undefined
    }

    // Two nodes without a custom alias resolve to the same `name` — in the
    // executor's context they occupy the same key, so the list shows a single entry.
    const vistos = new Set<string>()
    const adicionar = (s: Suggestion) => {
      if (vistos.has(s.label)) return
      vistos.add(s.label)
      suggestions.push(s)
    }

    // 1. Aliases of the connected nodes (priority)
    allNodes.filter(n => connectedIds.includes(n.id)).forEach(n => {
      const alias = resolveNodeAlias(n.data)
      if (!alias) return
      adicionar({ label: alias, type: "alias", connected: true, description: descricaoDe(n, alias) })
      saidasDoNo(n.data).forEach(f => {
        adicionar({ label: `${alias}.${f.name}`, type: "alias-field", connected: true, description: f.description ?? f.type })
      })
    })

    // 2. Aliases of the other nodes, with their fields too. Listing only the alias
    // made whoever builds the workflow back to front type "{{$Alias." and see
    // nothing, with no hint that connecting would change that — the fields are
    // declared by the node, they don't depend on the connection.
    allNodes.filter(n => n.id !== nodeFound.id && !connectedIds.includes(n.id)).forEach(n => {
      const alias = resolveNodeAlias(n.data)
      if (!alias) return
      adicionar({ label: alias, type: "alias", connected: false, description: descricaoDe(n, alias) })
      saidasDoNo(n.data).forEach(f => {
        adicionar({ label: `${alias}.${f.name}`, type: "alias-field", connected: false, description: f.description ?? f.type })
      })
    })

    return suggestions
  }, [allNodes, edges, nodeFound.id])

  // Input suggestions (ports + fields of the connected nodes)
  const inputSuggestions = useMemo(() => {
    const connectedIds = edges
      .filter(e => e.target === nodeFound.id)
      .map(e => e.source)

    // `inputs` is a single dict: two parents that declare `output` occupy the same
    // key. Without deduplicating, the list repeats the entry and React also gets
    // two equal keys — and the collision became likely once flattening started
    // seeing the fields of the grouped form.
    const suggestions: Suggestion[] = []
    const porLabel = new Map<string, Suggestion>()
    const adicionar = (s: Suggestion) => {
      const anterior = porLabel.get(s.label)
      if (anterior) {
        anterior.description = `${s.label} — vem de mais de um nó`
        return
      }
      porLabel.set(s.label, s)
      suggestions.push(s)
    }

    // Named input ports
    const inputPorts = (nodeFound.data.inputs ?? []).map(p => p.name)
    inputPorts.forEach(port => {
      adicionar({ label: port, type: "input-port", description: `Porta "${port}"` })
    })

    // Output fields of the connected nodes
    allNodes.filter(n => connectedIds.includes(n.id)).forEach(n => {
      saidasDoNo(n.data).forEach(f => {
        adicionar({ label: f.name, type: "input-field", description: `${f.name} de ${n.data.alias || n.data.name}` })
      })
    })

    return suggestions
  }, [allNodes, edges, nodeFound.id, nodeFound.data.inputs])

  // Jinja variables and functions
  const jinjaSuggestions = useMemo<Suggestion[]>(() => {
    const connectedIds = edges
      .filter(e => e.target === nodeFound.id)
      .map(e => e.source)

    const suggestions: Suggestion[] = [
      { label: "inputs", type: "variable", description: "Dados de entrada do nó" },
      { label: "env", type: "variable", description: "Variáveis de ambiente" },
    ]

    // Direct alias for each connected node (accessible as a top-level variable).
    // Inside {{ }} the alias is a Jinja variable — the executor's rule applies.
    const vistos = new Set(suggestions.map(s => s.label))
    allNodes.filter(n => connectedIds.includes(n.id)).forEach(n => {
      const alias = resolveNodeAlias(n.data)
      if (!alias || vistos.has(alias)) return
      vistos.add(alias)
      suggestions.push({ label: alias, type: "variable", description: `Saída de ${n.data.name}` })
    })

    suggestions.push(
      { label: "now()", type: "function", description: "Data/hora UTC" },
      { label: "uuid()", type: "function", description: "UUID aleatório" },
    )

    return suggestions
  }, [allNodes, edges, nodeFound.id])

  // Suggestions filtered based on the active trigger
  const filteredSuggestions = useMemo(() => {
    if (!trigger) return []
    const q = trigger.query.toLowerCase()

    let pool: Suggestion[] = []
    if (trigger.kind === "alias") pool = baseSuggestions
    else if (trigger.kind === "jinja") pool = jinjaSuggestions
    else if (trigger.kind === "inputs") pool = inputSuggestions
    else if (trigger.kind === "filter") pool = JINJA_FILTERS

    // Without a filter, a straight cut hid ALL aliases behind the first node's
    // fields — a single node with 6 outputs was enough for the second alias to
    // vanish from the list. Reserves half the slots for aliases and fills the rest.
    if (!q) {
      const aliases = pool.filter(s => s.type === "alias")
      const demais = pool.filter(s => s.type !== "alias")
      const cotaAlias = Math.min(aliases.length, Math.ceil(LIMITE_SUGESTOES / 2))
      return [
        ...aliases.slice(0, cotaAlias),
        ...demais.slice(0, LIMITE_SUGESTOES - cotaAlias),
      ]
    }
    // The friendly label ("Caixa Delimitadora", bounding box) lives in the
    // description since the label became the executor's alias — without matching
    // the description, the user types the name they see on the canvas and finds
    // nothing. With a dot in the middle they are already navigating a specific
    // alias, so only the label counts.
    const casaDescricao = !q.includes(".")
    return pool
      .filter(s => s.label.toLowerCase().includes(q)
        || (casaDescricao && (s.description ?? "").toLowerCase().includes(q)))
      .slice(0, LIMITE_SUGESTOES)
  }, [trigger, baseSuggestions, jinjaSuggestions, inputSuggestions])

  // Updates the trigger on every value change
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    onChange(newValue)

    const cursorPos = e.target.selectionStart ?? newValue.length
    const detected = detectTrigger(newValue, cursorPos)

    if (detected) {
      // Re-snapshots on every trigger: between one opening of the popup and the next
      // the user may have connected the node to another, and the list must reflect it.
      setGrafo({ nodes: getNodes(), edges: getEdges() })
      setTrigger(detected)
      setShowPopup(true)
      setSelectedIndex(0)
    } else {
      setShowPopup(false)
      setTrigger(null)
    }
  }, [onChange, getNodes, getEdges])

  // Inserts the suggestion into the text
  const insertSuggestion = useCallback((suggestion: Suggestion) => {
    if (!trigger || !inputRef.current) return

    const before = value.slice(0, trigger.start)
    const after = value.slice(inputRef.current.selectionStart ?? value.length)

    let inserted: string
    if (trigger.kind === "alias") {
      // Clears the text the user already typed after $
      const afterAlias = value.slice(trigger.start).replace(ALIAS_PREFIX, "")
      inserted = `${before}${suggestion.label}${afterAlias}`
    } else if (trigger.kind === "jinja") {
      // Inserts with a space and closes }}
      const needsClose = !after.trimStart().startsWith("}}")
      inserted = `${before} ${suggestion.label}${needsClose ? " }}" : ""}${after}`
    } else if (trigger.kind === "inputs") {
      // Completes the field after inputs.
      const afterField = value.slice(trigger.start).replace(/^\w*/, "")
      inserted = `${before}${suggestion.label}${afterField}`
    } else if (trigger.kind === "filter") {
      // Inserts the filter after |
      const trimmedBefore = before.replace(/\s*$/, " ")
      const afterFilter = after.replace(/^\w*/, "")
      inserted = `${trimmedBefore}${suggestion.label}${afterFilter}`
    } else {
      inserted = value
    }

    onChange(inserted)
    setShowPopup(false)
    setTrigger(null)

    // Restores focus to the input
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [trigger, value, onChange])

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!showPopup || filteredSuggestions.length === 0) return

    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex(i => (i + 1) % filteredSuggestions.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex(i => (i - 1 + filteredSuggestions.length) % filteredSuggestions.length)
    } else if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault()
      insertSuggestion(filteredSuggestions[selectedIndex])
    } else if (e.key === "Escape") {
      e.preventDefault()
      setShowPopup(false)
      setTrigger(null)
    }
  }, [showPopup, filteredSuggestions, selectedIndex, insertSuggestion])

  // Closes the popup when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        popupRef.current && !popupRef.current.contains(e.target as Node) &&
        inputRef.current && !inputRef.current.contains(e.target as Node)
      ) {
        setShowPopup(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Scrolls the selected item into view
  useEffect(() => {
    if (!popupRef.current) return
    const item = popupRef.current.children[selectedIndex] as HTMLElement | undefined
    item?.scrollIntoView({ block: "nearest" })
  }, [selectedIndex])

  return (
    <div className="relative">
      <Input
        ref={inputRef}
        id={id}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoComplete="off"
      />

      {showPopup && filteredSuggestions.length > 0 && (
        <div
          ref={popupRef}
          className="absolute left-0 right-0 top-full mt-1 z-50 max-h-52 overflow-y-auto rounded-md border border-border bg-popover shadow-md"
        >
          {filteredSuggestions.map((s, i) => {
            const style = TYPE_STYLES[s.type] ?? TYPE_STYLES.variable
            const Icon = style.icon
            return (
              <button
                key={`${s.type}-${s.label}`}
                type="button"
                onMouseDown={(e) => { e.preventDefault(); insertSuggestion(s) }}
                className={`flex w-full items-center gap-2 px-3 py-1.5 text-sm text-left transition-colors
                  ${i === selectedIndex ? "bg-accent" : "hover:bg-accent/50"}`}
              >
                <span className={`flex items-center justify-center w-5 h-5 rounded ${style.bg}`}>
                  <Icon className={`w-3.5 h-3.5 ${style.text}`} />
                </span>
                <span className="font-mono text-xs flex-1 truncate">{s.label}</span>
                {s.description && (
                  <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">{s.description}</span>
                )}
                {s.connected && (
                  <span className="text-[9px] text-green-500 font-medium shrink-0">conectado</span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
