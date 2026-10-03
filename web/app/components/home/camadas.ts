// web/app/components/home/camadas.ts
//
// Pure derivations from the assistant conversation: the layers/artifacts it
// pointed to (for the globe and for the panel's badges strip). Pure on purpose
// — the "what the conversation produced" logic needs tests without mounting the
// whole panel.
//
// There used to be a `derivarFluxos` here, which fed the badges strip when it
// showed the assistant's WORKFLOWS and opened the editor. The strip switched to
// showing artifacts and nothing else read the workflows, so it went away too.
// The `fluxo` frame and the `FluxoDoAssistente` type still exist: the server
// still emits them and the decoder still understands them.

import type {
  TurnoDoAssistente, CamadaDoAssistente,
} from "@/app/components/home/assistente/quadros"

/** The layers the conversation pointed to for the globe, without repeats (the last one wins). */
export function derivarCamadas(turnos: TurnoDoAssistente[]): CamadaDoAssistente[] {
  const porId = new Map<string, CamadaDoAssistente>()
  for (const turno of turnos) {
    for (const bloco of turno.blocos) {
      if (bloco.tipo === "camada" && bloco.camada.artifact_id) {
        porId.set(bloco.camada.artifact_id, bloco.camada)
      }
    }
  }
  return [...porId.values()]
}

/**
 * A bbox `[oeste, sul, leste, norte]` that fits in lon/lat — only then can it be
 * framed. The bbox may come in the data's native CRS (not reprojected); framing
 * by it without checking would send the camera to the middle of the ocean.
 */
export function pareceLonLat(bbox: number[] | null | undefined): boolean {
  if (!bbox || bbox.length !== 4) return false
  const [oeste, sul, leste, norte] = bbox
  return [oeste, leste].every((x) => x >= -180 && x <= 180)
    && [sul, norte].every((y) => y >= -90 && y <= 90)
    && oeste <= leste && sul <= norte
}

/** Layer palette — distinct, saturated hues, readable over the basemap imagery. */
export const PALETA = ["#f97316", "#22d3ee", "#a78bfa", "#4ade80", "#f43f5e", "#facc15", "#38bdf8", "#fb7185"]

export function corDaCamada(i: number): string {
  return PALETA[((i % PALETA.length) + PALETA.length) % PALETA.length]
}
