"use client"

/**
 * Data views shared by the node modal's Entradas and Saídas panels
 * (docs/specs/node-data-panels.md §6.2): Schema / Tabela / Mapa / JSON over
 * the sample each node sends after a run started from the editor.
 *
 * Insert rules are the panels' (the same as before the redesign): a key inserts
 * `{{ Alias.key }}`, a column inserts its name, a JSON leaf inserts
 * `{{ Alias.key.path }}` — by dragging, or by clicking with a form field
 * selected (insercao.ts). Whoever renders decides whether something can be
 * inserted at all (`arrastavel` / `inserivel`).
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import { TbCopy, TbGripVertical, TbLoader, TbPlayerPlay, TbPointer, TbSearch, TbTableOff } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { createToast } from "@/utils/createToast"
import {
  isGeometria, type AmostraCelula, type AmostraColuna, type AmostraMapa, type AmostraSaida, type AmostraTabela,
} from "@/types/amostra"
import { inserirNoAlvo, useRotuloDoAlvo } from "./insercao"

export type Visao = "schema" | "tabela" | "mapa" | "json"

const VISOES: { id: Visao; rotulo: string }[] = [
  { id: "schema", rotulo: "Schema" },
  { id: "tabela", rotulo: "Tabela" },
  { id: "mapa", rotulo: "Mapa" },
  { id: "json", rotulo: "JSON" },
]

const VISOES_VALIDAS = new Set<string>(VISOES.map(v => v.id))

/** The view picked in each panel, remembered across modals (per browser). */
export function useVisaoLembrada(painel: "entradas" | "saidas", comDados: boolean): [Visao, (v: Visao) => void] {
  const chave = `atlans:painel-no:${painel}:visao`
  const [escolhida, setEscolhida] = useState<Visao | null>(null)

  useEffect(() => {
    try {
      const salva = window.localStorage.getItem(chave)
      if (salva && VISOES_VALIDAS.has(salva)) setEscolhida(salva as Visao)
    } catch { /* no storage: the default applies */ }
  }, [chave])

  const definir = useCallback((v: Visao) => {
    setEscolhida(v)
    try { window.localStorage.setItem(chave, v) } catch { /* ignore */ }
  }, [chave])

  // Without a choice: Tabela when there is data to show, Schema otherwise.
  return [escolhida ?? (comDados ? "tabela" : "schema"), definir]
}

export function SeletorDeVisao({ visao, onChange, desabilitar = [], comMapa = false }: {
  visao: Visao
  onChange: (v: Visao) => void
  desabilitar?: Visao[]
  /** The current output has geometries to draw: shows the Mapa view. */
  comMapa?: boolean
}) {
  return (
    <div role="group" aria-label="Visão dos dados" className="inline-flex shrink-0 rounded-md bg-muted p-0.5">
      {VISOES.filter(v => comMapa || v.id !== "mapa").map(({ id, rotulo }) => {
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

/** Click on a key/column: into the selected form field, or to the clipboard
 *  when no field was selected yet (and the toast says how to insert directly). */
export function inserirOuCopiar(texto: string) {
  const onde = inserirNoAlvo(texto)
  if (onde?.aceitou) {
    createToast.success(`Inserido em “${onde.rotulo}”`, texto)
    return
  }
  if (onde) {
    createToast.info(`“${onde.rotulo}” não aceitou ${texto}`, "Selecione outro campo e clique de novo.")
    return
  }
  copiar(texto)
  createToast.info("Copiado", "Clique antes num campo do formulário para inserir direto nele.")
}

/** One line over the Entradas data saying what a click does right now. */
export function DicaDeInsercao({ python = false }: { python?: boolean }) {
  const alvo = useRotuloDoAlvo()
  return (
    <p className="flex items-start gap-1.5 rounded-md bg-primary/5 px-2 py-1.5 text-[11px] leading-snug text-foreground/80">
      <TbPointer className="mt-px h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
      <span>
        {alvo
          ? <>Clique numa {python ? "chave ou coluna" : "chave, coluna ou valor"} para inserir em <strong className="font-semibold">“{alvo}”</strong>.</>
          : <>Selecione um campo do formulário e clique numa chave ou coluna para inserir. Arrastar também funciona.</>}
      </span>
    </p>
  )
}

/** "Executar até este nó": the button of the panels' empty states. */
export function BotaoExecutarAteAqui({ onExecutar, executando, compacto = false }: {
  onExecutar: () => void
  executando: boolean
  compacto?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onExecutar}
      disabled={executando}
      title="Aplica o formulário e roda só este nó e os nós de que ele depende"
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md bg-primary font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-wait disabled:opacity-70",
        compacto ? "min-h-8 px-2.5 text-[11px]" : "min-h-9 px-3 text-xs",
      )}
    >
      {executando ? <TbLoader className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <TbPlayerPlay className="h-3.5 w-3.5" aria-hidden />}
      {executando ? "Executando…" : "Executar até este nó"}
    </button>
  )
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

/** Above this many columns the table offers a filter by column name. */
const COLUNAS_PARA_FILTRO = 6

export function VisaoTabela({ saida, inserivel = false }: {
  saida: AmostraTabela
  /** Clicking (or dragging) a column header inserts its name. */
  inserivel?: boolean
}) {
  const [filtro, setFiltro] = useState("")
  const termo = filtro.trim().toLowerCase()
  const visiveis = useMemo(
    () => saida.columns
      .map((c, i) => ({ c, i }))
      .filter(({ c }) => !termo || c.name.toLowerCase().includes(termo)),
    [saida.columns, termo],
  )
  if (saida.columns.length === 0) {
    return <p className="py-4 text-center text-xs text-muted-foreground">Tabela sem colunas.</p>
  }
  const parcial = saida.rows.length < saida.rows_total
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-xs font-semibold tabular-nums text-foreground">
          {parcial
            ? `${saida.rows.length} de ${saida.rows_total.toLocaleString("pt-BR")} linhas`
            : `${saida.rows_total.toLocaleString("pt-BR")} linha(s)`}
        </span>
        <span className="text-[10px] text-muted-foreground">
          {saida.columns.length} coluna(s){saida.truncated.columns ? " (cortadas)" : ""}
          {saida.crs ? ` · ${saida.crs}` : ""}
          {parcial ? " · amostra" : ""}
        </span>
      </div>
      {saida.columns.length > COLUNAS_PARA_FILTRO && (
        <label className="flex h-7 items-center gap-1.5 rounded-md border px-2 focus-within:ring-1 focus-within:ring-primary">
          <TbSearch className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden />
          <span className="sr-only">Filtrar colunas</span>
          <input
            type="search"
            value={filtro}
            onChange={e => setFiltro(e.target.value)}
            placeholder="Filtrar colunas"
            // Not a target for click-to-insert: it filters the panel itself.
            data-sem-insercao
            className="min-w-0 flex-1 bg-transparent text-[11px] outline-none"
          />
          {termo && <span className="shrink-0 text-[10px] text-muted-foreground">{visiveis.length}/{saida.columns.length}</span>}
        </label>
      )}
      <div className="max-h-[52vh] overflow-auto rounded-md border">
        <table className="w-max min-w-full border-collapse text-[11px] tabular-nums">
          <thead>
            <tr>
              <th className="sticky top-0 z-[1] bg-muted px-2 py-1 text-right font-normal text-muted-foreground">#</th>
              {visiveis.map(({ c }) => (
                <th
                  key={c.name}
                  draggable={inserivel}
                  onDragStart={inserivel ? e => iniciarArrasto(e, c.name) : undefined}
                  className={cn(
                    "sticky top-0 z-[1] whitespace-nowrap bg-muted px-2 py-1 text-left font-semibold",
                    inserivel && "cursor-grab active:cursor-grabbing",
                  )}
                >
                  {inserivel ? (
                    <button
                      type="button"
                      onClick={() => inserirOuCopiar(c.name)}
                      title={`Clique ou arraste para inserir ${c.name}`}
                      className="text-left font-semibold text-primary hover:underline"
                    >
                      {c.name}
                    </button>
                  ) : c.name}
                  <span className="block font-mono text-[9px] font-normal lowercase text-muted-foreground">{rotuloDoTipo(c.type)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {saida.rows.map((linha, i) => (
              <tr key={i} className="hover:bg-primary/5">
                <td className="border-t px-2 py-1 text-right text-muted-foreground">{i + 1}</td>
                {visiveis.map(({ i: j }) => {
                  const valor = linha[j]
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
    </div>
  )
}

/** The sample's geometries drawn small (no basemap, the layer's own CRS). */
export function VisaoMapa({ mapa, saida }: { mapa: AmostraMapa; saida: AmostraTabela }) {
  const margem = Math.max(mapa.w, mapa.h) * 0.04
  const raio = Math.max(mapa.w, mapa.h) * 0.008
  const traco = Math.max(mapa.w, mapa.h) * 0.003
  const desenhadas = mapa.features.length
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <svg
        role="img"
        aria-label={`Mapa das ${desenhadas} feições da amostra`}
        viewBox={`${-margem} ${-margem} ${mapa.w + 2 * margem} ${mapa.h + 2 * margem}`}
        preserveAspectRatio="xMidYMid meet"
        className="max-h-[52vh] w-full rounded-md border bg-sky-50/60 dark:bg-sky-950/30"
      >
        {mapa.features.map((f, i) => (
          "p" in f
            ? <circle key={i} cx={f.p[0]} cy={f.p[1]} r={raio} className="fill-primary stroke-background" strokeWidth={traco * 0.6} />
            : (
              <path
                key={i}
                d={f.d}
                fillRule="evenodd"
                strokeWidth={traco}
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                className={f.area ? "fill-primary/20 stroke-primary" : "fill-none stroke-primary"}
              />
            )
        ))}
      </svg>
      <span className="text-[10px] text-muted-foreground">
        {desenhadas} feição(ões) da amostra{saida.rows_total > saida.rows.length ? ` de ${saida.rows_total.toLocaleString("pt-BR")}` : ""}
        {saida.crs ? ` · ${saida.crs}` : ""} · sem mapa de fundo
      </span>
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
              {expr ? (
                <button
                  type="button"
                  draggable
                  onDragStart={e => iniciarArrasto(e, expr)}
                  onClick={() => inserirOuCopiar(expr)}
                  title={`Clique ou arraste para inserir ${expr}`}
                  className="cursor-pointer font-mono text-primary hover:underline"
                >
                  &quot;{k}&quot;
                </button>
              ) : (
                <span className="text-primary">&quot;{k}&quot;</span>
              )}
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
export function VisaoDaSaida({ saida, visao, exprDe, onVerJson, inserivel = false }: {
  saida: AmostraSaida
  visao: "tabela" | "mapa" | "json"
  exprDe?: (caminho: string[]) => string
  onVerJson: () => void
  /** Column headers insert their name on click/drag (Entradas panel). */
  inserivel?: boolean
}) {
  if (saida.kind === "omitted") return <SaidaOmitida motivo={saida.reason} />
  if (visao === "mapa" && saida.kind === "table" && saida.map) return <VisaoMapa mapa={saida.map} saida={saida} />
  if (visao === "tabela" || visao === "mapa") {
    if (saida.kind === "table") return <VisaoTabela saida={saida} inserivel={inserivel} />
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
          className={cn(
            "group grid grid-cols-[12px_minmax(0,1fr)_auto] items-center gap-1.5 rounded px-1 py-0.5",
            arrastavel ? "cursor-grab hover:bg-muted active:cursor-grabbing" : "cursor-default",
          )}
        >
          {arrastavel ? <TbGripVertical className="h-3 w-3 text-muted-foreground/40 group-hover:text-muted-foreground" /> : <span />}
          <span className="min-w-0 truncate">
            {arrastavel ? (
              <button
                type="button"
                onClick={() => inserirOuCopiar(f.arrasto)}
                title={`Clique ou arraste para inserir ${f.arrasto}`}
                className="font-mono text-[11px] hover:text-primary hover:underline"
              >
                {f.nome}
              </button>
            ) : (
              <code className="font-mono text-[11px]">{f.nome}</code>
            )}
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
export function SemAmostra({ motivo, deQuem, onExecutar, executando = false }: {
  motivo: "nao-executado" | "desligado" | "sem-amostra"
  /** Whose data would show here, with the preposition: "de Municipios", "deste nó". */
  deQuem: string
  /** "Executar até este nó". Omitted: no button (samples off, or no workflow). */
  onExecutar?: () => void
  executando?: boolean
}) {
  const texto = motivo === "desligado"
    ? "O administrador desligou as amostras de dados nesta instalação."
    : motivo === "sem-amostra"
      ? `A última execução não trouxe dados ${deQuem}. O nó pode não ter rodado, ou o histórico da execução já expirou (1 hora).`
      : onExecutar
        ? `Roda só os nós necessários e mostra as primeiras linhas ${deQuem}, sem sair desta tela.`
        : `Execute o fluxo para ver os dados ${deQuem}.`
  return (
    <div className="flex flex-col items-center gap-1.5 px-2 py-5 text-center text-xs text-muted-foreground">
      {motivo === "desligado" ? <TbTableOff size={22} /> : <TbPlayerPlay size={20} />}
      <span className="font-medium text-foreground">
        {motivo === "desligado" ? "Amostras de dados desligadas" : "Ainda sem dados de execução"}
      </span>
      <span className="max-w-[34ch]">{texto}</span>
      {onExecutar && motivo !== "desligado" && (
        <div className="mt-2"><BotaoExecutarAteAqui onExecutar={onExecutar} executando={executando} /></div>
      )}
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
