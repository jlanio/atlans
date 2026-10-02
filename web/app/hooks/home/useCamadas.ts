"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { MapLayer, MapLibreMapHandle } from "@/app/components/share/MapLibreMap"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import { corDaCamada, derivarCamadas, pareceLonLat } from "@/app/components/home/camadas"
import { useTextos, type Textos } from "@/app/components/home/i18n"

// Acima disto, a prévia é recusada: uma FeatureCollection de 100 MB em memória
// trava a aba, e o globo não é um visualizador de dados pesados.
const TETO_BYTES = 25 * 1024 * 1024
// E um teto AGREGADO: cinco camadas de 24 MB passam uma a uma no teto acima e
// somam ~120 MB de heap (GeoJSON expandido + a cópia no worker do MapLibre).
const TETO_TOTAL_BYTES = 60 * 1024 * 1024
const VAZIO: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] }

/** Por que um artefato não virou camada — com o nome, para a pessoa saber qual. */
export interface AvisoDeCamada {
  nome?: string
  motivo: string
}

export interface UseCamadas {
  camadas: MapLayer[]
  /** artifact_id → aviso de "sem prévia" (indisponível, grande demais, erro). */
  avisos: Record<string, AvisoDeCamada>
  /** artifact_id → rótulo das camadas sendo buscadas agora. */
  carregando: Record<string, string>
  refMapa: React.RefObject<MapLibreMapHandle | null>
  adicionar: (artifactId: string, nome?: string) => Promise<void>
  remover: (id: string) => void
  alternarVisivel: (id: string) => void
  enquadrar: (id: string) => void
  /** Tira um aviso da tela (o X da linha). */
  dispensarAviso: (artifactId: string) => void
}

/**
 * As camadas do globo, derivadas da conversa. Cada ponteiro `camada` (de um
 * `run_workflow` ou de `exibir_no_globo`) é buscado uma vez em
 * `GET /assistente/camadas/{id}` e vira uma `MapLayer`:
 * - geojson: `fetch` da URL pré-assinada → FeatureCollection EM MEMÓRIA (a URL
 *   expira em ~900s; nunca `addSource({data: url})`). Teto por camada e no total.
 * - mvt (publicada): camada vetorial por `/terra/assistente/tiles/…`.
 * - indisponível: um aviso "sem prévia" com a razão.
 * A `bbox` só enquadra quando cabe em lon/lat.
 *
 * O ciclo de vida é O DO `escopo` (a conversa ativa): trocar de chat zera
 * camadas, avisos e a memória de "já busquei este artefato". Sem isso o globo
 * somava as camadas de A, B e C, o painel não dizia de qual conversa cada uma
 * veio, e uma camada removida nunca mais voltava ao reabrir o chat que a
 * produziu. Quem decide o escopo é o HomeView — só ele sabe distinguir "a
 * pessoa abriu outro chat" de "a conversa nova acabou de ganhar um id".
 */
export function useCamadas(turnos: TurnoDoAssistente[], escopo?: string): UseCamadas {
  const [camadas, setCamadas] = useState<MapLayer[]>([])
  const [avisos, setAvisos] = useState<Record<string, AvisoDeCamada>>({})
  const [carregando, setCarregando] = useState<Record<string, string>>({})
  const refMapa = useRef<MapLibreMapHandle | null>(null)
  const buscados = useRef<Set<string>>(new Set())
  const emVoo = useRef<Set<string>>(new Set())
  const indice = useRef(0)
  // A cor é POR artefato: re-exibir o mesmo artefato tem de manter a cor que a
  // pessoa já associou à camada, e uma tentativa que falhou não pode queimar
  // uma cor da paleta.
  const cores = useRef<Map<string, string>>(new Map())
  // Bytes já baixados por camada, para o teto agregado; sai junto com a camada.
  const bytes = useRef<Map<string, number>>(new Map())
  // Bytes PROMETIDOS pelas buscas em voo. `bytes` só é escrito depois que o
  // download termina: sem esta reserva, N adições simultâneas liam todas o
  // mesmo mapa (ainda vazio) e passavam todas pelo teto agregado. Entra antes
  // da viagem de rede e sai no fim — a camada que entrou já contabilizou o
  // número real em `bytes`, e a que não entrou não deve nada.
  const reservas = useRef<Map<string, number>>(new Map())
  // AbortController por download em voo: trocar de conversa ou desmontar ABORTA
  // a rede. Sem isso o `baixarComTeto` seguia lendo um corpo de centenas de MB
  // de um chat que a pessoa já fechou, e a promessa do fetch só assentava
  // quando o download inteiro chegasse. Espelha o `abortoRef` do useAssistente.
  const controladores = useRef<Map<string, AbortController>>(new Map())
  const paraEnquadrar = useRef<string | null>(null)
  // Sobe a cada limpeza: uma busca que já estava em voo quando a conversa
  // trocou não pode plantar a camada da conversa anterior no globo da nova.
  const geracao = useRef(0)
  const assinatura = useRef("")
  // Os textos dos avisos vão por ref: `adicionar` é dependência do efeito que
  // busca as camadas, e trocar o idioma não pode mudar a identidade dela.
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
    // Dois cliques no mesmo artefato baixavam duas vezes a URL pré-assinada (o
    // `get()` do serviço só deduplica a chamada de metadados, não o fetch cru).
    if (emVoo.current.has(artifactId)) return
    const id = `art:${artifactId}`
    const minhaGeracao = geracao.current
    const rotuloProvisorio = (nomeSugerido || artifactId).trim()
    emVoo.current.add(artifactId)
    setCarregando((c) => ({ ...c, [artifactId]: rotuloProvisorio }))
    /** Só escreve estado se a conversa ainda for a mesma de quando começou. */
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
      // A bbox NÃO é reinterpretada pelo `crs`: o servidor já zera a que não
      // merece confiança, e no ramo MVT ela é 4326 por construção. Comparar a
      // string `crs` com "EPSG:4326" descartava bbox boa de dado publicado em
      // CRS nativo — a câmera nunca saía do enquadramento inicial.
      const bbox = pareceLonLat(c.bbox) ? (c.bbox as number[]) : undefined

      if (c.tipo === "geojson" && c.download_url) {
        // O que sobra do teto agregado conta o que já está NO GLOBO e o que já
        // foi prometido por outra busca em voo — senão duas adições ao mesmo
        // tempo enxergam as duas o orçamento inteiro e estouram juntas.
        const restante = TETO_TOTAL_BYTES - somar(bytes.current, id) - somar(reservas.current, id)
        const teto = Math.min(TETO_BYTES, restante)
        if (c.size_bytes != null && c.size_bytes > teto) {
          avisar(setAvisos, artifactId, nome, motivoDoTeto(restante, textos.current))
          return
        }
        // Reserva ANTES do fetch. Tamanho desconhecido reserva o `teto` INTEIRO
        // (o máximo que o corte no fio deixa entrar): reservar 0 fazia N buscas
        // de tamanho desconhecido não se enxergarem no teto agregado e estourarem
        // juntas. O valor real corrige em `bytes` quando o download termina.
        reservas.current.set(id, c.size_bytes ?? teto)
        const controle = new AbortController()
        controladores.current.set(artifactId, controle)
        try {
          // SEM Authorization: a URL é pré-assinada e some em ~900s. A
          // FeatureCollection fica em memória; nunca addSource({data: url}).
          // `signal`: a troca de conversa/desmontagem aborta o download em voo.
          const r = await fetch(c.download_url, { signal: controle.signal })
          if (!r.ok) throw new Error(String(r.status))
          // `size_bytes` nulo NÃO é "pequeno": o consumer grava NULL quando o
          // head do storage falha. O corte é pelo que chega no fio.
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
          // Abortado (troca de conversa/desmontagem): `atual()` é falso e não há
          // aviso — a rede parou de propósito, não é falha de prévia.
          if (atual()) avisar(setAvisos, artifactId, nome, textos.current.naoCarregouPrevia)
        } finally {
          controladores.current.delete(artifactId)
          // A reserva sai por geração: a limpeza da troca de conversa já zerou o
          // mapa, e apagar aqui derrubaria a reserva da busca NOVA de mesmo id.
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
        // Sem bbox não dá para enquadrar (a geometria vem dos tiles, não do estado).
        paraEnquadrar.current = bbox ? id : null
        setCamadas((cs) => comA(cs, layer))
        setAvisos((a) => semAviso(a, artifactId))
        return
      }

      avisar(setAvisos, artifactId, nome, c.hint ?? textos.current.semPreviaCurto)
    } finally {
      // Tudo aqui é por GERAÇÃO: a limpeza da troca de conversa já esvaziou o
      // `emVoo`, e uma busca do escopo ANTIGO chegando depois apagaria a marca
      // da busca NOVA do mesmo artefato — que então baixaria duas vezes.
      if (atual()) {
        emVoo.current.delete(artifactId)
        setCarregando((c) => semA(c, artifactId))
      }
    }
  }, [corDe])

  // Troca de escopo: o globo é da conversa.
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

  // Na desmontagem: aborta a rede em voo e invalida a geração, para uma busca
  // que resolva depois não tocar no estado de um componente que já saiu.
  useEffect(() => () => {
    geracao.current += 1
    for (const c of controladores.current.values()) c.abort()
    controladores.current.clear()
  }, [])

  // Reage aos ponteiros `camada` da conversa: cada artifact_id novo é buscado
  // UMA vez (o ref evita re-buscar a cada delta do stream).
  //
  // A assinatura evita a varredura completa por TOKEN: durante o stream o
  // `aplicarQuadro` substitui o último bloco de texto, então nem a contagem de
  // turnos nem a de blocos do último mudam — e é exatamente aí que não há
  // camada nova para achar.
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

  // Enquadra a última camada nova DEPOIS que o estado atualizou. fitToLayer usa
  // a bbox/coords da própria camada, então funciona mesmo antes do sync do mapa.
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

/** Substitui NO LUGAR quando o id já existe — re-exibir não reordena a lista. */
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
 * Baixa a FeatureCollection cortando no `teto`. Lê em pedaços e ABORTA quando
 * passa do limite: o `JSON.parse` de um corpo de centenas de MB congela a aba,
 * e é justamente esse o caso que escapava quando `size_bytes` vinha nulo.
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
    // Sem corpo legível em pedaços: resta o Content-Length conferido acima.
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
