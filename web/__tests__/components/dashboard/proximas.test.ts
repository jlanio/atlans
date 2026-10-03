import { describe, expect, it } from "vitest"
import type { IWorkflow, IWorkflowSchedule } from "@/service/types"
import { MAXIMO_DE_PROXIMAS, proximas } from "@/app/components/dashboard/proximas"

// Fixed anchor to make "future/past" deterministic. The `fromBackend` helper
// treats a string without an offset as UTC, so we use explicit UTC times.
const AGORA = new Date("2026-09-07T12:00:00Z")

function agendamento(next: string | null, extra: Partial<IWorkflowSchedule> = {}): IWorkflowSchedule {
  return { active: true, next_run_at: next, last_run_at: null, strategy: "cron", ...extra }
}

function wf(id: string, extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: id, flag_ative: true, name: `Fluxo ${id}`, description: "", version: "1", priority: 0,
    definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u1", ...extra,
  }
}

describe("proximas", () => {
  it("mantém só os agendados ativos com próxima no futuro", () => {
    const lista = [
      wf("futuro", { schedule: agendamento("2026-09-07T18:00:00Z") }),
      wf("passado", { schedule: agendamento("2026-09-07T06:00:00Z") }),
      wf("sem-agendamento", { schedule: null }),
      wf("sem-next", { schedule: agendamento(null) }),
    ]
    expect(proximas(lista, AGORA).map(w => w.id_hash)).toEqual(["futuro"])
  })

  it("ordena por horário crescente", () => {
    const lista = [
      wf("tarde", { schedule: agendamento("2026-09-07T20:00:00Z") }),
      wf("cedo", { schedule: agendamento("2026-09-07T13:00:00Z") }),
      wf("meio", { schedule: agendamento("2026-09-07T16:00:00Z") }),
    ]
    expect(proximas(lista, AGORA).map(w => w.id_hash)).toEqual(["cedo", "meio", "tarde"])
  })

  it("corta em 5", () => {
    const lista = Array.from({ length: 8 }, (_, i) =>
      wf(`w${i}`, { schedule: agendamento(`2026-09-07T${String(13 + i).padStart(2, "0")}:00:00Z`) }))
    const r = proximas(lista, AGORA)
    expect(r).toHaveLength(MAXIMO_DE_PROXIMAS)
    expect(r.map(w => w.id_hash)).toEqual(["w0", "w1", "w2", "w3", "w4"])
  })

  it("ignora o pausado (schedule.active false) mesmo com next no futuro", () => {
    const lista = [wf("pausado", { schedule: agendamento("2026-09-07T18:00:00Z", { active: false }) })]
    expect(proximas(lista, AGORA)).toEqual([])
  })

  it("ignora o workflow inativo (flag_ative false)", () => {
    const lista = [wf("inativo", { flag_ative: false, schedule: agendamento("2026-09-07T18:00:00Z") })]
    expect(proximas(lista, AGORA)).toEqual([])
  })
})
