"use client"

/**
 * Data views shared by the node modal's Entradas and Saídas panels
 * (docs/specs/node-data-panels.md §6.2): Schema / Tabela / JSON over the
 * sample each node sends after a run started from the editor.
 *
 * Drag rules are the panels' (the same as before the redesign): a key inserts
 * `{{ Alias.key }}`, a column inserts its name, a JSON leaf inserts
 * `{{ Alias.key.path }}`. Whoever renders decides whether something is
 * draggable at all (`arrastavel`).
 */
import { useCallback, useEffect, useState } from "react"
import { TbCopy, TbGripVertical, TbPlayerPlay, TbTableOff } from "react-icons/tb"
import { cn } from "@/lib/utils"
import {
  isGeometria, type AmostraCelula, type AmostraColuna, type AmostraSaida, type AmostraTabela,
} from "@/types/amostra"

export type Visao = "schema" | "tabela" | "json"

const VISOES: { id: Visao; rotulo: string }[] = [
  { id: "schema", rotulo: "Schema" },
  { id: "tabela", rotulo: "Tabela" },
  { id: "json", rotulo: "JSON" },
]

/** The view picked in each panel, remembered across modals (per browser). */
export function useVisaoLembrada(painel: "entradas" | "saidas", comDados: boolean): [Visao, (v: Visao) => void] {
  const chave = `atlans:painel-no:${painel}:visao`
  const [escolhida, setEscolhida] = useState<Visao | null>(null)

  useEffect(() => {
    try {
      const salva = window.localStorage.getItem(chave)
      if (salva === "schema" || salva === "tabela" || salva === "json") setEscolhida(salva)
    } catch { /* no storage: the default applies */ }
  }, [chave])

  const definir = useCallback((v: Visao) => {
    setEscolhida(v)
    try { window.localStorage.setItem(chave, v) } catch { /* ignore */ }
  }, [chave])

  // Without a choice: Tabela when there is data to show, Schema otherwise.
  return [escolhida ?? (comDados ? "tabela" : "schema"), definir]
}

export function SeletorDeVisao({ visao, onChange, desabilitar = [] }: {
  visao: Visao
  onChange: (v: Visao) => void
  desabilitar?: Visao[]
}) {
  return (
    <div role="group" aria-label="Visão dos dados" className="inline-flex shrink-0 rounded-md bg-muted p-0.5">
      {VISOES.map(({ id, rotulo }) => {
        const off = desabilitar.includes(id)
        return (
          <button
            key={id}
            type="button"
            aria-pressed={visao === id}
            disabled={off}
            onClick={() => onChange(id)}
            title={off ? "Execute o fluxo para ver os dados" : undefined}
            className={cn(
              "rounded px-2 py-0.5 text-[11px] font-medium transition-colors",
              visao === id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
              off && "cursor-not-allowed opacity-40 hover:text-muted-foreground",
            )}
          >
            {rotulo}
          </button>
        )
      })}
    </div>
  )
}

/** One button per output key, when the node has more than one. */
export function AbasDeChave({ chaves, atual, onChange }: {
  chaves: string[]
  atual: string
  onChange: (k: string) => void
}) {
  if (chaves.length < 2) return null
  return (
    <div role="group" aria-label="Saída" className="flex flex-wrap gap-1">
      {chaves.map(k => (
        <button
          key={k}
          type="button"
          aria-pressed={k === atual}
          onClick={() => onChange(k)}
          className={cn(
            "rounded border px-1.5 py-0.5 font-mono text-[10px] transition-colors",
            k === atual ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:text-foreground",
          )}
        >
          {k}
        </button>
      ))}
    </div>
  )
}

export function iniciarArrasto(e: React.DragEvent, texto: string) {
  e.dataTransfer.setData("text/plain", texto)
  e.dataTransfer.effectAllowed = "copy"
}

export function copiar(texto: string) {
  navigator.clipboard?.writeText(texto).catch(() => { /* clipboard refused: nothing to do */ })
}

/** Text of a cell as the table shows it. */
export function textoDaCelula(valor: AmostraCelula): string {
  if (valor === null || valor === undefined) return "null"
  if (isGeometria(valor)) {
    return valor.vertices != null ? `${valor.type} · ${valor.vertices.toLocaleString("pt-BR")} vért.` : valor.type
  }
  if (typeof valor === "number") return valor.toLocaleString("pt-BR", { maximumFractionDigits: 6 })
  if (typeof valor === "boolean") return valor ? "true" : "false"
  return String(valor)
}

function rotuloDoTipo(tipo: string): string {
  return tipo.startsWith("geometry:") ? tipo.slice("geometry:".length) : tipo
}

const NUMERICO = new Set(["int", "float"])

export function VisaoTabela({ saida }: { saida: AmostraTabela }) {
  if (saida.columns.length === 0) {
    return <p className="py-4 text-center text-xs text-muted-foreground">Tabela sem colunas.</p>
  }
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <div className="max-h-[52vh] overflow-auto rounded-md border">
        <table className="w-max min-w-full border-collapse text-[11px] tabular-nums">
          <thead>
            <tr>
              <th className="sticky top-0 z-[1] bg-muted px-2 py-1 text-right font-normal text-muted-foreground">#</th>
              {saida.columns.map(c => (
                <th
                  key={c.name}
                  draggable
                  onDragStart={e => iniciarArrasto(e, c.name)}
                  title="Arraste para inserir o nome da coluna"
                  className="sticky top-0 z-[1] cursor-grab whitespace-nowrap bg-muted px-2 py-1 text-left font-semibold active:cursor-grabbing"
                >
                  {c.name}
                  <span className="block font-mono text-[9px] font-normal lowercase text-muted-foreground">{rotuloDoTipo(c.type)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {saida.rows.map((linha, i) => (
              <tr key={i} className="hover:bg-primary/5">
                <td className="border-t px-2 py-1 text-right text-muted-foreground">{i + 1}</td>
                {linha.map((valor, j) => {
                  const col = saida.columns[j]
                  const geo = isGeometria(valor)
                  return (
                    <td
                      key={j}
                      title={geo && valor.wkt ? valor.wkt : undefined}
                      className={cn(
                        "max-w-[260px] truncate whitespace-nowrap border-t px-2 py-1",
                        col && NUMERICO.has(col.type) && "text-right",
                        geo && "font-mono text-[10px] text-sky-700 dark:text-sky-400",
                        valor === null && "text-muted-foreground/60",
                      )}
                    >
                      {textoDaCelula(valor)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap justify-between gap-2 text-[10px] text-muted-foreground">
        <span>
          {saida.rows.length === saida.rows_total
            ? `${saida.rows_total.toLocaleString("pt-BR")} linha(s)`
            : `Mostrando ${saida.rows.length} de ${saida.rows_total.toLocaleString("pt-BR")} linhas (amostra)`}
        </span>
        <span>
          {saida.columns.length} coluna(s){saida.truncated.columns ? " (cortadas)" : ""}
          {saida.crs ? ` · ${saida.crs}` : ""}
        </span>
      </div>
    </div>
  )
}

/** The first rows of a table as objects, for the JSON view. */
export function linhasComoObjetos(saida: AmostraTabela, limite = 3): Record<string, unknown>[] {
  return saida.rows.slice(0, limite).map(linha =>
    Object.fromEntries(saida.columns.map((c, i) => [c.name, linha[i] ?? null])),
  )
}

function JsonNo({ valor, caminho, nivel, exprDe }: {
  valor: unknown
  caminho: string[]
  nivel: number
  exprDe?: (caminho: string[]) => string
}) {
  const recuo = "  ".repeat(nivel + 1)
  const fim = "  ".repeat(nivel)
  if (Array.isArray(valor)) {
    if (valor.length === 0) return <>[]</>
    return (
      <>
        [{valor.map((v, i) => (
          <span key={i}>{"\n"}{recuo}<JsonNo valor={v} caminho={[...caminho, String(i)]} nivel={nivel + 1} />{i < valor.length - 1 ? "," : ""}</span>
        ))}{"\n"}{fim}]
      </>
    )
  }
  if (valor && typeof valor === "object") {
    const entradas = Object.entries(valor as Record<string, unknown>)
    if (entradas.length === 0) return <>{"{}"}</>
    return (
      <>
        {"{"}{entradas.map(([k, v], i) => {
          const expr = exprDe?.([...caminho, k])
          return (
            <span key={k}>
              {"\n"}{recuo}
              <span
                draggable={!!expr}
                onDragStart={expr ? e => iniciarArrasto(e, expr) : undefined}
                title={expr ? `Arraste para inserir ${expr}` : undefined}
                className={cn("text-primary", expr && "cursor-grab hover:underline")}
              >
                &quot;{k}&quot;
              </span>
              : <JsonNo valor={v} caminho={[...caminho, k]} nivel={nivel + 1} exprDe={exprDe} />{i < entradas.length - 1 ? "," : ""}
            </span>
          )
        })}{"\n"}{fim}{"}"}
      </>
    )
  }
  if (typeof valor === "string") return <span className="text-emerald-700 dark:text-emerald-400">&quot;{valor}&quot;</span>
  if (typeof valor === "number") return <span className="text-sky-700 dark:text-sky-400">{valor}</span>
  return <span className="text-amber-700 dark:text-amber-400">{String(valor)}</span>
}

export function VisaoJson({ saida, exprDe }: {
  saida: AmostraSaida
  /** Expression a dragged key inserts, from its path inside the output. Omitted: keys are not draggable. */
  exprDe?: (caminho: string[]) => string
}) {
  if (saida.kind === "omitted") return <SaidaOmitida motivo={saida.reason} />
  const valor = saida.kind === "table" ? linhasComoObjetos(saida) : saida.value
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <pre className="max-h-[52vh] overflow-auto whitespace-pre rounded-md bg-muted/60 p-2 font-mono text-[11px] leading-relaxed">
        <JsonNo valor={valor} caminho={[]} nivel={0} exprDe={saida.kind === "json" ? exprDe : undefined} />
      </pre>
      {saida.kind === "table" && (
        <span className="text-[10px] text-muted-foreground">Primeiras {Math.min(3, saida.rows.length)} linhas como JSON</span>
      )}
      {saida.kind === "json" && saida.truncated && (
        <span className="text-[10px] text-muted-foreground">Valores longos e listas grandes foram cortados.</span>
      )}
    </div>
  )
}

export function SaidaOmitida({ motivo }: { motivo: string }) {
  return (
    <div className="flex flex-col items-center gap-1 py-6 text-center text-xs text-muted-foreground">
      <TbTableOff size={22} />
      <span>{motivo === "too_large" ? "Esta saída é grande demais para a amostra." : "Não foi possível montar a amostra desta saída."}</span>
    </div>
  )
}

/** Table or JSON view of one output, with the "not a table" fallback. */
export function VisaoDaSaida({ saida, visao, exprDe, onVerJson }: {
  saida: AmostraSaida
  visao: "tabela" | "json"
  exprDe?: (caminho: string[]) => string
  onVerJson: () => void
}) {
  if (saida.kind === "omitted") return <SaidaOmitida motivo={saida.reason} />
  if (visao === "tabela") {
    if (saida.kind === "table") return <VisaoTabela saida={saida} />
    return (
      <div className="flex flex-col items-center gap-2 py-6 text-center text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Esta saída não é uma tabela</span>
        <span>É um objeto. Veja em Schema ou JSON.</span>
        <button type="button" onClick={onVerJson} className="rounded-md border px-2 py-1 text-[11px] text-foreground hover:bg-muted">
          Ver JSON
        </button>
      </div>
    )
  }
  return <VisaoJson saida={saida} exprDe={exprDe} />
}

/** Columns (or object keys) under an output key, in the Schema view. */
export function FilhosDaChave({ saida, colunasConhecidas, exprDe, arrastavel }: {
  saida?: AmostraSaida
  /** Column names from the last run's stats, when there is no sample. */
  colunasConhecidas?: string[]
  /** Expression for a JSON key path; for table columns the drag inserts the name. */
  exprDe?: (caminho: string[]) => string
  arrastavel: boolean
}) {
  type Filho = { nome: string; tipo?: string; exemplo?: string; arrasto: string }
  let filhos: Filho[] = []
  if (saida?.kind === "table") {
    filhos = saida.columns.map((c: AmostraColuna, i) => ({
      nome: c.name,
      tipo: rotuloDoTipo(c.type),
      exemplo: saida.rows.length ? textoDaCelula(saida.rows[0][i]) : undefined,
      arrasto: c.name,
    }))
  } else if (saida?.kind === "json" && saida.value && typeof saida.value === "object" && !Array.isArray(saida.value)) {
    filhos = Object.entries(saida.value as Record<string, unknown>).map(([k, v]) => ({
      nome: k,
      tipo: Array.isArray(v) ? "lista" : v === null ? "null" : typeof v === "object" ? "objeto" : typeof v === "number" ? "número" : typeof v === "boolean" ? "booleano" : "texto",
      exemplo: v === null || typeof v === "object" ? undefined : String(v),
      arrasto: exprDe ? exprDe([k]) : k,
    }))
  } else if (colunasConhecidas?.length) {
    filhos = colunasConhecidas.map(nome => ({ nome, arrasto: nome }))
  }
  if (filhos.length === 0) return null

  return (
    <div className="ml-4 flex flex-col border-l pl-2">
      {filhos.map(f => (
        <div
          key={f.nome}
          draggable={arrastavel}
          onDragStart={arrastavel ? e => iniciarArrasto(e, f.arrasto) : undefined}
          title={arrastavel ? `Arraste para inserir ${f.arrasto}` : undefined}
          className={cn(
            "group grid grid-cols-[12px_minmax(0,1fr)_auto] items-center gap-1.5 rounded px-1 py-0.5",
            arrastavel ? "cursor-grab hover:bg-muted active:cursor-grabbing" : "cursor-default",
          )}
        >
          {arrastavel ? <TbGripVertical className="h-3 w-3 text-muted-foreground/40 group-hover:text-muted-foreground" /> : <span />}
          <span className="min-w-0 truncate">
            <code className="font-mono text-[11px]">{f.nome}</code>
            {f.tipo && <span className="ml-1.5 font-mono text-[9px] text-muted-foreground">{f.tipo}</span>}
          </span>
          <span className="flex items-center gap-1">
            {f.exemplo !== undefined && (
              <span className="max-w-[140px] truncate text-[10px] text-muted-foreground" title={f.exemplo}>{f.exemplo}</span>
            )}
            {arrastavel && (
              <button
                type="button"
                onClick={() => copiar(f.arrasto)}
                className="opacity-0 transition-opacity group-hover:opacity-100 coarse:opacity-70"
                title={`Copiar: ${f.arrasto}`}
              >
                <TbCopy className="h-3 w-3 text-muted-foreground hover:text-foreground" />
              </button>
            )}
          </span>
        </div>
      ))}
    </div>
  )
}

/** Empty state of the data views: why there is nothing yet, and what to do. */
export function SemAmostra({ motivo, deQuem }: {
  motivo: "nao-executado" | "desligado" | "sem-amostra"
  /** Whose data would show here, with the preposition: "de Municipios", "deste nó". */
  deQuem: string
}) {
  const texto = motivo === "desligado"
    ? "O administrador desligou as amostras de dados nesta instalação."
    : motivo === "sem-amostra"
      ? `A última execução não trouxe dados ${deQuem}. O nó pode não ter rodado, ou o histórico da execução já expirou (1 hora).`
      : `Execute o fluxo para ver os dados ${deQuem}.`
  return (
    <div className="flex flex-col items-center gap-1.5 px-2 py-5 text-center text-xs text-muted-foreground">
      {motivo === "desligado" ? <TbTableOff size={22} /> : <TbPlayerPlay size={20} />}
      <span className="font-medium text-foreground">
        {motivo === "desligado" ? "Amostras de dados desligadas" : "Ainda sem dados de execução"}
      </span>
      <span className="max-w-[34ch]">{texto}</span>
    </div>
  )
}

export function SeloAnterior() {
  return (
    <span
      className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
      title="Dados da execução anterior: a execução atual ainda não chegou a este nó"
    >
      da execução anterior
    </span>
  )
}
