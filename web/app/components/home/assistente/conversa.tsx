"use client"

// web/app/components/home/assistente/conversa.tsx
//
// The rendered conversation: turns from whoever asks, turns from the assistant.
//
// The assistant turn is a TIMELINE (`assistente-quadros.ts`), not text blocks
// separate from the steps. That is the choice that gives the model room to
// EXPLAIN what it did between one tool and the next — which is what keeps
// someone from applying a workflow without understanding it, and the reason the
// side drawer beat the command bar.
//
// The SAME Conversa serves as the CAPTION on the Home (`compacta`, the strip
// above the bar): the question on one line, and from each answer only what
// remained — the last text, clipped to 4 lines, the errors and the cards — plus
// what is live (the step in progress). The process (reasoning, completed steps,
// earlier texts) is left out: a caption that showed everything would fill the
// strip up to the ceiling and scroll again; it stays one "Expandir" away, in the panel.

import { useCallback, useEffect, useRef } from "react"
import { TbAlertTriangle, TbChevronRight, TbSparkles } from "react-icons/tb"

import { cn } from "@/lib/utils"
import ExecActivity from "@/app/components/shared/exec-activity"
import type { BlocoDoAssistente, TurnoDoAssistente, PropostaDeFluxo } from "@/app/components/home/assistente/quadros"
import Passo from "./passo"
import type { ErroDoAssistente } from "@/app/components/home/assistente/quadros"
import type { Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela, useTextos } from "../i18n"

/**
 * The on-screen text of an error. In Portuguese it is the server message AS IT
 * CAME (as always). In English and Spanish, a known code becomes the dictionary
 * sentence — the server message is in Portuguese; a new code still shows up as
 * it came, which is better than nothing.
 */
export function textoDoErro(erro: ErroDoAssistente, idioma: Idioma): { message: string; hint?: string } {
  if (idioma === "pt-BR") return { message: erro.message, hint: erro.hint }
  const erros = textosDe(idioma).assistente.erros
  if (!Object.hasOwn(erros, erro.code)) return { message: erro.message, hint: erro.hint }
  const conhecido = erros[erro.code]
  return { message: conhecido.message(erro.teto ?? null), hint: conhecido.hint || undefined }
}

/** What the `Conversa` knows about a block beyond the block itself, for whoever renders the `extras`. */
export interface ContextoDoBloco {
  /** The block is in the LAST turn of the list — the only one where an offer still holds. */
  ultimoTurno: boolean
}

/** The activity indicator of the pending item: an SVG that accepts `size` (the `ExecActivity`; the Home's logo). */
export type IndicadorDeAtividade = React.ComponentType<{ size?: number; className?: string }>

interface Props {
  turnos: TurnoDoAssistente[]
  correndo: boolean
  // Optional: only the editor drawer knows how to draw a proposal on the canvas —
  // it injects the card through here. The Home does not pass it (the HOME surface
  // does not emit `proposta`) and uses `extras` for the blocks only it has.
  proposta?: (proposta: PropostaDeFluxo) => React.ReactNode
  /**
   * Renders the blocks this Conversa does not know (`fluxo`/`camada`/
   * `confirmacao`/`respostas_rapidas` from the Home assistant). Without it, an
   * unknown block disappears. The editor does not pass it — and never emits these
   * types. The `contexto` says whether the block is in the LAST turn: that is what
   * makes the quick replies valid only for that one time.
   */
  extras?: (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => React.ReactNode
  /**
   * What the surface is called in the screen reader announcement. The editor is
   * the "assistente"; on the Home the same conversation is the "assistente", and
   * announcing the wrong name is announcing a screen that does not exist there.
   */
  nome?: string
  /**
   * The empty conversation's invitation. The default talks about the editor
   * (describe a workflow, apply it on the canvas); the Home, which has no canvas, passes its own.
   */
  vazio?: React.ReactNode
  /**
   * The Home's CAPTION view (the strip attached to the bar): the question on one
   * line ("Você · …", truncated, the full text in `title`), and from each answer
   * only what remained — the last text, clipped to 4 lines, the errors and the
   * `extras` cards — plus what is live while the turn runs (the "Trabalhando…" or
   * the step in progress). Reasoning, completed steps and earlier texts are left
   * for the panel. The editor and the panel do not pass it: the whole
   * conversation, as always.
   */
  compacta?: boolean
  /**
   * The activity indicator of the pending item (the "Trabalhando…" of a turn with
   * no block and the live reasoning). The default is the editor's `ExecActivity` —
   * a single "busy" vocabulary, the same as the running node. The Home passes the
   * animated logo (`assistente/marca-animada.tsx`): there, the one thinking is the site.
   */
  indicador?: IndicadorDeAtividade
  /**
   * A blinking cursor at the end of the paragraph being written (the last group
   * of the turn in progress), like the one in the Home's typed suggestion. Opt-in
   * by the Home (`.home-caret` lives in its CSS); the editor does not pass it and stays the same.
   */
  cursorAoEscrever?: boolean
}

export default function Conversa({
  turnos, correndo, proposta, extras,
  nome = "assistente", vazio, compacta = false,
  indicador: Indicador = ExecActivity, cursorAoEscrever = false,
}: Props) {
  const t = useTextos().assistente.conversa
  const fimRef = useRef<HTMLDivElement>(null)
  const grudadoRef = useRef(true)

  // Scrolls only when already at the bottom. Someone who scrolled up to reread an
  // explanation must not be dragged back on every text delta.
  useEffect(() => {
    if (grudadoRef.current) fimRef.current?.scrollIntoView({ block: "end" })
  }, [turnos])

  function aoRolar(e: React.UIEvent<HTMLDivElement>) {
    const el = e.currentTarget
    grudadoRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48
  }

  // Opening a `<details>` increases `scrollHeight` WITHOUT firing a `scroll`
  // event — content growth does not fire it. So `grudadoRef` stays stuck at the
  // last value read, almost always `true`, and the next delta drags back to the
  // bottom: the click of someone who only wanted to read the reasoning is undone
  // on its own. Whoever opens an OLD block unsticks; whoever opens the one being
  // written keeps following, which is what is wanted in both cases.
  const desgrudar = useCallback(() => { grudadoRef.current = false }, [])

  const idDoUltimo = turnos[turnos.length - 1]?.id

  return (
    // `min-h-0` is NOT a detail: without it the layout breaks as the conversation
    // grows. A flex child starts with `min-height: auto`, so `flex-1` +
    // `overflow-y-auto` does not shrink below its content — the list pushes the
    // send form out of the drawer instead of scrolling. The symptom shows up
    // only after a few turns, which is what makes it hard to find.
    // `min-w-0` for the same reason on the other axis, with the drawer at 300px.
    //
    // And this container ALWAYS exists, including with an empty conversation.
    // Before, the empty state was an early return, a sibling of the form with no
    // scrolling at all: with the drawer gaining a height ceiling, ~300px of
    // invitation plus the header and the form do not fit in a short viewport
    // (phone in landscape, short window) and the send field would leave the
    // screen with nothing to scroll — precisely on `/workflow/create`, where the
    // drawer starts open.
    <div
      // The caption has no padding of its own: the strip (`.home-pilha`) provides it.
      className={cn("nowheel min-h-0 min-w-0 flex-1 overflow-y-auto", !compacta && "px-3 py-3")}
      onScroll={aoRolar}
      aria-busy={correndo}
    >
      {/* The screen reader announcement is COARSE, and the list is NOT `aria-live`.
          The model's text arrives in dozens of deltas that pile up in the same
          paragraph; a live region there would re-announce the whole answer on
          every chunk, and the person would never hear the end of any sentence. */}
      <p className="sr-only" role="status">
        {correndo ? t.respondendo(nome) : ""}
      </p>

      {turnos.length === 0 ? (vazio ?? <Vazio />) : (
        <>
          <ol className={cn("flex min-w-0 flex-col", compacta ? "gap-1.5" : "gap-4")}>
            {turnos.map(turno => (
              <li key={turno.id}>
                {turno.papel === "user" ? <Pergunta texto={turno.texto ?? ""} compacta={compacta} /> : (
                  <Resposta
                    turno={turno}
                    proposta={proposta}
                    extras={extras}
                    compacta={compacta}
                    // The model turn that is running is, by construction, the
                    // LAST one in the list. There is no new state here.
                    pensando={correndo && turno.id === idDoUltimo}
                    ultimoTurno={turno.id === idDoUltimo}
                    Indicador={Indicador}
                    cursorAoEscrever={cursorAoEscrever}
                    onDesgrudar={desgrudar}
                  />
                )}
              </li>
            ))}
          </ol>
          <div ref={fimRef} />
        </>
      )}
    </div>
  )
}

function Pergunta({ texto, compacta }: { texto: string; compacta: boolean }) {
  const t = useTextos().assistente.conversa
  if (compacta) {
    // One line: "Você · pergunta", truncated, with the full text in `title`.
    // The question sits in its own `<span>`, not loose next to "Você": it is
    // what the screen reader reads and what someone searching for the sentence finds.
    return (
      <p className="truncate text-xs text-muted-foreground" title={texto}>
        <span className="text-primary">{t.voce}</span> · <span>{texto}</span>
      </p>
    )
  }
  return (
    <p className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap break-words rounded-lg rounded-br-sm bg-primary/10 px-3 py-2 text-sm text-foreground">
      {texto}
    </p>
  )
}

function Resposta({
  turno,
  proposta,
  extras,
  pensando,
  compacta,
  ultimoTurno,
  Indicador,
  cursorAoEscrever,
  onDesgrudar,
}: {
  turno: TurnoDoAssistente
  proposta?: (proposta: PropostaDeFluxo) => React.ReactNode
  extras?: (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => React.ReactNode
  /** This turn is the one being written right now. */
  pensando: boolean
  compacta: boolean
  /** This turn is the last in the list (the `extras` know: an offer only holds there). */
  ultimoTurno: boolean
  Indicador: IndicadorDeAtividade
  cursorAoEscrever: boolean
  onDesgrudar: () => void
}) {
  if (!turno.blocos.length) return <Pensando Indicador={Indicador} />

  // Consecutive steps become a single list: five `<ul>` of one item each
  // drew five loose blocks where there is a sequence.
  const grupos: BlocoDoAssistente[][] = []
  for (const bloco of turno.blocos) {
    const ultimo = grupos[grupos.length - 1]
    if (bloco.tipo === "ferramenta" && ultimo?.[0]?.tipo === "ferramenta") ultimo.push(bloco)
    else grupos.push([bloco])
  }

  // In the caption (`compacta`) only what REMAINED goes in — the last text, the
  // errors and the cards — plus what is LIVE: the last group while the turn runs
  // (the "Trabalhando…" or the step in progress). Reasoning and completed steps,
  // and the texts before the last one, are left for the panel. The stored index
  // is the ORIGINAL one (the `key` and `pensandoAgora` depend on it): the filter
  // must not shift ownership.
  const ultimoTexto = grupos.map((g) => g[0].tipo).lastIndexOf("texto")
  const vivo = grupos.length - 1
  const visiveis = grupos
    .map((grupo, i) => ({ grupo, i }))
    .filter(({ grupo, i }) => {
      if (!compacta) return true
      const tipo = grupo[0].tipo
      if (tipo === "texto") return i === ultimoTexto
      if (tipo === "pensando" || tipo === "ferramenta") return pensando && i === vivo
      return true // `erro` and the Home's cards; `proposta` never reaches the Home
    })

  return (
    <div className="flex min-w-0 flex-col gap-2">
      {visiveis.map(({ grupo, i }) => (
        <Grupo
          key={i}
          grupo={grupo}
          proposta={proposta}
          extras={extras}
          // The `key={i}` is safe because the indices are APPEND-ONLY: `acumular`
          // replaces the last block or appends, `mapearFerramenta` replaces in
          // place, and everything else appends. No group shifts in the middle, so
          // an open <details> does not jump owners during the stream. If some new
          // frame starts inserting a block in the MIDDLE, this no longer holds.
          pensandoAgora={pensando && i === vivo}
          compacta={compacta}
          ultimoTurno={ultimoTurno}
          Indicador={Indicador}
          cursorAoEscrever={cursorAoEscrever}
          onDesgrudar={onDesgrudar}
        />
      ))}
    </div>
  )
}

function Grupo({
  grupo,
  proposta,
  extras,
  pensandoAgora,
  compacta,
  ultimoTurno,
  Indicador,
  cursorAoEscrever,
  onDesgrudar,
}: {
  grupo: BlocoDoAssistente[]
  proposta?: (proposta: PropostaDeFluxo) => React.ReactNode
  extras?: (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => React.ReactNode
  /** This is the last group of a turn in progress — that is, the live one. */
  pensandoAgora: boolean
  compacta: boolean
  ultimoTurno: boolean
  Indicador: IndicadorDeAtividade
  cursorAoEscrever: boolean
  onDesgrudar: () => void
}) {
  const primeiro = grupo[0]
  const idioma = useIdiomaDaTela()
  const t = textosDe(idioma).assistente.conversa

  if (primeiro.tipo === "ferramenta") {
    // In the caption, only the step in progress: the earlier ones in the group are done.
    const passos = compacta ? grupo.slice(-1) : grupo
    return (
      <ul className="rounded-md border border-dashed bg-muted/30 px-2.5 py-1">
        {passos.map((b, i) => (
          b.tipo === "ferramenta" ? <Passo key={`${b.id}-${i}`} bloco={b} /> : null
        ))}
      </ul>
    )
  }

  if (primeiro.tipo === "pensando") {
    // COLLAPSED by default, no longer always open.
    //
    // The text comes in ENGLISH and there is no way to ask for another language:
    // with `display: "summarized"` the raw thinking never comes back, and the
    // summary is generated by a separate step that does not obey the "Responda
    // sempre em {ASSISTENTE_IDIOMA}" of the system prompt (`app/services/assistente/editor_service.py`).
    // Translating would cost another model call per block and would kill
    // precisely the streaming. So: while the model thinks there is only the
    // animation, and the text remains one click away — in the DOM, findable by
    // Ctrl+F and by screen readers.
    //
    // Native `<details>` and not `useState`: the open state lives in the DOM, so
    // rebuilding the turns on every delta does not close it; and `<summary>` is
    // already focusable and already announces collapsed/expanded without
    // `aria-expanded`. Pattern copied from `components/executores/dialogs.tsx`.
    return (
      <details
        className="group rounded-md border-l-2 border-primary/40 bg-muted/20 py-1.5 pl-2.5 pr-2"
        onToggle={pensandoAgora ? undefined : onDesgrudar}
      >
        <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/80 transition-colors hover:text-muted-foreground [&::-webkit-details-marker]:hidden">
          {pensandoAgora ? (
            <>
              <Indicador size={12} />
              {/* The label gets the sweeping shimmer (the bar's "Trabalhando…" system)
                  and the ellipsis is TYPED by the ::after of .tic-pensando —
                  life in the indicator without exposing the reasoning, which
                  stays collapsed (and in English) on purpose. The real "…" stays
                  in sr-only: the screen reader and the tests read "Trabalhando…",
                  while the eye sees the dots appear one by one. */}
              <span className="texto-pensando">
                {t.trabalhando}
                <span className="tic-pensando" aria-hidden="true" />
                <span className="sr-only">…</span>
              </span>
            </>
          ) : t.raciocinio}
          <TbChevronRight
            size={12}
            className="ml-auto shrink-0 transition-transform group-open:rotate-90"
            aria-hidden="true"
          />
        </summary>
        {/* `lang="en"`: the content IS English, demonstrably, and without this the
            screen reader spells it out with Portuguese phonetics. */}
        <p lang="en" className="mt-1 whitespace-pre-wrap break-words text-xs leading-relaxed text-muted-foreground">
          {primeiro.texto}
        </p>
      </details>
    )
  }

  if (primeiro.tipo === "texto") {
    return (
      // In the caption the answer is clipped to 4 lines; the full text stays in the panel.
      // The cursor only on the LIVE paragraph: it disappears when a tool follows it
      // or the turn ends.
      <p className={cn("whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground", compacta && "line-clamp-4")}>
        {primeiro.texto}
        {cursorAoEscrever && pensandoAgora && <span className="home-caret" aria-hidden="true" />}
      </p>
    )
  }

  if (primeiro.tipo === "proposta") {
    // Only the drawer injects the card; without the slot (the Home) the block is not drawn.
    return proposta ? <>{proposta(primeiro.proposta)}</> : null
  }

  if (primeiro.tipo === "erro") {
    const erro = textoDoErro(primeiro.erro, idioma)
    return (
      <p
        role="alert"
        className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 px-2.5 py-2 text-xs text-destructive"
      >
        <TbAlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span className="min-w-0">
          {erro.message}
          {erro.hint && (
            <span className="block text-destructive/80">{erro.hint}</span>
          )}
        </span>
      </p>
    )
  }

  // Blocks this Conversa does not know (the Home's fluxo/camada/confirmação/quick
  // replies). The editor does not pass `extras` and never emits these types →
  // it disappears, as before. The context says whether the block is in the last turn.
  return <>{extras?.(primeiro, { ultimoTurno })}</>
}

/**
 * The turn that has not produced any block yet.
 *
 * In the editor the indicator is the `ExecActivity` — the four out-of-phase
 * oscillating bars the running node already uses. It is not just code economy:
 * its docstring records WHY that shape was chosen (rotation is the "please wait"
 * glyph; oscillation says work is HAPPENING), and that is exactly what the
 * drawer needs to say while the model builds; a second "busy" animation in the
 * editor would be a second vocabulary for the same idea. The Home passes another
 * one through the Conversa's `indicador`: the site's animated logo — there, the
 * one thinking is the site, and the logo is what says so.
 *
 * What was here before was three dots with `animate-pulse` and a 150ms delay.
 * The `animate-pulse` cycle is 2s, so 150ms is 7.5% of phase: the three blinked
 * practically TOGETHER, and what one saw was a blinking block, not a wave. The
 * `exec-activity` cycles in 1s with 0.14s steps — 14% of phase, the wave that
 * was wanted. And it already degrades under `prefers-reduced-motion`, freezing
 * the bars at different heights instead of disappearing.
 *
 * It fits inside a `<summary>` because `<svg>` is *phrasing content*; the `<p>`
 * from here would not fit, and neither would its `role="status"` — one per
 * reasoning block would be the live region the comment on the `<ol>` above rejects.
 */
function Pensando({ Indicador }: { Indicador: IndicadorDeAtividade }) {
  const t = useTextos().assistente.barra
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
      <Indicador size={13} />
      <span className="texto-pensando">{t.trabalhando}</span>
    </p>
  )
}

function Vazio() {
  return (
    // `min-h-full` and not `flex-1`: the parent is now the scroll container, and no
    // longer the drawer column. It resolves against its content box — the height
    // minus `py-3` —, so it centers when there is room and SCROLLS when there is not.
    <div className="flex min-h-full flex-col items-center justify-center gap-3 px-6 py-10 text-center">
      <span className="rounded-full bg-muted/60 p-4" aria-hidden="true">
        <TbSparkles size={22} className="text-muted-foreground/50" />
      </span>
      <p className="text-sm font-semibold text-foreground">Descreva o fluxo que você quer</p>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Diga de onde vêm os dados, o que fazer com eles e onde entregar. O assistente monta,
        valida e mostra — aplicar no canvas é você quem decide.
      </p>
      <p className="rounded-md bg-muted/50 px-2.5 py-2 text-left text-xs italic text-muted-foreground">
        «lê municipios.shp do Drive, faz buffer de 500 m, dissolve por UF e publica no portal»
      </p>
    </div>
  )
}
