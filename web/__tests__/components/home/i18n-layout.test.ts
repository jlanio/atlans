import { describe, it, expect } from "vitest"
import fs from "node:fs"
import path from "node:path"

/**
 * O layout do dashboard carrega em TODA rota, a administração inclusive. Se
 * algo dele importa o índice dos textos da Home (`home/i18n`), o bloco do
 * layout leva junto os dicionários do assistente e da entrada, nos três
 * idiomas (~20 KB gzip), para telas que nunca os mostram — e a tabela de rotas
 * do `next build` não mostra isso. A casca importa `home/i18n/da-casca`.
 *
 * O teste segue os imports a partir do layout, como o bundler faria (os
 * `import type` somem na compilação e não contam).
 */
const WEB = path.resolve(__dirname, "../../..")
const EXTENSOES = ["", ".ts", ".tsx", ".js", ".mjs", "/index.ts", "/index.tsx"]

function resolver(de: string, especificador: string): string | null {
  let base: string
  if (especificador.startsWith("@/")) base = path.join(WEB, especificador.slice(2))
  else if (especificador.startsWith(".")) base = path.resolve(path.dirname(de), especificador)
  else return null // pacote
  for (const ext of EXTENSOES) {
    const alvo = base + ext
    if (fs.existsSync(alvo) && fs.statSync(alvo).isFile()) return alvo
  }
  return null
}

const IMPORT = /(?:import|export)\s+(type\s+)?(?:[^"'`]*?\sfrom\s+)?["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/g

function alcancaveis(inicio: string): Set<string> {
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
    const grafo = alcancaveis("app/(dashboard)/layout.tsx")
    // O teste enxerga o grafo: a barra lateral da Home e os textos dela estão lá.
    expect(grafo).toContain("app/components/sidebar/home-sidebar.tsx")
    expect(grafo).toContain("app/components/home/i18n/da-casca.ts")

    expect(grafo).not.toContain("app/components/home/i18n/index.ts")
    expect(grafo).not.toContain("app/components/home/i18n/secoes/assistente.ts")
    expect(grafo).not.toContain("app/components/home/i18n/secoes/entrada.ts")
  })

  it("a Home, sim, alcança todos", () => {
    const grafo = alcancaveis("app/(dashboard)/page.tsx")
    expect(grafo).toContain("app/components/home/i18n/secoes/assistente.ts")
    expect(grafo).toContain("app/components/home/i18n/secoes/entrada.ts")
  })
})
