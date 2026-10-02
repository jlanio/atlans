import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { AtencaoLista } from "@/app/components/observability/atencao-lista"
import type { ItemDeAtencao } from "@/app/components/observability/atencao"

// As dispensas vivem no localStorage (conveniência por navegador). Limpo entre
// os casos para um não herdar as dispensas do outro.
afterEach(() => {
  cleanup()
  try { localStorage.clear() } catch { /* jsdom sem storage: nada a limpar */ }
})

const itens: ItemDeAtencao[] = [
  {
    chave: "presa:run-1", tipo: "presa", nome: "Cadastro rural · lote 7",
    titulo: "Cadastro rural · lote 7 está em andamento há 2 h 14 min",
    detalhe: "Em geo-02 · a duração típica é 6 min",
    acao: { tipo: "abrir-execucao", runId: "run-1" }, rotuloDaAcao: "Abrir", assinatura: "run-1",
  },
  {
    chave: "falhas:wf-sicar", tipo: "falhas", nome: "Integração SICAR",
    titulo: "Integração SICAR falhou 28 vezes em 30 dias",
    detalhe: "Último erro: tempo esgotado · Timeout ao consultar o WFS do SICAR (30 s)",
    acao: { tipo: "filtrar-workflow", workflowHash: "wf-sicar", status: "failed" }, rotuloDaAcao: "Ver falhas", assinatura: "28",
  },
  {
    chave: "saturado:executor:geo-02", tipo: "saturado", nome: "geo-02",
    titulo: "geo-02 está no teto: 4 de 4 em execução",
    detalhe: "12 execuções na fila",
    acao: { tipo: "abrir-executor", agentHost: "executor:geo-02" }, rotuloDaAcao: "Ver executor", assinatura: "4:12",
  },
]

/** Botão de ação principal de um item (pelo título no aria-label), não o × de dispensar. */
const acaoDe = (regex: RegExp) => screen.getByRole("button", { name: regex })

describe("AtencaoLista", () => {
  it("lista os itens com o nome em destaque e a ação de cada um", () => {
    const onAcao = vi.fn()
    render(<AtencaoLista itens={itens} carregando={false} vazio="Nenhuma falha no período." onAcao={onAcao} />)
    expect(screen.getByRole("heading", { name: "Precisa de atenção" })).toBeInTheDocument()
    expect(screen.getByText("3 itens · o que mudaria uma decisão hoje")).toBeInTheDocument()

    const presa = acaoDe(/Cadastro rural · lote 7 está em andamento/)
    expect(presa).toHaveTextContent("Abrir")
    expect(presa.querySelector(".font-semibold")?.textContent).toBe("Cadastro rural · lote 7")

    fireEvent.click(acaoDe(/Integração SICAR falhou/))
    expect(onAcao).toHaveBeenCalledWith({ tipo: "filtrar-workflow", workflowHash: "wf-sicar", status: "failed" })
    fireEvent.click(acaoDe(/geo-02 está no teto/))
    expect(onAcao).toHaveBeenLastCalledWith({ tipo: "abrir-executor", agentHost: "executor:geo-02" })
  })

  it("dispensar um item o esconde; Restaurar traz de volta", () => {
    render(<AtencaoLista itens={itens} carregando={false} vazio="x" onAcao={() => {}} />)
    fireEvent.click(screen.getByRole("button", { name: "Dispensar o alerta de Integração SICAR" }))

    expect(screen.queryByRole("button", { name: /Integração SICAR falhou/ })).toBeNull()
    expect(screen.getByText("2 itens · o que mudaria uma decisão hoje")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Restaurar (1)" }))
    expect(screen.getByRole("button", { name: /Integração SICAR falhou/ })).toBeInTheDocument()
    expect(screen.getByText("3 itens · o que mudaria uma decisão hoje")).toBeInTheDocument()
  })

  it("Limpar tudo esconde todos os itens e mostra o estado dispensado, sem o verde de 'tudo tranquilo'", () => {
    render(<AtencaoLista itens={itens} carregando={false} vazio="Nenhuma falha no período." onAcao={() => {}} />)
    fireEvent.click(screen.getByRole("button", { name: "Limpar tudo" }))

    expect(screen.getByText("tudo dispensado")).toBeInTheDocument()
    expect(screen.getByText("3 alertas dispensados.")).toBeInTheDocument()
    // Não é o vazio verde de "nada pede atenção".
    expect(screen.queryByText("Nenhuma falha no período.")).toBeNull()
    expect(screen.queryByRole("button", { name: /está em andamento|falhou|está no teto/ })).toBeNull()

    fireEvent.click(screen.getByRole("button", { name: "Restaurar" }))
    expect(screen.getByRole("button", { name: /Cadastro rural · lote 7 está em andamento/ })).toBeInTheDocument()
  })

  it("um item volta a aparecer se a assinatura muda (o problema piorou), mesmo dispensado", () => {
    const { rerender } = render(<AtencaoLista itens={itens} carregando={false} vazio="x" onAcao={() => {}} />)
    fireEvent.click(screen.getByRole("button", { name: "Dispensar o alerta de Integração SICAR" }))
    expect(screen.queryByRole("button", { name: /Integração SICAR falhou/ })).toBeNull()

    // Uma nova falha muda a assinatura (28 → 29): o alerta reaparece.
    const piorado = itens.map(i => i.chave === "falhas:wf-sicar" ? { ...i, assinatura: "29" } : i)
    rerender(<AtencaoLista itens={piorado} carregando={false} vazio="x" onAcao={() => {}} />)
    expect(screen.getByRole("button", { name: /Integração SICAR falhou/ })).toBeInTheDocument()
  })

  it("vazio: a frase recebida, e nenhum botão", () => {
    render(<AtencaoLista itens={[]} carregando={false} vazio="Nada pendente. Última falha há 3 dias." onAcao={() => {}} />)
    expect(screen.getByText("Nada pendente. Última falha há 3 dias.")).toBeInTheDocument()
    expect(screen.queryAllByRole("button")).toHaveLength(0)
  })

  it("skeleton só na primeira carga", () => {
    const { container, rerender } = render(<AtencaoLista itens={[]} carregando vazio="x" onAcao={() => {}} />)
    expect(container.querySelectorAll("[data-slot='skeleton']").length).toBeGreaterThan(0)
    expect(screen.queryByText("x")).toBeNull()

    rerender(<AtencaoLista itens={itens} carregando vazio="x" onAcao={() => {}} />)
    expect(container.querySelectorAll("[data-slot='skeleton']")).toHaveLength(0)
    expect(screen.getByRole("button", { name: /Cadastro rural · lote 7 está em andamento/ })).toBeInTheDocument()
  })

  it("falha parcial: aviso visível, e a última leitura continua na tela", () => {
    render(<AtencaoLista itens={itens} carregando={false} vazio="x" onAcao={() => {}} falha="Não foi possível carregar os executores." />)
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar os executores. Mostrando a última leitura.")
    expect(screen.getByRole("button", { name: /Cadastro rural · lote 7 está em andamento/ })).toBeInTheDocument()
  })
})
