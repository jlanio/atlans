import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook } from "@testing-library/react"

// The URL is doubled by a mutable `URLSearchParams`: the test controls what
// `useSearchParams` returns and observes what `router.replace` receives.
const url = { sp: new URLSearchParams(""), pathname: "/observability" }
const replace = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
}))

import { useHistoricoUrl } from "@/app/components/observability/use-historico-url"

beforeEach(() => {
  replace.mockReset()
  url.sp = new URLSearchParams("")
})
afterEach(() => vi.restoreAllMocks())

const ultimaUrl = () => replace.mock.calls.at(-1)![0] as string

describe("useHistoricoUrl", () => {
  it("lê o estado da query string com defaults", () => {
    url.sp = new URLSearchParams("periodo=7&status=failed&execucao=run-1")
    const { result } = renderHook(() => useHistoricoUrl())
    expect(result.current.estado.periodo).toBe(7)
    expect(result.current.estado.status).toBe("failed")
    expect(result.current.estado.execucao).toBe("run-1")
    expect(result.current.estado.visao).toBe("execucoes")
  })

  it("grava só o que difere do padrão, sem scroll, na mesma rota", () => {
    const { result } = renderHook(() => useHistoricoUrl())
    act(() => result.current.atualizar({ periodo: 90 }))
    expect(replace).toHaveBeenCalledWith("/observability?periodo=90", { scroll: false })
  })

  it("voltar tudo ao padrão deixa a URL limpa (sem '?')", () => {
    url.sp = new URLSearchParams("periodo=7")
    const { result } = renderHook(() => useHistoricoUrl())
    act(() => result.current.atualizar({ periodo: 30 }))
    expect(ultimaUrl()).toBe("/observability")
  })

  it("mudar período ou filtro mantém a execução aberta", () => {
    url.sp = new URLSearchParams("execucao=run-1")
    const { result } = renderHook(() => useHistoricoUrl())
    act(() => result.current.atualizar({ periodo: 7 }))
    expect(ultimaUrl()).toContain("execucao=run-1")
    act(() => result.current.atualizar({ status: "failed" }))
    expect(ultimaUrl()).toContain("execucao=run-1")
    expect(ultimaUrl()).toContain("status=failed")
  })

  it("mudar de visão fecha a execução", () => {
    url.sp = new URLSearchParams("execucao=run-1")
    const { result } = renderHook(() => useHistoricoUrl())
    act(() => result.current.atualizar({ visao: "workflows" }))
    expect(ultimaUrl()).toBe("/observability?visao=workflows")
  })

  it("abrir e fechar execução", () => {
    url.sp = new URLSearchParams("periodo=7")
    const { result } = renderHook(() => useHistoricoUrl())
    act(() => result.current.abrirExecucao("run-9"))
    expect(ultimaUrl()).toBe("/observability?periodo=7&execucao=run-9")

    url.sp = new URLSearchParams("periodo=7&execucao=run-9")
    act(() => result.current.fecharExecucao())
    expect(ultimaUrl()).toBe("/observability?periodo=7")
  })

  it("fechar sem execução aberta não escreve nada", () => {
    const { result } = renderHook(() => useHistoricoUrl())
    act(() => result.current.fecharExecucao())
    expect(replace).not.toHaveBeenCalled()
  })

  it("duas escritas seguidas, antes de a URL refletir a primeira, se acumulam", () => {
    const { result } = renderHook(() => useHistoricoUrl())
    act(() => result.current.atualizar({ status: "failed" }))
    // The URL is still the old one (the router hasn't responded): the second
    // write starts from what was written, not from what's in the bar.
    act(() => result.current.atualizar({ workflow: "wf-1" }))
    expect(ultimaUrl()).toBe("/observability?status=failed&workflow=wf-1")
  })
})
