"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useTextosDaCasca } from "@/app/components/home/i18n/da-casca"
import type { IConversaResumo } from "@/service/types"
import type { AnuncioDeConversa } from "@/app/stores/homeStore"

/** The result of an optimistic write. `erro` exists because a boolean only
 *  said "it didn't work" — and the rename dialog stayed open without explaining anything. */
export interface ResultadoDaEscrita {
  ok: boolean
  erro?: string
}

export interface UseConversas {
  conversas: IConversaResumo[]
  /** Only the FIRST load (the skeleton). */
  carregando: boolean
  /** Reload in flight over the list already on screen — `aria-busy`, not a skeleton. */
  atualizando: boolean
  /** An accepted load has already happened: the error block only takes over the list before that. */
  jaCarregou: boolean
  erro: string | null
  /** Quantas conversas o servidor tem — a lista vem cortada em `LIMITE`. */
  total: number
  /** One more page in flight (the "Ver mais" (see more)). */
  carregandoMais: boolean
  /** Rereads what is on screen — ALL pages already loaded, at once. */
  recarregar: () => void
  /** Appends the next page. Without this the cutoff at 50 was invisible. */
  carregarMais: () => void
  /** Redoes what failed last: the "Ver mais" page, or the reload. */
  tentarDeNovo: () => void
  /**
   * Applies an announcement from the assistant stream (see `AnuncioDeConversa`):
   * a new conversation goes in at the top with its title; an existing one moves up. No GET.
   */
  anunciar: (anuncio: AnuncioDeConversa) => void
  /** Renomeia (otimista). */
  renomear: (id: string, titulo: string) => Promise<ResultadoDaEscrita>
  /** Apaga (soft, otimista). */
  apagar: (id: string) => Promise<ResultadoDaEscrita>
}

// The endpoint's ceiling (`limit = max(1, min(limit, 100))` in agente_router) — and
// it is SILENT: asking for more returns 100 with no error. That is why the reload reads by pages.
const LIMITE = 100

/**
 * The stored failure: our own microcopy as a KEY, so the sentence comes out in
 * the language in use when it is shown (switching language in Preferences does
 * not reload the list), or the server's `detail`, which is not translated.
 */
type Falha = "carregar" | "carregarMais" | { detalhe: string }

/**
 * The list with an announcement applied — what the server would return on the
 * next read (ordered by `updated_at DESC`), without fetching:
 * - the conversation is already in the list → moves to the top (the
 *   announcement's title, if present, is the server's; `updated_at` = now);
 * - it is not, and the announcement has a title → new row at the top (`inseriu`);
 * - it is not, and it came WITHOUT a title (the accepted confirmation only knows
 *   the id) → nothing: a "Sem título" (untitled) row is never invented.
 * Idempotent: applying the same announcement twice does not duplicate.
 */
export function comAnuncio(
  lista: IConversaResumo[],
  anuncio: AnuncioDeConversa,
  agora: string = new Date().toISOString(),
): { lista: IConversaResumo[]; inseriu: boolean } {
  const atual = lista.find((c) => c.id === anuncio.id)
  const resto = lista.filter((c) => c.id !== anuncio.id)
  if (atual) {
    return {
      lista: [{ ...atual, titulo: anuncio.titulo ?? atual.titulo, updated_at: agora }, ...resto],
      inseriu: false,
    }
  }
  if (!anuncio.titulo) return { lista, inseriu: false }
  const nova: IConversaResumo = {
    id: anuncio.id, titulo: anuncio.titulo, workflow_id: null, tokens_total: 0,
    created_at: agora, updated_at: agora,
  }
  return { lista: [nova, ...resto], inseriu: true }
}

/**
 * The list of the Home assistant's conversations (the "Chats"). Plain JSON — the
 * live conversation is SSE and lives in another hook (the panel). Rename and
 * delete are optimistic: the row changes/disappears right away and the list is
 * not reloaded (GisFlowService's write epoch already invalidates concurrent reads).
 *
 * The list does NOT update by itself: what teaches it about a new conversation
 * (or one that got a message) is `anunciar`, fed by `ChatsLista` with the
 * announcement HomeView leaves in the store. Accepted residual: a reload started
 * IN THE MIDDLE of a turn of an existing conversation shows the pre-turn order
 * until the next activity or F5 — the server stamps `updated_at` only at the
 * end of the turn.
 *
 * State precedence from §3: a reload that fails does NOT erase the conversations
 * already on screen — `setConversas` only happens with ALL pages good.
 */
export function useConversas(): UseConversas {
  const t = useTextosDaCasca().listas
  const [conversas, setConversas] = useState<IConversaResumo[]>([])
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [jaCarregou, setJaCarregou] = useState(false)
  const [falha, setFalha] = useState<Falha | null>(null)
  const [total, setTotal] = useState(0)
  const [carregandoMais, setCarregandoMais] = useState(false)
  // Discards responses from a load older than the most recent one (quick switch).
  const geracao = useRef(0)
  const jaCarregouRef = useRef(false)
  // The current list without entering the dependencies: "Ver mais" needs the size
  // and the announcement needs to know whether the conversation is already here
  // (the callbacks must be stable so as not to recreate handlers on every new row).
  const listaRef = useRef<IConversaResumo[]>([])
  listaRef.current = conversas
  // What failed last — it is what "Tentar de novo" redoes.
  const ultimaFalha = useRef<"recarga" | "pagina">("recarga")

  const recarregar = useCallback(() => {
    const minha = ++geracao.current
    if (jaCarregouRef.current) setAtualizando(true)
    else setCarregando(true)
    // Rereads ALL pages on screen, not just the first: after "Ver mais" the
    // list had 200, 300 rows and a reload brought it back to 100.
    // The server ceiling is silent, so it goes by offset, in parallel and
    // all-or-nothing — one bad page and the list stays as it was (§3).
    const paginas = Math.max(1, Math.ceil(listaRef.current.length / LIMITE))
    const pedidos = Array.from({ length: paginas }, (_, i) =>
      i === 0 ? GisFlowService.listarConversas(LIMITE) : GisFlowService.listarConversas(LIMITE, i * LIMITE),
    )
    Promise.all(pedidos).then((respostas) => {
      if (minha !== geracao.current) return
      const ruim = respostas.find((r) => !r.success || !r.data)
      if (!ruim) {
        // A conversation that moved up between two pages may come repeated: the key
        // is the id, not the position (the same care as "Ver mais").
        const vistos = new Set<string>()
        const itens: IConversaResumo[] = []
        for (const r of respostas) {
          for (const c of r.data!.itens) {
            if (vistos.has(c.id)) continue
            vistos.add(c.id)
            itens.push(c)
          }
        }
        setConversas(itens)
        setTotal(respostas[0].data!.total)
        setFalha(null)
        jaCarregouRef.current = true
        setJaCarregou(true)
      } else {
        ultimaFalha.current = "recarga"
        // Our own microcopy comes before the backend's raw `detail`: a 500
        // returned "Erro inesperado." (unexpected error) as if it were text written for the person.
        const detalhe = ruim.error?.message
        setFalha(ruim.status >= 500 || !detalhe ? "carregar" : { detalhe })
      }
      setCarregando(false)
      setAtualizando(false)
    })
  }, [])

  // Loads on mount. `geracao` already discards responses from a load older than
  // the most recent one (quick switch); a setState after unmount is a no-op in React 18.
  useEffect(() => { recarregar() }, [recarregar])

  const carregarMais = useCallback(() => {
    // The generation does NOT advance: this is another page of the SAME load, and a
    // parallel reload must be able to invalidate it.
    const minha = geracao.current
    setCarregandoMais(true)
    GisFlowService.listarConversas(LIMITE, listaRef.current.length).then((res) => {
      if (minha !== geracao.current) { setCarregandoMais(false); return }
      if (res.success && res.data) {
        const pagina = res.data.itens
        setConversas((atual) => {
          // Deleting is optimistic and shortens the list, so the offset may repeat a
          // conversation already on screen — the key is the id, not the position.
          const vistos = new Set(atual.map((c) => c.id))
          return [...atual, ...pagina.filter((c) => !vistos.has(c.id))]
        })
        setTotal(res.data.total)
        setFalha(null)
      } else {
        ultimaFalha.current = "pagina"
        setFalha("carregarMais")
      }
      setCarregandoMais(false)
    })
  }, [])

  const tentarDeNovo = useCallback(() => {
    if (ultimaFalha.current === "pagina") carregarMais()
    else recarregar()
  }, [carregarMais, recarregar])

  const anunciar = useCallback((anuncio: AnuncioDeConversa) => {
    const agora = new Date().toISOString()
    setConversas((atual) => comAnuncio(atual, anuncio, agora).lista)
    // The total goes up only when the conversation was JUST born and was not here
    // yet (the mount load may have arrived after it). OUTSIDE the `setConversas`
    // updater: in StrictMode updaters run twice.
    const jaEstava = listaRef.current.some((c) => c.id === anuncio.id)
    if (anuncio.nova && anuncio.titulo && !jaEstava) setTotal((n) => n + 1)
  }, [])

  const renomear = useCallback(async (id: string, titulo: string): Promise<ResultadoDaEscrita> => {
    const res = await GisFlowService.renomearConversa(id, titulo)
    if (res.success) {
      // The server stamps `updated_at` on PATCH: renaming counts as activity
      // and the conversation moves up. Mirroring it here avoids the order jump on F5.
      const agora = new Date().toISOString()
      setConversas((atual) => comAnuncio(atual, { id, titulo, nova: false }, agora).lista)
      return { ok: true }
    }
    return { ok: false, erro: res.error?.message ?? t.geral.tenteDeNovo }
  }, [t])

  const apagar = useCallback(async (id: string): Promise<ResultadoDaEscrita> => {
    const res = await GisFlowService.apagarConversa(id)
    if (res.success) {
      setConversas((atual) => atual.filter((c) => c.id !== id))
      setTotal((n) => Math.max(0, n - 1))
      return { ok: true }
    }
    return { ok: false, erro: res.error?.message ?? t.geral.tenteDeNovo }
  }, [t])

  const erro = falha == null
    ? null
    : falha === "carregar"
      ? t.chats.carregarFalhou
      : falha === "carregarMais"
        ? t.chats.carregarMaisFalhou
        : falha.detalhe

  return {
    conversas, carregando, atualizando, jaCarregou, erro, total, carregandoMais,
    recarregar, carregarMais, tentarDeNovo, anunciar, renomear, apagar,
  }
}
