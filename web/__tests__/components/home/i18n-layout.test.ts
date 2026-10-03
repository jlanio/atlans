import { describe, it, expect } from "vitest"
import fs from "node:fs"
import path from "node:path"

/**
 * The dashboard layout loads on EVERY route, administration included. If
 * something in it imports the index of the Home's texts (`home/i18n`), the layout's
 * chunk carries along the assistant and sign-in dictionaries, in all three
 * languages (~20 KB gzip), to screens that never show them — and the route table
 * of `next build` does not show that. The shell imports `home/i18n/da-casca`.
 *
 * The test follows the imports starting from the layout, as the bundler would (the
 * `import type`s vanish at compile time and do not count).
 */
const WEB = path.resolve(__dirname, "../../..")
const EXTENSOES = ["", ".ts", ".tsx", ".js", ".mjs", "/index.ts", "/index.tsx"]

function resolver(de: string, specifier: string): string | null {
  let base: string
  if (specifier.startsWith("@/")) base = path.join(WEB, specifier.slice(2))
  else if (specifier.startsWith(".")) base = path.resolve(path.dirname(de), specifier)
  else return null // pacote
  for (const ext of EXTENSOES) {
    const alvo = base + ext
    if (fs.existsSync(alvo) && fs.statSync(alvo).isFile()) return alvo
  }
  return null
}

const IMPORT = /(?:import|export)\s+(type\s+)?(?:[^"'`]*?\sfrom\s+)?["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/g

function reachable(inicio: string): Set<string> {
  const vistos = new Set<string>()
  const pilha = [path.join(WEB, inicio)]
  while (pilha.length) {
    const arquivo = pilha.pop()!
    if (vistos.has(arquivo)) continue
    vistos.add(arquivo)
    for (const m of fs.readFileSync(arquivo, "utf8").matchAll(IMPORT)) {
      if (m[1]) continue // import type
      const alvo = resolver(arquivo, m[2] ?? m[3])
      if (alvo) pilha.push(alvo)
    }
  }
  return new Set([...vistos].map((a) => path.relative(WEB, a)))
}

describe("o layout do dashboard e os dicionários da Home", () => {
  it("a casca não alcança o índice nem os dicionários do assistente e da entrada", () => {
    const grafo = reachable("app/(dashboard)/layout.tsx")
    // The test sees the graph: the Home's sidebar and its texts are there.
    expect(grafo).toContain("app/components/sidebar/home-sidebar.tsx")
    expect(grafo).toContain("app/components/home/i18n/da-casca.ts")

    expect(grafo).not.toContain("app/components/home/i18n/index.ts")
    expect(grafo).not.toContain("app/components/home/i18n/secoes/assistente.ts")
    expect(grafo).not.toContain("app/components/home/i18n/secoes/entrada.ts")
  })

  it("a Home, sim, alcança todos", () => {
    const grafo = reachable("app/(dashboard)/page.tsx")
    expect(grafo).toContain("app/components/home/i18n/secoes/assistente.ts")
    expect(grafo).toContain("app/components/home/i18n/secoes/entrada.ts")
  })
})
