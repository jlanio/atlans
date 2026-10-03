"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { MapLayer, MapLibreMapHandle } from "@/app/components/share/MapLibreMap"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import { corDaCamada, derivarCamadas, pareceLonLat } from "@/app/components/home/camadas"
import { useTextos, type Textos } from "@/app/components/home/i18n"

// Above this, the preview is refused: a 100 MB FeatureCollection in memory
// freezes the tab, and the globe is not a heavy-data viewer.
const TETO_BYTES = 25 * 1024 * 1024
// And an AGGREGATE ceiling: five 24 MB layers pass the ceiling above one by one
// and add up to ~120 MB of heap (expanded GeoJSON + the copy in MapLibre's worker).
const TETO_TOTAL_BYTES = 60 * 1024 * 1024
const VAZIO: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] }

/** Why an artifact did not become a layer — with the name, so the person knows which. */
export interface AvisoDeCamada {
  nome?: string
  motivo: string
}

export interface UseCamadas {
  camadas: MapLayer[]
  /** artifact_id → "no preview" notice (unavailable, too large, error). */
  avisos: Record<string, AvisoDeCamada>
  /** artifact_id → label of the layers being fetched right now. */
  carregando: Record<string, string>
  refMapa: React.RefObject<MapLibreMapHandle | null>
  adicionar: (artifactId: string, nome?: string) => Promise<void>
  remover: (id: string) => void
  alternarVisivel: (id: string) => void
  enquadrar: (id: string) => void
  /** Removes a notice from the screen (the row's X). */
  dispensarAviso: (artifactId: string) => void
}

/**
 * The globe's layers, derived from the conversation. Each `camada` pointer (from
 * a `run_workflow` or from `exibir_no_globo`) is fetched once from
 * `GET /assistente/camadas/{id}` and becomes a `MapLayer`:
 * - geojson: `fetch` of the presigned URL → FeatureCollection IN MEMORY (the URL
 *   expires in ~900s; never `addSource({data: url})`). Ceiling per layer and in total.
 * - mvt (published): vector layer via `/terra/assistente/tiles/…`.
 * - unavailable: a "no preview" notice with the reason.
 * The `bbox` only frames when it fits in lon/lat.
 *
 * The lifecycle is THAT OF the `escopo` (the active conversation): switching
 * chats clears layers, notices and the "already fetched this artifact" memory.
 * Without that the globe piled up the layers of A, B and C, the panel did not
 * say which conversation each one came from, and a removed layer never came
 * back when reopening the chat that produced it. HomeView decides the scope —
 * only it can tell "the person opened another chat" from "the new conversation
 * just got an id".
 */
export function useCamadas(turnos: TurnoDoAssistente[], escopo?: string): UseCamadas {
  const [camadas, setCamadas] = useState<MapLayer[]>([])
  const [avisos, setAvisos] = useState<Record<string, AvisoDeCamada>>({})
  const [carregando, setCarregando] = useState<Record<string, string>>({})
  const refMapa = useRef<MapLibreMapHandle | null>(null)
  const buscados = useRef<Set<string>>(new Set())
  const emVoo = useRef<Set<string>>(new Set())
  const indice = useRef(0)
  // The color is PER artifact: re-displaying the same artifact has to keep the
  // color the person already associated with the layer, and a failed attempt
  // must not burn a palette color.
  const cores = useRef<Map<string, string>>(new Map())
  // Bytes already downloaded per layer, for the aggregate ceiling; removed along with the layer.
  const bytes = useRef<Map<string, number>>(new Map())
  // Bytes PROMISED by in-flight fetches. `bytes` is only written after the
  // download finishes: without this reservation, N simultaneous additions all
  // read the same (still empty) map and all got past the aggregate ceiling. It
  // goes in before the network trip and comes out at the end — the layer that
  // made it in has already accounted the real number in `bytes`, and the one
  // that did not owes nothing.
  const reservas = useRef<Map<string, number>>(new Map())
  // AbortController per in-flight download: switching conversations or unmounting
  // ABORTS the network. Without it `baixarComTeto` kept reading a body of
  // hundreds of MB from a chat the person had already closed, and the fetch
  // promise only settled when the whole download arrived. Mirrors useAssistente's `abortoRef`.
  const controladores = useRef<Map<string, AbortController>>(new Map())
  const paraEnquadrar = useRef<string | null>(null)
  // Goes up on every cleanup: a fetch already in flight when the conversation
  // switched must not plant the previous conversation's layer on the new one's globe.
  const geracao = useRef(0)
  const assinatura = useRef("")
  // The notice texts go through a ref: `adicionar` is a dependency of the effect
  // that fetches the layers, and switching language must not change its identity.
  const textosDaTela = useTextos().assistente.camada
  const textos = useRef(textosDaTela)
  useEffect(() => { textos.current = textosDaTela }, [textosDaTela])

  const corDe = useCallback((artifactId: string) => {
    const guardada = cores.current.get(artifactId)
    if (guardada) return guardada
    const nova = corDaCamada(indice.current++)
    cores.current.set(artifactId, nova)
    return nova
  }, [])

  const adicionar = useCallback(async (artifactId: string, nomeSugerido?: string) => {
    // Two clicks on the same artifact downloaded the presigned URL twice (the
    // service's `get()` only deduplicates the metadata call, not the raw fetch).
    if (emVoo.current.has(artifactId)) return
    const id = `art:${artifactId}`
    const minhaGeracao = geracao.current
    const rotuloProvisorio = (nomeSugerido || artifactId).trim()
    emVoo.current.add(artifactId)
    setCarregando((c) => ({ ...c, [artifactId]: rotuloProvisorio }))
    /** Only writes state if the conversation is still the one from when it started. */
    const atual = () => geracao.current === minhaGeracao

    try {
      const res = await GisFlowService.camadaDoGlobo(artifactId)
      const c = res.data
      if (!atual()) return
      if (!res.success || !c) {
        avisar(setAvisos, artifactId, rotuloProvisorio, res.error?.message ?? textos.current.naoCarregou)
        return
      }
      const nome = (nomeSugerido || c.nome || artifactId).trim()
      // The bbox is NOT reinterpreted by `crs`: the server already clears the one
      // that does not deserve trust, and in the MVT branch it is 4326 by
      // construction. Comparing the `crs` string with "EPSG:4326" discarded good
      // bboxes of data published in a native CRS — the camera never left the initial framing.
      const bbox = pareceLonLat(c.bbox) ? (c.bbox as number[]) : undefined

      if (c.tipo === "geojson" && c.download_url) {
        // What is left of the aggregate ceiling counts what is already ON THE GLOBE
        // and what has already been promised by another in-flight fetch —
        // otherwise two simultaneous additions both see the whole budget and
        // overflow together.
        const restante = TETO_TOTAL_BYTES - somar(bytes.current, id) - somar(reservas.current, id)
        const teto = Math.min(TETO_BYTES, restante)
        if (c.size_bytes != null && c.size_bytes > teto) {
          avisar(setAvisos, artifactId, nome, motivoDoTeto(restante, textos.current))
          return
        }
        // Reserve BEFORE the fetch. An unknown size reserves the ENTIRE `teto`
        // (the most the on-the-wire cutoff lets in): reserving 0 made N fetches
        // of unknown size not see each other in the aggregate ceiling and
        // overflow together. The real value corrects `bytes` when the download ends.
        reservas.current.set(id, c.size_bytes ?? teto)
        const controle = new AbortController()
        controladores.current.set(artifactId, controle)
        try {
          // NO Authorization: the URL is presigned and expires in ~900s. The
          // FeatureCollection stays in memory; never addSource({data: url}).
          // `signal`: switching conversation/unmounting aborts the in-flight download.
          const r = await fetch(c.download_url, { signal: controle.signal })
          if (!r.ok) throw new Error(String(r.status))
          // A null `size_bytes` is NOT "small": the consumer writes NULL when the
          // storage head fails. The cutoff is by what arrives on the wire.
          const baixado = await baixarComTeto(r, teto, controle.signal)
          if (!atual()) return
          if (!baixado) {
            avisar(setAvisos, artifactId, nome, motivoDoTeto(restante, textos.current))
            return
          }
          const layer: MapLayer = {
            id, label: nome, color: corDe(artifactId), opacity: 0.6,
            geojson: baixado.geojson, visible: true,
            geomType: c.geometry_type ?? "", bbox, baixavel: c.baixavel ?? false,
          }
          bytes.current.set(id, baixado.bytes)
          paraEnquadrar.current = id
          setCamadas((cs) => comA(cs, layer))
          setAvisos((a) => semAviso(a, artifactId))
        } catch {
          // Aborted (conversation switch/unmount): `atual()` is false and there is no
          // notice — the network stopped on purpose, it is not a preview failure.
          if (atual()) avisar(setAvisos, artifactId, nome, textos.current.naoCarregouPrevia)
        } finally {
          controladores.current.delete(artifactId)
          // The reservation is removed by generation: the conversation-switch cleanup
          // already cleared the map, and deleting here would drop the reservation
          // of the NEW fetch with the same id.
          if (atual()) reservas.current.delete(id)
        }
        return
      }

      if (c.tipo === "mvt" && c.mvt?.workflow_id && c.mvt?.layer_key) {
        const layer: MapLayer = {
          id, label: nome, color: corDe(artifactId), opacity: 0.6, geojson: VAZIO, visible: true,
          geomType: c.geometry_type ?? "", bbox, baixavel: c.baixavel ?? false,
          mvt: { workflowHash: c.mvt.workflow_id, layerKey: c.mvt.layer_key },
        }
        // Without a bbox there is no way to frame (the geometry comes from the tiles, not the state).
        paraEnquadrar.current = bbox ? id : null
        setCamadas((cs) => comA(cs, layer))
        setAvisos((a) => semAviso(a, artifactId))
        return
      }

      avisar(setAvisos, artifactId, nome, c.hint ?? textos.current.semPreviaCurto)
    } finally {
      // Everything here is by GENERATION: the conversation-switch cleanup already
      // emptied `emVoo`, and a fetch from the OLD scope arriving later would erase
      // the mark of the NEW fetch of the same artifact — which would then download twice.
      if (atual()) {
        emVoo.current.delete(artifactId)
        setCarregando((c) => semA(c, artifactId))
      }
    }
  }, [corDe])

  // Scope switch: the globe belongs to the conversation.
  const escopoAnterior = useRef<string | undefined>(undefined)
  useEffect(() => {
    const anterior = escopoAnterior.current
    escopoAnterior.current = escopo
    if (anterior === undefined || anterior === escopo) return

    geracao.current += 1
    for (const c of controladores.current.values()) c.abort()
    controladores.current.clear()
    buscados.current.clear()
    emVoo.current.clear()
    cores.current.clear()
    bytes.current.clear()
    reservas.current.clear()
    indice.current = 0
    paraEnquadrar.current = null
    assinatura.current = ""
    setCamadas([])
    setAvisos({})
    setCarregando({})
  }, [escopo])

  // On unmount: abort in-flight network requests and invalidate the generation,
  // so a fetch that resolves later does not touch the state of a component that is gone.
  useEffect(() => () => {
    geracao.current += 1
    for (const c of controladores.current.values()) c.abort()
    controladores.current.clear()
  }, [])

  // Reacts to the conversation's `camada` pointers: each new artifact_id is fetched
  // ONCE (the ref avoids re-fetching on every stream delta).
  //
  // The signature avoids the full scan per TOKEN: during the stream
  // `aplicarQuadro` replaces the last text block, so neither the turn count nor
  // the last turn's block count changes — and that is exactly when there is no
  // new layer to find.
  const marca = `${turnos.length}:${turnos[turnos.length - 1]?.blocos.length ?? 0}`
  useEffect(() => {
    if (assinatura.current === marca) return
    assinatura.current = marca
    for (const p of derivarCamadas(turnos)) {
      if (buscados.current.has(p.artifact_id)) continue
      buscados.current.add(p.artifact_id)
      void adicionar(p.artifact_id, p.nome)
    }
  }, [marca, turnos, adicionar])

  // Frame the last new layer AFTER the state has updated. fitToLayer uses
  // the layer's own bbox/coords, so it works even before the map sync.
  useEffect(() => {
    if (paraEnquadrar.current) {
      refMapa.current?.fitToLayer(paraEnquadrar.current)
      paraEnquadrar.current = null
    }
  }, [camadas])

  const remover = useCallback((id: string) => {
    bytes.current.delete(id)
    setCamadas((cs) => semO(cs, id))
  }, [])
  const alternarVisivel = useCallback(
    (id: string) => setCamadas((cs) => cs.map((c) => (c.id === id ? { ...c, visible: !c.visible } : c))),
    [],
  )
  const enquadrar = useCallback((id: string) => refMapa.current?.fitToLayer(id), [])
  const dispensarAviso = useCallback(
    (artifactId: string) => setAvisos((a) => semAviso(a, artifactId)),
    [],
  )

  return { camadas, avisos, carregando, refMapa, adicionar, remover, alternarVisivel, enquadrar, dispensarAviso }
}

const semO = (cs: MapLayer[], id: string) => cs.filter((c) => c.id !== id)

/** Replaces IN PLACE when the id already exists — re-displaying does not reorder the list. */
function comA(cs: MapLayer[], layer: MapLayer): MapLayer[] {
  return cs.some((c) => c.id === layer.id)
    ? cs.map((c) => (c.id === layer.id ? layer : c))
    : [...cs, layer]
}

function somar(mapa: Map<string, number>, exceto: string): number {
  let total = 0
  for (const [id, n] of mapa) if (id !== exceto) total += n
  return total
}

const motivoDoTeto = (restante: number, t: Textos["assistente"]["camada"]) =>
  restante < TETO_BYTES ? t.globoNoLimite : t.grandeDemais

function avisar(
  set: React.Dispatch<React.SetStateAction<Record<string, AvisoDeCamada>>>,
  artifactId: string,
  nome: string,
  motivo: string,
): void {
  set((a) => ({ ...a, [artifactId]: { nome, motivo } }))
}

function semAviso(a: Record<string, AvisoDeCamada>, artifactId: string): Record<string, AvisoDeCamada> {
  if (!(artifactId in a)) return a
  const copia = { ...a }
  delete copia[artifactId]
  return copia
}

function semA<T>(r: Record<string, T>, chave: string): Record<string, T> {
  if (!(chave in r)) return r
  const copia = { ...r }
  delete copia[chave]
  return copia
}

/**
 * Downloads the FeatureCollection, cutting off at `teto`. Reads in chunks and
 * ABORTS when it goes over the limit: `JSON.parse` of a body of hundreds of MB
 * freezes the tab, and that is precisely the case that slipped through when
 * `size_bytes` came back null.
 */
async function baixarComTeto(
  r: Response,
  teto: number,
  signal?: AbortSignal,
): Promise<{ geojson: GeoJSON.FeatureCollection; bytes: number } | null> {
  const declarado = Number(r.headers?.get?.("content-length") ?? NaN)
  if (Number.isFinite(declarado) && declarado > teto) return null

  const leitor = r.body?.getReader?.()
  if (!leitor) {
    // No body readable in chunks: what is left is the Content-Length checked above.
    const geojson = (await r.json()) as GeoJSON.FeatureCollection
    return { geojson, bytes: Number.isFinite(declarado) ? declarado : 0 }
  }

  const utf8 = new TextDecoder()
  let total = 0
  let texto = ""
  for (;;) {
    // Abortado (troca de conversa/desmontagem): larga o corpo e o fio.
    if (signal?.aborted) {
      await leitor.cancel().catch(() => {})
      return null
    }
    const { done, value } = await leitor.read()
    if (done) break
    total += value.byteLength
    if (total > teto) {
      await leitor.cancel().catch(() => {})
      return null
    }
    texto += utf8.decode(value, { stream: true })
  }
  texto += utf8.decode()
  return { geojson: JSON.parse(texto) as GeoJSON.FeatureCollection, bytes: total }
}
