import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { TbInbox, TbPlus } from "react-icons/tb"
import {
  AvisoAmbar, CartaoDeEstado, ErroDeCarga, SemResultado, VazioPrimeiroUso, textoDeSemResultado,
} from "@/app/components/shared/estados"

afterEach(cleanup)

describe("CartaoDeEstado", () => {
  it("no tom de erro anuncia (role=alert) e pinta a moldura destrutiva", () => {
    render(<CartaoDeEstado tom="erro" icone={TbInbox} titulo="Caiu" descricao="Detalhe" />)
    const alerta = screen.getByRole("alert")
    expect(alerta).toHaveClass("border-destructive/20")
    expect(alerta).toHaveTextContent("CaiuDetalhe")
    // The icon circle is destructive too; the icon is decorative.
    const icone = alerta.querySelector("svg")!
    expect(icone).toHaveAttribute("aria-hidden", "true")
    expect(icone.parentElement).toHaveClass("bg-destructive/10")
  })

  it("no tom neutro não é alerta nem pinta a borda", () => {
    const { container } = render(<CartaoDeEstado icone={TbInbox} titulo="Nada aqui" />)
    expect(screen.queryByRole("alert")).toBeNull()
    expect(container.firstElementChild).not.toHaveClass("border-destructive/20")
    expect(container.querySelector("svg")!.parentElement).toHaveClass("bg-muted/60")
  })

  it("compacto × amplo: o tamanho muda ícone, título e respiro — a moldura é a mesma", () => {
    const { container, rerender } = render(<CartaoDeEstado icone={TbInbox} titulo="T" />)
    const cartao = () => container.firstElementChild!
    expect(cartao()).toHaveClass("rounded-lg", "border", "bg-card", "px-6", "py-14", "shadow-xs", "gap-3")
    expect(container.querySelector("svg")).toHaveAttribute("width", "26")
    expect(screen.getByText("T")).toHaveClass("text-sm", "font-medium")

    rerender(<CartaoDeEstado icone={TbInbox} titulo="T" tamanho="amplo" />)
    expect(cartao()).toHaveClass("rounded-lg", "border", "bg-card", "px-6", "py-14", "shadow-xs", "gap-5")
    expect(container.querySelector("svg")).toHaveAttribute("width", "36")
    expect(screen.getByText("T")).toHaveClass("text-base", "font-semibold")
  })

  it("tituloId permite rotular uma região pelo título", () => {
    render(
      <section aria-labelledby="t-vazio">
        <CartaoDeEstado icone={TbInbox} titulo="Sem camadas" tituloId="t-vazio" />
      </section>,
    )
    expect(screen.getByRole("region", { name: "Sem camadas" })).toBeInTheDocument()
  })
})

describe("ErroDeCarga", () => {
  it("título da tela, mensagem do servidor e Tentar de novo", () => {
    const onTentar = vi.fn()
    render(<ErroDeCarga titulo="Não foi possível carregar os arquivos" mensagem="timeout" onTentar={onTentar} />)
    const alerta = screen.getByRole("alert")
    expect(alerta).toHaveTextContent("Não foi possível carregar os arquivos")
    expect(alerta).toHaveTextContent("timeout")
    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar de novo" }))
    expect(onTentar).toHaveBeenCalledTimes(1)
  })

  it("sem mensagem, só o título; sem onTentar, sem botão", () => {
    render(<ErroDeCarga titulo="Não foi possível carregar" mensagem={null} />)
    const alerta = screen.getByRole("alert")
    expect(alerta.querySelectorAll("p")).toHaveLength(1)
    expect(within(alerta).queryByRole("button")).toBeNull()
  })
})

describe("VazioPrimeiroUso", () => {
  const base = { icone: TbInbox, titulo: "Nenhum arquivo ainda", descricao: "Os arquivos ficam aqui." }

  it("quem pode criar vê o CTA", () => {
    const onClick = vi.fn()
    render(<VazioPrimeiroUso {...base} cta={{ rotulo: "Enviar arquivos", icone: TbPlus, onClick }} pedirA="enviar" />)
    fireEvent.click(screen.getByRole("button", { name: "Enviar arquivos" }))
    expect(onClick).toHaveBeenCalledTimes(1)
    expect(screen.queryByText(/Peça a um editor/)).toBeNull()
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("quem não pode lê a quem pedir, e não há botão", () => {
    render(
      <VazioPrimeiroUso
        {...base}
        cta={{ rotulo: "Enviar arquivos", onClick: () => {} }}
        podeCriar={false}
        pedirA="enviar os primeiros arquivos"
      />,
    )
    expect(screen.getByText("Peça a um editor do workspace para enviar os primeiros arquivos.")).toBeInTheDocument()
    expect(screen.queryByRole("button")).toBeNull()
  })

  it("uma ação pronta (um diálogo com o próprio gatilho) toma o lugar do CTA", () => {
    render(<VazioPrimeiroUso {...base} acao={<button type="button">Novo executor</button>} />)
    expect(screen.getByRole("button", { name: "Novo executor" })).toBeInTheDocument()
  })

  it("os passos saem numerados, na ordem", () => {
    render(
      <VazioPrimeiroUso
        {...base}
        passos={[{ titulo: "Desenhe", detalhe: "d1" }, { titulo: "Execute", detalhe: "d2" }]}
      />,
    )
    const itens = screen.getAllByRole("listitem")
    expect(itens.map(li => li.textContent)).toEqual(["1Desenhed1", "2Executed2"])
  })
})

describe("SemResultado e textoDeSemResultado", () => {
  it("a frase, a dica e Limpar filtros", () => {
    const onLimpar = vi.fn()
    render(<SemResultado texto="Nenhum arquivo com «x»" dica="Ajuste a busca." onLimpar={onLimpar} />)
    expect(screen.getByText("Nenhum arquivo com «x»")).toBeInTheDocument()
    expect(screen.getByText("Ajuste a busca.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("sem onLimpar, sem botão", () => {
    render(<SemResultado texto="Nada com esses filtros" />)
    expect(screen.queryByRole("button")).toBeNull()
  })

  it("termo, filtro, os dois e nenhum", () => {
    const nada = "Nenhum arquivo"
    expect(textoDeSemResultado({ nada, termo: " bacia ", comFiltro: true })).toBe("Nenhum arquivo com «bacia» e este filtro")
    expect(textoDeSemResultado({ nada, termo: "bacia", comFiltro: false })).toBe("Nenhum arquivo com «bacia»")
    expect(textoDeSemResultado({ nada, termo: "  ", comFiltro: true })).toBe("Nenhum arquivo com este filtro")
    expect(textoDeSemResultado({ nada, termo: "", comFiltro: false })).toBe("Nenhum arquivo")
  })

  it("recorte com nome (sufixoFiltro) e frase própria sem recorte (semRecorte)", () => {
    const nada = "Nenhum artefato"
    expect(textoDeSemResultado({ nada, termo: "rio", comFiltro: true, sufixoFiltro: "em CSV" })).toBe("Nenhum artefato com «rio» em CSV")
    expect(textoDeSemResultado({ nada, termo: "", comFiltro: true, sufixoFiltro: "em CSV" })).toBe("Nenhum artefato em CSV")
    expect(textoDeSemResultado({ nada, termo: "", comFiltro: false, semRecorte: "Nenhum artefato com este filtro" })).toBe("Nenhum artefato com este filtro")
  })
})

describe("AvisoAmbar", () => {
  it("uma linha de status (não alerta) com Tentar de novo", () => {
    const onTentar = vi.fn()
    render(<AvisoAmbar onTentar={onTentar}>Não foi possível carregar o gráfico.</AvisoAmbar>)
    const aviso = screen.getByRole("status")
    expect(aviso).toHaveTextContent("Não foi possível carregar o gráfico.")
    expect(screen.queryByRole("alert")).toBeNull()
    fireEvent.click(within(aviso).getByRole("button", { name: "Tentar de novo" }))
    expect(onTentar).toHaveBeenCalledTimes(1)
  })

  it("o rótulo do botão pode vir traduzido (a Home fala três idiomas)", () => {
    render(<AvisoAmbar onTentar={() => {}} rotuloDoBotao="Try again">Could not refresh.</AvisoAmbar>)
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument()
  })
})
