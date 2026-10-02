import { describe, it, expect } from "vitest"
import { transformarRequisicao, ehTileDoAgente } from "@/app/components/home/mapa/requisicao"

/**
 * O transformRequest do globo faz UMA coisa: manda o cookie de sessão nos tiles
 * do assistente (proxy same-origin). Todo o resto passa cru (undefined) — o
 * basemap da instalação inclusive, que não exige chave. (A CARTO, que exigia
 * `?key=` no CDN dela, saiu da Home; com ela saiu o ramo que anexava a chave.)
 */
describe("transformarRequisicao", () => {
  it("manda credentials same-origin nos tiles do assistente", () => {
    expect(transformarRequisicao("/terra/assistente/tiles/wf/layer/1/2/3.pbf"))
      .toEqual({ url: "/terra/assistente/tiles/wf/layer/1/2/3.pbf", credentials: "same-origin" })
  })

  it("deixa o basemap e qualquer outro host crus", () => {
    expect(transformarRequisicao("https://hibrido.example.org/3/1/2.jpg")).toBeUndefined()
    expect(transformarRequisicao("https://s3.atlans.example.org/artefato.geojson")).toBeUndefined()
  })

  it("não confunde os tiles do portal com os do assistente", () => {
    expect(transformarRequisicao("/terra/artifacts/tiles/a/b/1/2/3.pbf")).toBeUndefined()
  })

  it("nunca põe Authorization: o navegador não tem o token do servidor", () => {
    const r = transformarRequisicao("/terra/assistente/tiles/a/b/1/2/3.pbf")!
    expect("headers" in r).toBe(false)
    expect(Object.keys(r).sort()).toEqual(["credentials", "url"])
  })
})

describe("ehTileDoAgente", () => {
  it("casa o prefixo do proxy, inclusive URL relativa e absoluta", () => {
    expect(ehTileDoAgente("/terra/assistente/tiles/a/b/1/2/3.pbf")).toBe(true)
    expect(ehTileDoAgente("http://localhost/terra/assistente/tiles/a/b/1/2/3.pbf")).toBe(true)
    expect(ehTileDoAgente("/terra/artifacts/tiles/a/b/1/2/3.pbf")).toBe(false)
  })
})
