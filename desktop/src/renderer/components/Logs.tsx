// desktop/src/renderer/components/Logs.tsx
//
// Log panel with filter, search and export.
//
// The lines come from two sources that the store mixes on purpose, because for
// someone investigating a problem they tell the same story in order:
//
//   structured — `{"t":"log"}` events from the NDJSON channel, with level and alias
//   raw        — the process stderr (formatted human log) and any
//                `print()` from a workflow node
//
// The level only exists in the structured ones. The raw ones are marked as RAW
// instead of having their level guessed by a regex over the message — which is
// exactly what rotted the previous app.
import {
  memo, useDeferredValue, useEffect, useLayoutEffect, useMemo, useRef, useState,
} from 'react'
import {
  TbArrowDown, TbDownload, TbFileText, TbFolderOpen, TbSearch, TbSearchOff, TbX,
} from 'react-icons/tb'
import type { VisibleLine } from '../lib/useLog.js'
import { Button } from './ui/button.js'
import { Input } from './ui/input.js'
import { cn } from '../lib/utils.js'

const LEVELS = ['ERROR', 'WARN', 'INFO', 'DEBUG', 'RAW'] as const
type Nivel = (typeof LEVELS)[number]

/** Color of the message TEXT. Only where the color carries meaning. */
const COLORS: Record<string, string> = {
  ERROR: 'text-destructive',
  WARN: 'text-yellow-600 dark:text-yellow-500',
  RAW: 'text-muted-foreground',
}

/** Level marker in the filter — a dot, so the chip does not become a block. */
const DOTS: Record<Nivel, string> = {
  ERROR: 'bg-destructive',
  WARN: 'bg-yellow-500',
  INFO: 'bg-sky-500',
  DEBUG: 'bg-muted-foreground',
  RAW: 'bg-muted-foreground/50',
}

/** Row background strip. Only ERROR and WARN — the rest would be pointless zebra. */
const BACKGROUNDS: Record<string, string> = {
  ERROR: 'bg-destructive/8',
  WARN: 'bg-yellow-500/8',
}

function hora(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString('pt-BR', { hour12: false })
}

/**
 * Highlights the searched term inside the message.
 *
 * Without this, searching a thousand-line log returns thirty similar lines and
 * the eye still needs to scan each one for where the match is.
 */
function Highlighted({ texto, termo }: { texto: string; termo: string }) {
  if (!termo) return <>{texto}</>

  const partes: Array<{ t: string; hit: boolean }> = []
  const alvo = texto.toLowerCase()
  const busca = termo.toLowerCase()
  let i = 0
  // Index scan instead of regex: the term is typed by the user and may contain
  // `(`, `[`, `\` — building a regex with it would throw.
  for (;;) {
    const achou = alvo.indexOf(busca, i)
    if (achou === -1) break
    if (achou > i) partes.push({ t: texto.slice(i, achou), hit: false })
    partes.push({ t: texto.slice(achou, achou + busca.length), hit: true })
    i = achou + busca.length
  }
  if (i < texto.length) partes.push({ t: texto.slice(i), hit: false })

  return (
    <>
      {partes.map((p, k) => p.hit
        ? <mark key={k} className="rounded-sm bg-primary/30 text-inherit">{p.t}</mark>
        : <span key={k}>{p.t}</span>)}
    </>
  )
}

/**
 * How many lines stay in the output DOM.
 *
 * The buffer reaches 1000, and mounting all 1000 is expensive on every render —
 * worse, each new batch re-rendered all of them. With the bounded window and
 * the `memo` below, a batch of 5 lines mounts 5 nodes and leaves the rest
 * untouched.
 *
 * The number is generous enough to scroll a good way before needing the
 * "mostrar anteriores" (show earlier) button.
 */
const WINDOW_SIZE = 400

/**
 * One log line.
 *
 * `memo` + the `seq` key is what makes the list stop rebuilding itself
 * entirely: the line object is never mutated (the main process creates it once
 * and delivers it in a single batch), so the props of an old line are identical
 * between renders and React skips the work.
 *
 * The key is `seq`, and NOT the index: the buffer is trimmed from the start,
 * and with the index every line would change key on each discard —
 * invalidating the memoization exactly when it matters most, with the log full.
 */
const LogRow = memo(function LogRow({
  linha, termo,
}: {
  linha: VisibleLine
  termo: string
}) {
  return (
    <div className={cn('flex gap-3 px-3 py-0.5 hover:bg-muted/40', BACKGROUNDS[linha.level])}>
      <span className="shrink-0 text-muted-foreground/70 tabular-nums">{hora(linha.ts)}</span>
      {/* Fixed width so the messages stay in a single column: with automatic
          width, each different alias misaligned everything. */}
      <span className="w-12 shrink-0 truncate text-muted-foreground" title={linha.alias}>
        {linha.alias}
      </span>
      <span className={cn('min-w-0 whitespace-pre-wrap break-words', COLORS[linha.level])}>
        <Highlighted texto={linha.msg} termo={termo} />
      </span>
    </div>
  )
})

/**
 * Log panel.
 *
 * ALWAYS lives in its own window, opened by the button in the footer bar —
 * reading a log is almost always comparing it with something else, and a tab
 * forces you to choose between the two. That is why there is no longer an
 * "embedded" mode nor the pop-out button: the screen fills the whole window,
 * which is the only form in which it exists.
 */
export function Logs({ linhas, pastaDeLogs }: {
  linhas: VisibleLine[]
  /** Folder of the log files — enables the shortcut in the footer. */
  pastaDeLogs?: string
}) {
  const [busca, setSearch] = useState('')
  const [ocultos, setHidden] = useState<Set<Nivel>>(new Set())
  const [exportado, setExported] = useState<string | null>(null)
  const areaRef = useRef<HTMLDivElement>(null)
  // Auto-scroll only while the user is at the end. Always scrolling would yank
  // the screen away from someone who scrolled up to read an old line — and a
  // new line arrives every second.
  const [seguindo, setFollowing] = useState(true)
  const [limite, setLimit] = useState(WINDOW_SIZE)
  // Position saved before growing the window — see `showEarlier`.
  const ancora = useRef<{ altura: number; topo: number } | null>(null)

  const contagem = useMemo(() => {
    const c: Record<string, number> = {}
    for (const l of linhas) c[l.level] = (c[l.level] ?? 0) + 1
    return c
  }, [linhas])

  /**
   * The term the FILTER uses — deferred on purpose.
   *
   * `busca` paints the letter on the screen; `termo` only catches up one render
   * later, and it is what refilters the buffer and rebuilds the list. Without
   * this separation, each keystroke did both things in the same render and the
   * letter only appeared after the filter finished.
   */
  const termo = useDeferredValue(busca.trim().toLowerCase())

  const visiveis = useMemo(() => (
    // `l.busca` already comes lowercased (see useLog.ts): before, it was two string
    // allocations per line, 2000 per keystroke.
    linhas.filter((l) => {
      if (ocultos.has(l.level as Nivel)) return false
      return !termo || l.busca.includes(termo)
    })
  ), [linhas, termo, ocultos])

  // The slice that goes to the DOM. Memoized so the scroll effect has a stable
  // dependency: loose, the `slice` returned a new array on every render and the
  // effect forced layout even when the list had not changed.
  const recorte = useMemo(
    () => (visiveis.length > limite ? visiveis.slice(-limite) : visiveis),
    [visiveis, limite],
  )

  /**
   * Grows the rendered window, without moving what the person is reading.
   *
   * The lines come in ABOVE the current position, which pushes all the content
   * down. Without compensating, clicking "mostrar anteriores" (show earlier)
   * makes the screen jump and the line being read disappears — the opposite of
   * what the button promises.
   */
  function showEarlier() {
    const el = areaRef.current
    if (el) ancora.current = { altura: el.scrollHeight, topo: el.scrollTop }
    setLimit((n) => n + WINDOW_SIZE)
  }

  // `useLayoutEffect` and not `useEffect`: scrolling after paint produces a
  // visible jump on every new line.
  //
  // WITH a dependency list: without it the effect ran after EVERY render —
  // including those that only changed the search field text — and each pass
  // read `scrollHeight`, which forces layout on the spot.
  useLayoutEffect(() => {
    const el = areaRef.current
    if (!el) return

    if (ancora.current) {
      // Restores by the height DIFFERENCE: it is exactly how much the content
      // moved down when gaining lines at the top.
      el.scrollTop = ancora.current.topo + (el.scrollHeight - ancora.current.altura)
      ancora.current = null
      return
    }
    if (seguindo) el.scrollTop = el.scrollHeight
  }, [recorte, seguindo])

  // A new filter changes the whole content; going back to the end is what the
  // user expects from "apply filter". The window goes back to the default size
  // along with it: the previous slice was over another set of lines.
  //
  // Depends on `termo`, not `busca`: it is the filtering that changes the
  // content, and it arrives one render after the keystroke.
  useEffect(() => { setFollowing(true); setLimit(WINDOW_SIZE) }, [termo, ocultos])

  function handleScroll() {
    const el = areaRef.current
    if (!el) return
    // 24px of tolerance: requiring the exact end makes wheel scrolling, which
    // moves in steps, turn off follow mode without the user having asked.
    setFollowing(el.scrollHeight - el.scrollTop - el.clientHeight < 24)
  }

  function alternar(n: Nivel) {
    const novo = new Set(ocultos)
    if (novo.has(n)) novo.delete(n)
    else novo.add(n)
    setHidden(novo)
  }

  async function exportar() {
    // Exports what is VISIBLE, not everything: someone who filtered to isolate a
    // problem wants to send that, not 1000 lines of noise around it.
    const texto = visiveis
      .map((l) => `${hora(l.ts)} ${l.level.padEnd(5)} ${l.alias.padEnd(6)} ${l.msg}`)
      .join('\n')
    const caminho = await window.atlas.exportarLog(texto)
    if (caminho) setExported(caminho)
  }

  const filtrando = Boolean(termo) || ocultos.size > 0

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex h-9 min-w-56 flex-1 items-center">
          <TbSearch size={15} className="pointer-events-none absolute left-3 text-muted-foreground" />
          <Input
            value={busca}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar no log…"
            spellCheck={false}
            aria-label="Buscar no log"
            className="h-full pr-8 pl-9 select-text"
          />
          {busca && (
            <button type="button" onClick={() => setSearch('')} aria-label="Limpar busca"
                    className="absolute right-2 rounded-sm p-1 text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-ring/50 focus-visible:ring-2 animate-in fade-in-0 zoom-in-75 duration-150">
              <TbX size={14} />
            </button>
          )}
        </div>

        <Button variant="outline" size="sm" disabled={visiveis.length === 0} onClick={exportar}
                title="Salva TODAS as linhas que passam pelo filtro atual — não só as visíveis na janela">
          <TbDownload size={15} /> Exportar
        </Button>
      </div>

      {/* Level chips on a row of their own: next to the search they wrapped
          to the line below in a narrow window and the alignment fell apart. */}
      <div className="flex flex-wrap items-center gap-1.5">
        {LEVELS.map((n) => {
          const escondido = ocultos.has(n)
          const total = contagem[n] ?? 0
          return (
            <button
              key={n}
              type="button"
              aria-pressed={!escondido}
              onClick={() => alternar(n)}
              title={escondido ? `Mostrar ${n}` : `Ocultar ${n}`}
              className={cn(
                'flex items-center gap-1.5 rounded-full border py-1 pr-2.5 pl-2 text-[11px] font-medium outline-none',
                'transition-colors focus-visible:ring-ring/50 focus-visible:ring-2',
                escondido
                  ? 'border-input text-muted-foreground/60 hover:text-muted-foreground'
                  : 'border-transparent bg-muted text-foreground',
              )}
            >
              <span className={cn(
                'size-1.5 shrink-0 rounded-full transition-opacity',
                DOTS[n], escondido && 'opacity-30',
              )} />
              <span className="font-mono">{n}</span>
              <span className={cn('tabular-nums', escondido ? 'opacity-60' : 'text-muted-foreground')}>
                {total}
              </span>
            </button>
          )
        })}

        {filtrando && (
          <button
            type="button"
            onClick={() => { setSearch(''); setHidden(new Set()) }}
            className="ml-1 text-[11px] text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            limpar filtros
          </button>
        )}
      </div>

      {exportado && (
        <p className="text-xs text-muted-foreground">
          Salvo em <span className="font-mono select-text">{exportado}</span>
        </p>
      )}

      {/* ── Log area ────────────────────────────────────────────────── */}
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border bg-card">
        {visiveis.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
            {linhas.length === 0
              ? <TbFileText size={26} className="text-muted-foreground/50" />
              : <TbSearchOff size={26} className="text-muted-foreground/50" />}
            <p className="text-sm text-muted-foreground">
              {linhas.length === 0
                ? 'Sem registros ainda. As linhas aparecem aqui assim que o executor iniciar.'
                : `Nenhuma das ${linhas.length} linhas em memória corresponde ao filtro.`}
            </p>
          </div>
        ) : (
          <div
            ref={areaRef}
            onScroll={handleScroll}
            // `log` brings the panel typography — see the rule in index.css.
            className="log flex min-h-0 flex-1 flex-col overflow-y-auto py-1.5 font-mono select-text"
          >
            {visiveis.length > limite && (
              <button
                type="button"
                onClick={showEarlier}
                className="mx-3 mb-1 rounded-md border border-dashed py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
              >
                mostrar {Math.min(WINDOW_SIZE, visiveis.length - limite)} linha(s) anterior(es)
                {' · '}{visiveis.length - limite} acima
              </button>
            )}
            {recorte.map((l) => (
              <LogRow key={l.seq} linha={l} termo={termo} />
            ))}
          </div>
        )}

        {/* Floats OVER the area, not below it: the button only exists when the
            user has scrolled up, and that is where their eye is. */}
        {!seguindo && visiveis.length > 0 && (
          <button
            type="button"
            onClick={() => setFollowing(true)}
            className="absolute right-4 bottom-3 flex items-center gap-1.5 rounded-full border bg-popover px-3 py-1.5 text-xs font-medium shadow-md transition-colors hover:bg-accent"
          >
            <TbArrowDown size={13} /> Acompanhar o fim
          </button>
        )}
      </div>

      {/* Discreet footer: how many lines are here, and where the rest is.
          The previous mention said to look "em Ajustes" (in Settings) — which
          is now ANOTHER window. Sending someone to switch windows to find a
          path, when the button fits here, is instruction in place of action. */}
      <p className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
        <span>
          {visiveis.length === linhas.length
            ? `${linhas.length} linha(s) em memória`
            : `${visiveis.length} de ${linhas.length} linha(s) em memória`}
          {' · '}o registro completo fica em arquivo
        </span>
        {pastaDeLogs && (
          <button type="button" onClick={() => window.atlas.abrirCaminho(pastaDeLogs)}
                  title={`Abrir no Explorer: ${pastaDeLogs}`}
                  className="inline-flex items-center gap-1 underline-offset-4 hover:text-foreground hover:underline">
            <TbFolderOpen size={13} /> abrir pasta
          </button>
        )}
      </p>
    </div>
  )
}
