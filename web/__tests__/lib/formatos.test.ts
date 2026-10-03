import { describe, it, expect } from "vitest"
import {
  formatarDuracao,
  formatarInicio,
  formatarDiaCurto,
  formatarInteiro,
  formatarPercentual,
  formatarPontos,
  plural,
  rotuloDaCategoria,
  rotuloDaOrigem,
  rotuloDoNivel,
  variacao,
  formatarDuracaoGrossa,
  formatarDecorridoGrosso,
  formatarDolar,
  formatarQuando,
} from "@/lib/formatos"
import { rotuloDoStatus } from "@/app/components/shared/status-rotulos"

describe("formatarDuracao", () => {
  it("usa a unidade que a pessoa usa", () => {
    expect(formatarDuracao(31)).toBe("31 s")
    expect(formatarDuracao(31.4)).toBe("31 s")
    expect(formatarDuracao(242)).toBe("4 min 02 s")
    expect(formatarDuracao(300)).toBe("5 min")
    expect(formatarDuracao(8040)).toBe("2 h 14 min")
    expect(formatarDuracao(7200)).toBe("2 h")
    expect(formatarDuracao(0.4)).toBe("< 1 s")
  })
  it("cala sem dado", () => {
    expect(formatarDuracao(null)).toBe("—")
    expect(formatarDuracao(undefined)).toBe("—")
    expect(formatarDuracao(-5)).toBe("—")
    expect(formatarDuracao(NaN)).toBe("—")
  })
  it("arredonda para a hora cheia em vez de mostrar 60 min", () => {
    expect(formatarDuracao(3600 + 59 * 60 + 40)).toBe("2 h")
  })
})

describe("formatarInicio", () => {
  const agora = new Date(2026, 8, 6, 19, 43) // 2026-09-06, 19:43 local
  const iso = (d: Date) => d.toISOString()
  it("relativo na última hora", () => {
    expect(formatarInicio(iso(new Date(2026, 8, 6, 19, 41)), agora)).toBe("há 2 min")
    expect(formatarInicio(iso(new Date(2026, 8, 6, 19, 43)), agora)).toBe("agora")
  })
  it("hoje e ontem com a hora", () => {
    expect(formatarInicio(iso(new Date(2026, 8, 6, 3, 0)), agora)).toBe("hoje, 03:00")
    expect(formatarInicio(iso(new Date(2026, 8, 5, 17, 22)), agora)).toBe("ontem, 17:22")
  })
  it("data curta no mesmo ano, com o ano quando muda", () => {
    expect(formatarInicio(iso(new Date(2026, 8, 4, 3, 0)), agora)).toBe("4 set, 03:00")
    expect(formatarInicio(iso(new Date(2025, 11, 24, 8, 5)), agora)).toBe("24 dez 2025, 08:05")
  })
  it("sem dado", () => {
    expect(formatarInicio(null, agora)).toBe("—")
    expect(formatarInicio("", agora)).toBe("—")
  })
  it("dia curto para o eixo do gráfico", () => {
    expect(formatarDiaCurto("2026-08-08")).toBe("8 ago")
    expect(formatarDiaCurto("2026-12-25")).toBe("25 dez")
    expect(formatarDiaCurto("x")).toBe("x")
  })
})

describe("rótulos", () => {
  it("status em português, e o texto cru quando é desconhecido", () => {
    expect(rotuloDoStatus("success")).toBe("Concluída")
    expect(rotuloDoStatus("failed")).toBe("Falhou")
    expect(rotuloDoStatus("error")).toBe("Falhou")
    expect(rotuloDoStatus("running")).toBe("Em andamento")
    expect(rotuloDoStatus("pending")).toBe("Na fila")
    expect(rotuloDoStatus("cancelled")).toBe("Cancelada")
    expect(rotuloDoStatus("cached")).toBe("Cache")
    expect(rotuloDoStatus("estranho")).toBe("estranho")
    expect(rotuloDoStatus(null)).toBe("—")
  })
  it("origem, categoria e nível", () => {
    expect(rotuloDaOrigem("schedule")).toBe("agendado")
    expect(rotuloDaOrigem("retry")).toBe("reexecução")
    expect(rotuloDaOrigem("mcp")).toBe("agente")
    expect(rotuloDaOrigem(null)).toBeNull()
    expect(rotuloDaCategoria("timeout")).toBe("tempo esgotado")
    expect(rotuloDaCategoria("executor_lost")).toBe("executor caiu")
    expect(rotuloDaCategoria("qualquer")).toBeNull()
    expect(rotuloDoNivel("primary")).toBeNull()
    expect(rotuloDoNivel("fallback")).toBe("reserva")
    expect(rotuloDoNivel("pool")).toBe("pool")
    expect(rotuloDoNivel(null)).toBeNull()
  })
})

describe("números", () => {
  it("variação com percentual, e sem base quando o anterior é zero", () => {
    expect(variacao(1284, 1147)).toEqual({ pct: expect.closeTo(11.94, 1), delta: 137, direcao: "sobe" })
    expect(variacao(46, 37)).toMatchObject({ delta: 9, direcao: "sobe" })
    expect(variacao(100, 100)).toMatchObject({ direcao: "igual" })
    expect(variacao(100.3, 100)).toMatchObject({ direcao: "igual" })
    expect(variacao(5, 0)).toEqual({ pct: null, delta: 5, direcao: "sobe" })
    expect(variacao(0, 0)).toEqual({ pct: null, delta: 0, direcao: "igual" })
    expect(variacao(null, 3)).toBeNull()
  })
  it("formatos pt-BR", () => {
    expect(formatarInteiro(1284)).toBe("1.284")
    expect(formatarInteiro(null)).toBe("—")
    expect(formatarPercentual(0.964)).toBe("96,4%")
    expect(formatarPercentual(1)).toBe("100,0%")
    expect(formatarPercentual(null)).toBe("—")
    expect(formatarPontos(0.964 - 0.975)).toBe("−1,1 pt")
    expect(formatarPontos(0.02)).toBe("+2,0 pt")
    expect(plural(1, "presa")).toBe("1 presa")
    expect(plural(2, "presa")).toBe("2 presas")
    expect(plural(1, "confirmação atrasada", "confirmações atrasadas")).toBe("1 confirmação atrasada")
  })
})

describe("formatadores grossos (coluna 'como anda' de Projetos)", () => {
  it("formatarDuracaoGrossa: segundos até 1 min, depois só minutos e horas", () => {
    expect(formatarDuracaoGrossa(31)).toBe("31 s")
    expect(formatarDuracaoGrossa(369)).toBe("6 min")
    expect(formatarDuracaoGrossa(90)).toBe("2 min")
    expect(formatarDuracaoGrossa(3599)).toBe("1 h")
    expect(formatarDuracaoGrossa(8040)).toBe("2 h 14 min")
    expect(formatarDuracaoGrossa(7200)).toBe("2 h")
    expect(formatarDuracaoGrossa(null)).toBe("—")
    expect(formatarDuracaoGrossa(0.4)).toBe("< 1 s")
  })

  it("formatarDecorridoGrosso: 'há' + a mesma granularidade", () => {
    expect(formatarDecorridoGrosso(2937)).toBe("há 49 min")
    expect(formatarDecorridoGrosso(undefined)).toBe("—")
  })

  it("formatarQuando: relativo dentro de 24 h mesmo atravessando a meia-noite, calendário depois", () => {
    // Instants in UTC and times checked by regex: the test environment's time
    // zone isn't the user's, and what matters here is the rule, not the time.
    const agora = new Date("2026-09-07T23:40:00Z")
    expect(formatarQuando("2026-09-07T23:00:00Z", agora)).toBe("há 40 min")
    expect(formatarQuando("2026-09-07T20:40:00Z", agora)).toBe("há 3 h")
    expect(formatarQuando("2026-09-07T00:10:00Z", agora)).toBe("há 23 h")
    // 29 h ago: already calendar format, and "ontem" (yesterday) because the civil day is the previous one.
    expect(formatarQuando("2026-09-06T18:12:00Z", agora)).toMatch(/^ontem, \d\d:\d\d$/)
    expect(formatarQuando("2026-09-01T11:04:00Z", agora)).toMatch(/^1 set, \d\d:\d\d$/)
    expect(formatarQuando(null, agora)).toBe("—")
    expect(formatarQuando("2026-09-07T23:39:40Z", agora)).toBe("agora")
  })
})

// ── Dinheiro ──────────────────────────────────────────────────────────────────

describe("formatarDolar", () => {
  it("escreve o dólar em pt-BR e o desconhecido como ausência, nunca zero", () => {
    expect(formatarDolar(12.34)).toBe("US$ 12,34")
    expect(formatarDolar(0)).toBe("US$ 0,00")
    // An unknown price doesn't become zero: zero would read as "free".
    expect(formatarDolar(null)).toBe("—")
    expect(formatarDolar(undefined)).toBe("—")
  })
})
