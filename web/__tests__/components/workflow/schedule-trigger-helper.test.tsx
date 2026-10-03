import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, fireEvent, cleanup, within } from "@testing-library/react"
import ScheduleTriggerHelper from "@/app/components/workflow/nodes-configuration/schedule-trigger-helper"

afterEach(cleanup)

type Campos = Record<string, string | number | boolean>

/** Collects the setNodeField calls into an object (last value per field). */
function harness(valores: Campos) {
  const escritos: Campos = {}
  const setNodeField = vi.fn((f: string, v: string | number | boolean) => { escritos[f] = v })
  render(<ScheduleTriggerHelper values={valores} setNodeField={setNodeField} hasUnsaved={false} nodeId="n1" />)
  return { escritos, setNodeField }
}

const DEFAULTS: Campos = {
  strategy: "cron", cron_expression: "0 9 * * *", interval: 60, unit: "minutes",
  timezone: "America/Sao_Paulo", active: true, rrule_expression: "",
}

describe("ScheduleTriggerHelper — leitura inicial", () => {
  it("cron semanal abre com a frequência e os dias certos", () => {
    harness({ ...DEFAULTS, cron_expression: "30 14 * * 2,4" })
    expect(screen.getByRole("button", { name: "Semanalmente" }).getAttribute("aria-pressed")).toBe("true")
    // Tuesday and Thursday checked; Monday not.
    expect(screen.getByRole("button", { name: "terça" }).getAttribute("aria-pressed")).toBe("true")
    expect(screen.getByRole("button", { name: "quinta" }).getAttribute("aria-pressed")).toBe("true")
    expect(screen.getByRole("button", { name: "segunda" }).getAttribute("aria-pressed")).toBe("false")
    expect(screen.getByText("Toda ter, qui às 14:30")).toBeTruthy()
  })

  it("mostra as próximas execuções (lista não vazia)", () => {
    harness({ ...DEFAULTS })
    const lista = screen.getByRole("list", { name: "Próximas execuções" })
    expect(within(lista).getAllByRole("listitem").length).toBeGreaterThan(0)
  })

  it("dia 31 mostra o aviso de meses pulados", () => {
    harness({ ...DEFAULTS, cron_expression: "0 9 31 * *" })
    expect(screen.getByText(/são pulados/i)).toBeTruthy()
  })

  it("cron legado '*/15 * * * *' abre em Avançado", () => {
    harness({ ...DEFAULTS, cron_expression: "*/15 * * * *" })
    expect(screen.getByRole("button", { name: "Avançado" }).getAttribute("aria-pressed")).toBe("true")
    expect((screen.getByDisplayValue("*/15 * * * *") as HTMLInputElement).value).toBe("*/15 * * * *")
  })
})

describe("ScheduleTriggerHelper — edição grava os campos canônicos", () => {
  it("trocar para Diariamente grava o novo cron mantendo o horário (14:30)", () => {
    const { escritos } = harness({ ...DEFAULTS, cron_expression: "30 14 * * 2,4" }) // semanal 14:30
    fireEvent.click(screen.getByRole("button", { name: "Diariamente" }))
    expect(escritos.cron_expression).toBe("30 14 * * *")
    // strategy stays 'cron' → diff-only write doesn't rewrite what didn't change
    expect(escritos.strategy).toBeUndefined()
  })

  it("trocar para Intervalo grava strategy=interval", () => {
    const { escritos } = harness({ ...DEFAULTS, cron_expression: "0 9 * * *" })
    fireEvent.click(screen.getByRole("button", { name: "Intervalo" }))
    expect(escritos.strategy).toBe("interval")
  })

  it("marcar mais um dia no semanal atualiza o cron", () => {
    const { escritos } = harness({ ...DEFAULTS, cron_expression: "30 14 * * 2,4" })
    fireEvent.click(screen.getByRole("button", { name: "sexta" })) // add sexta (5)
    expect(escritos.cron_expression).toBe("30 14 * * 2,4,5")
  })

  it("não deixa desmarcar o último dia (semanal sempre tem ≥1)", () => {
    const { setNodeField } = harness({ ...DEFAULTS, cron_expression: "30 14 * * 2" }) // Tuesday only
    fireEvent.click(screen.getByRole("button", { name: "terça" })) // tries to remove the only one
    // No write: the click was ignored.
    expect(setNodeField).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: "terça" }).getAttribute("aria-pressed")).toBe("true")
  })

  it("desligar o 'ativo' grava active=false", () => {
    const { escritos } = harness({ ...DEFAULTS })
    fireEvent.click(screen.getByRole("switch", { name: "Agendamento ativo" }))
    expect(escritos.active).toBe(false)
  })

  it("mudar só o 'ativo' NÃO regrava o cron (evita recriar o schedule e pular o dia)", () => {
    const { escritos, setNodeField } = harness({ ...DEFAULTS, cron_expression: "00 09 * * *" })
    fireEvent.click(screen.getByRole("switch", { name: "Agendamento ativo" }))
    expect(escritos.active).toBe(false)
    // cron_expression intocado: nenhuma escrita canonizando '00 09' -> '0 9'.
    expect(setNodeField.mock.calls.some(c => c[0] === "cron_expression")).toBe(false)
  })

  it("cron avançado inválido não é gravado (preserva o agendamento) e mostra erro", () => {
    const { escritos } = harness({ ...DEFAULTS }) // daily 09:00 (valid cron)
    fireEvent.click(screen.getByRole("button", { name: "Avançado" }))
    fireEvent.change(screen.getByPlaceholderText("0 9 * * *"), { target: { value: "0 9 * *" } }) // 4 campos
    expect(escritos.cron_expression).not.toBe("0 9 * *")
    expect(screen.getByText(/precisa ter 5 campos/)).toBeTruthy()
  })

  it("abrir a aba RRule vazia NÃO apaga o cron salvo (ALTA #2)", () => {
    // Node saved with a daily cron. Going to Advanced → RRule tab (empty = invalid)
    // must not write strategy=rrule + cron_expression="" over the schedule.
    const { setNodeField } = harness({ ...DEFAULTS, cron_expression: "0 9 * * *", strategy: "cron" })
    fireEvent.click(screen.getByRole("button", { name: "Avançado" }))
    fireEvent.click(screen.getByRole("button", { name: "RRule" }))
    const tocou = (campo: string) => setNodeField.mock.calls.some(c => c[0] === campo)
    expect(tocou("strategy")).toBe(false)
    expect(tocou("cron_expression")).toBe(false)
    expect(tocou("rrule_expression")).toBe(false)
    expect(screen.getByText(/Informe a expressão RRule/)).toBeTruthy()
  })

  it("RRule válida em Avançado é gravada (a guarda não bloqueia o caso bom)", () => {
    const { escritos } = harness({ ...DEFAULTS, cron_expression: "0 9 * * *", strategy: "cron" })
    fireEvent.click(screen.getByRole("button", { name: "Avançado" }))
    fireEvent.click(screen.getByRole("button", { name: "RRule" }))
    fireEvent.change(screen.getByLabelText("Expressão RRule"), {
      target: { value: "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0" },
    })
    expect(escritos.strategy).toBe("rrule")
    expect(escritos.rrule_expression).toBe("FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0")
  })
})

describe("ScheduleTriggerHelper — re-sincroniza com valores que chegam depois (ALTA #1)", () => {
  it("monta com values=undefined e re-sincroniza quando os valores salvos chegam", () => {
    // node-config-modal MOUNTS the helper with values=undefined and only fills
    // the fields in a later effect (same nodeId). Without re-sync, the saved node
    // would open on the default and the edit would write over the real rule.
    const setNodeField = vi.fn()
    const { rerender } = render(
      <ScheduleTriggerHelper values={undefined} setNodeField={setNodeField} hasUnsaved={false} nodeId="n1" />,
    )
    expect(screen.getByRole("button", { name: "Diariamente" }).getAttribute("aria-pressed")).toBe("true")

    rerender(
      <ScheduleTriggerHelper
        values={{ ...DEFAULTS, cron_expression: "30 14 * * 2,4" }}
        setNodeField={setNodeField} hasUnsaved={false} nodeId="n1"
      />,
    )
    expect(screen.getByRole("button", { name: "Semanalmente" }).getAttribute("aria-pressed")).toBe("true")
    expect(screen.getByRole("button", { name: "terça" }).getAttribute("aria-pressed")).toBe("true")
    // Re-syncing isn't a user edit: nothing should be written.
    expect(setNodeField).not.toHaveBeenCalled()
  })

  it("o eco da própria gravação (cron equivalente) NÃO re-inicializa o estado", () => {
    // The user is in Advanced; the parent re-renders with a canonically equal
    // cron — the canonical comparison avoids throwing the user back to Diariamente (daily).
    const setNodeField = vi.fn()
    const { rerender } = render(
      <ScheduleTriggerHelper values={{ ...DEFAULTS, cron_expression: "*/15 * * * *" }}
        setNodeField={setNodeField} hasUnsaved={false} nodeId="n1" />,
    )
    expect(screen.getByRole("button", { name: "Avançado" }).getAttribute("aria-pressed")).toBe("true")
    // New values object, same canonical content.
    rerender(
      <ScheduleTriggerHelper values={{ ...DEFAULTS, cron_expression: "*/15 * * * *" }}
        setNodeField={setNodeField} hasUnsaved={false} nodeId="n1" />,
    )
    expect(screen.getByRole("button", { name: "Avançado" }).getAttribute("aria-pressed")).toBe("true")
  })
})
