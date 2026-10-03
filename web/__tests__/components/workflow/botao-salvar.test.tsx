/**
 * The Save button sits in the bottom column, away from the state chip. It
 * echoes the state with a dot (amber = there's something to save, red = the
 * last attempt failed) and with the title, which is what the hover and the
 * screen reader say.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup, fireEvent } from "@testing-library/react"

const salvar = vi.fn()
vi.mock("@/app/hooks/workflow/useSaveWorkflow", () => ({
  useSaveWorkflow: () => ({ isSaving: false, saveWorkflow: salvar }),
}))

import SaveWorkflow from "@/app/components/workflow/buttons/save-workflow"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"

const ponto = () => document.querySelector('[data-role="save-pending-dot"]')

beforeEach(() => {
  cleanup()
  salvar.mockReset()
  useWorkflowSaveStore.setState({ saveStatus: "idle" })
})

describe("botão Salvar", () => {
  it("em repouso: sem ponto, título neutro", () => {
    render(<SaveWorkflow />)
    expect(screen.getByRole("button", { name: "Salvar workflow (Ctrl+S)" })).toBeTruthy()
    expect(ponto()).toBeNull()
  })

  it("com alterações: ponto âmbar e título que pede o save", () => {
    useWorkflowSaveStore.setState({ saveStatus: "unsaved" })
    render(<SaveWorkflow />)
    expect(screen.getByRole("button", { name: "Salvar alterações (Ctrl+S)" })).toBeTruthy()
    expect(ponto()?.className).toContain("bg-amber-500")
  })

  it("depois de uma falha: ponto vermelho e título que oferece tentar de novo", () => {
    useWorkflowSaveStore.setState({ saveStatus: "error" })
    render(<SaveWorkflow />)
    expect(screen.getByRole("button", { name: "Falha ao salvar. Tentar novamente (Ctrl+S)" })).toBeTruthy()
    expect(ponto()?.className).toContain("bg-destructive")
  })

  it("clicar salva", () => {
    useWorkflowSaveStore.setState({ saveStatus: "unsaved" })
    render(<SaveWorkflow />)
    fireEvent.click(screen.getByRole("button"))
    expect(salvar).toHaveBeenCalledTimes(1)
  })
})
