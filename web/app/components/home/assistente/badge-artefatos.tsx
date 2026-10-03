"use client"
import { TbAlertTriangle, TbMap2 } from "react-icons/tb"
import { derivarCamadas } from "@/app/components/home/camadas"
import { useHomeStore } from "@/app/stores/homeStore"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import { useTextos } from "../i18n"

/**
 * The artifacts THIS conversation produced, in a strip fixed at the top of the
 * panel. Clicking puts the artifact on the globe — nothing here navigates away
 * from the Home.
 *
 * This strip used to show the assistant's WORKFLOWS and opened `/workflow/{id}`
 * (the old decision 4). The owner replaced it: the Home is the only page for
 * those who don't administer the system, and what is worth reaching from here
 * is the RESULT, not the machine that produced it. The workflow remains in
 * Projects, with the "mostrar os do assistente" (show the assistant's) switch
 * on, for whoever gets there.
 *
 * **It doesn't duplicate what already exists** — they are three different slices:
 *
 * - `CartaoCamada`, inline in the conversation: the "the layer entered the globe"
 *   moment. It scrolls along with the conversation and goes out of view.
 * - this strip: the index of what the WHOLE conversation produced. It stays fixed
 *   between the header and the scroll, so it survives scrolling.
 * - `PainelCamadas`, in the globe's corner: what is on the globe NOW, with eye,
 *   remove and frame.
 */
export default function BadgeArtefatos({ turnos }: { turnos: TurnoDoAssistente[] }) {
  const pedirCamada = useHomeStore((s) => s.pedirCamada)
  const t = useTextos().assistente.camada
  const camadas = derivarCamadas(turnos)
  if (camadas.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5 border-b border-border px-3 py-2">
      {camadas.map((c) => {
        const nome = c.nome?.trim() || t.artefato
        const comum = "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] max-md:min-h-10 max-md:px-3 max-md:text-xs"

        // Without a preview there is nothing to put on the globe: it stays a `<span>`,
        // not a `<button>`. A button with no action promises a click that doesn't
        // happen, and the screen reader would still announce it as actionable —
        // the same reason that removed the `<button>` from the Schedules row.
        if (!c.available) {
          return (
            <span
              key={c.artifact_id}
              title={c.hint ?? t.semPrevia}
              className={`${comum} border-dashed border-border bg-muted/20 text-muted-foreground/70`}
            >
              <TbAlertTriangle size={12} className="shrink-0" aria-hidden="true" />
              <span className="max-w-[10rem] truncate">{nome}</span>
            </span>
          )
        }

        return (
          <button
            key={c.artifact_id}
            type="button"
            // The `homeStore` queue is the same channel the Artifacts list
            // uses: the one that calls `useCamadas.adicionar` is `HomeView`,
            // which drains it. `adicionar` already deduplicates, so re-clicking is harmless.
            onClick={() => pedirCamada(c.artifact_id, c.nome)}
            title={t.mostrarNoGlobo(nome)}
            className={`${comum} border-border bg-muted/40 text-muted-foreground transition-colors hover:border-muted-foreground/40 hover:text-foreground`}
          >
            <TbMap2 size={12} className="shrink-0 text-primary" aria-hidden="true" />
            <span className="max-w-[10rem] truncate">{nome}</span>
          </button>
        )
      })}
    </div>
  )
}
