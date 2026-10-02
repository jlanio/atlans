/**
 * A ajuda dos campos é tooltip, não parágrafo.
 *
 * O painel de configuração virava parede de texto: cada campo imprimia a
 * descrição inteira abaixo do controle, e num nó de 7 campos (os que mais se
 * configura têm de 6 a 10) o texto auxiliar ocupava mais espaço que os próprios
 * controles. São 182 descrições no catálogo, mediana de 53 caracteres mas com
 * picos de 210.
 *
 * O teste que importa é o NEGATIVO — a descrição não pode estar no documento
 * antes do hover. O parágrafo volta sozinho no dia em que alguém copiar o
 * padrão antigo (`<Label>` + `<p className="text-xs text-muted-foreground">`)
 * para um campo novo, e nada além disto perceberia.
 */
import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent, within } from "@testing-library/react"
import { ReactFlowProvider } from "@xyflow/react"

import BooleanField from "@/app/components/workflow/nodes-configuration/fields/boolean-field"
import NumericField from "@/app/components/workflow/nodes-configuration/fields/numeric-field"
import SelectField from "@/app/components/workflow/nodes-configuration/fields/select-field"
import StringField from "@/app/components/workflow/nodes-configuration/fields/string-field"
import { FieldLabel } from "@/app/components/workflow/nodes-configuration/fields/field-label"
import { INodesPropertyAPI } from "@/service/types"
import { INodeContext } from "@/context/useFlowContext"

const AJUDA =
  "Se ligado e já houver um arquivo com este nome no Drive, ele é substituído " +
  "em vez de gerar uma cópia."

function campo(over: Partial<INodesPropertyAPI> = {}): INodesPropertyAPI {
  return {
    name: "overwrite",
    label: "Sobrescrever se já existir",
    type: "boolean",
    default: false,
    description: AJUDA,
    ...over,
  } as INodesPropertyAPI
}

const props = { setNodeField: () => {}, values: {} }

afterEach(cleanup)

// ── O rótulo ────────────────────────────────────────────────────────────────

describe("FieldLabel", () => {
  it("mostra o rótulo e esconde a descrição até o hover", async () => {
    render(<FieldLabel field={campo()} />)

    expect(screen.getByText("Sobrescrever se já existir")).toBeInTheDocument()
    expect(screen.queryByText(AJUDA)).not.toBeInTheDocument()

    fireEvent.focus(screen.getByRole("button", { name: /^Ajuda:/ }))
    // O Radix duplica o conteúdo (um visível, um para leitor de tela), então
    // `getAllBy`: `getBy` falharia por múltiplos elementos, o que seria um
    // falso negativo.
    expect((await screen.findAllByText(AJUDA)).length).toBeGreaterThan(0)
  })

  it("o gatilho é um button com nome acessível", () => {
    render(<FieldLabel field={campo()} />)
    const gatilho = screen.getByRole("button", { name: "Ajuda: Sobrescrever se já existir" })
    // `type="button"` porque o painel tem um form em volta: sem isso, apertar
    // Enter no campo dispararia o tooltip em vez de salvar.
    expect(gatilho).toHaveAttribute("type", "button")
  })

  it("campo sem descrição não ganha ícone de ajuda", () => {
    render(<FieldLabel field={campo({ description: undefined })} />)
    expect(screen.queryByRole("button", { name: /^Ajuda:/ })).not.toBeInTheDocument()
  })
})

// ── Nenhum campo imprime a descrição direto na tela ─────────────────────────

describe("os campos não imprimem mais parágrafo de ajuda", () => {
  const casos: Array<[string, React.ReactElement]> = [
    ["boolean", <BooleanField key="b" field={campo()} {...props} />],
    ["select",  <SelectField  key="s" field={campo({ type: "select", options: [{ value: "a", label: "A" }] })} {...props} />],
    ["numeric", <NumericField key="n" field={campo({ type: "number" })} {...props} variant="number" />],
    ["string",  <StringField  key="t" field={campo({ type: "string" })} {...props} />],
  ]

  it.each(casos)("%s", (_nome, elemento) => {
    render(elemento)
    expect(screen.queryByText(AJUDA)).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^Ajuda:/ })).toBeInTheDocument()
  })
})

// ── Regressões pontuais ─────────────────────────────────────────────────────

describe("regressões", () => {
  it("StringField não usa a descrição como placeholder", () => {
    // Aparecia DUAS vezes: no placeholder e no parágrafo. Placeholder é para
    // exemplo de valor, não para a documentação do campo.
    //
    // Precisa do `nodeFound` para cair no ramo do ExpressionInput — é lá que o
    // placeholder existia. Sem ele o componente renderiza o `<Input>` simples e
    // o teste passaria sem tocar no código que interessa. E o ExpressionInput
    // usa `useNodes`/`useEdges`, daí o ReactFlowProvider.
    const nodeFound = {
      id: "n1",
      data: { inputs: [], properties: {}, fields: [] },
    } as unknown as INodeContext

    const { container } = render(
      <ReactFlowProvider>
        <StringField field={campo({ type: "string" })} {...props} nodeFound={nodeFound} />
      </ReactFlowProvider>,
    )
    const input = container.querySelector("input, textarea")
    expect(input?.getAttribute("placeholder") ?? "").not.toContain("Drive")
  })

  it("BooleanField é uma linha, não um cartão", () => {
    // Era o único campo com moldura e sombra. Numa lista mista, isso fazia um
    // toggle pesar mais que o select que governa o nó inteiro.
    const { container } = render(<BooleanField field={campo()} {...props} />)
    const raiz = container.firstElementChild as HTMLElement
    expect(raiz.className).not.toMatch(/\bborder\b/)
    expect(raiz.className).not.toMatch(/shadow/)
    // E continua sendo um switch operável.
    expect(within(raiz).getByRole("switch")).toBeInTheDocument()
  })
})

// ── Achados da revisão da própria mudança ───────────────────────────────────

describe("associação rótulo ↔ controle", () => {
  it("aponta para o controle quando ele existe", () => {
    const { container } = render(<BooleanField field={campo()} {...props} />)
    const label = container.querySelector("label")
    // O Switch do Radix é um `<button role="switch">`, e button é elemento
    // rotulável: clicar no rótulo alterna o campo.
    expect(label).toHaveAttribute("for", "overwrite")
    expect(container.querySelector("#overwrite")).toBeInTheDocument()
  })

  it("não aponta para nada quando o controle é de terceiros", () => {
    // `<label for>` para um id inexistente é associação QUEBRADA: o leitor de
    // tela anuncia um rótulo órfão e o clique não faz nada. Acontecia no
    // ObjectField (JsonEditor) e nos dois campos com Monaco.
    render(<FieldLabel field={campo()} htmlFor={null} />)
    expect(document.querySelector("label")).not.toHaveAttribute("for")
  })
})

describe("o ícone de ajuda é operável pelo teclado", () => {
  it("mantém indicador de foco visível", () => {
    // `outline-none` sem substituto apagaria o único sinal de onde o teclado
    // está — e o gatilho não tem texto, então a mudança de cor sozinha é fraca
    // demais para servir de indicador.
    render(<FieldLabel field={campo()} />)
    const gatilho = screen.getByRole("button", { name: /^Ajuda:/ })
    expect(gatilho.className).toMatch(/focus-visible:ring/)
  })
})
