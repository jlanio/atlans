/**
 * Key/value pair editor — `headers` and `params` of the HttpRequest node.
 *
 * The component is CONTROLLED: `values` comes from the modal and `setNodeField`
 * writes back (node-config-modal/index.tsx:124 — there's no local state anywhere
 * along the path). These tests build that same loop, because the defect only
 * shows up when the round trip happens: the new row was discarded on write and
 * the component re-rendered from the saved value, without it.
 */
import { useState } from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import KeyValueField from "@/app/components/workflow/nodes-configuration/fields/key-value-field"

const campo = { name: "headers", label: "Cabeçalhos", type: "keyvalue" } as never

/** Reproduces the modal's real controlled loop. */
function Host({ inicial = {} }: { inicial?: Record<string, string> }) {
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
    render(<Host />)
    expect(screen.queryByLabelText("Nome do item 1")).toBeNull()

    fireEvent.click(screen.getByRole("button", { name: /adicionar/i }))

    // Before, `gravar` filtered out the empty key before saving: the object came
    // back unchanged, `pares` recomputed without the row and the click did
    // NOTHING — both fields of the HttpRequest node were impossible to fill from the UI.
    expect(screen.getByLabelText("Nome do item 1")).toBeInTheDocument()
  })

  it("dá para digitar nome e valor na linha recém-criada", () => {
    render(<Host />)
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
    render(<Host inicial={{ "Content-Typo": "application/json" }} />)

    // The natural step when renaming: clear the field before typing the right one.
    fireEvent.change(screen.getByLabelText("Nome do item 1"), { target: { value: "" } })
    expect(screen.getByLabelText("Nome do item 1")).toBeInTheDocument()
    // And the value already typed is still there to be reused.
    expect(screen.getByLabelText("Valor do item 1")).toHaveValue("application/json")

    fireEvent.change(screen.getByLabelText("Nome do item 1"), {
      target: { value: "Content-Type" },
    })
    expect(screen.getByLabelText("Nome do item 1")).toHaveValue("Content-Type")
  })

  it("duas linhas novas não colapsam numa só", () => {
    render(<Host />)
    const botao = screen.getByRole("button", { name: /adicionar/i })
    fireEvent.click(botao)
    fireEvent.click(botao)

    expect(screen.getByLabelText("Nome do item 1")).toBeInTheDocument()
    expect(screen.getByLabelText("Nome do item 2")).toBeInTheDocument()
  })

  it("remover apaga a linha certa", () => {
    render(<Host inicial={{ a: "1", b: "2" }} />)
    fireEvent.click(screen.getByLabelText("Remover item 1"))

    expect(screen.getByLabelText("Nome do item 1")).toHaveValue("b")
    expect(screen.queryByLabelText("Nome do item 2")).toBeNull()
  })

  it("linha sem nome não é gravada no valor do nó", () => {
    let ultimo: unknown = null
    function Spy() {
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
    render(<Spy />)
    fireEvent.click(screen.getByRole("button", { name: /adicionar/i }))
    fireEvent.change(screen.getByLabelText("Valor do item 1"), { target: { value: "orfao" } })

    // The row exists on the screen, but without a name it doesn't become a
    // header: what comes out of the component stays clean.
    expect(ultimo).toEqual({})
  })
})
