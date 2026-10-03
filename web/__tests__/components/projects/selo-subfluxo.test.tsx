/**
 * Badge that distinguishes, in the listing, a workflow made to be CALLED by another.
 *
 * The difference is not decorative: a sub-workflow generally has no trigger of its own,
 * and the card's run button fires a run that does not do what is expected. Without the
 * badge, both kinds of project are the same card.
 */
import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

import { SeloSubFluxo } from "@/app/components/projects/selo-subfluxo"

afterEach(cleanup)

describe("SeloSubFluxo", () => {
  it("aparece no workflow que declara saída de sub-fluxo", () => {
    render(<SeloSubFluxo workflow={{ is_subworkflow: true }} />)
    expect(screen.getByText("Sub-fluxo")).toBeInTheDocument()
  })

  it("o texto de ajuda avisa sobre o gatilho ausente", () => {
    // It is the actionable part: it explains why running from the list does not help.
    render(<SeloSubFluxo workflow={{ is_subworkflow: true }} />)
    expect(screen.getByTitle(/não ter gatilho próprio/)).toBeInTheDocument()
  })

  it("não aparece em workflow comum", () => {
    render(<SeloSubFluxo workflow={{ is_subworkflow: false }} />)
    expect(screen.queryByText("Sub-fluxo")).not.toBeInTheDocument()
  })

  it("não aparece quando o campo não veio", () => {
    // A backend older than this field, or a cached response: absence must not
    // mark every project as a sub-workflow.
    render(<SeloSubFluxo workflow={{}} />)
    expect(screen.queryByText("Sub-fluxo")).not.toBeInTheDocument()
  })
})
