/**
 * Home's language per request: explicit choice > browser > the connection's
 * country > default. The browser comes before the country on purpose — it's
 * the signal of what the person READS (the American tourist in Brazil wants
 * English). And the country only counts for those who sent `Accept-Language`:
 * without it, it's a bot, not a person.
 */
import { describe, it, expect } from "vitest"
import { ehIdioma, idiomaDoAcceptLanguage, idiomaDoPais, resolverIdioma } from "@/lib/idioma"

describe("idiomaDoAcceptLanguage", () => {
  it("devolve o primeiro dos nossos idiomas, na ordem do navegador", () => {
    expect(idiomaDoAcceptLanguage("pt-BR,pt;q=0.9,en;q=0.8")).toBe("pt-BR")
    expect(idiomaDoAcceptLanguage("en-US,en;q=0.9")).toBe("en")
    expect(idiomaDoAcceptLanguage("es-MX,es;q=0.9,en;q=0.7")).toBe("es")
    // French isn't one of ours: the next one that is wins.
    expect(idiomaDoAcceptLanguage("fr-FR,fr;q=0.9,en;q=0.8,pt;q=0.5")).toBe("en")
  })

  it("respeita os pesos q — e q=0 é recusa", () => {
    expect(idiomaDoAcceptLanguage("en;q=0.3,es;q=0.9")).toBe("es")
    expect(idiomaDoAcceptLanguage("pt;q=0,en")).toBe("en")
    // Refused with nobody of greater weight: it stays out.
    expect(idiomaDoAcceptLanguage("fr,pt;q=0")).toBeNull()
  })

  it("português de Portugal também cai no nosso português", () => {
    expect(idiomaDoAcceptLanguage("pt-PT")).toBe("pt-BR")
  })

  it("sem nada nosso (ou sem cabeçalho) é null", () => {
    expect(idiomaDoAcceptLanguage("fr-FR,de;q=0.8")).toBeNull()
    expect(idiomaDoAcceptLanguage("*")).toBeNull()
    expect(idiomaDoAcceptLanguage("")).toBeNull()
    expect(idiomaDoAcceptLanguage(null)).toBeNull()
  })
})

describe("idiomaDoPais", () => {
  it("lusófonos, hispanófonos e o resto em inglês", () => {
    expect(idiomaDoPais("BR")).toBe("pt-BR")
    expect(idiomaDoPais("ao")).toBe("pt-BR")
    expect(idiomaDoPais("MX")).toBe("es")
    expect(idiomaDoPais("ES")).toBe("es")
    expect(idiomaDoPais("US")).toBe("en")
    expect(idiomaDoPais("DE")).toBe("en")
  })

  it("XX (desconhecido), T1 (Tor) e lixo não dizem nada", () => {
    for (const v of ["XX", "T1", "", "BRA", "1", null, undefined]) {
      expect(idiomaDoPais(v), String(v)).toBeNull()
    }
  })
})

describe("resolverIdioma", () => {
  it("a escolha explícita vence tudo", () => {
    expect(resolverIdioma({ cookie: "es", acceptLanguage: "en-US", pais: "BR" })).toEqual({
      idioma: "es",
      detectado: "en",
      escolhido: "es",
    })
  })

  it("cookie inválido é ignorado (volta ao automático)", () => {
    expect(resolverIdioma({ cookie: "fr", acceptLanguage: "en-US" }).escolhido).toBeNull()
  })

  it("o navegador vem antes do país", () => {
    expect(resolverIdioma({ acceptLanguage: "en-US,en;q=0.9", pais: "BR" }).idioma).toBe("en")
  })

  it("o país decide quando o navegador não fala nenhum dos nossos idiomas", () => {
    expect(resolverIdioma({ acceptLanguage: "fr-FR", pais: "AR" }).idioma).toBe("es")
    expect(resolverIdioma({ acceptLanguage: "de-DE", pais: "BR" }).idioma).toBe("pt-BR")
  })

  it("sinal sem idioma nosso → inglês; nenhum sinal → português", () => {
    expect(resolverIdioma({ acceptLanguage: "fr-FR" }).idioma).toBe("en")
    expect(resolverIdioma({ acceptLanguage: "ja", pais: "XX" }).idioma).toBe("en")
    expect(resolverIdioma({}).idioma).toBe("pt-BR")
  })

  it("sem Accept-Language (robô de busca, script), o país não decide", () => {
    // Googlebot comes out of the US without Accept-Language: it would index Home in English.
    expect(resolverIdioma({ pais: "US" })).toEqual({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    expect(resolverIdioma({ acceptLanguage: "  ", pais: "AR" }).idioma).toBe("pt-BR")
    // XX (unknown) and T1 (Tor) aren't a signal either.
    expect(resolverIdioma({ pais: "XX" }).idioma).toBe("pt-BR")
    expect(resolverIdioma({ pais: "T1" }).idioma).toBe("pt-BR")
  })
})

describe("ehIdioma", () => {
  it("só os três", () => {
    expect(["pt-BR", "en", "es"].every(ehIdioma)).toBe(true)
    expect(["pt", "EN", "fr", "", null, 1].some(ehIdioma)).toBe(false)
  })
})
