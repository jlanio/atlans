import { describe, it, expect } from "vitest"
import { ORIGENS } from "@/app/components/observability/historico-url"
import { ORIGENS_DA_UI } from "@/app/components/observability/filtros"
import { rotuloDaOrigem } from "@/lib/formatos"

/**
 * Duas listas de origens de propósito: a URL (`ORIGENS`) e o seletor
 * (`ORIGENS_DA_UI`, na ordem em que as pessoas leem). Se uma ganhar um valor
 * e a outra não, o filtro mostra uma origem que a URL descarta ao recarregar
 * — ou aceita na URL algo que o seletor não consegue exibir.
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
