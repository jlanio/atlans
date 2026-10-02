/**
 * Os padrões do cliente de consultas são os das telas de HOJE: migrar uma tela
 * para o react-query não pode, por herança, fazê-la repetir falhas, reler no
 * foco, pausar sem rede ou guardar cache.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import {
  QueryClientProvider, focusManager, onlineManager, useMutation, useQuery, type QueryClient,
} from "@tanstack/react-query"
import type { ReactNode } from "react"
import { criarClienteDeConsultas } from "@/lib/consultas"

function embrulho(cliente: QueryClient) {
  return function Embrulho({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={cliente}>{children}</QueryClientProvider>
  }
}

function consultar(queryFn: () => Promise<unknown>, cliente = criarClienteDeConsultas()) {
  return renderHook(() => useQuery({ queryKey: ["x"], queryFn }), { wrapper: embrulho(cliente) })
}

afterEach(() => {
  onlineManager.setOnline(true)
  focusManager.setFocused(undefined)
})

describe("criarClienteDeConsultas", () => {
  it("uma leitura que falha não se repete: o erro aparece na hora", async () => {
    const queryFn = vi.fn().mockRejectedValue(new Error("caiu"))
    const { result } = consultar(queryFn)
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toBe("caiu")
    expect(queryFn).toHaveBeenCalledTimes(1)
  })

  it("sem rede declarada, a leitura sai assim mesmo e a falha vira erro, sem ficar pausada", async () => {
    onlineManager.setOnline(false)
    const queryFn = vi.fn().mockRejectedValue(new Error("Network Error"))
    const { result } = consultar(queryFn)
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.fetchStatus).toBe("idle")
    expect(queryFn).toHaveBeenCalledTimes(1)
  })

  it("não relê ao voltar o foco nem ao reconectar", async () => {
    const queryFn = vi.fn().mockResolvedValue(1)
    const { result } = consultar(queryFn)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    act(() => {
      focusManager.setFocused(false)
      focusManager.setFocused(true)
      onlineManager.setOnline(false)
      onlineManager.setOnline(true)
    })
    await act(async () => { await new Promise(r => setTimeout(r, 20)) })
    expect(queryFn).toHaveBeenCalledTimes(1)
  })

  it("sem cache: desmontar descarta o dado, e a montagem seguinte começa do zero", async () => {
    const cliente = criarClienteDeConsultas()
    const queryFn = vi.fn().mockResolvedValue(1)
    const primeira = consultar(queryFn, cliente)
    await waitFor(() => expect(primeira.result.current.isSuccess).toBe(true))

    primeira.unmount()
    await waitFor(() => expect(cliente.getQueryCache().getAll()).toHaveLength(0))

    const segunda = consultar(queryFn, cliente)
    expect(segunda.result.current.isPending).toBe(true)
    await waitFor(() => expect(segunda.result.current.isSuccess).toBe(true))
    expect(queryFn).toHaveBeenCalledTimes(2)
  })

  it("uma mutação sai mesmo sem rede declarada", async () => {
    onlineManager.setOnline(false)
    const mutationFn = vi.fn().mockResolvedValue("ok")
    const { result } = renderHook(() => useMutation({ mutationFn }), {
      wrapper: embrulho(criarClienteDeConsultas()),
    })
    act(() => { result.current.mutate() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mutationFn).toHaveBeenCalledTimes(1)
  })
})
