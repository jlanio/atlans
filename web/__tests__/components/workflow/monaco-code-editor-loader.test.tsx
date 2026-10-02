/**
 * O editor de código carrega o Monaco da própria origem (`public/monaco/vs`,
 * copiado no build por scripts/copiar-monaco.mjs). Sem o `loader.config`, o
 * @monaco-editor/loader vai ao jsdelivr — que a CSP bloqueante recusa, e o
 * editor fica no skeleton para sempre.
 */
import { describe, it, expect, vi } from "vitest"

const { config } = vi.hoisted(() => ({ config: vi.fn() }))

vi.mock("@monaco-editor/react", () => ({
  default: () => null,
  loader: { config },
}))

describe("monaco-code-editor", () => {
  it("aponta o loader para /monaco/vs antes de qualquer editor montar", async () => {
    await import("@/app/components/workflow/nodes-configuration/fields/monaco-code-editor")
    expect(config).toHaveBeenCalledTimes(1)
    expect(config).toHaveBeenCalledWith({ paths: { vs: "/monaco/vs" } })
  })
})
