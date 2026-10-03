// desktop/src/renderer/components/BarraSalvar.tsx
//
// Action bar of the settings screens (Ajustes and GeoSync).
//
// It stays FIXED at the bottom of the content area, not at the end of the page:
// both screens scroll a lot, and a Save button way down there forces you to go
// through everything to confirm a change made in the first card.
//
// ## The notice became a button
//
// The previous version said "Reinicie o executor para que passe a valer"
// (restart the executor for it to take effect) — the app instructing the person
// to perform by hand a sequence (Stop, wait for the drain, Start) that it knows
// how to do itself. An instruction is what is left when a button is missing.
// Now the same text comes with "Reiniciar agora" (restart now) next to it.
//
// It is not a single "save and restart" on purpose: restarting DRAINS the runs
// in progress and can take much more than an instant, so it remains a separate
// decision, made after the save is already guaranteed.
import { useState } from 'react'
import { TbRotate } from 'react-icons/tb'
import { Button } from './ui/button.js'
import { useSnapshot } from '../lib/snapshot.js'

export function BarraSalvar({
  mudou, salvo, invalido, motivoInvalido, rodando, aoSalvar, aoDescartar,
}: {
  mudou: boolean
  salvo: boolean
  /** Blocks saving — there is a value outside the accepted range. */
  invalido?: boolean
  motivoInvalido?: string
  /** The executor is up; only then does offering the restart make sense. */
  rodando: boolean
  aoSalvar: () => Promise<void> | void
  aoDescartar: () => void
}) {
  const [ocupado, setOcupado] = useState(false)
  const [reiniciado, setReiniciado] = useState(false)
  // Runs in progress — the drain waits for them. Comes from the context, not
  // from a prop: that way the 1 Hz snapshot tick re-renders this bar, and not
  // the whole settings screens that contain it.
  const execucoes = useSnapshot()?.running_count

  if (!mudou && !salvo) return null

  async function reiniciar() {
    setOcupado(true)
    try {
      // A single channel: the main process does `stop()` and then `start()`, in
      // that order. Here it is no longer possible to sequence with two
      // invokes — `parar` returns right away, and the following `iniciar`
      // would arrive with the old process still draining.
      await window.atlas.reiniciar()
      setReiniciado(true)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="sticky bottom-0 -mx-6 -mb-16 flex flex-wrap items-center gap-3 border-t bg-background/95 px-6 py-3 backdrop-blur">
      {mudou ? (
        <>
          <Button disabled={invalido || ocupado} onClick={() => { setReiniciado(false); void aoSalvar() }}>
            Salvar alterações
          </Button>
          <Button variant="ghost" disabled={ocupado} onClick={aoDescartar}>Descartar</Button>
          <span className="text-xs text-muted-foreground">
            {invalido
              ? (motivoInvalido ?? 'Há um valor fora da faixa aceita.')
              : rodando
                ? 'O executor lê estes ajustes ao iniciar — dá para reiniciá-lo aqui depois de salvar.'
                : 'Será aplicado quando o executor iniciar.'}
          </span>
        </>
      ) : reiniciado ? (
        <span className="text-xs text-muted-foreground">
          Executor reiniciado — os ajustes estão valendo.
        </span>
      ) : rodando ? (
        <>
          <Button size="sm" variant="secondary" disabled={ocupado} onClick={reiniciar}>
            <TbRotate size={15} className={ocupado ? 'animate-spin' : undefined} />
            {ocupado ? 'Reiniciando…' : 'Reiniciar agora'}
          </Button>
          <span className="text-xs text-muted-foreground">
            Salvo. O executor precisa reiniciar para aplicar
            {/* The drain waits for the workflows to finish — it may not be
                instant, and the person deserves to know BEFORE clicking. */}
            {typeof execucoes === 'number' && execucoes > 0
              ? ` — ${execucoes} execução(ões) em andamento terminam antes.`
              : '.'}
          </span>
        </>
      ) : (
        <span className="text-xs text-muted-foreground">
          Salvo. Vale a partir do próximo início do executor.
        </span>
      )}
    </div>
  )
}
