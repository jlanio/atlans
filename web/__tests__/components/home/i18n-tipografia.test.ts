import { describe, it, expect } from "vitest"

import { textosDe } from "@/app/components/home/i18n"

/**
 * The dictionaries' typography: English uses the typographic apostrophe (’), as
 * the shell and the lists always did. Mixing the two left "Couldn't start
 * your session" on the login next to "Couldn’t load chats" in the bar.
 */
function textos(o: unknown, caminho: string): Array<[string, string]> {
  if (typeof o === "string") return [[caminho, o]]
  if (typeof o === "function") {
    // Text that depends on a number: sampled with one and with several.
    return [1, 3].flatMap((n) => {
      try {
        return textos(o(n, n), `${caminho}(${n})`)
      } catch {
        return []
      }
    })
  }
  if (o && typeof o === "object") return Object.entries(o).flatMap(([k, v]) => textos(v, `${caminho}.${k}`))
  return []
}

describe("a tipografia dos dicionários", () => {
  it.each(["en", "es"] as const)("em %s, nenhum apóstrofo reto entre letras", (idioma) => {
    const retos = textos(textosDe(idioma), idioma).filter(([, t]) => /[A-Za-z]'[A-Za-z]/.test(t))
    expect(retos).toEqual([])
  })

  it("a amostragem enxerga os textos (inclusive os que são função)", () => {
    const todos = textos(textosDe("en"), "en")
    expect(todos.length).toBeGreaterThan(300)
    expect(todos.some(([, t]) => t.includes("Try again in 3 minutes."))).toBe(true)
  })
})
