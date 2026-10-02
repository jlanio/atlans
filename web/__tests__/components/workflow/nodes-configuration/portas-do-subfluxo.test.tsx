/**
 * Editor de portas do sub-fluxo, depois que as portas viraram pontos de conexão.
 *
 * Enquanto `ports` era só uma allowlist, mexer nela era inofensivo. Agora cada
 * porta é um handle no canvas: renomear ou remover uma com aresta ligada deixa
 * a aresta apontando para um ponto que deixou de existir — ela some do canvas,
 * continua executando, e sem linha desenhada nem dá para apagá-la. É o mesmo
 * motivo pelo qual o editor de portas do Script Python trava.
 *
 * A trava vale só na saída: o `SubWorkflowInput` é um gatilho, não recebe
 * aresta, e lá as portas não são handles.
 */
import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

import SubWorkflowPortsHelper from "@/app/components/workflow/nodes-configuration/sub-workflow-ports-helper"

afterEach(cleanup)

function montar(variant: "input" | "output", conexoes: number) {
  return render(
    <SubWorkflowPortsHelper
      values={{ ports: JSON.stringify(["focos", "mapa"]) }}
      setNodeField={() => {}}
      hasUnsaved={false}
      variant={variant}
      conexoesDeEntrada={conexoes}
    />,
  )
}

const botaoAdicionar = () => screen.getByRole("button", { name: /adicionar porta/i })

describe("SubWorkflowPortsHelper — trava com arestas ligadas", () => {
  it("saída com aresta ligada bloqueia a edição", () => {
    montar("output", 2)

    expect(botaoAdicionar()).toBeDisabled()
    for (const campo of screen.getAllByRole("textbox")) {
      expect(campo).toBeDisabled()
    }
    for (const remover of screen.getAllByTitle("Remover porta")) {
      expect(remover).toBeDisabled()
    }
  })

  it("o aviso diz quantas conexões impedem a edição", () => {
    montar("output", 2)
    expect(screen.getByText(/Há 2 conexões/)).toBeInTheDocument()
  })

  it("uma conexão só é dita no singular", () => {
    montar("output", 1)
    expect(screen.getByText(/Há 1 conexão/)).toBeInTheDocument()
  })

  it("saída sem aresta continua editável", () => {
    montar("output", 0)

    expect(botaoAdicionar()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })

  it("entrada nunca trava", () => {
    // O SubWorkflowInput é gatilho: nada chega nele, e a contagem de arestas
    // que o formulário passa é a do nó — travar ali seria bloqueio sem causa.
    montar("input", 3)

    expect(botaoAdicionar()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })
})
