import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { CabecalhoDeProjetos, textoDoSubtitulo } from "@/app/components/projects/cabecalho"

afterEach(cleanup)

const contagens = { workflows: 10, grupos: 3, ativos: 8, agendados: 4, portal: 2 }
const base = { contagens, atualizando: false, canEdit: true, onAtualizar: () => {}, onNovoGrupo: () => {}, onCriarWorkflow: () => {} }

describe("textoDoSubtitulo", () => {
  it("frase completa, partes com zero omitidas, sem grupos e singular", () => {
    expect(textoDoSubtitulo(contagens)).toBe("10 workflows em 3 grupos · 8 ativos · 4 agendados · 2 com portal")
    expect(textoDoSubtitulo({ workflows: 10, grupos: 3, ativos: 8, agendados: 0, portal: 0 })).toBe("10 workflows em 3 grupos · 8 ativos")
    expect(textoDoSubtitulo({ workflows: 4, grupos: 0, ativos: 3, agendados: 1, portal: 1 })).toBe("4 workflows · 3 ativos · 1 agendado · 1 com portal")
    expect(textoDoSubtitulo({ workflows: 1, grupos: 1, ativos: 1, agendados: 0, portal: 0 })).toBe("1 workflow em 1 grupo · 1 ativo")
    expect(textoDoSubtitulo({ workflows: 0, grupos: 0, ativos: 0, agendados: 0, portal: 0 })).toBe("Nenhum workflow ainda")
    expect(textoDoSubtitulo({ workflows: 0, grupos: 2, ativos: 0, agendados: 0, portal: 0 })).toBe("Nenhum workflow · 2 grupos")
  })
})

describe("CabecalhoDeProjetos", () => {
  it("título, subtítulo com contagens e as três ações para quem edita", () => {
    const onAtualizar = vi.fn()
    const onNovoGrupo = vi.fn()
    const onCriarWorkflow = vi.fn()
    render(<CabecalhoDeProjetos {...base} onAtualizar={onAtualizar} onNovoGrupo={onNovoGrupo} onCriarWorkflow={onCriarWorkflow} />)
    expect(screen.getByRole("heading", { level: 1, name: "Projetos" })).toBeInTheDocument()
    expect(screen.getByText("10 workflows em 3 grupos · 8 ativos · 4 agendados · 2 com portal")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Atualizar a lista de projetos" }))
    expect(onAtualizar).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole("button", { name: "Novo grupo" }))
    expect(onNovoGrupo).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole("button", { name: "Criar workflow" }))
    expect(onCriarWorkflow).toHaveBeenCalledTimes(1)
  })

  it("sem permissão de editar: só Atualizar (Novo grupo e Criar workflow somem)", () => {
    render(<CabecalhoDeProjetos {...base} canEdit={false} />)
    expect(screen.getByRole("button", { name: "Atualizar a lista de projetos" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Novo grupo" })).toBeNull()
    expect(screen.queryByRole("button", { name: "Criar workflow" })).toBeNull()
  })

  it("Atualizar trava enquanto recarrega", () => {
    render(<CabecalhoDeProjetos {...base} atualizando />)
    expect(screen.getByRole("button", { name: "Atualizar a lista de projetos" })).toBeDisabled()
  })

  it("sem contagens (primeira carga) o subtítulo vira esqueleto", () => {
    const { container } = render(<CabecalhoDeProjetos {...base} contagens={null} />)
    expect(container.querySelector("[data-slot='skeleton']")).not.toBeNull()
    expect(screen.queryByText(/workflows/)).toBeNull()
  })

  it("no telefone o menu ⋯ oferece Novo grupo e Atualizar", () => {
    const onAtualizar = vi.fn()
    const onNovoGrupo = vi.fn()
    render(<CabecalhoDeProjetos {...base} onAtualizar={onAtualizar} onNovoGrupo={onNovoGrupo} />)
    fireEvent.keyDown(screen.getByRole("button", { name: "Mais ações" }), { key: "Enter" })
    const itens = screen.getAllByRole("menuitem")
    expect(itens.map(i => i.textContent?.trim())).toEqual(["Novo grupo", "Atualizar"])
    fireEvent.click(itens[0])
    expect(onNovoGrupo).toHaveBeenCalledTimes(1)
  })
})
