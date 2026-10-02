"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useTextosDaCasca } from "@/app/components/home/i18n/da-casca"
import type { IConversaResumo } from "@/service/types"
import type { AnuncioDeConversa } from "@/app/stores/homeStore"

/** O resultado de uma escrita otimista. O `erro` existe porque um booleano só
 *  dizia "não deu" — e o diálogo de renomear ficava aberto sem explicar nada. */
export interface ResultadoDaEscrita {
  ok: boolean
  erro?: string
}

export interface UseConversas {
  conversas: IConversaResumo[]
  /** Só a PRIMEIRA carga (o esqueleto). */
  carregando: boolean
  /** Recarga em voo sobre a lista já na tela — `aria-busy`, não esqueleto. */
  atualizando: boolean
  /** Já houve uma carga aceita: o bloco de erro só toma a lista antes disso. */
  jaCarregou: boolean
  erro: string | null
  /** Quantas conversas o servidor tem — a lista vem cortada em `LIMITE`. */
  total: number
  /** Uma página a mais em voo (o "Ver mais"). */
  carregandoMais: boolean
  /** Relê o que está na tela — TODAS as páginas já carregadas, de uma vez. */
  recarregar: () => void
  /** Anexa a próxima página. Sem isto o corte em 50 era invisível. */
  carregarMais: () => void
  /** Refaz o que falhou por último: a página do "Ver mais", ou a recarga. */
  tentarDeNovo: () => void
  /**
   * Aplica um anúncio do stream do assistente (ver `AnuncioDeConversa`): a
   * conversa nova entra no topo com o título; a existente sobe. Sem GET.
   */
  anunciar: (anuncio: AnuncioDeConversa) => void
  /** Renomeia (otimista). */
  renomear: (id: string, titulo: string) => Promise<ResultadoDaEscrita>
  /** Apaga (soft, otimista). */
  apagar: (id: string) => Promise<ResultadoDaEscrita>
}

// O teto do endpoint (`limit = max(1, min(limit, 100))` no agente_router) — e é
// SILENCIOSO: pedir mais devolve 100 sem erro. Por isso a recarga lê por páginas.
const LIMITE = 100

/**
 * A falha guardada: a microcopy da casa como CHAVE, para a frase sair no idioma
 * em uso quando é mostrada (trocar de idioma nas Preferências não recarrega a
 * lista), ou o `detail` do servidor, que não se traduz.
 */
type Falha = "carregar" | "carregarMais" | { detalhe: string }

/**
 * A lista com um anúncio aplicado — o que o servidor devolveria na próxima
 * leitura (ordem por `updated_at DESC`), sem ir buscar:
 * - a conversa já está na lista → sobe ao topo (o título do anúncio, se veio,
 *   é o do servidor; `updated_at` = agora);
 * - não está e o anúncio traz título → linha nova no topo (`inseriu`);
 * - não está e veio SEM título (a confirmação aceita só sabe o id) → nada:
 *   nunca se inventa uma linha "Sem título".
 * Idempotente: aplicar o mesmo anúncio duas vezes não duplica.
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
 * A lista de conversas do assistente da Home (os "Chats"). JSON puro — a
 * conversa ao vivo é SSE e mora noutro hook (o painel). Renomear e apagar são
 * otimistas: a linha muda/some na hora e a lista não é recarregada (a época de
 * escrita do GisFlowService já invalida leituras concorrentes).
 *
 * A lista NÃO se atualiza sozinha: quem a ensina sobre uma conversa nova (ou
 * uma que ganhou mensagem) é `anunciar`, alimentado pelo `ChatsLista` com o
 * anúncio que o HomeView deixa na store. Residual aceito: uma recarga iniciada
 * NO MEIO de um turno de conversa existente mostra a ordem pré-turno até a
 * próxima atividade ou F5 — o servidor carimba `updated_at` só no fim do turno.
 *
 * Precedência de estados do §3: uma recarga que falha NÃO apaga as conversas já
 * na tela — o `setConversas` só acontece com TODAS as páginas boas.
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
  // Descarta respostas de uma carga anterior à mais recente (troca rápida).
  const geracao = useRef(0)
  const jaCarregouRef = useRef(false)
  // A lista atual sem entrar nas dependências: o "Ver mais" precisa do tamanho e
  // o anúncio precisa saber se a conversa já está aqui (os callbacks têm de ser
  // estáveis para não recriar handlers a cada linha nova).
  const listaRef = useRef<IConversaResumo[]>([])
  listaRef.current = conversas
  // O que falhou por último — é o que "Tentar de novo" refaz.
  const ultimaFalha = useRef<"recarga" | "pagina">("recarga")

  const recarregar = useCallback(() => {
    const minha = ++geracao.current
    if (jaCarregouRef.current) setAtualizando(true)
    else setCarregando(true)
    // Relê TODAS as páginas que estão na tela, e não só a primeira: depois do
    // "Ver mais" a lista tinha 200, 300 linhas e uma recarga a devolvia a 100.
    // O teto do servidor é silencioso, então é por offset, em paralelo e
    // tudo-ou-nada — uma página ruim e a lista fica como estava (§3).
    const paginas = Math.max(1, Math.ceil(listaRef.current.length / LIMITE))
    const pedidos = Array.from({ length: paginas }, (_, i) =>
      i === 0 ? GisFlowService.listarConversas(LIMITE) : GisFlowService.listarConversas(LIMITE, i * LIMITE),
    )
    Promise.all(pedidos).then((respostas) => {
      if (minha !== geracao.current) return
      const ruim = respostas.find((r) => !r.success || !r.data)
      if (!ruim) {
        // Uma conversa que subiu entre duas páginas pode vir repetida: a chave
        // é o id, não a posição (o mesmo cuidado do "Ver mais").
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
        // A microcopy da casa vem antes do `detail` cru do backend: um 500
        // devolvia "Erro inesperado." como se fosse texto escrito para a pessoa.
        const detalhe = ruim.error?.message
        setFalha(ruim.status >= 500 || !detalhe ? "carregar" : { detalhe })
      }
      setCarregando(false)
      setAtualizando(false)
    })
  }, [])

  // Carrega no mount. A `geracao` já descarta respostas de uma carga anterior à
  // mais recente (troca rápida); um setState após desmontar é no-op no React 18.
  useEffect(() => { recarregar() }, [recarregar])

  const carregarMais = useCallback(() => {
    // A geração NÃO avança: esta é outra página da MESMA carga, e uma recarga em
    // paralelo precisa poder invalidá-la.
    const minha = geracao.current
    setCarregandoMais(true)
    GisFlowService.listarConversas(LIMITE, listaRef.current.length).then((res) => {
      if (minha !== geracao.current) { setCarregandoMais(false); return }
      if (res.success && res.data) {
        const pagina = res.data.itens
        setConversas((atual) => {
          // Apagar é otimista e encurta a lista, então o offset pode repetir uma
          // conversa que já está na tela — a chave é o id, não a posição.
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
    // O total sobe só quando a conversa NASCEU agora e ainda não estava aqui
    // (a carga de montagem pode ter chegado depois dela). FORA do updater de
    // `setConversas`: no StrictMode os updaters rodam duas vezes.
    const jaEstava = listaRef.current.some((c) => c.id === anuncio.id)
    if (anuncio.nova && anuncio.titulo && !jaEstava) setTotal((n) => n + 1)
  }, [])

  const renomear = useCallback(async (id: string, titulo: string): Promise<ResultadoDaEscrita> => {
    const res = await GisFlowService.renomearConversa(id, titulo)
    if (res.success) {
      // O servidor carimba `updated_at` no PATCH: renomear conta como atividade
      // e a conversa sobe. Espelhar aqui evita o pulo de ordem no F5.
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
