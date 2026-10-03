import { describe, it, expect } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { DispatchTierBadge } from "@/app/components/shared/dispatch-tier-badge"

// The badge says where the run ACTUALLY ran, only when that differs from what was expected.

describe("DispatchTierBadge", () => {
  it("\"rodou no pool\" só aparece com pool + workspace dedicado", () => {
    render(<DispatchTierBadge tier="pool" dedicado />)
    expect(screen.getByText("rodou no pool")).toBeTruthy()
    cleanup()
    // On Shared, the pool is the only destination: a badge on every row would be noise.
    const { container } = render(<DispatchTierBadge tier="pool" dedicado={false} />)
    expect(container.textContent).toBe("")
  })

  it("reserva aparece sempre — nunca é o caminho esperado", () => {
    render(<DispatchTierBadge tier="fallback" dedicado={false} />)
    expect(screen.getByText("reserva")).toBeTruthy()
  })

  it("primary e runs sem registro não ganham selo", () => {
    const a = render(<DispatchTierBadge tier="primary" dedicado />)
    expect(a.container.textContent).toBe("")
    cleanup()
    const b = render(<DispatchTierBadge tier={null} dedicado />)
    expect(b.container.textContent).toBe("")
  })
})
