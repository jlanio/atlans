"use client"

import { useState, useRef, useEffect, useCallback, useMemo } from "react"
import { Edge, useReactFlow } from "@xyflow/react"
import { Input } from "@/app/components/ui/input"
import { INodeContext } from "@/context/useFlowContext"
import { TbVariable, TbFunction, TbFilter, TbLink } from "react-icons/tb"
import { resolveNodeAlias, IDENTIFIER_SOURCE } from "../../utils/node-alias"
import { saidasDoNo } from "../../utils/node-ports"

// `Alias.campo.sub` como aparece no texto. Deriva da mesma regra de identificador
// do alias — usar \w aqui deixava aliases acentuados fora do gatilho.
const ALIAS_PATH = `${IDENTIFIER_SOURCE}(?:\\.[\\p{ID_Continue}]*)*`
const ALIAS_TRIGGER = new RegExp(`\\$(${ALIAS_PATH})$`, "u")
const ALIAS_PREFIX = new RegExp(`^${ALIAS_PATH}`, "u")

/** Teto do popup — o suficiente para rolar sem virar uma lista infinita. */
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

// ── Filtros Jinja disponíveis ────────────────────────────────────────────────

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

// ── Cores e ícones por tipo ──────────────────────────────────────────────────

const TYPE_STYLES: Record<string, { bg: string; text: string; icon: typeof TbLink }> = {
  "alias":       { bg: "bg-green-500/10", text: "text-green-600 dark:text-green-400", icon: TbLink },
  "alias-field": { bg: "bg-green-500/10", text: "text-green-600 dark:text-green-400", icon: TbLink },
  "input-port":  { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", icon: TbVariable },
  "input-field": { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", icon: TbVariable },
  "variable":    { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", icon: TbVariable },
  "function":    { bg: "bg-amber-500/10", text: "text-amber-600 dark:text-amber-400", icon: TbFunction },
  "filter":      { bg: "bg-purple-500/10", text: "text-purple-600 dark:text-purple-400", icon: TbFilter },
}

// ── Detecção de gatilho ──────────────────────────────────────────────────────

type TriggerKind = "alias" | "jinja" | "inputs" | "filter" | null

interface TriggerInfo {
  kind: TriggerKind
  start: number  // posição do gatilho no texto
  query: string  // texto digitado após o gatilho (para filtrar)
}

function detectTrigger(text: string, cursorPos: number): TriggerInfo | null {
  const before = text.slice(0, cursorPos)

  // Filtro: detecta | dentro de {{ }}
  const pipeMatch = before.match(/\{\{[^}]*\|\s*(\w*)$/)
  if (pipeMatch) {
    return { kind: "filter", start: before.lastIndexOf("|") + 1, query: pipeMatch[1] }
  }

  // Inputs: detecta {{ inputs. ou {{ inputs
  const inputsMatch = before.match(/\{\{\s*inputs\.(\w*)$/)
  if (inputsMatch) {
    return { kind: "inputs", start: before.lastIndexOf("inputs.") + 7, query: inputsMatch[1] }
  }

  // Jinja: detecta {{ seguido de texto
  const jinjaMatch = before.match(/\{\{\s*(\w*)$/)
  if (jinjaMatch) {
    return { kind: "jinja", start: before.lastIndexOf("{{") + 2, query: jinjaMatch[1].trim() }
  }

  // Alias: detecta $ seguido de texto
  const aliasMatch = before.match(ALIAS_TRIGGER)
  if (aliasMatch) {
    return { kind: "alias", start: before.lastIndexOf("$") + 1, query: aliasMatch[1] }
  }
  // $ acabou de ser digitado
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

  // Fotografia do grafo tirada quando o gatilho aparece, e não assinatura.
  // O formulário fica aberto sobre um canvas ainda editável: assinando
  // `useNodes()/useEdges()`, as três listas de sugestão eram recalculadas a cada
  // pointermove de um arraste — por campo de expressão da tela. E não há o que
  // ganhar acompanhando o arraste: as sugestões não mudam por posição.
  const [grafo, setGrafo] = useState<{ nodes: INodeContext[]; edges: Edge[] }>(
    () => ({ nodes: [], edges: [] }),
  )
  const { nodes: allNodes, edges } = grafo

  // Monta sugestões base (aliases, variáveis, funções, inputs)
  const baseSuggestions = useMemo(() => {
    const connectedIds = edges
      .filter(e => e.target === nodeFound.id)
      .map(e => e.source)

    const suggestions: Suggestion[] = []

    // O label é o que vai para o texto: precisa ser o alias que o EXECUTOR
    // registra no contexto, não o rótulo de exibição. Ver utils/node-alias.
    // A descrição carrega o nome amigável, quando diferir.
    const descricaoDe = (n: INodeContext, alias: string) => {
      const rotulo = typeof n.data.alias === "string" ? n.data.alias : ""
      // Sem rótulo próprio, o alias já é o nome do nó — repetir só polui a linha.
      return rotulo && rotulo !== alias ? rotulo : undefined
    }

    // Dois nós sem alias customizado resolvem para o mesmo `name` — no contexto
    // do executor eles ocupam a mesma chave, então a lista mostra uma entrada só.
    const vistos = new Set<string>()
    const adicionar = (s: Suggestion) => {
      if (vistos.has(s.label)) return
      vistos.add(s.label)
      suggestions.push(s)
    }

    // 1. Aliases dos nós conectados (prioridade)
    allNodes.filter(n => connectedIds.includes(n.id)).forEach(n => {
      const alias = resolveNodeAlias(n.data)
      if (!alias) return
      adicionar({ label: alias, type: "alias", connected: true, description: descricaoDe(n, alias) })
      saidasDoNo(n.data).forEach(f => {
        adicionar({ label: `${alias}.${f.name}`, type: "alias-field", connected: true, description: f.description ?? f.type })
      })
    })

    // 2. Aliases dos demais nós, com os campos também. Listar só o alias fazia
    // quem monta o fluxo de trás para frente digitar "{{$Alias." e não ver
    // nada, sem pista de que conectar mudaria isso — os campos são declarados
    // pelo nó, não dependem da conexão.
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

  // Sugestões de inputs (portas + campos dos nós conectados)
  const inputSuggestions = useMemo(() => {
    const connectedIds = edges
      .filter(e => e.target === nodeFound.id)
      .map(e => e.source)

    // `inputs` é um dict só: dois pais que declaram `output` ocupam a mesma
    // chave. Sem deduplicar, a lista repete a entrada e o React ainda recebe
    // duas chaves iguais — e a colisão ficou provável quando o achatamento
    // passou a enxergar os campos da forma agrupada.
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

    // Portas de entrada nomeadas
    const inputPorts = (nodeFound.data.inputs ?? []).map(p => p.name)
    inputPorts.forEach(port => {
      adicionar({ label: port, type: "input-port", description: `Porta "${port}"` })
    })

    // Campos de saída dos nós conectados
    allNodes.filter(n => connectedIds.includes(n.id)).forEach(n => {
      saidasDoNo(n.data).forEach(f => {
        adicionar({ label: f.name, type: "input-field", description: `${f.name} de ${n.data.alias || n.data.name}` })
      })
    })

    return suggestions
  }, [allNodes, edges, nodeFound.id, nodeFound.data.inputs])

  // Variáveis e funções Jinja
  const jinjaSuggestions = useMemo<Suggestion[]>(() => {
    const connectedIds = edges
      .filter(e => e.target === nodeFound.id)
      .map(e => e.source)

    const suggestions: Suggestion[] = [
      { label: "inputs", type: "variable", description: "Dados de entrada do nó" },
      { label: "env", type: "variable", description: "Variáveis de ambiente" },
    ]

    // Alias direto para cada nó conectado (acessível como variável de primeiro nível).
    // Dentro de {{ }} o alias é uma variável Jinja — vale a mesma regra do executor.
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

  // Sugestões filtradas com base no gatilho ativo
  const filteredSuggestions = useMemo(() => {
    if (!trigger) return []
    const q = trigger.query.toLowerCase()

    let pool: Suggestion[] = []
    if (trigger.kind === "alias") pool = baseSuggestions
    else if (trigger.kind === "jinja") pool = jinjaSuggestions
    else if (trigger.kind === "inputs") pool = inputSuggestions
    else if (trigger.kind === "filter") pool = JINJA_FILTERS

    // Sem filtro, um corte reto escondia TODOS os aliases atrás dos campos do
    // primeiro nó — bastava um nó com 6 saídas para o segundo alias sumir da
    // lista. Reserva metade das vagas para aliases e completa com o resto.
    if (!q) {
      const aliases = pool.filter(s => s.type === "alias")
      const demais = pool.filter(s => s.type !== "alias")
      const cotaAlias = Math.min(aliases.length, Math.ceil(LIMITE_SUGESTOES / 2))
      return [
        ...aliases.slice(0, cotaAlias),
        ...demais.slice(0, LIMITE_SUGESTOES - cotaAlias),
      ]
    }
    // O rótulo amigável ("Caixa Delimitadora") vive na descrição desde que o
    // label passou a ser o alias do executor — sem casar a descrição, o usuário
    // digita o nome que vê no canvas e não acha nada. Com ponto no meio ele já
    // está navegando um alias específico, aí só o label vale.
    const casaDescricao = !q.includes(".")
    return pool
      .filter(s => s.label.toLowerCase().includes(q)
        || (casaDescricao && (s.description ?? "").toLowerCase().includes(q)))
      .slice(0, LIMITE_SUGESTOES)
  }, [trigger, baseSuggestions, jinjaSuggestions, inputSuggestions])

  // Atualiza gatilho a cada mudança de valor
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    onChange(newValue)

    const cursorPos = e.target.selectionStart ?? newValue.length
    const detected = detectTrigger(newValue, cursorPos)

    if (detected) {
      // Refotografa a cada gatilho: entre uma abertura do popup e a próxima o
      // usuário pode ter ligado o nó a outro, e a lista precisa refletir isso.
      setGrafo({ nodes: getNodes(), edges: getEdges() })
      setTrigger(detected)
      setShowPopup(true)
      setSelectedIndex(0)
    } else {
      setShowPopup(false)
      setTrigger(null)
    }
  }, [onChange, getNodes, getEdges])

  // Insere sugestão no texto
  const insertSuggestion = useCallback((suggestion: Suggestion) => {
    if (!trigger || !inputRef.current) return

    const before = value.slice(0, trigger.start)
    const after = value.slice(inputRef.current.selectionStart ?? value.length)

    let inserted: string
    if (trigger.kind === "alias") {
      // Limpa o texto que o usuário já digitou após $
      const afterAlias = value.slice(trigger.start).replace(ALIAS_PREFIX, "")
      inserted = `${before}${suggestion.label}${afterAlias}`
    } else if (trigger.kind === "jinja") {
      // Insere com espaço e fecha }}
      const needsClose = !after.trimStart().startsWith("}}")
      inserted = `${before} ${suggestion.label}${needsClose ? " }}" : ""}${after}`
    } else if (trigger.kind === "inputs") {
      // Completa campo após inputs.
      const afterField = value.slice(trigger.start).replace(/^\w*/, "")
      inserted = `${before}${suggestion.label}${afterField}`
    } else if (trigger.kind === "filter") {
      // Insere filtro após |
      const trimmedBefore = before.replace(/\s*$/, " ")
      const afterFilter = after.replace(/^\w*/, "")
      inserted = `${trimmedBefore}${suggestion.label}${afterFilter}`
    } else {
      inserted = value
    }

    onChange(inserted)
    setShowPopup(false)
    setTrigger(null)

    // Restaura foco no input
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [trigger, value, onChange])

  // Navegação por teclado
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

  // Fecha popup ao clicar fora
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

  // Scroll item selecionado para visível
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
