import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

import { SheetSection } from "@/app/components/workspace/settings-sheet/section-shell"

// A casca de seção do painel do workspace. O contrato que interessa aqui é o
// posicionamento da `action`:
//
// - por padrão ela fica no canto superior direito, na MESMA linha do título
//   (dentro do flex `justify-between`);
// - com `actionBelow`, ela desce para uma linha própria, FORA daquele flex —
//   para ações largas (link + botão) que espremiam o título num painel
//   estreito (a "Política de execução").
//
// Em ambos os casos a ação continua sempre visível (fica no cabeçalho, acima
// da troca carregando/erro/conteúdo).

afterEach(cleanup)

describe("SheetSection — posição da ação", () => {
  it("por padrão, a ação fica na linha do título (canto superior direito)", () => {
    render(
      <SheetSection title="Membros" description="Quem tem acesso." action={<button>Adicionar</button>}>
        <div>corpo</div>
      </SheetSection>,
    )
    const acao = screen.getByRole("button", { name: "Adicionar" })
    // Está dentro do flex `justify-between` que também carrega o título.
    const linha = acao.closest(".justify-between")
    expect(linha).not.toBeNull()
    expect(linha?.textContent).toContain("Membros")
  })

  it("com actionBelow, a ação desce para fora da linha do título", () => {
    render(
      <SheetSection
        title="Política de execução"
        description="Em quais executores os workflows rodam."
        actionBelow
        action={<button>Gerenciar executores</button>}
      >
        <div>corpo</div>
      </SheetSection>,
    )
    const acao = screen.getByRole("button", { name: "Gerenciar executores" })
    // NÃO está no flex do título — está numa linha própria abaixo dele.
    expect(acao.closest(".justify-between")).toBeNull()
    // O título continua presente e não perde a ação.
    expect(screen.getByText("Política de execução")).toBeTruthy()
  })

  it("a ação sempre renderiza (fica no cabeçalho), mesmo enquanto carrega", () => {
    render(
      <SheetSection title="Política de execução" actionBelow action={<button>Atualizar</button>} loading>
        <div>corpo</div>
      </SheetSection>,
    )
    // Corpo trocado pelo esqueleto, mas a ação permanece.
    expect(screen.queryByText("corpo")).toBeNull()
    expect(screen.getByRole("button", { name: "Atualizar" })).toBeTruthy()
  })
})
