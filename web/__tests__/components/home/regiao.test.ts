/**
 * Where the globe starts: browser time zone > connection country > the time zone's
 * continent > the usual Brazil. And the latitude kept in check (the hero does not open on a pole).
 */
import { describe, it, expect } from "vitest"
import { DEFAULT_GLOBE_CENTER, centroDaRegiao } from "@/app/components/home/mapa/regiao"
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
    // Firefox with resistFingerprinting, Tor Browser and Mullvad Browser report
    // "Atlantic/Reykjavik" (and not "UTC") to hide the time zone.
    expect(centroDaRegiao({ fuso: "Atlantic/Reykjavik", pais: "BR" })).toEqual(PAISES.BR)
    expect(centroDaRegiao({ fuso: "Iceland", pais: "JP" })).toEqual(PAISES.JP)
    // No country, the neutral center — not Iceland's North Atlantic.
    expect(centroDaRegiao({ fuso: "Atlantic/Reykjavik" })).toEqual(DEFAULT_GLOBE_CENTER)
    // Someone REALLY in Iceland stays there (with the latitude kept in check).
    expect(centroDaRegiao({ fuso: "Atlantic/Reykjavik", pais: "is" })).toEqual([FUSOS["Atlantic/Reykjavik"][0], 50])
  })

  it("fuso desconhecido cai no continente do nome", () => {
    const [lon, lat] = centroDaRegiao({ fuso: "Europe/Inexistente" })
    expect(lon).toBe(15)
    expect(lat).toBe(50)
  })

  it("sem sinal nenhum (ou só lixo), o centro neutro, sem país de preferência", () => {
    expect(DEFAULT_GLOBE_CENTER).toEqual([0, 20])
    expect(centroDaRegiao({})).toEqual(DEFAULT_GLOBE_CENTER)
    expect(centroDaRegiao({ fuso: "UTC", pais: "XX" })).toEqual(DEFAULT_GLOBE_CENTER)
    expect(centroDaRegiao({ fuso: "Etc/GMT+3" })).toEqual(DEFAULT_GLOBE_CENTER)
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
