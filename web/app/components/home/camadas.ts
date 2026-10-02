// web/app/components/home/camadas.ts
//
// Derivações puras da conversa do assistente: as camadas/artefatos que ela
// apontou (para o globo e para a faixa de badges do painel). Puras de propósito
// — a lógica de "o que a conversa produziu" precisa de teste sem montar o painel
// inteiro.
//
// Havia aqui um `derivarFluxos`, que alimentava a faixa de badges quando ela
// mostrava os FLUXOS do assistente e abria o editor. A faixa passou a mostrar os
// artefatos e nada mais lia os fluxos, então ele saiu junto. O quadro `fluxo` e
// o tipo `FluxoDoAssistente` continuam existindo: o servidor ainda os emite e o
// decodificador ainda os entende.

import type {
  TurnoDoAssistente, CamadaDoAssistente,
} from "@/app/components/home/assistente/quadros"

/** As camadas que a conversa apontou para o globo, sem repetir (a última vence). */
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
 * Uma bbox `[oeste, sul, leste, norte]` que cabe em lon/lat — só aí dá para
 * enquadrar. A bbox pode vir no CRS nativo do dado (não reprojetado); enquadrar
 * por ela sem checar mandaria a câmera para o meio do oceano.
 */
export function pareceLonLat(bbox: number[] | null | undefined): boolean {
  if (!bbox || bbox.length !== 4) return false
  const [oeste, sul, leste, norte] = bbox
  return [oeste, leste].every((x) => x >= -180 && x <= 180)
    && [sul, norte].every((y) => y >= -90 && y <= 90)
    && oeste <= leste && sul <= norte
}

/** Paleta das camadas — tons distintos e saturados, legíveis sobre a imagem do basemap. */
export const PALETA = ["#f97316", "#22d3ee", "#a78bfa", "#4ade80", "#f43f5e", "#facc15", "#38bdf8", "#fb7185"]

export function corDaCamada(i: number): string {
  return PALETA[((i % PALETA.length) + PALETA.length) % PALETA.length]
}
