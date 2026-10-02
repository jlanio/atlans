import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, statSync } from "fs"
import { join, relative } from "path"
import { formatBytes, formatDuration, successRateColor } from "@/utils/formatters"

// Formatação de valores: uma implementação por conceito.
//
// `formatBytes` tinha quatro cópias em DUAS famílias incompatíveis (uma
// parava em MB, outra escalava até TB); `formatDate` tinha quatro wrappers do
// próprio default de `formatLocal`; e a cor por taxa de sucesso tinha quatro
// cópias com TRÊS limiares — a divergência mais visível de todas.

const RAIZ = join(__dirname, "..", "..")

describe("formatBytes", () => {
  it("escala até TB — a razão de unificar na família certa", () => {
    // A versão de /artifacts e /drive parava em MB: 3 GB viravam "3072.0 MB".
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
    // Sem o clamp, um valor acima de TB indexaria fora do array e produziria
    // "1.00 undefined".
    expect(formatBytes(1024 ** 6)).toContain("TB")
  })
})

describe("successRateColor", () => {
  it("60% é vermelho em TODAS as telas agora", () => {
    // Era a divergência: três telas mostravam vermelho e /observability/[id]
    // mostrava âmbar — o mesmo número, dois julgamentos opostos.
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
    // O tom âmbar ganhou variante escura: no card escuro o 600 tinha contraste baixo.
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

// ── Guardas contra a duplicação voltar ───────────────────────────────────────

function arquivosTs(dir: string, acc: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    if (nome === "node_modules" || nome === ".next") continue
    const caminho = join(dir, nome)
    if (statSync(caminho).isDirectory()) arquivosTs(caminho, acc)
    else if (/\.tsx?$/.test(nome)) acc.push(caminho)
  }
  return acc
}

describe("sem cópias locais", () => {
  it("nenhuma página redefine formatBytes", () => {
    const violacoes = arquivosTs(join(RAIZ, "app"))
      .filter(c => /^\s*(function|const)\s+formatBytes\b/m.test(readFileSync(c, "utf8")))
      .map(c => relative(RAIZ, c))
    expect(violacoes, "use formatBytes de @/utils/formatters").toEqual([])
  })

  it("nenhuma página redefine formatDate", () => {
    // As quatro cópias eram wrappers do DEFAULT de `formatLocal` — chamavam
    // `formatLocal(iso, "DD/MM/YYYY HH:mm")`, que é literalmente o default.
    const violacoes = arquivosTs(join(RAIZ, "app"))
      .filter(c => /^\s*(function|const)\s+formatDate\s*[(:=]/m.test(readFileSync(c, "utf8")))
      .map(c => relative(RAIZ, c))
    expect(violacoes, "chame formatLocal de @/lib/dayjs direto").toEqual([])
  })

  it("nenhuma página compara success_rate com limiar literal", () => {
    const violacoes: string[] = []
    for (const caminho of arquivosTs(join(RAIZ, "app"))) {
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
