import { describe, it, expect } from "vitest"
import { ORIGENS } from "@/app/components/observability/historico-url"
import { ORIGENS_DA_UI } from "@/app/components/observability/filtros"
import { rotuloDaOrigem } from "@/lib/formatos"

/**
 * Two lists of origins on purpose: the URL's (`ORIGENS`) and the picker's
 * (`ORIGENS_DA_UI`, in the order people read). If one gains a value and the
 * other doesn't, the filter shows an origin that the URL discards on reload
 * — or accepts in the URL something the picker can't display.
 */
describe("origens de execução", () => {
  it("URL e seletor aceitam exatamente o mesmo conjunto", () => {
    expect(new Set(ORIGENS_DA_UI)).toEqual(new Set(ORIGENS))
    expect(ORIGENS_DA_UI).toHaveLength(ORIGENS.length)
  })
  it("toda origem tem rótulo em português", () => {
    for (const o of ORIGENS) expect(rotuloDaOrigem(o), o).toEqual(expect.any(String))
  })
  it("inclui a origem do servidor MCP", () => {
    expect(ORIGENS).toContain("mcp")
  })
})
