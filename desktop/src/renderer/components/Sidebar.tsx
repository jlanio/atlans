// desktop/src/renderer/components/Sidebar.tsx
//
// Side navigation — same skeleton as Atlans Studio, so someone who uses both
// recognizes it immediately.
//
// Besides navigating, the bar carries the executor lifecycle control — a large
// target, in the same place on every tab. The STATE (connected, stopped) is not
// here: it is window chrome and lives in the StatusBar at the bottom, where the
// width is not contested by the navigation.
import { useEffect, useState, type ReactNode } from 'react'
import {
  TbActivity, TbAdjustments, TbCloudDataConnection, TbHandStop, TbLayoutDashboard,
  TbLoader2, TbPlayerPlayFilled, TbPlayerStopFilled,
} from 'react-icons/tb'
import type { AppState } from '../../main/state/store.js'
import { Button } from './ui/button.js'
import { cn } from '../lib/utils.js'

/**
 * The app's screens.
 *
 * No 'logs': the log is no longer a tab. It opens in its OWN WINDOW from the
 * footer bar button, which is how it is used — followed alongside something
 * else, not visited in its place.
 */
export type Tab = 'painel' | 'execucoes' | 'geosync' | 'ajustes'

const ITEMS: Array<{ id: Tab; rotulo: string; icone: ReactNode }> = [
  { id: 'painel', rotulo: 'Painel', icone: <TbLayoutDashboard size={17} /> },
  { id: 'execucoes', rotulo: 'Execuções', icone: <TbActivity size={17} /> },
  { id: 'geosync', rotulo: 'GeoSync', icone: <TbCloudDataConnection size={17} /> },
  { id: 'ajustes', rotulo: 'Ajustes', icone: <TbAdjustments size={17} /> },
]

/**
 * How long the "Forçar parada" (force stop) button stays inert after appearing.
 *
 * Half a second is the default Windows double-click interval: above that the
 * click is no longer accidental, and below it the destructive button would
 * inherit the second click of someone who only wanted to stop.
 */
const MS_UNTIL_FORCE_ENABLED = 500

/**
 * The lifecycle control — a single button that changes role with the state.
 *
 * Two buttons side by side (a "Iniciar" and a "Parar", one of them always
 * disabled) would force you to read both to find out which one is active. Here
 * there is always ONE possible action, and the icon says which before the text
 * is read: triangle to start, square to stop, hand to force.
 *
 * In the transition states the icon becomes a spinner — that is what separates
 * "it is taking a while" from "the click did not register", and without it the
 * only clue would be the dimmed button.
 *
 * There is no longer a GLOBAL "busy": the three actions return right away over
 * IPC, and progress is told by the state ITSELF (the button becomes
 * "Encerrando…", then "Forçar parada"). The old flag was tied to the `parar`
 * promise, which only resolved at the end of the drain — and it disabled even
 * the force button, which is the way out of the wait. What remains is local to
 * each button, below.
 */
function ExecutorControl({
  estado, aoIniciar, aoParar, aoForcar,
}: {
  estado: AppState
  aoIniciar: () => void
  aoParar: () => void
  aoForcar: () => void
}) {
  // `w-full` + `justify-start`: left-aligning the icons puts the button column
  // in line with the navigation icons above.
  const comum = 'w-full justify-start gap-2 font-medium'
  const fase = estado.supervisor

  // Immediate feedback for the click on "Parar".
  //
  // The IPC returns right away, but the `draining` state only arrives ~100 ms
  // later (store coalescing + IPC + render). In that gap the button still said
  // "Parar" and remained clickable: the second click of a double click got in
  // and requested a SECOND stop. This flag disables ONLY this button — never
  // "Forçar", which appears next.
  const [stopRequested, setStopRequested] = useState(false)
  useEffect(() => {
    // Left `running`/`starting`: the request arrived and the button is already another one.
    if (fase !== 'running' && fase !== 'starting') setStopRequested(false)
  }, [fase])

  // "Forçar parada" (force stop) starts inert for half a second.
  //
  // It occupies the SAME position on screen as the "Parar" that just vanished;
  // without this interval, the second click of a double click would land on it
  // and kill the runs in progress cold, without anyone having asked for that.
  const [forceEnabled, setForceEnabled] = useState(false)
  useEffect(() => {
    if (fase !== 'draining') {
      setForceEnabled(false)
      return
    }
    const t = setTimeout(() => setForceEnabled(true), MS_UNTIL_FORCE_ENABLED)
    return () => clearTimeout(t)
  }, [fase])

  function requestStop() {
    setStopRequested(true)
    aoParar()
  }

  switch (fase) {
    // Draining: insisting on "Parar" would do nothing. The way out is to force,
    // and it needs to look dangerous — the wait can reach 150s, but cutting it
    // short kills runs in progress.
    case 'draining':
      return (
        <Button size="sm" variant="destructive" className={comum}
                onClick={aoForcar} disabled={!forceEnabled}
                title="Encerra agora, interrompendo as execuções em andamento">
          <TbHandStop size={15} /> Forçar parada
        </Button>
      )

    case 'restarting':
      return (
        <Button size="sm" variant="outline" className={comum} disabled>
          <TbLoader2 size={15} className="animate-spin" /> Reiniciando…
        </Button>
      )

    // Still starting up, but clickable on purpose: a stuck boot needs a way out,
    // and disabling the button would leave the user with none.
    case 'starting':
      return (
        <Button size="sm" variant="outline" className={comum}
                onClick={requestStop} disabled={stopRequested}
                title="Cancela a inicialização">
          <TbLoader2 size={15} className="animate-spin" />
          {stopRequested ? 'Parando…' : 'Iniciando…'}
        </Button>
      )

    case 'running':
      return stopRequested ? (
        <Button size="sm" variant="outline" className={comum} disabled>
          <TbLoader2 size={15} className="animate-spin" /> Parando…
        </Button>
      ) : (
        <Button size="sm" variant="outline" className={comum}
                onClick={requestStop}
                title="Encerra depois que as execuções em andamento terminarem">
          <TbPlayerStopFilled size={15} className="text-destructive" />
          Parar
        </Button>
      )

    // `stopped` and `failed`: the action is the same, and it is the only
    // highlighted one in the app — it uses the button's `default`, in the
    // primary color.
    default:
      return (
        <Button size="sm" className={comum} onClick={aoIniciar}>
          <TbPlayerPlayFilled size={15} />
          Iniciar executor
        </Button>
      )
  }
}

export function Sidebar({
  aba, aoTrocar, pendencias, estado, aoIniciar, aoParar, aoForcar,
}: {
  aba: Tab
  aoTrocar: (a: Tab) => void
  /** Screens with unsaved changes — they get a dot in the navigation. */
  pendencias?: Partial<Record<Tab, boolean>>
  estado: AppState
  aoIniciar: () => void
  aoParar: () => void
  aoForcar: () => void
}) {

  return (
    <aside className="flex w-48 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <nav aria-label="Seções do aplicativo" className="flex flex-1 flex-col gap-0.5 p-2">
        {ITEMS.map((item) => {
          const ativo = aba === item.id
          const emExecucao = estado.snapshot?.running_count ?? 0
          return (
          <button
            key={item.id}
            type="button"
            onClick={() => aoTrocar(item.id)}
            // `aria-current="page"` is what says "you are here" to those who do not see
            // the highlight; `focus-visible` is the system.md recipe (Focus &
            // Accessibility) — this navigation is the ONLY keyboard route in the
            // app, and without a focus ring someone tabbing does not know where
            // they are.
            aria-current={ativo ? 'page' : undefined}
            className={cn(
              'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm outline-none',
              'transition-all active:scale-[0.98]',
              'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]',
              ativo
                ? 'bg-sidebar-accent font-medium text-sidebar-foreground'
                : 'text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground',
            )}
          >
            {/* `transition-colors` on the icon too: without it the background
                transitioned and the glyph jumped from gray to orange in the
                same frame. */}
            <span className={cn('shrink-0 transition-colors', ativo && 'text-primary')}>
              {item.icone}
            </span>
            <span className="flex-1 text-left">{item.rotulo}</span>

            {/* Counters only where there is something to notice — a "0" on every
                row does not inform and adds clutter. */}
            {item.id === 'execucoes' && emExecucao > 0 && (
              <span
                className="rounded-full bg-blue-500/20 px-1.5 text-[10px] font-semibold text-blue-400 tabular-nums animate-in fade-in-0 zoom-in-95 duration-200"
                title={`${emExecucao} ${emExecucao === 1 ? 'execução em andamento' : 'execuções em andamento'}`}
              >
                {emExecucao}
              </span>
            )}

            {/* Unsaved changes on this screen.
                A dot, not text: the navigation is 192px wide and the message
                is binary. The color is the primary one, not the error one —
                nothing is wrong, there is just work left to finish.

                `title` plus `sr-only`: the target is 6px and `title` alone is
                a message that only exists for someone who lands the pointer on
                it. */}
            {pendencias?.[item.id] && (
              <span
                className="size-1.5 shrink-0 rounded-full bg-primary animate-in fade-in-0 zoom-in-50 duration-200"
                title="Alterações não salvas"
              >
                <span className="sr-only">Alterações não salvas</span>
              </span>
            )}
          </button>
          )
        })}
      </nav>

      {/* ── Footer: state and action ──────────────────────────────────────
          It sits in the bar, not in a tab header, so it stays visible while
          the user reads the log or changes the settings. */}
      <div className="border-t border-sidebar-border p-2">
        <ExecutorControl
          estado={estado}
          aoIniciar={aoIniciar} aoParar={aoParar} aoForcar={aoForcar}
        />
      </div>
    </aside>
  )
}
