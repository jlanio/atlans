import { lazy } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { ExtensaoDoWeb, PropsDoEnvoltorioDoPainel } from "@/extensoes"
import type { IPainelDoModelo } from "@/service/types"

/**
 * A seção que troca o modelo do assistente, no núcleo: o modelo em uso, o
 * catálogo e o salvar. O que uma extensão soma a ela (a conta dos planos, por
 * exemplo) tem testes na pasta da extensão; aqui, o núcleo sozinho e o encaixe.
 *
 * O que se protege:
 *
 * 1. **Escolher não salva.** Salvar ao passar o mouse numa lista trocaria o
 *    modelo de produção.
 * 2. **Preço desconhecido não vira zero.** Zero lê como «de graça».
 * 3. **Provedor fora do ar não derruba a tela**: o admin ainda vê o que está
 *    em uso e pode voltar ao padrão.
 * 4. **O encaixe**: um envoltório de extensão cerca o seletor, sabe o que foi
 *    escolhido e divide com o núcleo o «salvando».
 */

const svc = vi.hoisted(() => ({ trocarModelo: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))
vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}))
// O núcleo sozinho, como na distribuição livre; um teste pendura uma extensão
// de mentira.
const registro = vi.hoisted(() => ({ EXTENSOES: [] as ExtensaoDoWeb[] }))
vi.mock("@/extensoes", async (original) => ({ ...(await original<typeof import("@/extensoes")>()), EXTENSOES: registro.EXTENSOES }))

import { ModeloDoAssistente } from "@/app/components/admin/settings/modelo-do-assistente"

const ok = <T,>(data: T) => ({ success: true, status: 200, data })

const CATALOGO = [
  { id: "a/barato", nome: "Barato", entrada_por_milhao: 1, saida_por_milhao: 5, contexto: 100000 },
  { id: "a/caro", nome: "Caro", entrada_por_milhao: 15, saida_por_milhao: 75, contexto: 200000 },
  { id: "a/sem-preco", nome: "Sem preço", entrada_por_milhao: null, saida_por_milhao: null, contexto: null },
]

/** O painel como o servidor o manda sem extensão nenhuma. */
function painel(over: Partial<IPainelDoModelo> = {}): IPainelDoModelo {
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
    render(<ModeloDoAssistente painel={painel()} onTrocado={vi.fn()} />)

    expect(screen.getAllByRole("option")).toHaveLength(3)
    expect(screen.getByText("preço não informado")).toBeTruthy()
    expect(screen.queryByText(/US\$ 0,00/)).toBeNull()
  })

  it("filtra por nome ou fornecedor", () => {
    render(<ModeloDoAssistente painel={painel()} onTrocado={vi.fn()} />)

    fireEvent.change(screen.getByPlaceholderText(/filtrar/), { target: { value: "caro" } })
    expect(screen.getAllByRole("option").map(o => o.textContent)).toEqual([expect.stringContaining("a/caro")])
  })

  it("escolher não salva", () => {
    render(<ModeloDoAssistente painel={painel()} onTrocado={vi.fn()} />)

    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))

    expect(screen.getByText(/Vai passar para a\/caro/)).toBeTruthy()
    expect(svc.trocarModelo).not.toHaveBeenCalled()
  })

  it("salvar troca o modelo e avisa o pai", async () => {
    svc.trocarModelo.mockResolvedValue(ok(painel()))
    const aoTrocar = vi.fn()
    render(<ModeloDoAssistente painel={painel()} onTrocado={aoTrocar} />)

    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))
    fireEvent.click(screen.getByRole("button", { name: /Salvar modelo/ }))

    await waitFor(() => expect(svc.trocarModelo).toHaveBeenCalledWith("a/caro"))
    await waitFor(() => expect(aoTrocar).toHaveBeenCalled())
  })

  it("sem mudança, salvar fica desabilitado", () => {
    render(<ModeloDoAssistente painel={painel()} onTrocado={vi.fn()} />)
    const botao = screen.getByRole("button", { name: /Salvar modelo/ }) as HTMLButtonElement
    expect(botao.disabled).toBe(true)
    expect(screen.getByText(/já é o modelo em uso/)).toBeTruthy()
  })

  it("«voltar ao padrão» só existe quando alguém já definiu um modelo aqui", () => {
    const { rerender } = render(<ModeloDoAssistente painel={painel()} onTrocado={vi.fn()} />)
    expect(screen.queryByRole("button", { name: /Voltar ao padrão/ })).toBeNull()

    rerender(<ModeloDoAssistente painel={painel({
      atual: { modelo: "a/caro", origem: "banco", definido_por: "jose",
               definido_em: "2026-09-21T12:00:00", padrao_do_ambiente: "a/barato" },
    })} onTrocado={vi.fn()} />)

    expect(screen.getByRole("button", { name: /Voltar ao padrão/ })).toBeTruthy()
    expect(screen.getByText(/por jose/)).toBeTruthy()
  })

  it("provedor fora do ar não derruba a tela", () => {
    // Sem catálogo o admin ainda precisa ver o que está em uso e poder voltar
    // ao padrão — esconder tudo trancaria a única saída.
    render(<ModeloDoAssistente painel={painel({
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
  /** Um envoltório de mentira que expõe o que recebeu. */
  const recebido: { atual: PropsDoEnvoltorioDoPainel | null } = { atual: null }
  function Envoltorio(props: PropsDoEnvoltorioDoPainel) {
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
    render(<ModeloDoAssistente painel={p} onTrocado={vi.fn()} />)

    const envoltorio = screen.getByTestId("envoltorio")
    expect(within(envoltorio).getByRole("listbox")).toBeTruthy()
    expect(envoltorio.dataset.escolhido).toBe("a/barato")
    expect(recebido.atual?.painel).toBe(p)

    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))
    expect(screen.getByTestId("envoltorio").dataset.escolhido).toBe("a/caro")
  })

  it("uma gravação da extensão trava os botões do núcleo", () => {
    registro.EXTENSOES.push({ nome: "teste", painelDoModelo: { Envoltorio } })
    render(<ModeloDoAssistente painel={painel()} onTrocado={vi.fn()} />)
    fireEvent.click(screen.getByRole("option", { name: /a\/caro/ }))
    expect((screen.getByRole("button", { name: /Salvar modelo/ }) as HTMLButtonElement).disabled).toBe(false)

    fireEvent.click(screen.getByRole("button", { name: "ocupar" }))

    expect((screen.getByRole("button", { name: /Salvar modelo/ }) as HTMLButtonElement).disabled).toBe(true)
    expect(recebido.atual?.ocupado).toBe(true)
  })

  it("um envoltório que não carrega não derruba a tela: o seletor e o «Voltar ao padrão» ficam", async () => {
    // O pedaço carregado sob demanda pode não chegar (rede, ou um deploy no
    // meio, que apaga os pedaços antigos). Sem o limite, o erro subia até a
    // raiz e o app inteiro desmontava — com a saída de emergência junto.
    const erro = vi.spyOn(console, "error").mockImplementation(() => {})
    const Quebrado = lazy<typeof Envoltorio>(() => Promise.reject(new Error("ChunkLoadError: Loading chunk 123 failed.")))
    registro.EXTENSOES.push({ nome: "teste", painelDoModelo: { Envoltorio: Quebrado } })
    render(<ModeloDoAssistente painel={painel({
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
    render(<ModeloDoAssistente painel={painel()} onTrocado={onTrocado} />)

    act(() => recebido.atual?.aoTrocar())
    expect(onTrocado).toHaveBeenCalledTimes(1)
  })
})
