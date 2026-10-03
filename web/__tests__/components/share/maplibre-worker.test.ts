import { execFileSync } from "node:child_process"
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { describe, it, expect, vi } from "vitest"

/**
 * maplibre-gl 6 runs the worker from a URL, which with a bundler it does not
 * find on its own. Without it the worker dies silently and the vector tiles never
 * load, but the rest of the map opens normally, so only this test would catch it.
 * MapLibreMap points `setWorkerUrl` at the copy that
 * scripts/copiar-maplibre.mjs makes in `public/maplibre` at build and in dev.
 * This test checks the whole chain: the URL, the copied file and what it
 * imports.
 */
const { setWorkerUrl } = vi.hoisted(() => ({ setWorkerUrl: vi.fn() }))
vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}))
vi.mock("maplibre-gl", () => ({ setWorkerUrl }))

import "@/app/components/share/MapLibreMap"

// The call happens on import, before the test runs. Vitest 5 clears mocks
// before each test (`clearMocks` defaults to true), so copy the calls now.
const workerUrlCalls = [...setWorkerUrl.mock.calls]

const WEB = path.resolve(__dirname, "..", "..", "..")

describe("worker do maplibre-gl", () => {
  it("a URL configurada aponta para o worker copiado, com tudo o que ele importa ao lado", () => {
    expect(workerUrlCalls).toHaveLength(1)
    const url: string = workerUrlCalls[0][0]
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
