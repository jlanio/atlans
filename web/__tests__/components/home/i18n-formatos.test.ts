/**
 * The Home's formatters per language: Portuguese is the one from `lib/formatos` (the Home
 * in Portuguese does not change a byte), English and Spanish mirror the granularity.
 */
import { describe, it, expect } from "vitest"
import { FORMATOS } from "@/app/components/home/i18n/formatos"
import { formatInteger, formatarQuando } from "@/lib/formatos"
import { textosDe } from "@/app/components/home/i18n"

// Local noon on a Wednesday: far from midnight, "today" and "yesterday" are stable.
const AGORA = new Date(2026, 8, 23, 12, 0, 0)
const iso = (d: Date) => d.toISOString()
const menos = (min: number) => iso(new Date(AGORA.getTime() - min * 60_000))

describe("FORMATOS pt-BR", () => {
  it("é exatamente o de lib/formatos", () => {
    expect(FORMATOS["pt-BR"].inteiro).toBe(formatInteger)
    expect(FORMATOS["pt-BR"].quando).toBe(formatarQuando)
  })
})

describe("FORMATOS en/es — inteiro", () => {
  it("separador de milhar do idioma, e — para o vazio", () => {
    expect(FORMATOS.en.inteiro(1284)).toBe("1,284")
    expect(FORMATOS.es.inteiro(12840)).toBe("12.840")
    expect(FORMATOS.en.inteiro(null)).toBe("—")
    expect(FORMATOS.es.inteiro(Number.NaN)).toBe("—")
  })
})

describe("FORMATOS en/es — quando", () => {
  it("relativo dentro de 24 h", () => {
    expect(FORMATOS.en.quando(menos(0), AGORA)).toBe("now")
    expect(FORMATOS.en.quando(menos(5), AGORA)).toBe("5 min ago")
    expect(FORMATOS.en.quando(menos(180), AGORA)).toBe("3 h ago")
    expect(FORMATOS.es.quando(menos(0), AGORA)).toBe("ahora")
    expect(FORMATOS.es.quando(menos(5), AGORA)).toBe("hace 5 min")
    expect(FORMATOS.es.quando(menos(180), AGORA)).toBe("hace 3 h")
  })

  it("ontem com a hora do idioma", () => {
    const ontem = iso(new Date(2026, 8, 22, 9, 5))
    expect(FORMATOS.en.quando(ontem, AGORA)).toMatch(/^yesterday, 9:05\sAM$/)
    expect(FORMATOS.es.quando(ontem, AGORA)).toBe("ayer, 9:05")
  })

  it("mais antigo: data curta do idioma (com ano quando é outro ano)", () => {
    const setembro = iso(new Date(2026, 8, 1, 8, 4))
    expect(FORMATOS.en.quando(setembro, AGORA)).toMatch(/^Sep 1, 8:04\sAM$/)
    expect(FORMATOS.es.quando(setembro, AGORA)).toMatch(/^1 sept?, 8:04$/)
    const lastYear = iso(new Date(2025, 8, 1, 8, 4))
    expect(FORMATOS.en.quando(lastYear, AGORA)).toContain("2025")
  })

  it("vazio é —", () => {
    expect(FORMATOS.en.quando(null, AGORA)).toBe("—")
  })

  it("data ilegível é — (o Intl lançaria e derrubaria a lista inteira)", () => {
    for (const idioma of ["en", "es"] as const) {
      expect(FORMATOS[idioma].quando("not-a-date", AGORA)).toBe("—")
      expect(FORMATOS[idioma].dataEHora("not-a-date")).toBe("—")
    }
  })
})

describe("FORMATOS en/es — dataEHora", () => {
  it("inglês com o mês por extenso: 09/01 seria setembro nos EUA e janeiro no Reino Unido", () => {
    const firstOfSeptember = iso(new Date(2026, 8, 1, 12, 0))
    expect(FORMATOS.en.dataEHora(firstOfSeptember)).toMatch(/^Sep 1, 2026, 12:00\sPM$/)
    expect(FORMATOS.es.dataEHora(firstOfSeptember)).toBe("01/09/2026, 12:00")
  })
})

describe("textosDe", () => {
  it("devolve um dicionário por idioma, com as mesmas seções", () => {
    const pt = textosDe("pt-BR")
    for (const idioma of ["en", "es"] as const) {
      expect(Object.keys(textosDe(idioma))).toEqual(Object.keys(pt))
    }
    expect(textosDe("en").comum.cancelar).toBe("Cancel")
    expect(textosDe("es").comum.cancelar).toBe("Cancelar")
  })
})
