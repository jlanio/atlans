/**
 * Field help is a tooltip, not a paragraph.
 *
 * The configuration panel had become a wall of text: each field printed its
 * whole description below the control, and on a 7-field node (the most
 * configured ones have 6 to 10) the helper text took up more space than the
 * controls themselves. There are 182 descriptions in the catalog, median of 53
 * characters but with peaks of 210.
 *
 * The test that matters is the NEGATIVE one — the description must not be in
 * the document before hover. The paragraph comes back on its own the day
 * someone copies the old pattern (`<Label>` + `<p className="text-xs text-muted-foreground">`)
 * into a new field, and nothing besides this would notice.
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

// ── The label ───────────────────────────────────────────────────────────────

describe("FieldLabel", () => {
  it("mostra o rótulo e esconde a descrição até o hover", async () => {
    render(<FieldLabel field={campo()} />)

    expect(screen.getByText("Sobrescrever se já existir")).toBeInTheDocument()
    expect(screen.queryByText(AJUDA)).not.toBeInTheDocument()

    fireEvent.focus(screen.getByRole("button", { name: /^Ajuda:/ }))
    // Radix duplicates the content (one visible, one for screen readers), hence
    // `getAllBy`: `getBy` would fail on multiple elements, which would be a
    // false negative.
    expect((await screen.findAllByText(AJUDA)).length).toBeGreaterThan(0)
  })

  it("o gatilho é um button com nome acessível", () => {
    render(<FieldLabel field={campo()} />)
    const gatilho = screen.getByRole("button", { name: "Ajuda: Sobrescrever se já existir" })
    // `type="button"` because the panel has a form around it: without it,
    // pressing Enter in the field would trigger the tooltip instead of saving.
    expect(gatilho).toHaveAttribute("type", "button")
  })

  it("campo sem descrição não ganha ícone de ajuda", () => {
    render(<FieldLabel field={campo({ description: undefined })} />)
    expect(screen.queryByRole("button", { name: /^Ajuda:/ })).not.toBeInTheDocument()
  })
})

// ── No field prints the description directly on the screen ──────────────────

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

// ── Specific regressions ────────────────────────────────────────────────────

describe("regressões", () => {
  it("StringField não usa a descrição como placeholder", () => {
    // It appeared TWICE: in the placeholder and in the paragraph. A placeholder
    // is for an example value, not for the field's documentation.
    //
    // It needs `nodeFound` to fall into the ExpressionInput branch — that's
    // where the placeholder existed. Without it the component renders the plain
    // `<Input>` and the test would pass without touching the code that matters.
    // And ExpressionInput uses `useNodes`/`useEdges`, hence the ReactFlowProvider.
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
    // It was the only field with a frame and shadow. In a mixed list, that made
    // a toggle weigh more than the select that governs the whole node.
    const { container } = render(<BooleanField field={campo()} {...props} />)
    const raiz = container.firstElementChild as HTMLElement
    expect(raiz.className).not.toMatch(/\bborder\b/)
    expect(raiz.className).not.toMatch(/shadow/)
    // And it's still an operable switch.
    expect(within(raiz).getByRole("switch")).toBeInTheDocument()
  })
})

// ── Findings from reviewing the change itself ───────────────────────────────

describe("associação rótulo ↔ controle", () => {
  it("aponta para o controle quando ele existe", () => {
    const { container } = render(<BooleanField field={campo()} {...props} />)
    const label = container.querySelector("label")
    // Radix's Switch is a `<button role="switch">`, and button is a labelable
    // element: clicking the label toggles the field.
    expect(label).toHaveAttribute("for", "overwrite")
    expect(container.querySelector("#overwrite")).toBeInTheDocument()
  })

  it("não aponta para nada quando o controle é de terceiros", () => {
    // A `<label for>` pointing to a nonexistent id is a BROKEN association: the
    // screen reader announces an orphan label and clicking does nothing. It
    // happened in ObjectField (JsonEditor) and in the two Monaco fields.
    render(<FieldLabel field={campo()} htmlFor={null} />)
    expect(document.querySelector("label")).not.toHaveAttribute("for")
  })
})

describe("o ícone de ajuda é operável pelo teclado", () => {
  it("mantém indicador de foco visível", () => {
    // `outline-none` without a replacement would erase the only sign of where
    // the keyboard is — and the trigger has no text, so a color change alone is
    // too weak to serve as an indicator.
    render(<FieldLabel field={campo()} />)
    const gatilho = screen.getByRole("button", { name: /^Ajuda:/ })
    expect(gatilho.className).toMatch(/focus-visible:ring/)
  })
})
