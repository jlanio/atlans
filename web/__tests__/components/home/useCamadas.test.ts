import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"

const camadaDoGlobo = vi.fn()
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { camadaDoGlobo: (...a: unknown[]) => camadaDoGlobo(...a) },
}))

import { useCamadas } from "@/app/hooks/home/useCamadas"

beforeEach(() => {
  camadaDoGlobo.mockReset()
  vi.stubGlobal("fetch", vi.fn())
})

const fc = (features: unknown[] = []) => ({ type: "FeatureCollection", features })

/** Uma resposta com corpo em pedaços, como a do navegador de verdade. */
function respostaEmPedacos(texto: string, pedaco = 64) {
  const bytes = new TextEncoder().encode(texto)
  let i = 0
  return {
    ok: true,
    headers: { get: () => null },
    body: {
      getReader: () => ({
        read: async () => {
          if (i >= bytes.length) return { done: true, value: undefined }
          const parte = bytes.slice(i, i + pedaco)
          i += pedaco
          return { done: false, value: parte }
        },
        cancel: async () => {},
      }),
    },
  }
}

describe("useCamadas.adicionar", () => {
  it("geojson: busca a FeatureCollection e vira MapLayer (bbox 4326 enquadra)", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: {
        artifact_id: "a1", nome: "Focos", tipo: "geojson", available: true,
        download_url: "https://s3/x.geojson", geometry_type: "Point",
        crs: "EPSG:4326", bbox: [-63, -10, -62, -9], size_bytes: 100,
      },
    })
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true, json: async () => fc([{ type: "Feature", geometry: { type: "Point", coordinates: [-62.5, -9.5] }, properties: {} }]),
    })

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("a1") })

    expect(result.current.camadas).toHaveLength(1)
    expect(result.current.camadas[0]).toMatchObject({
      id: "art:a1", label: "Focos", geomType: "Point", visible: true, bbox: [-63, -10, -62, -9],
    })
  })

  it("teto de 25 MB → aviso com o nome, sem camada", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: { artifact_id: "a2", nome: "Pesada", tipo: "geojson", available: true, download_url: "u", size_bytes: 30 * 1024 * 1024 },
    })
    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("a2") })

    expect(result.current.camadas).toHaveLength(0)
    expect(result.current.avisos["a2"].motivo).toMatch(/grande/)
    expect(result.current.avisos["a2"].nome).toBe("Pesada")
  })

  it("indisponível → aviso com o hint do servidor, e o X dispensa", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: { artifact_id: "a3", tipo: "indisponivel", available: false, hint: "fica no executor" },
    })
    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("a3") })
    expect(result.current.avisos["a3"].motivo).toBe("fica no executor")

    act(() => { result.current.dispensarAviso("a3") })
    expect(result.current.avisos["a3"]).toBeUndefined()
  })

  it("bbox fora de lon/lat não enquadra (bbox fica undefined)", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: { artifact_id: "a4", tipo: "geojson", available: true, download_url: "u", crs: "EPSG:31982", bbox: [500000, 9000000, 510000, 9100000] },
    })
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, json: async () => fc() })

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("a4") })

    expect(result.current.camadas[0].bbox).toBeUndefined()
  })

  it("bbox 4326 com crs nativo AINDA enquadra (o servidor já zera a que não vale)", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: {
        artifact_id: "a6", nome: "Publicada", tipo: "mvt", available: true,
        crs: "EPSG:31982", bbox: [-52, -12, -51, -11],
        mvt: { workflow_id: "w1", layer_key: "lk" },
      },
    })
    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("a6") })

    expect(result.current.camadas[0].bbox).toEqual([-52, -12, -51, -11])
  })

  it("mvt: vira camada vetorial com o par workflow/layer", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: { artifact_id: "a5", nome: "Pub", tipo: "mvt", available: true, mvt: { workflow_id: "w1", layer_key: "lk" }, geometry_type: "Polygon" },
    })
    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("a5") })

    expect(result.current.camadas[0]).toMatchObject({ id: "art:a5", mvt: { workflowHash: "w1", layerKey: "lk" } })
    expect(fetch).not.toHaveBeenCalled() // MVT não faz fetch de GeoJSON
  })

  it("size_bytes nulo NÃO é 'pequeno': o corte vale pelo que chega no fio", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: { artifact_id: "b1", nome: "Sem tamanho", tipo: "geojson", available: true, download_url: "u", size_bytes: null },
    })
    // 26 MB de corpo, acima do teto por camada.
    const gigante = JSON.stringify({ type: "FeatureCollection", features: [], lixo: "x".repeat(26 * 1024 * 1024) })
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(respostaEmPedacos(gigante, 1024 * 1024))

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("b1") })

    expect(result.current.camadas).toHaveLength(0)
    expect(result.current.avisos["b1"].motivo).toMatch(/grande|limite/)
  })

  it("dois cliques no mesmo artefato baixam UMA vez só", async () => {
    camadaDoGlobo.mockImplementation(async () => ({
      success: true,
      data: { artifact_id: "c1", nome: "Um", tipo: "geojson", available: true, download_url: "u" },
    }))
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, json: async () => fc() })

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => {
      await Promise.all([result.current.adicionar("c1"), result.current.adicionar("c1")])
    })

    expect(fetch).toHaveBeenCalledTimes(1)
    expect(result.current.camadas).toHaveLength(1)
  })

  it("re-exibir o mesmo artefato mantém a cor e a posição na lista", async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, json: async () => fc() })
    const dado = (id: string) => ({
      success: true,
      data: { artifact_id: id, nome: id, tipo: "geojson", available: true, download_url: "u" },
    })
    camadaDoGlobo.mockImplementation(async (id: string) => dado(id))

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("d1") })
    await act(async () => { await result.current.adicionar("d2") })
    const cor1 = result.current.camadas[0].color
    await act(async () => { await result.current.adicionar("d1") })

    expect(result.current.camadas.map((c) => c.id)).toEqual(["art:d1", "art:d2"])
    expect(result.current.camadas[0].color).toBe(cor1)
  })

  it("uma tentativa que falha não queima cor da paleta", async () => {
    camadaDoGlobo.mockImplementation(async (id: string) =>
      id === "ruim"
        ? { success: false, error: { message: "não deu" } }
        : { success: true, data: { artifact_id: id, nome: id, tipo: "geojson", available: true, download_url: "u" } },
    )
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, json: async () => fc() })

    const { result: sozinho } = renderHook(() => useCamadas([]))
    await act(async () => { await sozinho.current.adicionar("boa") })
    const primeiraCor = sozinho.current.camadas[0].color

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => { await result.current.adicionar("ruim") })
    await act(async () => { await result.current.adicionar("boa") })

    expect(result.current.camadas[0].color).toBe(primeiraCor)
  })

  it("trocar de escopo (outra conversa) limpa camadas, e a camada volta ao reabrir o chat", async () => {
    camadaDoGlobo.mockImplementation(async (id: string) => ({
      success: true,
      data: { artifact_id: id, nome: id, tipo: "geojson", available: true, download_url: "u" },
    }))
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, json: async () => fc() })

    const { result, rerender } = renderHook(
      ({ conversa }: { conversa: string }) => useCamadas([], conversa),
      { initialProps: { conversa: "A" } },
    )
    await act(async () => { await result.current.adicionar("x1") })
    expect(result.current.camadas).toHaveLength(1)

    rerender({ conversa: "B" })
    expect(result.current.camadas).toHaveLength(0)

    // De volta em A: o mesmo artefato pode entrar de novo (o "já busquei" zerou).
    rerender({ conversa: "A" })
    await act(async () => { await result.current.adicionar("x1") })
    expect(result.current.camadas).toHaveLength(1)
  })

  it("o teto AGREGADO conta o que está em voo: adições simultâneas não estouram juntas", async () => {
    // 3 × 24 MB = 72 MB, acima dos 60 MB do teto agregado. O mapa de bytes só é
    // escrito DEPOIS do download: sem reserva, as três liam o orçamento inteiro
    // e passavam todas — o globo ficava com 72 MB de GeoJSON em memória.
    camadaDoGlobo.mockImplementation(async (id: string) => ({
      success: true,
      data: {
        artifact_id: id, nome: id, tipo: "geojson", available: true,
        download_url: "u", size_bytes: 24 * 1024 * 1024,
      },
    }))
    // Os downloads só terminam quando o segundo começa: assim as três adições
    // se atropelam de verdade, que é a situação em que o teto era furado.
    let liberar!: () => void
    const espera = new Promise<void>((r) => { liberar = r })
    let chamadas = 0
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async () => {
      if (++chamadas >= 2) liberar()
      await espera
      return { ok: true, headers: { get: () => null }, json: async () => fc() }
    })

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => {
      await Promise.all([
        result.current.adicionar("g1"),
        result.current.adicionar("g2"),
        result.current.adicionar("g3"),
      ])
    })

    expect(result.current.camadas).toHaveLength(2)
    const recusadas = Object.values(result.current.avisos)
    expect(recusadas).toHaveLength(1)
    expect(recusadas[0].motivo).toMatch(/limite/)
  })

  it("a busca do escopo ANTIGO não apaga a marca 'em voo' da nova", async () => {
    camadaDoGlobo.mockImplementation(async (id: string) => ({
      success: true,
      data: { artifact_id: id, nome: id, tipo: "geojson", available: true, download_url: "u" },
    }))
    const portas: Array<() => void> = []
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise((resolve) => {
        portas.push(() => resolve({ ok: true, headers: { get: () => null }, json: async () => fc() }))
      }),
    )
    const respirar = () => new Promise((r) => setTimeout(r, 0))

    const { result, rerender } = renderHook(
      ({ conversa }: { conversa: string }) => useCamadas([], conversa),
      { initialProps: { conversa: "A" } },
    )
    let antiga!: Promise<void>
    await act(async () => { antiga = result.current.adicionar("x1"); await respirar() })

    rerender({ conversa: "B" })
    let nova!: Promise<void>
    await act(async () => { nova = result.current.adicionar("x1"); await respirar() })
    expect(fetch).toHaveBeenCalledTimes(2)

    // A antiga só termina agora, já fora do escopo dela: se ela apagar a marca
    // da nova, o mesmo artefato é baixado uma terceira vez.
    await act(async () => { portas[0](); await antiga; await respirar() })
    await act(async () => { await result.current.adicionar("x1") })
    expect(fetch).toHaveBeenCalledTimes(2)

    await act(async () => { portas[1](); await nova })
    expect(result.current.camadas).toHaveLength(1)
  })

  it("o mesmo escopo re-renderizando NÃO mexe nas camadas", async () => {
    camadaDoGlobo.mockImplementation(async (id: string) => ({
      success: true,
      data: { artifact_id: id, nome: id, tipo: "geojson", available: true, download_url: "u" },
    }))
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, json: async () => fc() })

    const { result, rerender } = renderHook(
      ({ conversa }: { conversa: string }) => useCamadas([], conversa),
      { initialProps: { conversa: "nova:1" } },
    )
    await act(async () => { await result.current.adicionar("y1") })
    rerender({ conversa: "nova:1" })

    expect(result.current.camadas).toHaveLength(1)
  })

  it("teto AGREGADO com tamanho DESCONHECIDO: reservar o teto barra a 3a; reservar 0 (o bug) deixava passar", async () => {
    // 3 buscas de tamanho nulo, simultâneas. A reserva `?? teto` faz cada uma
    // guardar o máximo que pode chegar, então a 3a só herda ~10 MB de orçamento
    // e é cortada no fio; com `?? 0` as três reservavam nada, liam 25 MB cada e
    // entravam — o globo ficava com o triplo do teto agregado em memória.
    camadaDoGlobo.mockImplementation(async (id: string) => ({
      success: true,
      data: { artifact_id: id, nome: id, tipo: "geojson", available: true, download_url: "u", size_bytes: null },
    }))
    // ~12 MB por corpo: cabe no teto por camada (25 MB) das duas primeiras, mas
    // não nos ~10 MB que sobram para a 3a depois das duas reservas.
    const corpo = JSON.stringify({ type: "FeatureCollection", features: [], lixo: "x".repeat(12 * 1024 * 1024) })
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async () => respostaEmPedacos(corpo, 1024 * 1024))

    const { result } = renderHook(() => useCamadas([]))
    await act(async () => {
      await Promise.all([
        result.current.adicionar("k1"),
        result.current.adicionar("k2"),
        result.current.adicionar("k3"),
      ])
    })

    expect(result.current.camadas).toHaveLength(2)
    const recusadas = Object.values(result.current.avisos)
    expect(recusadas).toHaveLength(1)
    expect(recusadas[0].motivo).toMatch(/limite/)
  })

  it("desmontar aborta o download em voo", async () => {
    camadaDoGlobo.mockResolvedValue({
      success: true,
      data: { artifact_id: "u1", nome: "U", tipo: "geojson", available: true, download_url: "u" },
    })
    let sinal: AbortSignal | undefined
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(async (_url: string, init?: RequestInit) => {
      sinal = init?.signal ?? undefined
      // Um corpo que nunca termina de ler — é o abort que o encerra.
      return { ok: true, headers: { get: () => null }, body: { getReader: () => ({ read: () => new Promise(() => {}), cancel: async () => {} }) } }
    })

    const { result, unmount } = renderHook(() => useCamadas([]))
    act(() => { void result.current.adicionar("u1") })
    await waitFor(() => expect(sinal).toBeDefined())
    expect(sinal!.aborted).toBe(false)

    unmount()
    expect(sinal!.aborted).toBe(true)
  })
})
