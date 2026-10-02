import { afterEach, describe, expect, it } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import { ComoAndaCelula, textoDaContagem, textoDaExecucao } from "@/app/components/projects/como-anda-celula"
import type { ComoAnda } from "@/app/components/projects/como-anda"

afterEach(cleanup)

const concluida: ComoAnda = { tipo: "concluida", quando: "há 3 h", instante: 1, erro: null, total: 61, falhas: 3, mediana: 180 }
const falhou: ComoAnda = { tipo: "falhou", quando: "há 40 min", instante: 1, erro: "Timeout ao consultar o WFS do SICAR (30 s)", total: 10, falhas: 1, mediana: null }
const cancelada: ComoAnda = { tipo: "cancelada", quando: "ontem, 06:00", instante: 1, erro: null, total: 5, falhas: 0, mediana: null }
const executando: ComoAnda = { tipo: "executando", desde: "há 4 min", instante: 1, origem: "agendado", executor: "geo-01", tipica: 420 }

describe("ComoAndaCelula", () => {
  it("concluída: verde, quando, e a contagem da janela na segunda linha", () => {
    const { container } = render(<ComoAndaCelula comoAnda={concluida} />)
    expect(screen.getByText("Concluída há 3 h").parentElement?.className).toContain("text-green")
    expect(screen.getByText("61 execuções em 30 d · 3 falhas · mediana 3 min")).toBeInTheDocument()
    expect(container.firstElementChild).toHaveAttribute("data-como-anda", "concluida")
  })

  it("falhou: vermelho, e o erro na segunda linha com o texto inteiro no title", () => {
    render(<ComoAndaCelula comoAnda={falhou} />)
    expect(screen.getByText("Falhou há 40 min").parentElement?.className).toContain("text-red")
    const erro = screen.getByTitle("Timeout ao consultar o WFS do SICAR (30 s)")
    expect(erro).toHaveTextContent("Timeout ao consultar o WFS do SICAR (30 s)")
    expect(erro.className).toContain("text-red")
  })

  it("falhou sem mensagem de erro cai na contagem, sem vermelho na segunda linha", () => {
    render(<ComoAndaCelula comoAnda={{ ...falhou, erro: null }} />)
    const segunda = screen.getByText("10 execuções em 30 d · 1 falha")
    expect(segunda.className).not.toContain("text-red")
    expect(segunda).not.toHaveAttribute("title")
  })

  it("cancelada: cinza, com a mesma segunda linha da concluída", () => {
    render(<ComoAndaCelula comoAnda={cancelada} />)
    expect(screen.getByText("Cancelada ontem, 06:00").parentElement?.className).toContain("text-muted-foreground")
    expect(screen.getByText("5 execuções em 30 d · nenhuma falha")).toBeInTheDocument()
  })

  it("em execução: azul com ping sob motion-safe, e o contexto do run vivo", () => {
    const { container } = render(<ComoAndaCelula comoAnda={executando} />)
    expect(screen.getByText("Em execução há 4 min").parentElement?.className).toContain("text-blue")
    expect(container.querySelector(".motion-safe\\:animate-ping")).not.toBeNull()
    expect(screen.getByText("agendado · em geo-01 · costuma levar 7 min")).toBeInTheDocument()
  })

  it("em execução ainda na fila: sem 'há', e sem segunda linha quando nada se sabe", () => {
    render(<ComoAndaCelula comoAnda={{ ...executando, desde: "", origem: null, executor: null, tipica: null }} />)
    expect(screen.getByText("Em execução")).toBeInTheDocument()
    expect(screen.queryByText(/costuma levar/)).toBeNull()
  })

  it("sem execuções, nunca e indisponível: os textos da spec", () => {
    const { rerender } = render(<ComoAndaCelula comoAnda={{ tipo: "sem-execucoes" }} />)
    expect(screen.getByText("Sem execuções em 30 dias")).toBeInTheDocument()
    rerender(<ComoAndaCelula comoAnda={{ tipo: "nunca" }} />)
    expect(screen.getByText("Ainda não executou")).toBeInTheDocument()
    expect(screen.getByText("execute uma vez para validar")).toBeInTheDocument()
    rerender(<ComoAndaCelula comoAnda={{ tipo: "indisponivel" }} />)
    expect(screen.getByText("Sem dados de execução")).toBeInTheDocument()
    expect(screen.queryByText("execute uma vez para validar")).toBeNull()
  })
})

describe("helpers", () => {
  it("textoDaContagem: singular, 'nenhuma falha' e mediana opcional", () => {
    expect(textoDaContagem({ total: 1, falhas: 0, mediana: null })).toBe("1 execução em 30 d · nenhuma falha")
    expect(textoDaContagem({ total: 1284, falhas: 1, mediana: 31 })).toBe("1.284 execuções em 30 d · 1 falha · mediana 31 s")
  })

  it("textoDaExecucao: só o que se sabe, nulo quando nada", () => {
    expect(textoDaExecucao({ origem: "manual", executor: null, tipica: 90 })).toBe("manual · costuma levar 2 min")
    expect(textoDaExecucao({ origem: null, executor: "geo-02", tipica: null })).toBe("em geo-02")
    expect(textoDaExecucao({ origem: null, executor: null, tipica: null })).toBeNull()
  })
})
