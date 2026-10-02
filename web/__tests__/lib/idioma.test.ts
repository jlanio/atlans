/**
 * O idioma da Home por requisição: escolha explícita > navegador > país da
 * conexão > padrão. O navegador vem antes do país de propósito — é o sinal do
 * que a pessoa LÊ (o turista americano no Brasil quer inglês). E o país só
 * conta para quem mandou `Accept-Language`: sem ele é robô, não pessoa.
 */
import { describe, it, expect } from "vitest"
import { ehIdioma, idiomaDoAcceptLanguage, idiomaDoPais, resolverIdioma } from "@/lib/idioma"

describe("idiomaDoAcceptLanguage", () => {
  it("devolve o primeiro dos nossos idiomas, na ordem do navegador", () => {
    expect(idiomaDoAcceptLanguage("pt-BR,pt;q=0.9,en;q=0.8")).toBe("pt-BR")
    expect(idiomaDoAcceptLanguage("en-US,en;q=0.9")).toBe("en")
    expect(idiomaDoAcceptLanguage("es-MX,es;q=0.9,en;q=0.7")).toBe("es")
    // Francês não é nosso: vale o próximo que é.
    expect(idiomaDoAcceptLanguage("fr-FR,fr;q=0.9,en;q=0.8,pt;q=0.5")).toBe("en")
  })

  it("respeita os pesos q — e q=0 é recusa", () => {
    expect(idiomaDoAcceptLanguage("en;q=0.3,es;q=0.9")).toBe("es")
    expect(idiomaDoAcceptLanguage("pt;q=0,en")).toBe("en")
    // Recusado sem ninguém com peso maior: continua fora.
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
    // O Googlebot sai dos EUA sem Accept-Language: indexaria a Home em inglês.
    expect(resolverIdioma({ pais: "US" })).toEqual({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    expect(resolverIdioma({ acceptLanguage: "  ", pais: "AR" }).idioma).toBe("pt-BR")
    // XX (desconhecido) e T1 (Tor) também não são sinal.
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
