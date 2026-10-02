import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { WorkspaceBadge } from "@/app/components/workspace/workspace-badge"

// O papel era derivado de `owner_id === currentUserId`, o que só sabe responder
// "dono ou não": admin, operador e editor caíam todos em "Convidado". Depois que
// o cabeçalho passou a exibir só nome + papel, esse rótulo virou metade do que a
// barra diz — e dizer "Convidado" a um admin é simplesmente errado.

const base = { id_hash: "ws-1", name: "Bacia do Paranapanema", description: null, is_default: false }

afterEach(cleanup)

describe("papel exibido no badge de workspace", () => {
  it("nomeia o papel real em vez de generalizar para Convidado", () => {
    render(<WorkspaceBadge workspace={{ ...base, owner_id: "u-9", my_role: "admin" }} showName showRole currentUserId="u-1" />)
    expect(screen.getByText("Admin")).toBeTruthy()
    expect(screen.queryByText("Convidado")).toBeNull()
  })

  it("reconhece o dono por my_role, sem depender do id do usuário", () => {
    render(<WorkspaceBadge workspace={{ ...base, owner_id: null, my_role: "owner" }} showName showRole currentUserId="u-1" />)
    expect(screen.getByText("Proprietário")).toBeTruthy()
  })

  it("continua reconhecendo o dono pela comparação de id quando my_role falta", () => {
    render(<WorkspaceBadge workspace={{ ...base, owner_id: "u-1", my_role: null }} showName showRole currentUserId="u-1" />)
    expect(screen.getByText("Proprietário")).toBeTruthy()
  })

  it("usa Convidado só quando o papel é mesmo desconhecido", () => {
    render(<WorkspaceBadge workspace={{ ...base, owner_id: "u-9", my_role: null }} showName showRole currentUserId="u-1" />)
    expect(screen.getByText("Convidado")).toBeTruthy()
  })
})
