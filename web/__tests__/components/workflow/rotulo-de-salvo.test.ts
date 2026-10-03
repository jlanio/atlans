/**
 * The chip at rest says WHEN the last save was, at the precision that answers
 * the question of the moment: minutes while it's recent, time of day if it was
 * today, date and time before that. Local times on purpose — it's what the user
 * reads on their own clock.
 */
import { describe, it, expect } from "vitest"
import { rotuloDeSalvo } from "@/app/components/workflow/utils/rotulo-de-salvo"

const MIN = 60_000
const agora = new Date(2026, 8, 5, 14, 32, 0).getTime() // 05/09/2026 14:32 local

describe("rotuloDeSalvo", () => {
  it("menos de um minuto: 'agora'", () => {
    expect(rotuloDeSalvo(agora - 10_000, agora)).toBe("Salvo agora")
    expect(rotuloDeSalvo(agora, agora)).toBe("Salvo agora")
  })

  it("até uma hora: minutos", () => {
    expect(rotuloDeSalvo(agora - 1 * MIN, agora)).toBe("Salvo há 1 min")
    expect(rotuloDeSalvo(agora - 5 * MIN - 20_000, agora)).toBe("Salvo há 5 min")
    expect(rotuloDeSalvo(agora - 59 * MIN, agora)).toBe("Salvo há 59 min")
  })

  it("mais de uma hora, hoje: a hora", () => {
    const tenOhFive = new Date(2026, 8, 5, 10, 5, 0).getTime()
    expect(rotuloDeSalvo(tenOhFive, agora)).toBe("Salvo às 10:05")
  })

  it("antes de hoje: dia e hora", () => {
    const ontem = new Date(2026, 8, 4, 23, 50, 0).getTime()
    expect(rotuloDeSalvo(ontem, agora)).toBe("Salvo em 04/09 às 23:50")
  })

  it("um relógio adiantado no servidor não vira 'há -3 min'", () => {
    expect(rotuloDeSalvo(agora + 3 * MIN, agora)).toBe("Salvo agora")
  })
})
