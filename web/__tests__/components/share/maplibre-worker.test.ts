import { execFileSync } from "node:child_process"
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { describe, it, expect, vi } from "vitest"

/**
 * O maplibre-gl 6 roda o worker a partir de uma URL, que com bundler ele não
 * acha sozinho. Sem ela o worker morre em silêncio e os tiles vetoriais nunca
 * carregam, mas o resto do mapa abre normalmente, então só este teste pegaria.
 * O MapLibreMap aponta o `setWorkerUrl` para a cópia que
 * scripts/copiar-maplibre.mjs faz em `public/maplibre` no build e no dev.
 * Este teste confere a cadeia inteira: a URL, o arquivo copiado e o que ele
 * importa.
 */
const { setWorkerUrl } = vi.hoisted(() => ({ setWorkerUrl: vi.fn() }))
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))
vi.mock("maplibre-gl", () => ({ setWorkerUrl }))

import "@/app/components/share/MapLibreMap"

const WEB = path.resolve(__dirname, "..", "..", "..")

describe("worker do maplibre-gl", () => {
  it("a URL configurada aponta para o worker copiado, com tudo o que ele importa ao lado", () => {
    expect(setWorkerUrl).toHaveBeenCalledTimes(1)
    const url: string = setWorkerUrl.mock.calls[0][0]
    expect(url).toMatch(/^\/maplibre\/[^/]+\.mjs$/)

    execFileSync(process.execPath, [path.join(WEB, "scripts", "copiar-maplibre.mjs")], { stdio: "pipe" })

    const worker = path.join(WEB, "public", url)
    expect(existsSync(worker), worker).toBe(true)
    const importados = [...readFileSync(worker, "utf8").matchAll(/\bfrom\s*["'`]\.\/([^"'`]+)["'`]/g)].map((m) => m[1])
    expect(importados.length).toBeGreaterThan(0)
    for (const arquivo of importados) {
      expect(existsSync(path.join(path.dirname(worker), arquivo)), arquivo).toBe(true)
    }
  })
})
