/**
 * A saída de `print()` chega agregada e SEM `message`.
 *
 * O executor fecha o lote de stdout por bytes e escreve o texto uma vez só, em
 * `extra.lines` — antes ele repetia tudo em `extra.message` e o evento passava do
 * teto de 64 KB, chegando ao painel reduzido aos campos de controle: as 200
 * linhas do lote sumiam de uma vez, em silêncio. Quem lê o evento no cliente
 * precisa, portanto, ler `lines`; ler só `message` deixa a linha vazia.
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
    // Uma linha de painel por evento no stream cru; o conteúdo completo aparece
    // ao expandir e, uma a uma, na aba "Nós".
    expect(textoDoEvento(evento({ lines: ["um", "dois", "três"] })))
      .toBe("um … (+2 linha(s))")
  })

  it("não deixa a linha vazia por falta de `message`", () => {
    // A regressão concreta: stdout sem `message` aparecia como uma linha em
    // branco na aba "Bruto", como se o script não tivesse impresso nada.
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
