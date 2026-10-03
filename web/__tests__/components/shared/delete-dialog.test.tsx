import { describe, it, expect, afterEach, vi } from "vitest"
import { useState } from "react"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"

/** The dialog is shared and portaled to <body>: whoever opens it from Home passes `home-portal`. */
afterEach(cleanup)

const montar = (className?: string) =>
  render(
    <Dialog open>
      <DeleteDialog title="Excluir x" description="d" onConfirm={() => {}} className={className} />
    </Dialog>,
  )

describe("DeleteDialog — a paleta de quem o abre", () => {
  it("repassa className ao DialogContent", () => {
    montar("home-portal")
    expect(screen.getByRole("dialog").className).toContain("home-portal")
  })

  it("sem className, o diálogo é o de sempre", () => {
    montar()
    expect(screen.getByRole("dialog").className).not.toContain("home-portal")
  })
})

describe("DeleteDialog — confirmação por digitação", () => {
  /** A deletion that only finishes when the test says so. */
  function lenta() {
    let terminar!: () => void
    const onConfirm = vi.fn(() => new Promise<void>(res => { terminar = res }))
    return { onConfirm, terminar: () => terminar() }
  }

  it("o botão só libera com o texto EXATO, e o Enter segue a mesma regra", () => {
    const onConfirm = vi.fn()
    render(
      <Dialog open>
        <DeleteDialog title="Excluir x" description="d" confirmarDigitando="REVOGAR" onConfirm={onConfirm} />
      </Dialog>,
    )
    const campo = screen.getByPlaceholderText("REVOGAR")
    const botao = screen.getByRole("button", { name: "Excluir" })
    expect(botao).toBeDisabled()

    fireEvent.change(campo, { target: { value: "revogar" } })
    fireEvent.keyDown(campo, { key: "Enter" })
    expect(botao).toBeDisabled()
    expect(onConfirm).not.toHaveBeenCalled()

    fireEvent.change(campo, { target: { value: "REVOGAR" } })
    expect(botao).toBeEnabled()
  })

  it("Enter, Enter e o clique numa ação lenta confirmam UMA vez, com as saídas travadas", async () => {
    const { onConfirm, terminar } = lenta()
    render(
      <Dialog open>
        <DeleteDialog title="Excluir x" description="d" confirmarDigitando="x" onConfirm={onConfirm} />
      </Dialog>,
    )
    const campo = screen.getByPlaceholderText("x")
    fireEvent.change(campo, { target: { value: "x" } })
    fireEvent.keyDown(campo, { key: "Enter" })
    fireEvent.keyDown(campo, { key: "Enter" })
    fireEvent.click(screen.getByRole("button", { name: /Excluindo/ }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("button", { name: "Fechar" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled()

    terminar()
    await waitFor(() => expect(screen.getByRole("button", { name: "Excluir" })).toBeEnabled())
  })

  it("durante a ação o campo fica só leitura, com o foco: depois de uma falha, o Enter tenta de novo", async () => {
    // The failure as the dialogs deliver it: `useAcaoDeDialogo` shows the toast
    // and resolves, and the dialog stays open so the person can try again.
    let falhar!: () => void
    const onConfirm = vi.fn(() => new Promise<void>(resolver => { falhar = resolver }))
    render(
      <Dialog open>
        <DeleteDialog title="Excluir x" description="d" confirmarDigitando="x" onConfirm={onConfirm} />
      </Dialog>,
    )
    const campo = screen.getByPlaceholderText("x") as HTMLInputElement
    fireEvent.change(campo, { target: { value: "x" } })
    campo.focus()
    fireEvent.keyDown(campo, { key: "Enter" })

    // `disabled` would make the browser take focus away from the field (jsdom
    // doesn't apply that rule; the attribute is what can be checked here).
    expect(campo).not.toBeDisabled()
    expect(campo.readOnly).toBe(true)
    expect(document.activeElement).toBe(campo)

    falhar()
    await waitFor(() => expect(campo.readOnly).toBe(false))
    fireEvent.keyDown(campo, { key: "Enter" })
    expect(onConfirm).toHaveBeenCalledTimes(2)
  })

  it("segurar o Enter (auto-repetição) não confirma", () => {
    const onConfirm = vi.fn()
    render(
      <Dialog open>
        <DeleteDialog title="Excluir x" description="d" confirmarDigitando="x" onConfirm={onConfirm} />
      </Dialog>,
    )
    const campo = screen.getByPlaceholderText("x")
    fireEvent.change(campo, { target: { value: "x" } })
    fireEvent.keyDown(campo, { key: "Enter", repeat: true })
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it("o que foi digitado não sobrevive a fechar e reabrir", async () => {
    // The dialog opened by a menu item stays mounted inside the closed
    // `Dialog`: it's the field that has to start out empty again.
    function Tela() {
      const [aberto, setAberto] = useState(true)
      return (
        <>
          <button onClick={() => setAberto(true)}>abrir</button>
          <Dialog open={aberto} onOpenChange={setAberto}>
            <DeleteDialog title="Excluir x" description="d" confirmarDigitando="nome" onConfirm={() => {}} />
          </Dialog>
        </>
      )
    }
    render(<Tela />)
    fireEvent.change(screen.getByPlaceholderText("nome"), { target: { value: "nome" } })
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" }))
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())

    fireEvent.click(screen.getByRole("button", { name: "abrir" }))
    expect(await screen.findByPlaceholderText("nome")).toHaveValue("")
  })

  it("os avisos (children) entram antes do campo de confirmação", () => {
    render(
      <Dialog open>
        <DeleteDialog title="Excluir x" description="d" confirmarDigitando="x" onConfirm={() => {}}>
          <p>os crons param</p>
        </DeleteDialog>
      </Dialog>,
    )
    const aviso = screen.getByText("os crons param")
    const campo = screen.getByPlaceholderText("x")
    expect(aviso.compareDocumentPosition(campo) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})
