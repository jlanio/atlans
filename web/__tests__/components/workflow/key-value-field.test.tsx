/**
 * Editor de pares chave/valor — `headers` e `params` do nó HttpRequest.
 *
 * O componente é CONTROLADO: `values` vem do modal e `setNodeField` escreve de
 * volta (node-config-modal/index.tsx:124 — não há estado local em lugar nenhum
 * do caminho). Estes testes montam esse mesmo laço, porque o defeito só aparece
 * quando a volta acontece: a linha nova era descartada na gravação e o
 * componente re-renderizava a partir do valor salvo, sem ela.
 */
import { useState } from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import KeyValueField from "@/app/components/workflow/nodes-configuration/fields/key-value-field"

const campo = { name: "headers", label: "Cabeçalhos", type: "keyvalue" } as never

/** Reproduz o laço controlado real do modal. */
function Anfitriao({ inicial = {} }: { inicial?: Record<string, string> }) {
  const [values, setValues] = useState<Record<string, unknown>>({ headers: inicial })
  return (
    <KeyValueField
      field={campo}
      values={values as never}
      setNodeField={(nome, valor) => setValues(v => ({ ...v, [nome]: valor }))}
    />
  )
}

describe("KeyValueField", () => {
  it("o botão Adicionar cria uma linha em branco", () => {
    render(<Anfitriao />)
    expect(screen.queryByLabelText("Nome do item 1")).toBeNull()

    fireEvent.click(screen.getByRole("button", { name: /adicionar/i }))

    // Antes, `gravar` filtrava a chave vazia antes de salvar: o objeto voltava
    // igual, `pares` recalculava sem a linha e o clique não fazia NADA — os
    // dois campos do nó HttpRequest eram impreenchíveis pela interface.
    expect(screen.getByLabelText("Nome do item 1")).toBeInTheDocument()
  })

  it("dá para digitar nome e valor na linha recém-criada", () => {
    render(<Anfitriao />)
    fireEvent.click(screen.getByRole("button", { name: /adicionar/i }))

    fireEvent.change(screen.getByLabelText("Nome do item 1"), {
      target: { value: "Authorization" },
    })
    fireEvent.change(screen.getByLabelText("Valor do item 1"), {
      target: { value: "Bearer abc" },
    })

    expect(screen.getByLabelText("Nome do item 1")).toHaveValue("Authorization")
    expect(screen.getByLabelText("Valor do item 1")).toHaveValue("Bearer abc")
  })

  it("apagar o nome para renomear não faz a linha sumir", () => {
    render(<Anfitriao inicial={{ "Content-Typo": "application/json" }} />)

    // Passo natural de renomear: limpar o campo antes de digitar o certo.
    fireEvent.change(screen.getByLabelText("Nome do item 1"), { target: { value: "" } })
    expect(screen.getByLabelText("Nome do item 1")).toBeInTheDocument()
    // E o valor que já estava digitado continua lá para ser aproveitado.
    expect(screen.getByLabelText("Valor do item 1")).toHaveValue("application/json")

    fireEvent.change(screen.getByLabelText("Nome do item 1"), {
      target: { value: "Content-Type" },
    })
    expect(screen.getByLabelText("Nome do item 1")).toHaveValue("Content-Type")
  })

  it("duas linhas novas não colapsam numa só", () => {
    render(<Anfitriao />)
    const botao = screen.getByRole("button", { name: /adicionar/i })
    fireEvent.click(botao)
    fireEvent.click(botao)

    expect(screen.getByLabelText("Nome do item 1")).toBeInTheDocument()
    expect(screen.getByLabelText("Nome do item 2")).toBeInTheDocument()
  })

  it("remover apaga a linha certa", () => {
    render(<Anfitriao inicial={{ a: "1", b: "2" }} />)
    fireEvent.click(screen.getByLabelText("Remover item 1"))

    expect(screen.getByLabelText("Nome do item 1")).toHaveValue("b")
    expect(screen.queryByLabelText("Nome do item 2")).toBeNull()
  })

  it("linha sem nome não é gravada no valor do nó", () => {
    let ultimo: unknown = null
    function Espia() {
      const [values, setValues] = useState<Record<string, unknown>>({ headers: {} })
      return (
        <KeyValueField
          field={campo}
          values={values as never}
          setNodeField={(nome, valor) => {
            ultimo = valor
            setValues(v => ({ ...v, [nome]: valor }))
          }}
        />
      )
    }
    render(<Espia />)
    fireEvent.click(screen.getByRole("button", { name: /adicionar/i }))
    fireEvent.change(screen.getByLabelText("Valor do item 1"), { target: { value: "orfao" } })

    // A linha existe na tela, mas sem nome não vira cabeçalho: o que sai do
    // componente continua limpo.
    expect(ultimo).toEqual({})
  })
})
