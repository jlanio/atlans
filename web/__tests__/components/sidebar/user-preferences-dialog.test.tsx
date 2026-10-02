import { describe, it, expect, vi, afterEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

/** O diálogo é portado ao <body>: aberto do menu de conta da Home, leva `home-portal`. */
vi.mock("@/context/ThemeContext", () => ({ useTheme: () => ({ theme: "light", setTheme: vi.fn() }) }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { username: "fulana", email: "fulana@exemplo.com", role: "user" } }, status: "authenticated" }),
}))

import { UserPreferencesDialog } from "@/app/components/sidebar/user-preferences-dialog"

afterEach(cleanup)

const montar = (className?: string) =>
  render(<UserPreferencesDialog open onOpenChange={() => {}} className={className} />)

describe("UserPreferencesDialog — a paleta de quem o abre", () => {
  it("repassa className ao DialogContent, sem perder a largura de sempre", () => {
    montar("home-portal")
    const dialogo = screen.getByRole("dialog")
    expect(dialogo.className).toContain("home-portal")
    expect(dialogo.className).toContain("max-w-md")
  })

  it("sem className, o diálogo é o de sempre", () => {
    montar()
    expect(screen.getByRole("dialog").className).not.toContain("home-portal")
  })
})
