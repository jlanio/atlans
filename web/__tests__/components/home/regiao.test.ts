/**
 * De onde o globo começa: fuso do navegador > país da conexão > continente do
 * fuso > o Brasil de sempre. E a latitude contida (o hero não abre num polo).
 */
import { describe, it, expect } from "vitest"
import { CENTRO_PADRAO_DO_GLOBO, centroDaRegiao } from "@/app/components/home/mapa/regiao"
import { FUSOS, PAISES } from "@/app/components/home/mapa/fusos.gerado"

describe("centroDaRegiao", () => {
  it("o fuso aponta a cidade de referência", () => {
    expect(centroDaRegiao({ fuso: "America/Sao_Paulo" })).toEqual([-46.6, -23.5])
    expect(centroDaRegiao({ fuso: "Europe/Madrid" })).toEqual([-3.7, 40.4])
    expect(centroDaRegiao({ fuso: "America/Los_Angeles" })[0]).toBeLessThan(-115)
    expect(centroDaRegiao({ fuso: "America/New_York" })[0]).toBeGreaterThan(-80)
  })

  it("os nomes ANTIGOS que alguns navegadores devolvem também valem", () => {
    expect(centroDaRegiao({ fuso: "Asia/Calcutta" })).toEqual(centroDaRegiao({ fuso: "Asia/Kolkata" }))
    expect(centroDaRegiao({ fuso: "America/Buenos_Aires" })[1]).toBeLessThan(-30)
  })

  it("o fuso vence o país (é o sinal mais fino)", () => {
    expect(centroDaRegiao({ fuso: "America/Manaus", pais: "US" })).toEqual(FUSOS["America/Manaus"])
  })

  it("sem fuso útil, o país da conexão", () => {
    expect(centroDaRegiao({ fuso: "UTC", pais: "jp" })).toEqual(PAISES.JP)
    expect(centroDaRegiao({ fuso: null, pais: "AR" })).toEqual(
      [PAISES.AR[0], Math.max(-45, PAISES.AR[1])],
    )
  })

  it("o fuso da Islândia dos modos de privacidade não é sinal: vale o país", () => {
    // Firefox com resistFingerprinting, Tor Browser e Mullvad Browser dizem
    // "Atlantic/Reykjavik" (e não "UTC") para esconder o fuso.
    expect(centroDaRegiao({ fuso: "Atlantic/Reykjavik", pais: "BR" })).toEqual(PAISES.BR)
    expect(centroDaRegiao({ fuso: "Iceland", pais: "JP" })).toEqual(PAISES.JP)
    // Sem país, o centro neutro — não o Atlântico Norte da Islândia.
    expect(centroDaRegiao({ fuso: "Atlantic/Reykjavik" })).toEqual(CENTRO_PADRAO_DO_GLOBO)
    // Quem está MESMO na Islândia continua lá (com a latitude contida).
    expect(centroDaRegiao({ fuso: "Atlantic/Reykjavik", pais: "is" })).toEqual([FUSOS["Atlantic/Reykjavik"][0], 50])
  })

  it("fuso desconhecido cai no continente do nome", () => {
    const [lon, lat] = centroDaRegiao({ fuso: "Europe/Inexistente" })
    expect(lon).toBe(15)
    expect(lat).toBe(50)
  })

  it("sem sinal nenhum (ou só lixo), o centro neutro, sem país de preferência", () => {
    expect(CENTRO_PADRAO_DO_GLOBO).toEqual([0, 20])
    expect(centroDaRegiao({})).toEqual(CENTRO_PADRAO_DO_GLOBO)
    expect(centroDaRegiao({ fuso: "UTC", pais: "XX" })).toEqual(CENTRO_PADRAO_DO_GLOBO)
    expect(centroDaRegiao({ fuso: "Etc/GMT+3" })).toEqual(CENTRO_PADRAO_DO_GLOBO)
  })

  it("a latitude fica numa faixa em que o hero não abre num polo", () => {
    expect(centroDaRegiao({ fuso: "Europe/Oslo" })[1]).toBe(50)
    expect(centroDaRegiao({ fuso: "Antarctica/McMurdo" })[1]).toBe(-45)
  })

  it("a tabela gerada cobre os fusos grandes e os países", () => {
    expect(Object.keys(FUSOS).length).toBeGreaterThan(500)
    expect(Object.keys(PAISES).length).toBeGreaterThan(240)
    for (const [lon, lat] of Object.values(FUSOS)) {
      expect(Math.abs(lon)).toBeLessThanOrEqual(180)
      expect(Math.abs(lat)).toBeLessThanOrEqual(90)
    }
  })
})
