/**
 * Painel "Parametros detectados" do editor SQL.
 *
 * O componente é CONTROLADO: `values` vem do modal e `setNodeField` escreve de
 * volta. A gravação era um `{...currentParams, [name]: value}` puro e nada
 * nunca saía do objeto: quem renomeava `:bairro` para `:cidade` deixava o
 * `bairro` na definição salva para sempre — invisível na tela, mas gravado no
 * workflow e em todo o histórico de versões, com o valor que tivesse dentro.
 */
import { useState } from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import SqlField from "@/app/components/workflow/nodes-configuration/fields/sql-field"

// O Monaco pesa ~2.5MB e é carregado por `next/dynamic`; aqui só precisamos do
// painel de parâmetros, então um textarea simples basta.
vi.mock("@/app/components/workflow/nodes-configuration/fields/monaco-code-editor", () => ({
  default: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea aria-label="sql" value={value} onChange={e => onChange(e.target.value)} />
  ),
}))

const campo = { name: "query", label: "Consulta SQL", type: "sql" } as never

function Anfitriao({ sql, params = {} }: { sql: string; params?: Record<string, string> }) {
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
    render(<Anfitriao sql="SELECT * FROM t WHERE a = :aa AND b = :bb" />)
    expect(screen.getByPlaceholderText("Valor para :aa")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Valor para :bb")).toBeInTheDocument()
  })

  it("não oferece placeholder que está dentro de um literal", () => {
    render(<Anfitriao sql="SELECT * FROM notas WHERE obs = 'urgente:revisar' AND id = :id" />)
    expect(screen.queryByPlaceholderText("Valor para :revisar")).toBeNull()
    expect(screen.getByPlaceholderText("Valor para :id")).toBeInTheDocument()
  })

  it("grava o valor digitado", () => {
    render(<Anfitriao sql="SELECT * FROM t WHERE b = :bairro" />)
    fireEvent.change(screen.getByPlaceholderText("Valor para :bairro"), {
      target: { value: "Centro" },
    })
    expect(gravado()).toEqual({ bairro: "Centro" })
  })

  it("o parâmetro renomeado sai da definição salva", () => {
    render(
      <Anfitriao
        sql="SELECT * FROM t WHERE b = :bairro"
        params={{ bairro: "Centro" }}
      />,
    )
    // Renomeia o placeholder na query...
    fireEvent.change(screen.getByLabelText("sql"), {
      target: { value: "SELECT * FROM t WHERE c = :cidade" },
    })
    // ...e preenche o novo. É neste momento que a poda acontece.
    fireEvent.change(screen.getByPlaceholderText("Valor para :cidade"), {
      target: { value: "Recife" },
    })

    expect(gravado()).toEqual({ cidade: "Recife" })
    expect(gravado()).not.toHaveProperty("bairro")
  })

  it("editar um valor não derruba os outros parâmetros da query", () => {
    render(
      <Anfitriao
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
    // A poda é ao gravar VALOR, não a cada tecla do editor: podar aqui apagaria
    // `:bairro` no instante em que a query dissesse `:bairr`, no meio de uma
    // renomeação.
    render(
      <Anfitriao sql="SELECT * FROM t WHERE b = :bairro" params={{ bairro: "Centro" }} />,
    )
    fireEvent.change(screen.getByLabelText("sql"), {
      target: { value: "SELECT * FROM t WHERE b = :bairr" },
    })
    expect(gravado()).toEqual({ bairro: "Centro" })
  })
})
