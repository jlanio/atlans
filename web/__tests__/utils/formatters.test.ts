import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, statSync } from "fs"
import { join, relative } from "path"
import { formatBytes, formatDuration, successRateColor } from "@/utils/formatters"

// Value formatting: one implementation per concept.
//
// `formatBytes` had four copies in TWO incompatible families (one stopped at
// MB, the other scaled up to TB); `formatDate` had four wrappers of
// `formatLocal`'s own default; and the success-rate color had four copies with
// THREE thresholds — the most visible divergence of all.

const RAIZ = join(__dirname, "..", "..")

describe("formatBytes", () => {
  it("escala até TB — a razão de unificar na família certa", () => {
    // The /artifacts and /drive version stopped at MB: 3 GB became "3072.0 MB".
    expect(formatBytes(3 * 1024 ** 3)).toBe("3.00 GB")
    expect(formatBytes(2 * 1024 ** 4)).toBe("2.00 TB")
  })

  it("usa precisão adaptativa", () => {
    expect(formatBytes(1536)).toBe("1.50 KB")       // < 10 → 2 casas
    expect(formatBytes(50 * 1024)).toBe("50.0 KB")  // < 100 → 1 casa
    expect(formatBytes(500 * 1024)).toBe("500 KB")  // >= 100 → inteiro
  })

  it("trata os casos de borda que as cópias divergiam", () => {
    expect(formatBytes(0)).toBe("0 B")
    expect(formatBytes(null)).toBe("—")
    expect(formatBytes(undefined)).toBe("—")
    expect(formatBytes(512)).toBe("512 B")
  })

  it("não estoura o array de unidades em valores absurdos", () => {
    // Without the clamp, a value above TB would index outside the array and produce
    // "1.00 undefined".
    expect(formatBytes(1024 ** 6)).toContain("TB")
  })
})

describe("successRateColor", () => {
  it("60% é vermelho em TODAS as telas agora", () => {
    // That was the divergence: three screens showed red and /observability/[id]
    // showed amber — the same number, two opposite judgments.
    expect(successRateColor(0.6)).toBe("text-red-500")
    expect(successRateColor(0.6, "amber")).toBe("text-red-500 dark:text-red-400")
  })

  it("respeita os limiares da maioria (0.9 / 0.7)", () => {
    expect(successRateColor(0.95)).toBe("text-green-500")
    expect(successRateColor(0.9)).toBe("text-green-500")
    expect(successRateColor(0.75)).toBe("text-yellow-500")
    expect(successRateColor(0.7)).toBe("text-yellow-500")
    expect(successRateColor(0.69)).toBe("text-red-500")
  })

  it("preserva a paleta que cada tela já usava", () => {
    // The amber tone got a dark variant: on the dark card the 600 had low contrast.
    expect(successRateColor(0.95, "amber")).toBe("text-green-600 dark:text-green-400")
    expect(successRateColor(0.75, "amber")).toBe("text-amber-600 dark:text-amber-400")
  })

  it("é null-safe — o card de detalhe renderiza antes das métricas chegarem", () => {
    expect(successRateColor(null)).toBe("text-muted-foreground")
    expect(successRateColor(undefined)).toBe("text-muted-foreground")
  })
})

describe("formatDuration", () => {
  it("continua com o contrato de antes", () => {
    expect(formatDuration(123)).toBe("123ms")
    expect(formatDuration(1234)).toBe("1.23s")
    expect(formatDuration(null)).toBeNull()
  })
})

// ── Guards against the duplication coming back ───────────────────────────────

function tsFiles(dir: string, acc: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    if (nome === "node_modules" || nome === ".next") continue
    const caminho = join(dir, nome)
    if (statSync(caminho).isDirectory()) tsFiles(caminho, acc)
    else if (/\.tsx?$/.test(nome)) acc.push(caminho)
  }
  return acc
}

describe("sem cópias locais", () => {
  it("nenhuma página redefine formatBytes", () => {
    const violacoes = tsFiles(join(RAIZ, "app"))
      .filter(c => /^\s*(function|const)\s+formatBytes\b/m.test(readFileSync(c, "utf8")))
      .map(c => relative(RAIZ, c))
    expect(violacoes, "use formatBytes de @/utils/formatters").toEqual([])
  })

  it("nenhuma página redefine formatDate", () => {
    // The four copies were wrappers of `formatLocal`'s DEFAULT — they called
    // `formatLocal(iso, "DD/MM/YYYY HH:mm")`, which is literally the default.
    const violacoes = tsFiles(join(RAIZ, "app"))
      .filter(c => /^\s*(function|const)\s+formatDate\s*[(:=]/m.test(readFileSync(c, "utf8")))
      .map(c => relative(RAIZ, c))
    expect(violacoes, "chame formatLocal de @/lib/dayjs direto").toEqual([])
  })

  it("nenhuma página compara success_rate com limiar literal", () => {
    const violacoes: string[] = []
    for (const caminho of tsFiles(join(RAIZ, "app"))) {
      const fonte = readFileSync(caminho, "utf8")
      fonte.split("\n").forEach((linha, i) => {
        if (/success_rate\s*[<>]=?\s*0\./.test(linha)) {
          violacoes.push(`${relative(RAIZ, caminho)}:${i + 1}`)
        }
      })
    }
    expect(violacoes, "use successRateColor — limiar copiado já divergiu uma vez").toEqual([])
  })
})
