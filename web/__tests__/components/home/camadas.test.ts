import { describe, it, expect } from "vitest"
import { derivarCamadas, pareceLonLat, corDaCamada, PALETA } from "@/app/components/home/camadas"
import type { AssistantTurn, AssistantBlock } from "@/app/components/home/assistente/quadros"

const turno = (blocos: AssistantBlock[]): AssistantTurn => ({ id: "t", papel: "assistant", blocos })

describe("derivarCamadas", () => {
  it("última menção do mesmo artefato vence", () => {
    const turnos = [
      turno([{ tipo: "camada", camada: { artifact_id: "a1", available: false, hint: "sem" } }]),
      turno([{ tipo: "camada", camada: { artifact_id: "a1", nome: "Focos", available: true } }]),
      turno([{ tipo: "camada", camada: { artifact_id: "a2", available: true } }]),
    ]
    const cs = derivarCamadas(turnos)
    expect(cs.map((c) => c.artifact_id)).toEqual(["a1", "a2"])
    expect(cs.find((c) => c.artifact_id === "a1")?.available).toBe(true) // the last one won
  })
})

describe("pareceLonLat", () => {
  it("aceita uma bbox em lon/lat coerente", () => {
    expect(pareceLonLat([-63, -10, -62, -9])).toBe(true)
  })
  it("recusa CRS métrico, ordem invertida e forma errada", () => {
    expect(pareceLonLat([500000, 9000000, 510000, 9100000])).toBe(false) // UTM
    expect(pareceLonLat([-62, -9, -63, -10])).toBe(false)                // invertida
    expect(pareceLonLat([1, 2, 3])).toBe(false)                          // 3 numbers
    expect(pareceLonLat(null)).toBe(false)
  })
})

describe("corDaCamada", () => {
  it("cicla pela paleta, inclusive índices altos", () => {
    expect(corDaCamada(0)).toBe(PALETA[0])
    expect(corDaCamada(PALETA.length)).toBe(PALETA[0])
    expect(corDaCamada(PALETA.length + 1)).toBe(PALETA[1])
  })
})
