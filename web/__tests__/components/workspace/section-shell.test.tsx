import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

import { SheetSection } from "@/app/components/workspace/settings-sheet/section-shell"

// The section shell of the workspace panel. The contract that matters here is
// the placement of the `action`:
//
// - by default it sits in the top-right corner, on the SAME line as the title
//   (inside the `justify-between` flex);
// - with `actionBelow`, it drops to a line of its own, OUTSIDE that flex —
//   for wide actions (link + button) that squeezed the title in a narrow
//   panel (the "Política de execução" one).
//
// In both cases the action stays always visible (it lives in the header, above
// the loading/error/content switch).

afterEach(cleanup)

describe("SheetSection — posição da ação", () => {
  it("por padrão, a ação fica na linha do título (canto superior direito)", () => {
    render(
      <SheetSection title="Membros" description="Quem tem acesso." action={<button>Adicionar</button>}>
        <div>corpo</div>
      </SheetSection>,
    )
    const acao = screen.getByRole("button", { name: "Adicionar" })
    // It's inside the `justify-between` flex that also holds the title.
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
    // It's NOT in the title's flex — it's on its own line below it.
    expect(acao.closest(".justify-between")).toBeNull()
    // The title is still present and doesn't lose the action.
    expect(screen.getByText("Política de execução")).toBeTruthy()
  })

  it("a ação sempre renderiza (fica no cabeçalho), mesmo enquanto carrega", () => {
    render(
      <SheetSection title="Política de execução" actionBelow action={<button>Atualizar</button>} loading>
        <div>corpo</div>
      </SheetSection>,
    )
    // Body replaced by the skeleton, but the action remains.
    expect(screen.queryByText("corpo")).toBeNull()
    expect(screen.getByRole("button", { name: "Atualizar" })).toBeTruthy()
  })
})
