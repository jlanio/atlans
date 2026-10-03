import { lazy } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { ExtensaoDoWeb, PanelWrapperProps } from "@/extensoes"
import type { IModelPanel } from "@/service/types"

/**
 * The section that switches the assistant's model, in the core: the model in use, the
 * catalog and saving. What an extension adds to it (the plans' accounting, for
 * example) has tests in the extension's folder; here, the core alone and the slot.
 *
 * What is protected:
 *
 * 1. **Choosing does not save.** Saving on hovering over a list would switch the
 *    production model.
 * 2. **An unknown price does not become zero.** Zero reads as "free".
 * 3. **A provider being down does not bring the screen down**: the admin still sees what is
 *    in use and can go back to the default.
 * 4. **The slot**: an extension wrapper surrounds the selector, knows what was
 *    chosen and shares the "saving" state with the core.
 */

const svc = vi.hoisted(() => ({ trocarModelo: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))
vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}))
// The core alone, as in the free distribution; one test hangs a fake
// extension on it.
const registro = vi.hoisted(() => ({ EXTENSOES: [] as ExtensaoDoWeb[] }))
vi.mock("@/extensoes", async (original) => ({ ...(await original<typeof import("@/extensoes")>()), EXTENSOES: registro.EXTENSOES }))

import { AssistantModel } from "@/app/components/admin/settings/modelo-do-assistente"

const ok = <T,>(data: T) => ({ success: true, status: 200, data })

const CATALOGO = [
  { id: "a/barato", nome: "Barato", entrada_por_milhao: 1, saida_por_milhao: 5, contexto: 100000 },
  { id: "a/caro", nome: "Caro", entrada_por_milhao: 15, saida_por_milhao: 75, contexto: 200000 },
  { id: "a/sem-preco", nome: "Sem preço", entrada_por_milhao: null, saida_por_milhao: null, contexto: null },
]

/** The panel as the server sends it with no extension at all. */
function painel(over: Partial<IModelPanel> = {}): IModelPanel {
  return {
    atual: {
      modelo: "a/barato", origem: "ambiente",
      definido_por: null, definido_em: null, padrao_do_ambiente: "a/barato",
    },
    catalogo: CATALOGO,
    catalogo_indisponivel: null,
    ...over,
  }
}

afterEach(() => { cleanup(); vi.clearAllMocks(); registro.EXTENSOES.length = 0 })

describe("o seletor do núcleo", () => {
  it("lista o catálogo e mostra «preço não informado», nunca zero", () => {
    render(<AssistantModel painel={painel()} onTrocado={vi.fn()} />)

    expect(screen.getAllByRole("option")).toHaveLength(3)
    expect(screen.getByText("preço não informado")).toBeTruthy()
    expect(screen.queryByText(/US\$ 0,00/)).toBeNull()
  })

  it("filtra por nome ou fornecedor", () => {
    render(<AssistantModel painel={painel()} onTrocado={vi.fn()} />)

    fireEvent.change(screen.getByPlaceholderText(/filtrar/), { target: { value: "caro" } })
    expect(screen.getAllByRole("option").map(o => o.textContent)).toEqual([expect.stringContaining("a/caro")])
  })

  it("escolher não salva", () => {
    render(<AssistantModel painel={painel()} onTrocado={vi.fn()} />)

    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))

    expect(screen.getByText(/Vai passar para a\/caro/)).toBeTruthy()
    expect(svc.trocarModelo).not.toHaveBeenCalled()
  })

  it("salvar troca o modelo e avisa o pai", async () => {
    svc.trocarModelo.mockResolvedValue(ok(painel()))
    const aoTrocar = vi.fn()
    render(<AssistantModel painel={painel()} onTrocado={aoTrocar} />)

    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))
    fireEvent.click(screen.getByRole("button", { name: /Salvar modelo/ }))

    await waitFor(() => expect(svc.trocarModelo).toHaveBeenCalledWith("a/caro"))
    await waitFor(() => expect(aoTrocar).toHaveBeenCalled())
  })

  it("sem mudança, salvar fica desabilitado", () => {
    render(<AssistantModel painel={painel()} onTrocado={vi.fn()} />)
    const botao = screen.getByRole("button", { name: /Salvar modelo/ }) as HTMLButtonElement
    expect(botao.disabled).toBe(true)
    expect(screen.getByText(/já é o modelo em uso/)).toBeTruthy()
  })

  it("«voltar ao padrão» só existe quando alguém já definiu um modelo aqui", () => {
    const { rerender } = render(<AssistantModel painel={painel()} onTrocado={vi.fn()} />)
    expect(screen.queryByRole("button", { name: /Voltar ao padrão/ })).toBeNull()

    rerender(<AssistantModel painel={painel({
      atual: { modelo: "a/caro", origem: "banco", definido_por: "jose",
               definido_em: "2026-09-21T12:00:00", padrao_do_ambiente: "a/barato" },
    })} onTrocado={vi.fn()} />)

    expect(screen.getByRole("button", { name: /Voltar ao padrão/ })).toBeTruthy()
    expect(screen.getByText(/por jose/)).toBeTruthy()
  })

  it("provedor fora do ar não derruba a tela", () => {
    // Without a catalog the admin still needs to see what is in use and be able to go back
    // to the default — hiding everything would lock the only way out.
    render(<AssistantModel painel={painel({
      catalogo: [], catalogo_indisponivel: "ErroDoOpenRouter",
      atual: { modelo: "a/caro", origem: "banco", definido_por: "jose",
               definido_em: "2026-09-21T12:00:00", padrao_do_ambiente: "a/barato" },
    })} onTrocado={vi.fn()} />)

    expect(screen.getAllByRole("status").map(e => e.textContent ?? "").join(" "))
      .toContain("Não foi possível ler o catálogo")
    expect(screen.getByText("a/caro")).toBeTruthy()
    expect(screen.getByRole("button", { name: /Voltar ao padrão/ })).toBeTruthy()
    expect(screen.queryByRole("listbox")).toBeNull()
  })
})

describe("o encaixe das extensões", () => {
  /** A fake wrapper that exposes what it received. */
  const recebido: { atual: PanelWrapperProps | null } = { atual: null }
  function Envoltorio(props: PanelWrapperProps) {
    recebido.atual = props
    return (
      <section data-testid="envoltorio" data-escolhido={props.escolhido}>
        <p>antes do seletor</p>
        {props.children}
        <button type="button" onClick={() => props.aoOcupar(true)}>ocupar</button>
      </section>
    )
  }

  it("cerca o seletor, sabe o que foi escolhido e recebe o painel", () => {
    registro.EXTENSOES.push({ nome: "teste", painelDoModelo: { Envoltorio } })
    const p = painel()
    render(<AssistantModel painel={p} onTrocado={vi.fn()} />)

    const envoltorio = screen.getByTestId("envoltorio")
    expect(within(envoltorio).getByRole("listbox")).toBeTruthy()
    expect(envoltorio.dataset.escolhido).toBe("a/barato")
    expect(recebido.atual?.painel).toBe(p)

    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))
    expect(screen.getByTestId("envoltorio").dataset.escolhido).toBe("a/caro")
  })

  it("uma gravação da extensão trava os botões do núcleo", () => {
    registro.EXTENSOES.push({ nome: "teste", painelDoModelo: { Envoltorio } })
    render(<AssistantModel painel={painel()} onTrocado={vi.fn()} />)
    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))
    expect((screen.getByRole("button", { name: /Salvar modelo/ }) as HTMLButtonElement).disabled).toBe(false)

    fireEvent.click(screen.getByRole("button", { name: "ocupar" }))

    expect((screen.getByRole("button", { name: /Salvar modelo/ }) as HTMLButtonElement).disabled).toBe(true)
    expect(recebido.atual?.ocupado).toBe(true)
  })

  it("um envoltório que não carrega não derruba a tela: o seletor e o «Voltar ao padrão» ficam", async () => {
    // The chunk loaded on demand may not arrive (network, or a deploy in the
    // middle, which deletes the old chunks). Without the boundary, the error bubbled up to the
    // root and the whole app unmounted — with the emergency exit along with it.
    const erro = vi.spyOn(console, "error").mockImplementation(() => {})
    const Quebrado = lazy<typeof Envoltorio>(() => Promise.reject(new Error("ChunkLoadError: Loading chunk 123 failed.")))
    registro.EXTENSOES.push({ nome: "teste", painelDoModelo: { Envoltorio: Quebrado } })
    render(<AssistantModel painel={painel({
      atual: { modelo: "a/caro", origem: "banco", definido_por: "jose",
               definido_em: "2026-09-21T12:00:00", padrao_do_ambiente: "a/barato" },
    })} onTrocado={vi.fn()} />)

    await waitFor(() => expect(erro.mock.calls.some(c => String(c[0]).includes("«teste»"))).toBe(true))
    expect(screen.getByRole("listbox")).toBeTruthy()
    expect(screen.getByRole("button", { name: /Voltar ao padrão/ })).toBeTruthy()
    expect(screen.getByText(/Em uso agora/)).toBeTruthy()
    erro.mockRestore()
  })

  it("o `aoTrocar` da extensão é o recarregar da página", () => {
    registro.EXTENSOES.push({ nome: "teste", painelDoModelo: { Envoltorio } })
    const onTrocado = vi.fn()
    render(<AssistantModel painel={painel()} onTrocado={onTrocado} />)

    act(() => recebido.atual?.aoTrocar())
    expect(onTrocado).toHaveBeenCalledTimes(1)
  })
})
