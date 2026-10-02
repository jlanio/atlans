"use client"
import { useSession } from "next-auth/react"
import { useCallback, useEffect, useRef, useState } from "react"

interface FetchState<T> {
  data: T | null
  /** Há requisição em voo — primeira carga OU recarga.
   *
   *  É o sinal do botão Atualizar (`disabled` + ícone girando). Ele NÃO pode
   *  virar "só a primeira carga": quando isso aconteceu, o botão de /admin/settings
   *  e o das telas de observabilidade nunca mais giraram nem desabilitaram — a
   *  tela ficava congelada durante os GETs e o usuário clicava de novo achando
   *  que o primeiro clique não tinha pegado. */
  loading: boolean
  /** Primeira carga: ainda não há NADA na tela. É o gate do skeleton. */
  firstLoad: boolean
  /** Recarga com dados já na tela (auto-refresh, busca, botão Atualizar).
   *  Serve para spinner/opacidade; trocar a lista por skeletons aqui é o que
   *  fazia a tabela piscar a cada tecla digitada e a cada 15 segundos. */
  refreshing: boolean
  error: string | null
  /** Carimbo (ms) da última resposta ACEITA; `null` enquanto nenhuma foi.
   *
   *  É o gate do cartão de erro (contrato de telas, §3.2): ele só toma a tela
   *  com `error && atualizadoEm == null`. Uma recarga que falha sobre a lista
   *  pronta mantém o que havia — quem avisa é o `onErroComDados`. O `setData`
   *  não mexe nele: um dado posto à mão não é uma resposta do servidor. */
  atualizadoEm: number | null
  /** Recarrega. Resolve com o dado aceito NESTA carga, ou `null` se ela falhou
   *  ou foi superada por uma mais nova (a guarda de geração a descartou). */
  refetch: () => Promise<T | null>
  /** Recarga de fundo (auto-refresh, volta à aba): o `refetch`, menos num caso.
   *  Com a 1ª carga em erro, tenta de novo SEM trocar o cartão pelo skeleton,
   *  e o cartão só sai se a resposta vier. Pelo `refetch`, cada tique tirava o
   *  cartão e o punha de volta, e cada volta era um `role="alert"` novo: o
   *  leitor de tela anunciava a mesma falha a cada 15 s. O "Tentar de novo" do
   *  cartão segue no `refetch`: ali quem pediu foi a pessoa. */
  recarregarEmFundo: () => Promise<T | null>
  /** Troca o dado na tela sem buscar: a atualização otimista, o que um
   *  POST/PUT devolveu. Aceita a função do valor anterior, como o `setState`. */
  setData: (valor: T | null | ((anterior: T | null) => T | null)) => void
}

export interface OpcoesDaCarga<T> {
  /** Cada resposta ACEITA (já passou pela guarda de geração), no mesmo tique em
   *  que o hook a guarda. Para quem espelha o dado fora do hook — o contexto
   *  das credenciais, o rascunho da allowlist — sem um quadro de atraso. */
  onDados?: (dados: T) => void
  /** Carga que falha quando já há resposta aceita na tela: o cartão de erro
   *  não toma o lugar da lista, e quem avisa é isto (tipicamente um toast).
   *  Recebe a mensagem do erro. Na 1ª carga não é chamado — ali o erro é o
   *  cartão. */
  onErroComDados?: (mensagem: string) => void
  /** Desligada (`false`), a carga não roda e o estado volta ao inicial — sem
   *  dado, sem erro, `firstLoad` —, descartando o que estiver em voo; religada,
   *  carrega do zero. Para o que só busca enquanto aberto (um modal) ou para
   *  quem pode (uma tela de admin). `true` por padrão. */
  ativo?: boolean
}

// Hook genérico para buscar dados autenticados (aguarda status === "authenticated").
// debounceMs: intervalo mínimo entre execuções (útil para inputs de busca em tempo real).
//
// As telas que refaziam isto à mão — cada uma com seu loading/refreshing/
// loadError/atualizadoEm e o gate de sessão — divergiram onde doía: sem a
// guarda de geração, a resposta de um filtro antigo chegava depois e
// sobrescrevia a lista do filtro atual (Admin › Usuários).
export function useFetchData<T>(
  fetcher: () => Promise<{ data?: T | null; error?: { message?: string } | null } | null>,
  errorMsg = "Erro ao carregar dados.",
  deps: unknown[] = [],
  debounceMs = 0,
  opcoes: OpcoesDaCarga<T> = {},
): FetchState<T> {
  const { status } = useSession()
  const ativo = opcoes.ativo ?? true
  const [data, setDataState]            = useState<T | null>(null)
  const [firstLoad, setFirstLoad]       = useState(true)
  const [refreshing, setRefreshing]     = useState(false)
  const [error, setError]               = useState<string | null>(null)
  const [atualizadoEm, setAtualizadoEm] = useState<number | null>(null)
  const timerRef                        = useRef<ReturnType<typeof setTimeout> | null>(null)

  // O chamador recria `fetcher` (e o `errorMsg`) a cada render; lê-los de um ref
  // é o que permite `executar` ter identidade CONSTANTE. Sem isso, todo
  // `useEffect(..., [refetch])` — o auto-refresh de 15s de /executores — refazia
  // clearInterval + setInterval a cada render, e numa tela que renderiza com
  // frequência o intervalo nunca chegava ao fim: a atualização automática
  // simplesmente parava, sem sinal nenhum na UI.
  const fetcherRef  = useRef(fetcher)
  const errorMsgRef = useRef(errorMsg)
  const debounceRef = useRef(debounceMs)
  const opcoesRef   = useRef(opcoes)
  fetcherRef.current  = fetcher
  errorMsgRef.current = errorMsg
  debounceRef.current = debounceMs
  opcoesRef.current   = opcoes

  // `data` também num ref: `executar` precisa saber se já há algo na tela para
  // escolher entre skeleton e refresh, e lê-lo do estado prenderia o callback.
  // Idem o carimbo, que decide entre o cartão de erro e o `onErroComDados`.
  const dataRef         = useRef<T | null>(null)
  const atualizadoEmRef = useRef<number | null>(null)

  // Contador de geração: duas execuções sobrepostas (a URL/deps mudam enquanto a
  // anterior ainda resolve) não podem deixar a resposta VELHA sobrescrever a nova
  // — hoje a que resolvesse por último vencia. Cada `executar` leva um número; ao
  // voltar do await, se a geração já avançou o resultado é obsoleto e é ignorado.
  const geracao = useRef(0)

  const executar = useCallback(async (deFundo: boolean): Promise<T | null> => {
    const gen = ++geracao.current
    // De fundo e sem dado na tela, nada muda enquanto a busca voa: nem
    // skeleton nem erro apagado (ver `recarregarEmFundo`).
    if (!deFundo || dataRef.current !== null) {
      if (dataRef.current === null) setFirstLoad(true)
      else setRefreshing(true)
      setError(null)
    }

    function falhou(mensagem: string) {
      setError(mensagem)
      if (atualizadoEmRef.current != null) opcoesRef.current.onErroComDados?.(mensagem)
    }

    try {
      const result = await fetcherRef.current()
      if (gen !== geracao.current) return null
      if (result?.data != null) {
        const dados = result.data
        const agora = Date.now()
        dataRef.current = dados
        atualizadoEmRef.current = agora
        setDataState(dados)
        setAtualizadoEm(agora)
        // A recarga de fundo não apaga o erro ao sair: quem apaga é a resposta.
        setError(null)
        opcoesRef.current.onDados?.(dados)
        return dados
      }
      falhou(result?.error?.message ?? errorMsgRef.current)
      return null
    } catch (exc) {
      if (gen !== geracao.current) return null
      falhou(exc instanceof Error ? exc.message : errorMsgRef.current)
      return null
    } finally {
      // Sempre limpa — se o fetcher lançar (ex: network error não-axios), o
      // botão de Atualizar ficaria disabled para sempre. Mas só para a geração
      // CORRENTE: um resolve obsoleto não pode desligar o spinner do request novo.
      if (gen === geracao.current) {
        setFirstLoad(false)
        setRefreshing(false)
      }
    }
  }, [])
  // Sem repassar argumentos: o `refetch` desce direto para `onClick`, e o
  // evento do clique não pode virar o `deFundo`.
  const refetch = useCallback(() => executar(false), [executar])
  const recarregarEmFundo = useCallback(() => executar(true), [executar])

  const setData = useCallback((valor: T | null | ((anterior: T | null) => T | null)) => {
    const novo = typeof valor === "function"
      ? (valor as (anterior: T | null) => T | null)(dataRef.current)
      : valor
    dataRef.current = novo
    setDataState(novo)
  }, [])

  useEffect(() => {
    if (!ativo) {
      // Desligada: o que estiver em voo não escreve mais, e a tela volta ao
      // começo — a próxima vez que ligar é uma 1ª carga, com skeleton.
      geracao.current++
      dataRef.current = null
      atualizadoEmRef.current = null
      setDataState(null)
      setAtualizadoEm(null)
      setError(null)
      setRefreshing(false)
      setFirstLoad(true)
      return
    }
    // A sessão pode resolver como "unauthenticated": não há o que buscar, e sem
    // isto o skeleton ficaria para sempre, porque `firstLoad` nasce true e nada
    // o desligaria.
    if (status === "unauthenticated") {
      setFirstLoad(false)
      return
    }
    if (status !== "authenticated") return
    if (debounceRef.current > 0) {
      timerRef.current = setTimeout(refetch, debounceRef.current)
    } else {
      refetch()
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, refetch, ativo, ...deps])

  // `loading` é a união dos dois: quem só quer saber "está buscando?" (botão
  // Atualizar) lê `loading`; quem decide entre skeleton e lista lê `firstLoad`.
  return {
    data, loading: firstLoad || refreshing, firstLoad, refreshing, error, atualizadoEm,
    refetch, recarregarEmFundo, setData,
  }
}
