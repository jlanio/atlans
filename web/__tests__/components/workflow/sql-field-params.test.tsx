/**
 * The SQL editor's "Parametros detectados" (detected parameters) panel.
 *
 * The component is CONTROLLED: `values` comes from the modal and `setNodeField`
 * writes back. The write was a plain `{...currentParams, [name]: value}` and
 * nothing ever left the object: whoever renamed `:bairro` to `:cidade` left
 * `bairro` in the saved definition forever — invisible on the screen, but saved
 * in the workflow and in the whole version history, with whatever value it held.
 */
import { useState } from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import SqlField from "@/app/components/workflow/nodes-configuration/fields/sql-field"

// Monaco weighs ~2.5MB and is loaded through `next/dynamic`; here we only need
// the parameters panel, so a plain textarea is enough.
vi.mock("@/app/components/workflow/nodes-configuration/fields/monaco-code-editor", () => ({
  default: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea aria-label="sql" value={value} onChange={e => onChange(e.target.value)} />
  ),
}))

const campo = { name: "query", label: "Consulta SQL", type: "sql" } as never

function Host({ sql, params = {} }: { sql: string; params?: Record<string, string> }) {
  const [values, setValues] = useState<Record<string, unknown>>({
    query: sql, queryParams: params,
  })
  return (
    <>
      <SqlField
        field={campo}
        values={values as never}
        setNodeField={(nome, valor) => setValues(v => ({ ...v, [nome]: valor }))}
        paramsFieldName="queryParams"
      />
      <output data-testid="gravado">{JSON.stringify(values.queryParams)}</output>
    </>
  )
}

const gravado = () => JSON.parse(screen.getByTestId("gravado").textContent || "{}")

describe("SqlField — parâmetros detectados", () => {
  it("mostra um campo por placeholder da query", () => {
    render(<Host sql="SELECT * FROM t WHERE a = :aa AND b = :bb" />)
    expect(screen.getByPlaceholderText("Valor para :aa")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Valor para :bb")).toBeInTheDocument()
  })

  it("não oferece placeholder que está dentro de um literal", () => {
    render(<Host sql="SELECT * FROM notas WHERE obs = 'urgente:revisar' AND id = :id" />)
    expect(screen.queryByPlaceholderText("Valor para :revisar")).toBeNull()
    expect(screen.getByPlaceholderText("Valor para :id")).toBeInTheDocument()
  })

  it("grava o valor digitado", () => {
    render(<Host sql="SELECT * FROM t WHERE b = :bairro" />)
    fireEvent.change(screen.getByPlaceholderText("Valor para :bairro"), {
      target: { value: "Centro" },
    })
    expect(gravado()).toEqual({ bairro: "Centro" })
  })

  it("o parâmetro renomeado sai da definição salva", () => {
    render(
      <Host
        sql="SELECT * FROM t WHERE b = :bairro"
        params={{ bairro: "Centro" }}
      />,
    )
    // Renames the placeholder in the query...
    fireEvent.change(screen.getByLabelText("sql"), {
      target: { value: "SELECT * FROM t WHERE c = :cidade" },
    })
    // ...and fills in the new one. This is the moment the pruning happens.
    fireEvent.change(screen.getByPlaceholderText("Valor para :cidade"), {
      target: { value: "Recife" },
    })

    expect(gravado()).toEqual({ cidade: "Recife" })
    expect(gravado()).not.toHaveProperty("bairro")
  })

  it("editar um valor não derruba os outros parâmetros da query", () => {
    render(
      <Host
        sql="SELECT * FROM t WHERE a = :aa AND b = :bb"
        params={{ aa: "1", bb: "2" }}
      />,
    )
    fireEvent.change(screen.getByPlaceholderText("Valor para :aa"), {
      target: { value: "9" },
    })
    expect(gravado()).toEqual({ aa: "9", bb: "2" })
  })

  it("editar o SQL sozinho não apaga valor nenhum", () => {
    // Pruning happens when a VALUE is written, not on every editor keystroke:
    // pruning here would erase `:bairro` the instant the query said `:bairr`, in
    // the middle of a rename.
    render(
      <Host sql="SELECT * FROM t WHERE b = :bairro" params={{ bairro: "Centro" }} />,
    )
    fireEvent.change(screen.getByLabelText("sql"), {
      target: { value: "SELECT * FROM t WHERE b = :bairr" },
    })
    expect(gravado()).toEqual({ bairro: "Centro" })
  })
})
