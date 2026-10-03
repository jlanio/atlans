/**
 * `dadoOuAviso` — the single reading of the service's `IResponse` on the editor screens.
 *
 * The service never rejects (the failure comes back in `res.error`), so it's
 * here, and not in a `catch`, that the failure becomes a warning. And the return
 * value distinguishes "don't know" (`null`) from "empty" (the empty list the
 * server sent).
 */
import { describe, it, expect, vi, beforeEach } from "vitest"

const toast = vi.hoisted(() => ({ error: vi.fn() }))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

import { dadoOuAviso } from "@/lib/respostas"
import type { IResponse } from "@/service/types"

beforeEach(() => { toast.error.mockReset() })

describe("dadoOuAviso", () => {
  it("devolve o dado e não avisa nada", () => {
    const res: IResponse<number[]> = { status: 200, success: true, data: [1, 2] }
    expect(dadoOuAviso(res, "Erro ao carregar")).toEqual([1, 2])
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("a lista vazia do servidor é dado, não falha", () => {
    const res: IResponse<number[]> = { status: 200, success: true, data: [] }
    expect(dadoOuAviso(res, "Erro ao carregar")).toEqual([])
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("na falha, avisa com o título da tela e a mensagem do servidor — e devolve null", () => {
    const res: IResponse<number[]> = {
      status: 503, success: false, error: { name: "AxiosError", message: "Serviço indisponível." },
    }
    expect(dadoOuAviso(res, "Erro ao carregar execuções recentes")).toBeNull()
    expect(toast.error).toHaveBeenCalledWith("Erro ao carregar execuções recentes", "Serviço indisponível.")
  })
})
