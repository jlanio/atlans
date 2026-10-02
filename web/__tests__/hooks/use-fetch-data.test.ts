import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"

const sessao = vi.hoisted(() => ({ status: "authenticated" }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: sessao.status }) }))
import { useFetchData } from "@/app/hooks/useFetchData"

beforeEach(() => {
  vi.clearAllMocks()
  sessao.status = "authenticated"
})

/** Fetcher controlável: cada chamada devolve uma promise que o teste resolve. */
function fetcherControlado<T>() {
  const resolvers: ((valor: { data: T }) => void)[] = []
  const fetcher = vi.fn(() => new Promise<{ data: T }>(res => { resolvers.push(res) }))
  return { fetcher, resolverProxima: (valor: T) => act(async () => { resolvers.shift()!({ data: valor }) }) }
}

describe("useFetchData — sinais de carga", () => {
  it("firstLoad só na primeira carga; loading em TODA requisição", async () => {
    const { fetcher, resolverProxima } = fetcherControlado<string[]>()
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))

    // Primeira carga: sem nada na tela, os dois sinais ligados (skeleton + spinner).
    expect(result.current.firstLoad).toBe(true)
    expect(result.current.loading).toBe(true)

    await resolverProxima(["a"])
    await waitFor(() => expect(result.current.data).toEqual(["a"]))
    expect(result.current.firstLoad).toBe(false)
    expect(result.current.loading).toBe(false)

    // Recarga (botão Atualizar): `loading` TEM de voltar a true — foi
    // exatamente o que sumiu e deixou o botão de /admin/settings sem girar e
    // sem desabilitar, como se o clique não tivesse pegado.
    act(() => { result.current.refetch() })
    await waitFor(() => expect(result.current.loading).toBe(true))
    expect(result.current.refreshing).toBe(true)
    // ...mas sem trocar a lista por skeletons: os dados continuam na tela.
    expect(result.current.firstLoad).toBe(false)
    expect(result.current.data).toEqual(["a"])

    await resolverProxima(["a", "b"])
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.refreshing).toBe(false)
    expect(result.current.data).toEqual(["a", "b"])
  })

  it("loading é a união de firstLoad e refreshing, nunca menos", async () => {
    const { fetcher, resolverProxima } = fetcherControlado<number[]>()
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))

    const uniao = () => result.current.firstLoad || result.current.refreshing
    expect(result.current.loading).toBe(uniao())

    await resolverProxima([1])
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.loading).toBe(uniao())

    act(() => { result.current.refetch() })
    await waitFor(() => expect(result.current.refreshing).toBe(true))
    expect(result.current.loading).toBe(uniao())
  })
})

describe("useFetchData — guarda de geração", () => {
  it("resposta obsoleta NÃO sobrescreve a mais recente", async () => {
    // Duas execuções se sobrepõem (deps mudam antes de a 1a resolver). A que
    // resolvesse por último vencia; agora cada execute leva um número e o
    // resultado de uma geração passada é ignorado.
    const resolvers: Array<(v: { data: string }) => void> = []
    const fetcher = vi.fn(() => new Promise<{ data: string }>(res => { resolvers.push(res) }))
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))

    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1)) // execute#1
    act(() => { result.current.refetch() })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2)) // execute#2

    // A 2a resolve primeiro (a nova), e só depois a 1a (a velha).
    await act(async () => { resolvers[1]({ data: "nova" }) })
    await act(async () => { resolvers[0]({ data: "velha" }) })

    // A velha, resolvendo por último, não pode vencer.
    expect(result.current.data).toBe("nova")
  })

  it("a resposta obsoleta também não chega ao `onDados`, e o `refetch` dela resolve com null", async () => {
    const resolvers: Array<(v: { data: string }) => void> = []
    const fetcher = vi.fn(() => new Promise<{ data: string }>(res => { resolvers.push(res) }))
    const onDados = vi.fn()
    const { result } = renderHook(() => useFetchData(fetcher, "erro", [], 0, { onDados }))
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))

    let nova!: Promise<string | null>
    act(() => { nova = result.current.refetch() })
    await act(async () => { resolvers[1]({ data: "nova" }) })
    await act(async () => { resolvers[0]({ data: "velha" }) })

    expect(onDados).toHaveBeenCalledTimes(1)
    expect(onDados).toHaveBeenCalledWith("nova")
    expect(await nova).toBe("nova")
  })
})

/** Fetcher que responde, na ordem, cada item da fila (dado ou erro). */
function fetcherEmFila<T>(...fila: Array<{ data: T } | { error: { message: string } }>) {
  return vi.fn(async () => fila.shift() ?? null)
}

describe("useFetchData — cartão de erro × toast da recarga", () => {
  it("atualizadoEm: null até a 1ª resposta aceita; recarga que falha não o mexe", async () => {
    const fetcher = fetcherEmFila<string[]>({ data: ["a"] }, { error: { message: "caiu" } })
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))
    expect(result.current.atualizadoEm).toBeNull()

    await waitFor(() => expect(result.current.data).toEqual(["a"]))
    const carimbo = result.current.atualizadoEm
    expect(carimbo).toEqual(expect.any(Number))

    await act(async () => { await result.current.refetch() })
    expect(result.current.error).toBe("caiu")
    expect(result.current.atualizadoEm).toBe(carimbo)
    // A lista continua: é o `error && atualizadoEm == null` que dá o cartão.
    expect(result.current.data).toEqual(["a"])
  })

  it("onErroComDados: o toast é da recarga — na 1ª carga o erro é o cartão", async () => {
    const onErroComDados = vi.fn()
    const fetcher = fetcherEmFila<string[]>(
      { error: { message: "1ª caiu" } }, { data: ["a"] }, { error: { message: "recarga caiu" } },
    )
    const { result } = renderHook(() => useFetchData(fetcher, "erro", [], 0, { onErroComDados }))

    await waitFor(() => expect(result.current.error).toBe("1ª caiu"))
    expect(result.current.atualizadoEm).toBeNull()
    expect(onErroComDados).not.toHaveBeenCalled()

    await act(async () => { await result.current.refetch() })
    await act(async () => { await result.current.refetch() })
    expect(onErroComDados).toHaveBeenCalledTimes(1)
    expect(onErroComDados).toHaveBeenCalledWith("recarga caiu")
  })

  it("sem mensagem do servidor, vale o errorMsg da tela", async () => {
    const fetcher = vi.fn(async () => ({ error: {} }))
    const { result } = renderHook(() => useFetchData(fetcher, "Não foi possível carregar X."))
    await waitFor(() => expect(result.current.error).toBe("Não foi possível carregar X."))
  })
})

describe("useFetchData — recarga de fundo", () => {
  it("com a 1ª carga em erro, a tentativa não troca o cartão pelo skeleton nem apaga o erro", async () => {
    const resolvers: ((valor: { data?: string[]; error?: { message: string } }) => void)[] = []
    const fetcher = vi.fn(() => new Promise<{ data?: string[]; error?: { message: string } }>(res => { resolvers.push(res) }))
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))
    await act(async () => { resolvers.shift()!({ error: { message: "fora do ar" } }) })
    expect(result.current.error).toBe("fora do ar")
    expect(result.current.firstLoad).toBe(false)

    // Em voo: o cartão continua (erro na tela, sem skeleton, sem spinner). Pelo
    // `refetch`, o cartão saía e voltava — um `role="alert"` novo a cada tique.
    act(() => { result.current.recarregarEmFundo() })
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(result.current.firstLoad).toBe(false)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe("fora do ar")

    // Falhou de novo: o mesmo erro, nada mais muda.
    await act(async () => { resolvers.shift()!({ error: { message: "fora do ar" } }) })
    expect(result.current.error).toBe("fora do ar")
    expect(result.current.firstLoad).toBe(false)

    // Voltou: a lista toma o lugar do cartão.
    act(() => { result.current.recarregarEmFundo() })
    await act(async () => { resolvers.shift()!({ data: ["a"] }) })
    expect(result.current.data).toEqual(["a"])
    expect(result.current.error).toBeNull()
    expect(result.current.atualizadoEm).toEqual(expect.any(Number))
  })

  it("com dado na tela, é a recarga de sempre (gira o Atualizar, a lista fica)", async () => {
    const { fetcher, resolverProxima } = fetcherControlado<string[]>()
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))
    await resolverProxima(["a"])
    await waitFor(() => expect(result.current.data).toEqual(["a"]))

    act(() => { result.current.recarregarEmFundo() })
    expect(result.current.refreshing).toBe(true)
    expect(result.current.firstLoad).toBe(false)
    expect(result.current.data).toEqual(["a"])
    await resolverProxima(["a", "b"])
    await waitFor(() => expect(result.current.data).toEqual(["a", "b"]))
    expect(result.current.refreshing).toBe(false)
  })

  it("o `refetch` do \"Tentar de novo\" segue mostrando o skeleton, e ignora o evento do clique", async () => {
    const fetcher = fetcherEmFila<string[]>({ error: { message: "caiu" } }, { error: { message: "caiu" } })
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))
    await waitFor(() => expect(result.current.error).toBe("caiu"))

    // Passado direto ao onClick, o refetch recebe o evento: ele não pode virar
    // a recarga de fundo.
    const refetch = result.current.refetch as unknown as (evento: unknown) => Promise<unknown>
    act(() => { refetch({ type: "click" }) })
    expect(result.current.firstLoad).toBe(true)
    await waitFor(() => expect(result.current.firstLoad).toBe(false))
    expect(result.current.error).toBe("caiu")
  })

  it("recarregarEmFundo e refetch têm identidade estável entre renders", async () => {
    const fetcher = fetcherEmFila<string[]>({ data: ["a"] })
    const { result, rerender } = renderHook(() => useFetchData(fetcher, "erro"))
    await waitFor(() => expect(result.current.data).toEqual(["a"]))
    const { refetch, recarregarEmFundo } = result.current
    rerender()
    expect(result.current.refetch).toBe(refetch)
    expect(result.current.recarregarEmFundo).toBe(recarregarEmFundo)
  })
})

describe("useFetchData — sessão, ativo e setData", () => {
  it("sessão não autenticada desliga o skeleton sem buscar nada", async () => {
    sessao.status = "unauthenticated"
    const fetcher = vi.fn(async () => ({ data: 1 }))
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))
    await waitFor(() => expect(result.current.firstLoad).toBe(false))
    expect(fetcher).not.toHaveBeenCalled()
  })

  it("sessão ainda carregando: espera, com o skeleton", () => {
    sessao.status = "loading"
    const fetcher = vi.fn(async () => ({ data: 1 }))
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))
    expect(result.current.firstLoad).toBe(true)
    expect(fetcher).not.toHaveBeenCalled()
  })

  it("ativo=false não busca; ligar carrega; desligar descarta o que estava em voo e zera a tela", async () => {
    const { fetcher, resolverProxima } = fetcherControlado<string>()
    const { result, rerender } = renderHook(
      ({ ativo }: { ativo: boolean }) => useFetchData(fetcher, "erro", [], 0, { ativo }),
      { initialProps: { ativo: false } },
    )
    expect(fetcher).not.toHaveBeenCalled()

    rerender({ ativo: true })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
    await resolverProxima("primeira")
    expect(result.current.data).toBe("primeira")

    act(() => { result.current.refetch() })
    rerender({ ativo: false })
    await resolverProxima("tarde demais")
    expect(result.current.data).toBeNull()
    expect(result.current.atualizadoEm).toBeNull()
    expect(result.current.firstLoad).toBe(true)
    expect(result.current.refreshing).toBe(false)
  })

  it("setData troca o dado sem buscar e sem virar 'resposta aceita'", async () => {
    const { fetcher, resolverProxima } = fetcherControlado<string[]>()
    const { result } = renderHook(() => useFetchData(fetcher, "erro"))
    await resolverProxima(["a"])
    await waitFor(() => expect(result.current.data).toEqual(["a"]))
    const carimbo = result.current.atualizadoEm

    act(() => { result.current.setData(anterior => [...(anterior ?? []), "b"]) })
    expect(result.current.data).toEqual(["a", "b"])
    expect(result.current.atualizadoEm).toBe(carimbo)
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
})
