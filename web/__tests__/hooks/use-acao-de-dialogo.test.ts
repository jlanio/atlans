import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, renderHook } from "@testing-library/react"

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

import { useAcaoDeDialogo, type OpcoesDaAcao } from "@/app/hooks/useAcaoDeDialogo"

beforeEach(() => vi.clearAllMocks())

/** Uma ação que só termina quando o teste manda. */
function lenta<T>() {
  let resolver!: (valor: T) => void
  const fn = vi.fn(() => new Promise<T>(res => { resolver = res }))
  return { fn, resolver: (valor: T) => resolver(valor) }
}

describe("useAcaoDeDialogo", () => {
  it("chamar de novo durante a ação devolve a MESMA ação, sem chamar o serviço outra vez", async () => {
    const { fn, resolver } = lenta<{ data: string }>()
    const { result } = renderHook(() => useAcaoDeDialogo(fn, { sucesso: "ok", erro: () => "erro" }))

    let primeira!: Promise<void>, segunda!: Promise<void>
    act(() => { primeira = result.current.executar(); segunda = result.current.executar() })
    expect(fn).toHaveBeenCalledTimes(1)
    expect(segunda).toBe(primeira)
    expect(result.current.executando).toBe(true)

    await act(async () => { resolver({ data: "x" }); await primeira })
    expect(result.current.executando).toBe(false)
    expect(toast.success).toHaveBeenCalledTimes(1)
  })

  it("sucesso: toast, fecha e só então `aoConcluir`, com o que o servidor devolveu", async () => {
    const aoConcluir = vi.fn()
    const { result } = renderHook(() => useAcaoDeDialogo(
      async () => ({ data: { n: 3 } }),
      { sucesso: d => ["Feito", `${d.n} itens`], erro: () => "erro", aoConcluir },
    ))
    act(() => { result.current.setAberto(true) })
    await act(async () => { await result.current.executar() })

    expect(toast.success).toHaveBeenCalledWith("Feito", "3 itens")
    expect(result.current.aberto).toBe(false)
    expect(aoConcluir).toHaveBeenCalledWith({ n: 3 })
  })

  it("falha: toast com a mensagem do servidor, o diálogo fica aberto e `aoConcluir` não roda", async () => {
    const aoConcluir = vi.fn()
    const { result } = renderHook(() => useAcaoDeDialogo(
      async () => ({ error: { name: "AxiosError", message: "sem permissão" } }),
      { sucesso: "ok", erro: m => ["Não deu", m], aoConcluir },
    ))
    act(() => { result.current.setAberto(true) })
    await act(async () => { await result.current.executar() })

    expect(toast.error).toHaveBeenCalledWith("Não deu", "sem permissão")
    expect(result.current.aberto).toBe(true)
    expect(aoConcluir).not.toHaveBeenCalled()
  })

  it("`erro` que devolve null é tratado na tela: nenhum toast", async () => {
    const { result } = renderHook(() => useAcaoDeDialogo(
      async () => ({ error: { name: "AxiosError", message: "conflito", code: "workspace_policy_conflict" } }),
      { sucesso: "ok", erro: () => null },
    ))
    await act(async () => { await result.current.executar() })
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("ação que LANÇA vira o toast de erro com a mensagem da exceção", async () => {
    const { result } = renderHook(() => useAcaoDeDialogo(
      async () => { throw new Error("Falha ao remover workspace.") },
      { sucesso: "ok", erro: m => m ?? "reserva" },
    ))
    await act(async () => { await result.current.executar() })
    expect(toast.error).toHaveBeenCalledWith("Falha ao remover workspace.")
  })

  it("fechar no meio da ação é ignorado", async () => {
    const { fn, resolver } = lenta<{ data: null }>()
    const { result } = renderHook(() => useAcaoDeDialogo(fn, { sucesso: null, erro: () => "erro" }))
    act(() => { result.current.setAberto(true) })

    let rodada!: Promise<void>
    act(() => { rodada = result.current.executar() })
    act(() => { result.current.setAberto(false) })
    expect(result.current.aberto).toBe(true)

    await act(async () => { resolver({ data: null }); await rodada })
    expect(result.current.aberto).toBe(false)
  })

  it("vale o que estava na tela quando se CONFIRMOU, não o que mudou durante a espera", async () => {
    const { fn, resolver } = lenta<{ data: null }>()
    const { result, rerender } = renderHook(
      (opcoes: OpcoesDaAcao<null>) => useAcaoDeDialogo(fn, opcoes),
      { initialProps: { sucesso: "Role alterado para admin.", erro: () => "erro" } },
    )
    let rodada!: Promise<void>
    act(() => { rodada = result.current.executar() })
    rerender({ sucesso: "Role alterado para usuário.", erro: () => "erro" })

    await act(async () => { resolver({ data: null }); await rodada })
    expect(toast.success).toHaveBeenCalledWith("Role alterado para admin.")
  })
})
