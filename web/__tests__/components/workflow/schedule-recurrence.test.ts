import { describe, it, expect } from "vitest"
import {
  lerEstado, gerarCampos, descrever, resumoSalvo, proximasExecucoes, validarAvancado,
  type EstadoAgenda,
} from "@/app/components/workflow/nodes-configuration/schedule-recurrence"

// Reads the "wall clock" components of a date in a time zone (to check the
// preview without depending on the test machine's time zone).
function parts(d: Date, tz: string) {
  const f = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz, hour12: false, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", weekday: "short",
  })
  const p: Record<string, string> = {}
  f.formatToParts(d).forEach(x => { p[x.type] = x.value })
  return {
    y: +p.year, mo: +p.month, d: +p.day, h: +(p.hour === "24" ? "0" : p.hour), mi: +p.minute,
    wd: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(p.weekday),
  }
}

const SP = "America/Sao_Paulo"
const AGORA = new Date("2026-03-10T15:00:00Z") // 12:00 in São Paulo (−3)

function base(over: Partial<EstadoAgenda> = {}): EstadoAgenda {
  return {
    freq: "diario", intervalo: 15, unidade: "minutes", hora: 9, minuto: 0,
    everyDays: 1, weekdays: [1, 2, 3, 4, 5], monthDay: 1, monthLast: false,
    timezone: SP, active: true, advTipo: "cron", advCron: "0 9 * * *", advRrule: "",
    ...over,
  }
}

describe("gerarCampos — estado → campos gravados", () => {
  it("intervalo vira strategy=interval sem cron/rrule", () => {
    const c = gerarCampos(base({ freq: "intervalo", intervalo: 2, unidade: "hours" }))
    expect(c).toMatchObject({ strategy: "interval", interval: 2, unit: "hours", cron_expression: "", rrule_expression: "" })
  })
  it("diário (todo dia) vira cron M H * * *", () => {
    expect(gerarCampos(base({ freq: "diario", hora: 9, minuto: 0 })).cron_expression).toBe("0 9 * * *")
    expect(gerarCampos(base({ freq: "diario", hora: 14, minuto: 30 })).cron_expression).toBe("30 14 * * *")
  })
  it("a cada N dias vira rrule DAILY;INTERVAL (cron */N no dia reinicia por mês)", () => {
    const c = gerarCampos(base({ freq: "diario", everyDays: 3, hora: 9, minuto: 0 }))
    expect(c.strategy).toBe("rrule")
    expect(c.rrule_expression).toBe("FREQ=DAILY;INTERVAL=3;BYHOUR=9;BYMINUTE=0;BYSECOND=0")
    expect(c.cron_expression).toBe("")
  })
  it("semanal vira cron M H * * d,d ordenado", () => {
    expect(gerarCampos(base({ freq: "semanal", weekdays: [4, 2], hora: 14, minuto: 30 })).cron_expression).toBe("30 14 * * 2,4")
  })
  it("mensal dia D vira cron M H D * *", () => {
    expect(gerarCampos(base({ freq: "mensal", monthDay: 1, hora: 9, minuto: 0 })).cron_expression).toBe("0 9 1 * *")
  })
  it("mensal último dia vira rrule BYMONTHDAY=-1", () => {
    const c = gerarCampos(base({ freq: "mensal", monthLast: true, hora: 9, minuto: 0 }))
    expect(c.strategy).toBe("rrule")
    expect(c.rrule_expression).toBe("FREQ=MONTHLY;BYMONTHDAY=-1;BYHOUR=9;BYMINUTE=0;BYSECOND=0")
  })
  it("semanal sem dias cai para dia 1 (nunca gera dow vazio)", () => {
    expect(gerarCampos(base({ freq: "semanal", weekdays: [] })).cron_expression).toMatch(/\* \* [0-6]$/)
  })
})

describe("lerEstado — campos gravados → estado (round-trip)", () => {
  const casos: [string, Partial<EstadoAgenda>][] = [
    ["intervalo", { freq: "intervalo", intervalo: 2, unidade: "hours" }],
    ["diário", { freq: "diario", hora: 14, minuto: 30, everyDays: 1 }],
    ["a cada 3 dias", { freq: "diario", hora: 9, minuto: 0, everyDays: 3 }],
    ["semanal", { freq: "semanal", weekdays: [2, 4], hora: 14, minuto: 30 }],
    ["mensal dia 15", { freq: "mensal", monthDay: 15, hora: 6, minuto: 0 }],
    ["mensal último", { freq: "mensal", monthLast: true, hora: 18, minuto: 0 }],
  ]
  for (const [nome, over] of casos) {
    it(`round-trip: ${nome}`, () => {
      const campos = gerarCampos(base(over))
      const lido = lerEstado(campos as unknown as Record<string, string | number | boolean>)
      expect(lido).toMatchObject(over)
    })
  }

  it("lê os defaults do nó (cron '0 9 * * *') como diário 09:00", () => {
    const e = lerEstado({ strategy: "cron", cron_expression: "0 9 * * *", interval: 60, unit: "minutes", timezone: "America/La_Paz", active: true, rrule_expression: "" })
    expect(e).toMatchObject({ freq: "diario", hora: 9, minuto: 0, everyDays: 1, timezone: "America/La_Paz", active: true })
  })
  it("cron legado '*/15 * * * *' abre em Avançado (não finge um modo)", () => {
    const e = lerEstado({ strategy: "cron", cron_expression: "*/15 * * * *" })
    expect(e.freq).toBe("avancado")
    expect(e.advTipo).toBe("cron")
    expect(e.advCron).toBe("*/15 * * * *")
  })
  it("cron com faixa de dias '0 8 * * 1-5' vira semanal seg–sex", () => {
    const e = lerEstado({ strategy: "cron", cron_expression: "0 8 * * 1-5" })
    expect(e).toMatchObject({ freq: "semanal", weekdays: [1, 2, 3, 4, 5], hora: 8, minuto: 0 })
  })
  it("rrule desconhecida abre em Avançado (rrule)", () => {
    const e = lerEstado({ strategy: "rrule", rrule_expression: "FREQ=YEARLY;BYMONTH=1" })
    expect(e.freq).toBe("avancado")
    expect(e.advTipo).toBe("rrule")
  })
  it("active=false é preservado", () => {
    expect(lerEstado({ strategy: "cron", cron_expression: "0 9 * * *", active: false }).active).toBe(false)
  })
})

describe("robustez de lerEstado (achados da revisão)", () => {
  it("dow inválido 8 cai em Avançado (croniter rejeitaria)", () => {
    expect(lerEstado({ strategy: "cron", cron_expression: "0 9 * * 8" }).freq).toBe("avancado")
    expect(lerEstado({ strategy: "cron", cron_expression: "0 9 * * 9" }).freq).toBe("avancado")
  })
  it("faixa 1-7 (7=domingo) vira semanal com todos os dias", () => {
    const e = lerEstado({ strategy: "cron", cron_expression: "0 9 * * 1-7" })
    expect(e.freq).toBe("semanal")
    expect(e.weekdays).toEqual([0, 1, 2, 3, 4, 5, 6])
  })
  it("active como string 'false' é lido como inativo", () => {
    expect(lerEstado({ strategy: "cron", cron_expression: "0 9 * * *", active: "false" }).active).toBe(false)
    expect(lerEstado({ strategy: "cron", cron_expression: "0 9 * * *", active: 0 }).active).toBe(false)
    expect(lerEstado({ strategy: "cron", cron_expression: "0 9 * * *", active: "true" }).active).toBe(true)
  })

  it("rrule que casa um modo simples carrega com advTipo='rrule' (não apaga ao abrir Avançado)", () => {
    // A saved strategy=rrule ("every 3 days") maps to the daily mode, but the
    // advanced mode's TYPE has to be 'rrule' — not the default 'cron'. Without
    // it, opening "Avançado" (advanced) showed the cron tab and a "Salvar" (save)
    // from there wrote strategy=cron with CRON_PADRAO, silently erasing the rrule.
    const RRULE = "FREQ=DAILY;INTERVAL=3;BYHOUR=9;BYMINUTE=0;BYSECOND=0"
    const lido = lerEstado({ strategy: "rrule", rrule_expression: RRULE })
    expect(lido).toMatchObject({ freq: "diario", everyDays: 3, hora: 9, minuto: 0 })
    expect(lido.advTipo).toBe("rrule")
    expect(lido.advRrule).toBe(RRULE)
    // Switching to "Avançado" and saving preserves the rrule — it doesn't become the default cron.
    const salvo = gerarCampos({ ...lido, freq: "avancado" })
    expect(salvo).toMatchObject({ strategy: "rrule", rrule_expression: RRULE })
    expect(salvo.cron_expression).toBe("")
  })
})

describe("validarAvancado", () => {
  it("cron precisa ter 5 campos", () => {
    expect(validarAvancado(base({ freq: "avancado", advTipo: "cron", advCron: "0 9 * *" }))).toBeTruthy()
    expect(validarAvancado(base({ freq: "avancado", advTipo: "cron", advCron: "0 9 * * * *" }))).toBeTruthy()
    expect(validarAvancado(base({ freq: "avancado", advTipo: "cron", advCron: "0 9 * * *" }))).toBeNull()
  })
  it("rrule precisa de FREQ e não pode ser vazia", () => {
    expect(validarAvancado(base({ freq: "avancado", advTipo: "rrule", advRrule: "" }))).toBeTruthy()
    expect(validarAvancado(base({ freq: "avancado", advTipo: "rrule", advRrule: "toda segunda" }))).toBeTruthy()
    expect(validarAvancado(base({ freq: "avancado", advTipo: "rrule", advRrule: "FREQ=WEEKLY;BYDAY=MO" }))).toBeNull()
  })
  it("modos não-avançados nunca têm erro", () => {
    expect(validarAvancado(base({ freq: "semanal", weekdays: [2] }))).toBeNull()
  })
})

describe("descrever — frase em pt-BR", () => {
  it("intervalo", () => {
    expect(descrever(base({ freq: "intervalo", intervalo: 15, unidade: "minutes" }))).toBe("A cada 15 minutos")
    expect(descrever(base({ freq: "intervalo", intervalo: 1, unidade: "hours" }))).toBe("A cada 1 hora")
  })
  it("diário / a cada N dias", () => {
    expect(descrever(base({ freq: "diario", hora: 9, minuto: 0, everyDays: 1 }))).toBe("Todos os dias às 09:00")
    expect(descrever(base({ freq: "diario", hora: 9, minuto: 5, everyDays: 3 }))).toBe("A cada 3 dias às 09:05")
  })
  it("semanal", () => {
    expect(descrever(base({ freq: "semanal", weekdays: [2, 4], hora: 14, minuto: 30 }))).toBe("Toda ter, qui às 14:30")
    expect(descrever(base({ freq: "semanal", weekdays: [1, 2, 3, 4, 5], hora: 8, minuto: 0 }))).toBe("De segunda a sexta às 08:00")
    expect(descrever(base({ freq: "semanal", weekdays: [0, 6], hora: 8, minuto: 0 }))).toBe("Sábado e domingo às 08:00")
  })
  it("mensal", () => {
    expect(descrever(base({ freq: "mensal", monthDay: 1, hora: 9, minuto: 0 }))).toBe("Todo dia 1 às 09:00")
    expect(descrever(base({ freq: "mensal", monthLast: true, hora: 9, minuto: 0 }))).toBe("No último dia do mês às 09:00")
  })
})

describe("resumoSalvo", () => {
  it("mostra cron/intervalo/rrule conforme a estratégia", () => {
    expect(resumoSalvo(base({ freq: "semanal", weekdays: [2, 4], hora: 14, minuto: 30 }))).toBe("cron: 30 14 * * 2,4")
    expect(resumoSalvo(base({ freq: "intervalo", intervalo: 5, unidade: "minutes" }))).toBe("intervalo: 5 (minutes)")
    expect(resumoSalvo(base({ freq: "mensal", monthLast: true, hora: 9, minuto: 0 }))).toContain("rrule: FREQ=MONTHLY;BYMONTHDAY=-1")
  })
})

describe("proximasExecucoes — mesma semântica do agendador", () => {
  it("intervalo: agora + N a cada passo", () => {
    const runs = proximasExecucoes(base({ freq: "intervalo", intervalo: 15, unidade: "minutes" }), 5, AGORA)!
    expect(runs).toHaveLength(5)
    expect(runs[0].getTime()).toBe(AGORA.getTime() + 15 * 60000)
    expect(runs[1].getTime() - runs[0].getTime()).toBe(15 * 60000)
  })

  it("diário: 5 execuções, todas às 09:00 no fuso, futuras e crescentes", () => {
    const runs = proximasExecucoes(base({ freq: "diario", hora: 9, minuto: 0 }), 5, AGORA)!
    expect(runs).toHaveLength(5)
    for (const r of runs) {
      expect(r.getTime()).toBeGreaterThan(AGORA.getTime())
      const p = parts(r, SP); expect(p.h).toBe(9); expect(p.mi).toBe(0)
    }
    for (let i = 1; i < runs.length; i++) expect(runs[i].getTime()).toBeGreaterThan(runs[i - 1].getTime())
  })

  it("a cada 3 dias: passos de ~3 dias", () => {
    const runs = proximasExecucoes(base({ freq: "diario", everyDays: 3, hora: 9, minuto: 0 }), 4, AGORA)!
    for (let i = 1; i < runs.length; i++) {
      const dias = Math.round((runs[i].getTime() - runs[i - 1].getTime()) / 86400000)
      expect(dias).toBe(3)
    }
  })

  it("a cada N dias grande ainda devolve 5 execuções (teto adaptativo)", () => {
    const runs = proximasExecucoes(base({ freq: "diario", everyDays: 200, hora: 9, minuto: 0 }), 5, AGORA)!
    expect(runs).toHaveLength(5)
    for (let i = 1; i < runs.length; i++)
      expect(Math.round((runs[i].getTime() - runs[i - 1].getTime()) / 86400000)).toBe(200)
  })

  it("semanal ter/qui: cada execução cai em terça ou quinta às 14:30", () => {
    const runs = proximasExecucoes(base({ freq: "semanal", weekdays: [2, 4], hora: 14, minuto: 30 }), 6, AGORA)!
    expect(runs.length).toBe(6)
    for (const r of runs) {
      const p = parts(r, SP)
      expect([2, 4]).toContain(p.wd)
      expect(p.h).toBe(14); expect(p.mi).toBe(30)
    }
  })

  it("mensal dia 1: cada execução no dia 1", () => {
    const runs = proximasExecucoes(base({ freq: "mensal", monthDay: 1, hora: 9, minuto: 0 }), 4, AGORA)!
    for (const r of runs) { const p = parts(r, SP); expect(p.d).toBe(1); expect(p.h).toBe(9) }
  })

  it("mensal dia 31: só meses com 31 dias (pula fev/abr/…)", () => {
    const runs = proximasExecucoes(base({ freq: "mensal", monthDay: 31, hora: 9, minuto: 0 }), 4, AGORA)!
    expect(runs.length).toBe(4)
    for (const r of runs) { const p = parts(r, SP); expect(p.d).toBe(31) }
    // Confirms there was a jump larger than a month at some point (Feb was skipped).
    const meses = runs.map(r => parts(r, SP).mo)
    expect(meses).not.toContain(2) // February never has a 31st
    expect(meses).not.toContain(4) // April has 30
  })

  it("mensal último dia: cada execução no último dia do mês", () => {
    const runs = proximasExecucoes(base({ freq: "mensal", monthLast: true, hora: 18, minuto: 0 }), 4, AGORA)!
    for (const r of runs) {
      const p = parts(r, SP)
      const ultimo = new Date(Date.UTC(p.y, p.mo, 0)).getUTCDate()
      expect(p.d).toBe(ultimo)
      expect(p.h).toBe(18)
    }
  })

  it("avançado cron reconhecível tem prévia; rrule cru não", () => {
    expect(proximasExecucoes(base({ freq: "avancado", advTipo: "cron", advCron: "0 9 * * *" }), 3, AGORA)).toHaveLength(3)
    expect(proximasExecucoes(base({ freq: "avancado", advTipo: "cron", advCron: "invalido" }), 3, AGORA)).toBeNull()
    expect(proximasExecucoes(base({ freq: "avancado", advTipo: "rrule", advRrule: "FREQ=DAILY" }), 3, AGORA)).toBeNull()
  })

  it("respeita o fuso: 09:00 em UTC ≠ 09:00 em São Paulo", () => {
    const spRun = proximasExecucoes(base({ freq: "diario", hora: 9, minuto: 0, timezone: SP }), 1, AGORA)![0]
    const utcRun = proximasExecucoes(base({ freq: "diario", hora: 9, minuto: 0, timezone: "UTC" }), 1, AGORA)![0]
    // 09:00 São Paulo = 12:00Z; 09:00 UTC = 09:00Z. Different instants.
    expect(spRun.getTime()).not.toBe(utcRun.getTime())
    expect(parts(spRun, SP).h).toBe(9)
    expect(parts(utcRun, "UTC").h).toBe(9)
  })
})
