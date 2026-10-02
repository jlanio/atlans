import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook } from "@testing-library/react"

// A URL é dublada por um `URLSearchParams` mutável: o teste controla o que
// `useSearchParams` devolve e observa o que `router.replace` recebe.
const url = { sp: new URLSearchParams(""), pathname: "/projects" }
const replace = vi.fn()
const push = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
}))

import { useProjetosUrl } from "@/app/components/projects/use-projetos-url"

beforeEach(() => {
  replace.mockReset()
  push.mockReset()
  url.sp = new URLSearchParams("")
})
afterEach(() => vi.restoreAllMocks())

const ultimaUrl = () => replace.mock.calls.at(-1)![0] as string

describe("useProjetosUrl", () => {
  it("lê o estado da query string com defaults", () => {
    url.sp = new URLSearchParams("filtro=falha&q=sicar")
    const { result } = renderHook(() => useProjetosUrl())
    expect(result.current.estado).toEqual({ q: "sicar", filtro: "falha", ordem: "nome" })
  })

  it("grava só o que difere do padrão, com replace (não push), sem scroll, na mesma rota", () => {
    const { result } = renderHook(() => useProjetosUrl())
    act(() => result.current.atualizar({ filtro: "agendados" }))
    expect(replace).toHaveBeenCalledWith("/projects?filtro=agendados", { scroll: false })
    expect(push).not.toHaveBeenCalled()
  })

  it("voltar tudo ao padrão deixa a URL limpa (sem '?')", () => {
    url.sp = new URLSearchParams("filtro=falha")
    const { result } = renderHook(() => useProjetosUrl())
    act(() => result.current.atualizar({ filtro: "todos" }))
    expect(ultimaUrl()).toBe("/projects")
  })

  it("duas escritas seguidas, antes de a URL refletir a primeira, se acumulam", () => {
    const { result } = renderHook(() => useProjetosUrl())
    act(() => result.current.atualizar({ filtro: "falha" }))
    // A URL ainda é a antiga (o router não respondeu): a tecla na busca
    // parte do que foi escrito, não do que está na barra.
    act(() => result.current.atualizar({ q: "sic" }))
    expect(ultimaUrl()).toBe("/projects?q=sic&filtro=falha")
  })

  it("limpar filtros zera busca e chip, mas mantém a ordenação", () => {
    url.sp = new URLSearchParams("q=x&filtro=pausado&ordem=alterado")
    const { result } = renderHook(() => useProjetosUrl())
    act(() => result.current.limparFiltros())
    expect(ultimaUrl()).toBe("/projects?ordem=alterado")
  })

  it("limpar sem nada ativo não escreve nada", () => {
    url.sp = new URLSearchParams("ordem=execucao")
    const { result } = renderHook(() => useProjetosUrl())
    act(() => result.current.limparFiltros())
    expect(replace).not.toHaveBeenCalled()
  })
})
