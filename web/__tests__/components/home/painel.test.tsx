import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"

vi.mock("@/app/hooks/useResizablePanel", () => ({
  useResizablePanel: () => ({ width: 420, isResizing: false, resizeHandleProps: {} }),
}))
vi.mock("@/hooks/use-mobile", () => ({ useIsMobile: () => false }))
vi.mock("next/link", () => ({
  default: ({ href, children, ...p }: { href: string; children: React.ReactNode }) => <a href={href} {...p}>{children}</a>,
}))

import Painel from "@/app/components/home/assistente/painel"
import { LanguageProvider } from "@/context/IdiomaContext"
import { useHomeStore } from "@/app/stores/homeStore"
import type { IAssistantState } from "@/service/types"
import type { AssistantBlock, AssistantTurn } from "@/app/components/home/assistente/quadros"

const ATIVO: IAssistantState = { ativo: true, cota: { gasto: 0, teto: 1_000_000, reabre_em_segundos: null } }
const turno = (blocos: AssistantBlock[]): AssistantTurn => ({ id: "t1", papel: "assistant", blocos })

type PanelProps = React.ComponentProps<typeof Painel>
function montar(props: Partial<PanelProps> = {}): PanelProps {
  const p: PanelProps = {
    estado: ATIVO, turnos: [], correndo: false,
    enviar: vi.fn(), confirmar: vi.fn(), parar: vi.fn(), ...props,
  }
  render(<Painel {...p} />)
  return p
}

beforeEach(() => {
  cleanup()
  useHomeStore.setState({ painel: "aberto", conversaId: null, decididos: {}, expirados: {}, rascunho: "" })
})

const confirmacao = (extra: Record<string, unknown> = {}) => ({
  tipo: "confirmacao" as const,
  confirmacao: {
    tool_use_id: "tu1", token: "TOK",
    acao: { tool: "delete_drive_file", argumentos: { file_id: "a3f9c2e1", file_name: "municipios.shp" }, ...extra },
  },
})

describe("a alça de largura do painel", () => {
  const alca = () => document.querySelector<HTMLElement>(".group\\/alca")!

  it("em português, o rótulo de sempre", () => {
    montar()
    expect(alca().getAttribute("aria-label")).toBe("Redimensionar painel")
    expect(alca().getAttribute("title")).toBe("Arraste para redimensionar · duplo clique para restaurar")
  })

  it("em inglês, no idioma da Home", () => {
    render(
      <LanguageProvider inicial={{ idioma: "en", detectado: "en", escolhido: "en" }}>
        <Painel estado={ATIVO} turnos={[]} correndo={false} enviar={vi.fn()} confirmar={vi.fn()} parar={vi.fn()} />
      </LanguageProvider>,
    )
    expect(alca().getAttribute("aria-label")).toBe("Resize panel")
    expect(alca().getAttribute("title")).toBe("Drag to resize · double-click to restore")
  })
})

describe("Painel do assistente", () => {
  it("mostra o donut da cota sob o campo do composer", () => {
    montar({ estado: { ativo: true, cota: { gasto: 450_000, teto: 1_500_000, reabre_em_segundos: 3_600 } } })
    expect(screen.getByTestId("uso-da-cota").textContent).toBe("30%")
  })

  it("confirma: POSTa (tool_use_id, token, decisão) e NUNCA os argumentos", () => {
    const confirmar = vi.fn()
    montar({
      confirmar,
      turnos: [turno([{
        tipo: "confirmacao",
        confirmacao: { tool_use_id: "tu1", token: "TOK", acao: { tool: "delete_schedule", argumentos: { job_id: "SEGREDO" }, alvo: "X" } },
      }])],
    })
    fireEvent.click(screen.getByRole("button", { name: /confirmar/i }))
    expect(confirmar).toHaveBeenCalledWith("tu1", "TOK", "confirmar")
    expect(confirmar.mock.calls[0]).toHaveLength(3) // only id/token/decision
    expect(JSON.stringify(confirmar.mock.calls[0])).not.toContain("SEGREDO")
  })

  it("recusar também só manda a decisão", () => {
    const confirmar = vi.fn()
    montar({
      confirmar,
      turnos: [turno([{
        tipo: "confirmacao",
        confirmacao: { tool_use_id: "tu2", token: "T2", acao: { tool: "run_workflow", argumentos: { x: 1 } } },
      }])],
    })
    fireEvent.click(screen.getByRole("button", { name: /recusar/i }))
    expect(confirmar).toHaveBeenCalledWith("tu2", "T2", "recusar")
  })

  it("fluxo NÃO vira link nenhum — a Home não leva ao editor", () => {
    // The `next/link` double (top of the file) stays registered ON PURPOSE: it is
    // what gives this absence something to catch. Without the double, "there is no link"
    // would pass by accident, and putting the `<Link>` back on the badge would break nothing.
    montar({ turnos: [turno([{ tipo: "fluxo", fluxo: { workflow_id: "w9", nome: "Análise" } }])] })
    expect(document.querySelector('a[href^="/workflow/"]')).toBeNull()
    expect(screen.queryByText(/análise/i)).toBeNull() // not even the workflow name shows up
  })

  it("artefato da conversa vira badge, e clicar o põe no globo", () => {
    montar({ turnos: [turno([{ tipo: "camada", camada: { artifact_id: "a7", nome: "Talhões", available: true } }])] })
    // The accessible name comes from the button's CONTENT; the `title` is just the hover hint.
    const badge = screen.getByRole("button", { name: /talhões/i })
    expect(badge.getAttribute("title")).toBe("Mostrar Talhões no globo")
    fireEvent.click(badge)
    // The store queue is the channel; what calls `adicionar` is the HomeView.
    expect(useHomeStore.getState().pedidosDeCamada).toEqual([{ artifactId: "a7", nome: "Talhões" }])
  })

  it("artefato sem prévia não é botão — e diz por quê", () => {
    // A button with no action would promise a click that does not happen, and the screen
    // reader would still announce it as actionable.
    montar({ turnos: [turno([{ tipo: "camada", camada: { artifact_id: "a8", nome: "Malha", available: false, hint: "fica no executor" } }])] })
    expect(screen.queryByRole("button", { name: /malha/i })).toBeNull()
    expect(screen.getByTitle("fica no executor")).toBeTruthy()
  })

  it("camada disponível vira o cartão 'no globo'", () => {
    montar({ turnos: [turno([{ tipo: "camada", camada: { artifact_id: "a1", nome: "Focos", available: true } }])] })
    expect(screen.getByText(/Focos no globo/i)).toBeTruthy()
  })

  it("enviar dispara o callback com o texto", () => {
    const enviar = vi.fn()
    montar({ enviar })
    const campo = screen.getByLabelText(/Mensagem para o assistente/i)
    fireEvent.change(campo, { target: { value: "buffer de 500m" } })
    fireEvent.submit(campo.closest("form")!)
    expect(enviar).toHaveBeenCalledWith("buffer de 500m")
  })

  it("recolher manda o painel para a barra", () => {
    montar()
    fireEvent.click(screen.getByRole("button", { name: /recolher/i }))
    expect(useHomeStore.getState().painel).toBe("barra")
  })

  it("o cartão diz EM QUE a ação mexe, e não só o id cru", () => {
    montar({ turnos: [turno([confirmacao()])] })
    expect(screen.getByText("municipios.shp")).toBeTruthy()
    expect(screen.getByText(/vale por 15 minutos/i)).toBeTruthy()
  })

  it("a confirmação pendente é anunciada para leitor de tela", () => {
    montar({ turnos: [turno([confirmacao()])] })
    const anuncios = screen.getAllByRole("status").map((e) => e.textContent ?? "")
    expect(anuncios.some((t) => /confirmação pendente/i.test(t))).toBe(true)
  })

  it("a decisão sobrevive a recolher e reabrir o painel", () => {
    const props = montar({ confirmar: vi.fn(), turnos: [turno([confirmacao()])] })
    fireEvent.click(screen.getByRole("button", { name: /confirmar/i }))
    expect(useHomeStore.getState().decididos["tu1"]).toBe(true)

    cleanup() // collapsing UNMOUNTS the panel; the turns (with the token) survive
    render(<Painel {...props} />)
    expect(screen.getByRole("button", { name: /confirmar/i }).hasAttribute("disabled")).toBe(true)
    expect(screen.getByText("Decidido.")).toBeTruthy()
  })

  it("falha de transporte destrava o cartão — a ação não aconteceu", async () => {
    const confirmar = vi.fn().mockResolvedValue("falhou")
    montar({ confirmar, turnos: [turno([confirmacao()])] })
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /confirmar/i }))
    })
    expect(useHomeStore.getState().decididos["tu1"]).toBeUndefined()
    expect(screen.getByRole("button", { name: /confirmar/i }).hasAttribute("disabled")).toBe(false)
  })

  it("409 NÃO destrava: a chave já foi consumida, e o cartão explica isso", async () => {
    // Unlocking here offered a click that would only render another 409 — and also
    // suggested the action had not happened, when it may have happened.
    const confirmar = vi.fn().mockResolvedValue("expirada")
    montar({ confirmar, turnos: [turno([confirmacao()])] })
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /confirmar/i }))
    })
    expect(useHomeStore.getState().decididos["tu1"]).toBe(true)
    expect(screen.getByRole("button", { name: /confirmar/i }).hasAttribute("disabled")).toBe(true)
    expect(screen.getByText(/já foi decidida ou expirou/i)).toBeTruthy()
    expect(screen.queryByText("Decidido.")).toBeNull()
  })

  it("o rascunho vive na store: recolher para a barra não pode apagá-lo", () => {
    montar()
    const campo = screen.getByLabelText(/Mensagem para o assistente/i)
    fireEvent.change(campo, { target: { value: "buffer de 500 m" } })
    expect(useHomeStore.getState().rascunho).toBe("buffer de 500 m")

    cleanup() // it is what Ctrl+I (or the button) does with this panel
    expect(useHomeStore.getState().rascunho).toBe("buffer de 500 m")
  })

  it("a conversa vazia é a da Home: fala do globo, não de canvas", () => {
    montar({ turnos: [] })
    expect(screen.getByText(/o que você quer saber/i)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/canvas/i)
  })
})

const respostas = (opcoes: string[]): AssistantBlock => ({ tipo: "respostas_rapidas", opcoes })

describe("Painel — respostas rápidas e o item pendente", () => {
  it("os chips do último turno enviam a frase escolhida", () => {
    const enviar = vi.fn()
    montar({
      enviar,
      turnos: [turno([{ tipo: "texto", texto: "Achei 128 focos." }, respostas(["Só os últimos 7 dias", "Cruzar com o CAR"])])],
    })
    const grupo = screen.getByRole("group", { name: /respostas rápidas/i })
    expect(grupo.querySelectorAll("button").length).toBe(2)
    fireEvent.click(screen.getByRole("button", { name: "Cruzar com o CAR" }))
    expect(enviar).toHaveBeenCalledWith("Cruzar com o CAR")
  })

  it("chips de um turno anterior não aparecem — valem só para aquela vez", () => {
    montar({
      turnos: [
        { id: "a1", papel: "assistant", blocos: [respostas(["Agendar"])] },
        { id: "u2", papel: "user", texto: "agenda", blocos: [] },
        { id: "a2", papel: "assistant", blocos: [{ tipo: "texto", texto: "Agendado." }] },
      ],
    })
    expect(screen.queryByRole("group", { name: /respostas rápidas/i })).toBeNull()
    expect(screen.queryByRole("button", { name: "Agendar" })).toBeNull()
  })

  it("durante o stream não há chips: o enviar do hook voltaria em silêncio", () => {
    montar({ correndo: true, turnos: [turno([{ tipo: "texto", texto: "…" }, respostas(["Agendar"])])] })
    expect(screen.queryByRole("group", { name: /respostas rápidas/i })).toBeNull()
  })

  it("o item pendente usa a marca animada, não as barras do editor", () => {
    const { container } = render(
      <Painel estado={ATIVO} turnos={[turno([])]} correndo enviar={vi.fn()} confirmar={vi.fn()} parar={vi.fn()} />,
    )
    expect(screen.getByText("Trabalhando…")).toBeTruthy()
    expect(container.querySelector("svg.home-marca-anim")).toBeTruthy()
    expect(container.querySelector("svg.exec-activity")).toBeNull()
  })
})

describe("Painel — o movimento", () => {
  it("entra da direita (a classe da animação) e o botão de enviar afunda", () => {
    montar()
    expect(screen.getByLabelText("Assistente").classList.contains("home-painel-entra")).toBe(true)
    expect(screen.getByRole("button", { name: /^enviar$/i }).className).toContain("active:scale-90")
  })

  it("o parágrafo que está sendo escrito termina no cursor", () => {
    const { container } = render(
      <Painel estado={ATIVO} turnos={[turno([{ tipo: "texto", texto: "Achei 1 2" }])]} correndo enviar={vi.fn()} confirmar={vi.fn()} parar={vi.fn()} />,
    )
    expect(container.querySelector("p > span.home-caret")).toBeTruthy()
  })
})

describe("Painel — os anexos (o recurso não some ao recolher em painel)", () => {
  beforeEach(() => useHomeStore.setState({ painel: "aberto", rascunho: "", anexos: [], arrastandoArquivo: false }))

  const pronto = (nome: string, id = nome) =>
    ({ id, nome, bytes: 2048, estado: "pronto" as const })

  it("o painel mostra os mesmos chips da barra e leva a referência ao enviar", () => {
    useHomeStore.setState({ anexos: [pronto("bacias.gpkg")] })
    const enviar = vi.fn()
    montar({ enviar })

    expect(screen.getByText("bacias.gpkg")).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: /^enviar$/i }))
    expect(enviar.mock.calls[0][0]).toContain("bacias.gpkg")
    expect(useHomeStore.getState().anexos).toHaveLength(0)
  })

  it("o convite de soltura aparece no composer do painel durante o arraste", () => {
    useHomeStore.setState({ arrastandoArquivo: true })
    montar()
    expect(screen.getByTestId("convite-de-soltura")).toBeTruthy()
  })
})
