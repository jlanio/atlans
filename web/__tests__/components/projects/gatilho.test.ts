import { describe, expect, it } from "vitest"
import {
  ROTULO_DO_GATILHO, derivarGatilho, descreverIntervalo, formatarProxima, resumirAgendamento,
} from "@/app/components/projects/gatilho"
import type { IWorkflowSchedule } from "@/service/types"

const agora = new Date("2026-09-07T12:00:00Z")
const iso = (horas: number) => new Date(agora.getTime() + horas * 3600_000).toISOString()

function schedule(extra: Partial<IWorkflowSchedule> = {}): IWorkflowSchedule {
  return {
    active: true, next_run_at: iso(24), last_run_at: null,
    strategy: "cron", cron_expression: "0 6 * * *", timezone: "America/Sao_Paulo", ...extra,
  }
}

describe("derivarGatilho", () => {
  it("nenhum gatilho e não é sub-fluxo: só manual", () => {
    expect(derivarGatilho({})).toEqual({ tipo: "manual", rotulo: "Só manual", extras: [] })
  })

  it("um gatilho só: tipo e rótulo dele, sem extras", () => {
    expect(derivarGatilho({ has_schedule_trigger: true })).toEqual({ tipo: "agendado", rotulo: "Agendado", extras: [] })
    expect(derivarGatilho({ has_webhook_trigger: true }).rotulo).toBe("Webhook")
    expect(derivarGatilho({ has_file_trigger: true }).rotulo).toBe("Por arquivo")
    expect(derivarGatilho({ has_geofence_trigger: true }).rotulo).toBe("Por geofence")
    expect(derivarGatilho({ is_subworkflow: true })).toEqual({
      tipo: "subfluxo", rotulo: "Chamado por outros workflows", extras: [],
    })
  })

  it("precedência: subfluxo > agendado > webhook > arquivo > geofence", () => {
    expect(derivarGatilho({ is_subworkflow: true, has_schedule_trigger: true, has_webhook_trigger: true }).tipo).toBe("subfluxo")
    expect(derivarGatilho({ has_schedule_trigger: true, has_webhook_trigger: true }).tipo).toBe("agendado")
    expect(derivarGatilho({ has_webhook_trigger: true, has_file_trigger: true, has_geofence_trigger: true }).tipo).toBe("webhook")
    expect(derivarGatilho({ has_file_trigger: true, has_geofence_trigger: true }).tipo).toBe("arquivo")
  })

  it("os demais viram extras, na mesma ordem, e o rótulo os concatena", () => {
    expect(derivarGatilho({ has_schedule_trigger: true, has_webhook_trigger: true })).toEqual({
      tipo: "agendado", rotulo: "Agendado + webhook", extras: ["webhook"],
    })
    expect(derivarGatilho({ has_webhook_trigger: true, has_file_trigger: true, has_geofence_trigger: true })).toEqual({
      tipo: "webhook", rotulo: "Webhook + arquivo + geofence", extras: ["arquivo", "geofence"],
    })
    expect(derivarGatilho({ is_subworkflow: true, has_schedule_trigger: true }).rotulo)
      .toBe("Chamado por outros workflows + agendado")
  })

  it("tem rótulo para todo tipo", () => {
    expect(Object.keys(ROTULO_DO_GATILHO).sort()).toEqual(["agendado", "arquivo", "geofence", "manual", "subfluxo", "webhook"])
  })
})

describe("descrição do cron", () => {
  const descricao = (expr: string) => resumirAgendamento(schedule({ cron_expression: expr }), true, agora)?.descricao

  it.each([
    ["0 6 * * *", "todo dia às 06:00"],
    ["30 18 * * *", "todo dia às 18:30"],
    ["30 7 * * 1-5", "seg–sex às 07:30"],
    ["0 2 * * 0", "aos domingos às 02:00"],
    ["0 2 * * 7", "aos domingos às 02:00"],
    ["0 9 * * 1", "às segundas às 09:00"],
    ["15 22 * * 6", "aos sábados às 22:15"],
    ["0 8 1 * *", "dia 1 às 08:00"],
    ["0 0 15 * *", "dia 15 às 00:00"],
    ["0 */6 * * *", "a cada 6 h"],
    ["*/15 * * * *", "a cada 15 min"],
    ["0 * * * *", "a cada 1 h"],
    ["* * * * *", "a cada 1 min"],
  ])("%s → %s", (expr, esperado) => {
    expect(descricao(expr)).toBe(esperado)
  })

  it("aceita espaços a mais nas pontas e entre campos", () => {
    expect(descricao("  0   6 * * *  ")).toBe("todo dia às 06:00")
  })

  it.each([
    "5 4 * 2 *",          // specific month
    "0 6 * * 1,3",        // list of days
    "0 6 1 * 1",          // day of month AND day of week
    "*/10 8-18 * * *",    // range of hours
    "0 6 * *",            // 4 campos
    "60 6 * * *",         // minute out of range
    "0 25 * * *",         // hour out of range
    "0 6 32 * *",         // day out of range
    "0 */0 * * *",        // passo zero
  ])("não reconhecido devolve o cron cru: %s", (expr) => {
    expect(descricao(expr)).toBe(expr)
  })
})

describe("descreverIntervalo", () => {
  it("usa a unidade abreviada, e 'dia/dias' por extenso", () => {
    expect(descreverIntervalo(15, "minutes")).toBe("a cada 15 min")
    expect(descreverIntervalo(6, "hours")).toBe("a cada 6 h")
    expect(descreverIntervalo(2, "days")).toBe("a cada 2 dias")
    expect(descreverIntervalo(1, "days")).toBe("a cada 1 dia")
    expect(descreverIntervalo(30, "seconds")).toBe("a cada 30 s")
  })
  it("unidade desconhecida ou intervalo inválido não quebram", () => {
    expect(descreverIntervalo(3, "weeks")).toBe("a cada 3 weeks")
    expect(descreverIntervalo(null, "hours")).toBe("intervalo")
    expect(descreverIntervalo(0, "hours")).toBe("intervalo")
  })
})

describe("resumirAgendamento", () => {
  it("sem schedule é nulo", () => {
    expect(resumirAgendamento(null, true, agora)).toBeNull()
    expect(resumirAgendamento(undefined, true, agora)).toBeNull()
  })

  it("ativo: descrição do cron, próxima formatada, sem motivo de pausa", () => {
    const r = resumirAgendamento(schedule(), true, agora)
    expect(r).toEqual({
      estado: "ativo",
      descricao: "todo dia às 06:00",
      descricaoCrua: false,
      proxima: expect.stringMatching(/^amanhã, \d{2}:\d{2}$/),
      motivoPausa: null,
    })
  })

  it("pausado pelo schedule: sem próxima, sem motivo", () => {
    const r = resumirAgendamento(schedule({ active: false }), true, agora)
    expect(r?.estado).toBe("pausado")
    expect(r?.proxima).toBeNull()
    expect(r?.motivoPausa).toBeNull()
  })

  it("workflow inativo conta como pausado, com o motivo — mesmo que a linha do schedule ainda diga ativo", () => {
    const r = resumirAgendamento(schedule({ active: true }), false, agora)
    expect(r?.estado).toBe("pausado")
    expect(r?.proxima).toBeNull()
    expect(r?.motivoPausa).toBe("workflow inativo")
  })

  it("next_run_at no passado é 'calculando', não 'próxima há 3 h'", () => {
    // The scheduler has not advanced the mark yet; showing an already past time
    // as "next" is misleading. It becomes "calculando" (the scheduler's tick fixes it).
    const r = resumirAgendamento(schedule({ next_run_at: iso(-3) }), true, agora)
    expect(r?.estado).toBe("calculando")
    expect(r?.proxima).toBeNull()
  })

  it("ativo sem next_run_at é 'calculando' (o agendador preenche em ≤30 s)", () => {
    const r = resumirAgendamento(schedule({ next_run_at: null }), true, agora)
    expect(r?.estado).toBe("calculando")
    expect(r?.proxima).toBeNull()
    expect(r?.motivoPausa).toBeNull()
  })

  it("cron não reconhecido vai cru, marcado para o componente mostrar em code", () => {
    const r = resumirAgendamento(schedule({ cron_expression: "5 4 * 2 *" }), true, agora)
    expect(r?.descricao).toBe("5 4 * 2 *")
    expect(r?.descricaoCrua).toBe(true)
  })

  it("intervalo e rrule", () => {
    expect(resumirAgendamento(schedule({ strategy: "interval", interval: 15, unit: "minutes", cron_expression: null }), true, agora)?.descricao)
      .toBe("a cada 15 min")
    expect(resumirAgendamento(schedule({ strategy: "rrule", rrule_expression: "FREQ=WEEKLY", cron_expression: null }), true, agora)?.descricao)
      .toBe("recorrência (RRULE)")
  })
})

describe("formatarProxima", () => {
  it("amanhã ganha o próprio nome; hoje e datas distantes seguem formatarInicio", () => {
    expect(formatarProxima(iso(24), agora)).toMatch(/^amanhã, \d{2}:\d{2}$/)
    expect(formatarProxima(iso(0.5), agora)).toMatch(/^hoje, \d{2}:\d{2}$/)
    expect(formatarProxima(iso(24 * 20), agora)).toMatch(/^27 set, \d{2}:\d{2}$/)
    expect(formatarProxima(null, agora)).toBe("—")
  })
})
