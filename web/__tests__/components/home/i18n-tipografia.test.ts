import { describe, it, expect } from "vitest"

import { textosDe } from "@/app/components/home/i18n"

/**
 * A tipografia dos dicionários: o inglês usa o apóstrofo tipográfico (’), como
 * a casca e as listas sempre usaram. Misturar os dois deixava "Couldn't start
 * your session" no login ao lado de "Couldn’t load chats" na barra.
 */
function textos(o: unknown, caminho: string): Array<[string, string]> {
  if (typeof o === "string") return [[caminho, o]]
  if (typeof o === "function") {
    // Texto que depende de número: amostrado com um e com vários.
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
