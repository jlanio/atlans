import { describe, expect, it } from "vitest"
import { resumirAgendamento } from "@/app/components/projects/gatilho"
import { resumirNoIdioma, traduzirResumo } from "@/app/components/home/agendamentos/resumo"
import type { IWorkflowSchedule } from "@/service/types"

/**
 * O resumo do agendamento na lista da Home, por idioma. Em português é o
 * `resumirAgendamento` do gatilho tal e qual (o painel de administração usa o
 * mesmo); em inglês e espanhol o estado vem de lá e só as frases mudam.
 *
 * As datas são montadas no fuso LOCAL: "amanhã" e "hoje" não dependem do fuso
 * da máquina que roda o teste.
 */

const AGORA = new Date(2026, 8, 7, 12, 0, 0)
const local = (dia: number, h: number, m = 0, ano = 2026, mes = 8) => new Date(ano, mes, dia, h, m).toISOString()

function schedule(extra: Partial<IWorkflowSchedule> = {}): IWorkflowSchedule {
  return {
    active: true, next_run_at: local(8, 6), last_run_at: null,
    strategy: "cron", cron_expression: "0 6 * * *", timezone: "America/Sao_Paulo", ...extra,
  }
}
const cron = (expr: string, extra: Partial<IWorkflowSchedule> = {}) => schedule({ cron_expression: expr, ...extra })
const intervalo = (interval: number | null, unit: string | null) =>
  schedule({ strategy: "interval", interval, unit, cron_expression: null })

// As formas que o gatilho traduz e as que ele deixa cruas (as mesmas do teste dele).
const CRONS = [
  "0 6 * * *", "30 18 * * *", "30 7 * * 1-5", "0 2 * * 0", "0 2 * * 7", "0 9 * * 1", "15 22 * * 6",
  "0 8 1 * *", "0 0 15 * *", "0 */6 * * *", "*/15 * * * *", "0 * * * *", "* * * * *", "  0   6 * * *  ",
  "5 4 * 2 *", "0 6 * * 1,3", "0 6 1 * 1", "*/10 8-18 * * *", "0 6 * *", "60 6 * * *", "0 25 * * *",
  "0 6 32 * *", "0 */0 * * *", "*/0 * * * *",
]

const TODOS: IWorkflowSchedule[] = [
  ...CRONS.map((expr) => cron(expr)),
  cron(""),
  intervalo(30, "seconds"), intervalo(15, "minutes"), intervalo(6, "hours"),
  intervalo(1, "days"), intervalo(2, "days"), intervalo(3, "weeks"), intervalo(4, null),
  intervalo(null, "hours"), intervalo(0, "hours"),
  schedule({ strategy: "rrule", rrule_expression: "FREQ=WEEKLY", cron_expression: null }),
  schedule({ strategy: "outra" }),
  // Os estados: pausado, calculando (sem próxima e com a próxima vencida) e as próximas.
  schedule({ active: false }),
  schedule({ next_run_at: null }),
  schedule({ next_run_at: local(7, 9) }),
  schedule({ next_run_at: local(7, 18, 30) }),
  schedule({ next_run_at: local(27, 8, 4) }),
  schedule({ next_run_at: local(5, 8, 4, 2027, 0) }),
]

describe("resumirNoIdioma — português", () => {
  it("é o resumo do gatilho tal e qual, em todos os casos", () => {
    for (const s of TODOS) {
      for (const ativo of [true, false]) {
        expect(resumirNoIdioma(s, ativo, "pt-BR", AGORA)).toEqual(resumirAgendamento(s, ativo, AGORA))
      }
    }
  })

  it("sem schedule é nulo nos três idiomas", () => {
    expect(resumirNoIdioma(null, true, "pt-BR", AGORA)).toBeNull()
    expect(resumirNoIdioma(undefined, true, "en", AGORA)).toBeNull()
    expect(resumirNoIdioma(null, true, "es", AGORA)).toBeNull()
  })
})

describe("o molde em português do dicionário", () => {
  it("passado pelo caminho dos outros idiomas, dá exatamente o texto do gatilho", () => {
    // É o que prova que o reconhecimento de cron daqui espelha o do gatilho:
    // uma forma que um traduz e o outro não sairia diferente aqui.
    for (const s of TODOS) {
      for (const ativo of [true, false]) {
        const doGatilho = resumirAgendamento(s, ativo, AGORA)!
        expect(traduzirResumo(doGatilho, s, "pt-BR", AGORA)).toEqual(doGatilho)
      }
    }
  })
})

describe("resumirNoIdioma — o estado é o do gatilho nos três idiomas", () => {
  it("estado, `descricaoCrua` e a presença da próxima não mudam com o idioma", () => {
    for (const s of TODOS) {
      for (const ativo of [true, false]) {
        const base = resumirAgendamento(s, ativo, AGORA)!
        for (const idioma of ["en", "es"] as const) {
          const r = resumirNoIdioma(s, ativo, idioma, AGORA)!
          expect(r.estado).toBe(base.estado)
          expect(r.descricaoCrua).toBe(base.descricaoCrua)
          expect(r.proxima == null).toBe(base.proxima == null)
          expect(r.motivoPausa == null).toBe(base.motivoPausa == null)
        }
      }
    }
  })

  it("o cron que o gatilho não traduz segue cru — é a expressão que a pessoa escreveu", () => {
    for (const expr of CRONS.filter((e) => resumirAgendamento(cron(e), true, AGORA)!.descricaoCrua)) {
      expect(resumirNoIdioma(cron(expr), true, "en", AGORA)?.descricao).toBe(expr.trim())
      expect(resumirNoIdioma(cron(expr), true, "es", AGORA)?.descricao).toBe(expr.trim())
    }
  })
})

describe("resumirNoIdioma — inglês", () => {
  const d = (s: IWorkflowSchedule) => resumirNoIdioma(s, true, "en", AGORA)!.descricao

  it("a cadência do cron com a hora de relógio do inglês", () => {
    expect(d(cron("0 6 * * *"))).toMatch(/^every day at 6:00\sAM$/)
    expect(d(cron("30 18 * * *"))).toMatch(/^every day at 6:30\sPM$/)
    expect(d(cron("30 7 * * 1-5"))).toMatch(/^Mon–Fri at 7:30\sAM$/)
    expect(d(cron("0 9 * * 1"))).toMatch(/^Mondays at 9:00\sAM$/)
    expect(d(cron("0 2 * * 7"))).toMatch(/^Sundays at 2:00\sAM$/)
    expect(d(cron("15 22 * * 6"))).toMatch(/^Saturdays at 10:15\sPM$/)
    expect(d(cron("0 8 5 * *"))).toMatch(/^monthly on day 5 at 8:00\sAM$/)
    expect(d(cron("*/15 * * * *"))).toBe("every 15 min")
    expect(d(cron("0 */6 * * *"))).toBe("every 6 h")
    expect(d(cron("* * * * *"))).toBe("every 1 min")
    expect(d(cron(""))).toBe("schedule")
  })

  it("intervalo, rrule e o que não se reconhece", () => {
    expect(d(intervalo(2, "days"))).toBe("every 2 days")
    expect(d(intervalo(1, "days"))).toBe("every 1 day")
    expect(d(intervalo(30, "seconds"))).toBe("every 30 s")
    expect(d(intervalo(3, "weeks"))).toBe("every 3 weeks")
    expect(d(intervalo(null, "hours"))).toBe("interval")
    expect(d(schedule({ strategy: "rrule", cron_expression: null }))).toBe("recurrence (RRULE)")
  })

  it("a próxima execução: amanhã tem nome, o resto é o calendário da Home", () => {
    const p = (next: string) => resumirNoIdioma(schedule({ next_run_at: next }), true, "en", AGORA)!.proxima
    expect(p(local(8, 6))).toMatch(/^tomorrow, 6:00\sAM$/)
    expect(p(local(7, 18, 30))).toMatch(/^today, 6:30\sPM$/)
    expect(p(local(27, 8, 4))).toMatch(/^Sep 27, 8:04\sAM$/)
    expect(p(local(5, 8, 4, 2027, 0))).toContain("2027")
  })

  it("o motivo da pausa", () => {
    expect(resumirNoIdioma(schedule(), false, "en", AGORA)?.motivoPausa).toBe("workflow inactive")
  })
})

describe("resumirNoIdioma — espanhol", () => {
  const d = (s: IWorkflowSchedule) => resumirNoIdioma(s, true, "es", AGORA)!.descricao

  it("a cadência do cron, com o artigo que concorda com a hora", () => {
    expect(d(cron("0 6 * * *"))).toBe("todos los días a las 6:00")
    expect(d(cron("0 1 * * *"))).toBe("todos los días a la 1:00")
    expect(d(cron("5 13 * * *"))).toBe("todos los días a las 13:05")
    expect(d(cron("30 7 * * 1-5"))).toBe("lun–vie a las 7:30")
    expect(d(cron("0 9 * * 1"))).toBe("los lunes a las 9:00")
    expect(d(cron("0 2 * * 0"))).toBe("los domingos a las 2:00")
    expect(d(cron("0 8 5 * *"))).toBe("el día 5 de cada mes a las 8:00")
    expect(d(cron("*/15 * * * *"))).toBe("cada 15 min")
    expect(d(cron("0 * * * *"))).toBe("cada 1 h")
    expect(d(cron(""))).toBe("programación")
  })

  it("intervalo e rrule", () => {
    expect(d(intervalo(2, "days"))).toBe("cada 2 días")
    expect(d(intervalo(1, "days"))).toBe("cada 1 día")
    expect(d(intervalo(0, "hours"))).toBe("intervalo")
    expect(d(schedule({ strategy: "rrule", cron_expression: null }))).toBe("recurrencia (RRULE)")
  })

  it("a próxima execução e o motivo da pausa", () => {
    const p = (next: string) => resumirNoIdioma(schedule({ next_run_at: next }), true, "es", AGORA)!.proxima
    expect(p(local(8, 6))).toBe("mañana, 6:00")
    expect(p(local(7, 18, 30))).toBe("hoy, 18:30")
    expect(p(local(27, 8, 4))).toMatch(/^27 sept?, 8:04$/)
    expect(resumirNoIdioma(schedule(), false, "es", AGORA)?.motivoPausa).toBe("flujo inactivo")
  })
})
