import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

/**
 * ShellSidebar swaps the shell by route: HomeSidebar ONLY on `/` (exact match),
 * AppSidebar everywhere else. A `startsWith("/")` would match everything.
 */
const nav = vi.hoisted(() => ({ pathname: "/" }))
vi.mock("next/navigation", () => ({ usePathname: () => nav.pathname }))
vi.mock("@/app/components/sidebar/app-sidebar", () => ({ default: () => <div data-testid="app-sidebar" /> }))
vi.mock("@/app/components/sidebar/home-sidebar", () => ({ default: () => <div data-testid="home-sidebar" /> }))

import ShellSidebar from "@/app/components/sidebar/shell-sidebar"

beforeEach(() => cleanup())

describe("ShellSidebar", () => {
  it("renderiza o HomeSidebar em /", () => {
    nav.pathname = "/"
    render(<ShellSidebar />)
    expect(screen.getByTestId("home-sidebar")).toBeTruthy()
    expect(screen.queryByTestId("app-sidebar")).toBeNull()
  })

  it("renderiza o AppSidebar fora de / (exato)", () => {
    for (const p of ["/projects", "/workflow/create", "/dashboard", "/artifacts"]) {
      cleanup()
      nav.pathname = p
      render(<ShellSidebar />)
      expect(screen.getByTestId("app-sidebar"), p).toBeTruthy()
      expect(screen.queryByTestId("home-sidebar"), p).toBeNull()
    }
  })
})
