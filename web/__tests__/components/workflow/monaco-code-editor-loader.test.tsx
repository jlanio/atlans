/**
 * The code editor loads Monaco from its own origin (`public/monaco/vs`, copied
 * at build time by scripts/copiar-monaco.mjs). Without `loader.config`,
 * @monaco-editor/loader goes to jsdelivr — which the blocking CSP refuses, and
 * the editor stays on the skeleton forever.
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
