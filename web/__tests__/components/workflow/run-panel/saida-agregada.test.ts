/**
 * `print()` output arrives aggregated and WITHOUT `message`.
 *
 * The executor closes the stdout batch by bytes and writes the text only once,
 * in `extra.lines` — before, it repeated everything in `extra.message` and the
 * event went over the 64 KB ceiling, reaching the panel stripped down to the
 * control fields: the batch's 200 lines vanished at once, silently. Whoever reads
 * the event on the client therefore needs to read `lines`; reading only
 * `message` leaves the row empty.
 */
import { describe, it, expect } from "vitest"
import { RunEvent } from "@/app/stores/workflowExecutionStore"
import { textoDoEvento } from "@/app/components/workflow/run-panel/raw-tab"

function evento(over: Partial<RunEvent>): RunEvent {
  return { seq: 0, ts: 1_700_000_000_000, kind: "stdout", level: "info", status: "log", raw: {}, ...over }
}

describe("textoDoEvento (aba Bruto)", () => {
  it("mostra a linha quando o lote agregado tem uma só", () => {
    expect(textoDoEvento(evento({ lines: ["processando 1200 feições"] })))
      .toBe("processando 1200 feições")
  })

  it("resume o lote agregado dizendo quantas linhas vieram junto", () => {
    // One panel row per event in the raw stream; the full content appears when
    // expanded and, one by one, in the "Nós" (nodes) tab.
    expect(textoDoEvento(evento({ lines: ["um", "dois", "três"] })))
      .toBe("um … (+2 linha(s))")
  })

  it("não deixa a linha vazia por falta de `message`", () => {
    // The concrete regression: stdout without `message` showed up as a blank
    // row in the "Bruto" (raw) tab, as if the script hadn't printed anything.
    expect(textoDoEvento(evento({ lines: ["saída"], message: null }))).not.toBe("")
  })

  it("eventos de ciclo de vida continuam usando `message`", () => {
    expect(textoDoEvento(evento({ kind: "lifecycle", status: "failed", level: "error", message: "estourou" })))
      .toBe("estourou")
  })

  it("evento sem texto nenhum não inventa conteúdo", () => {
    expect(textoDoEvento(evento({ kind: "lifecycle", status: "started" }))).toBe("")
    expect(textoDoEvento(evento({ lines: [] }))).toBe("")
  })
})
