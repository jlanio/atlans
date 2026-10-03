/**
 * The rule for when the camera follows the workflow being built.
 *
 * The test that justifies this file is the "grew a little" one: without slack,
 * auto-layout repositioning the nodes by a few pixels at each step would
 * trigger a fresh reframing on every draw — which is exactly the zoom jump the
 * rule exists to remove.
 */
import { describe, it, expect, afterEach, vi } from "vitest"

import {
  cabeNoEnquadrado,
  semMovimento,
  FIT_PADDING,
  type Caixa,
} from "@/app/components/workflow/utils/enquadrar"

const caixa = (x: number, y: number, width: number, height: number): Caixa =>
  ({ x, y, width, height })

describe("cabeNoEnquadrado", () => {
  it("sem quadro anterior, sempre precisa enquadrar", () => {
    // The conversation's first draw: there is nothing to compare, and leaving the
    // person looking at a still screen while the workflow is born outside it is the
    // defect the framing exists to avoid.
    expect(cabeNoEnquadrado(caixa(0, 0, 100, 100), null)).toBe(false)
  })

  it("a mesma caixa cabe — ninguém se mexe", () => {
    const c = caixa(10, 10, 200, 120)
    expect(cabeNoEnquadrado(c, c)).toBe(true)
  })

  // The slack is EXPLICIT in these, not via the constant. Writing
  // `FOLGA_DO_ENQUADRAMENTO - 1` looks more robust and is the opposite: the
  // test's number starts moving along with the constant, and zeroing the constant
  // no longer breaks anything. Measured — the mutation survived written that way.
  it("crescer menos que a folga não move a câmera", () => {
    // This is the auto-layout case: nodes reposition slightly at each step, and
    // without this every step would become a reframing.
    const antes = caixa(0, 0, 200, 200)
    expect(cabeNoEnquadrado(caixa(0, 0, 230, 230), antes, 40)).toBe(true)
  })

  it("crescer mais que a folga move a câmera", () => {
    const antes = caixa(0, 0, 200, 200)
    expect(cabeNoEnquadrado(caixa(0, 0, 250, 200), antes, 40)).toBe(false)
  })

  it("a folga padrão é útil nos dois extremos", () => {
    // Zero would turn every auto-layout repositioning into a reframing — the
    // jump the rule exists to remove. And too large would swallow a whole
    // node coming in: the layout spaces nodes 180 apart, so the slack has to
    // stay well below that.
    expect(FIT_PADDING).toBeGreaterThan(0)
    expect(FIT_PADDING).toBeLessThan(90)
  })

  it("cada borda conta sozinha", () => {
    const antes = caixa(0, 0, 200, 200)
    const fora = 41
    // left, top, right, bottom — a new node can come in through any of them,
    // and a comparison that only looked at width and height would miss the
    // first two.
    expect(cabeNoEnquadrado(caixa(-fora, 0, 200, 200), antes)).toBe(false)
    expect(cabeNoEnquadrado(caixa(0, -fora, 200, 200), antes)).toBe(false)
    expect(cabeNoEnquadrado(caixa(0, 0, 200 + fora, 200), antes)).toBe(false)
    expect(cabeNoEnquadrado(caixa(0, 0, 200, 200 + fora), antes)).toBe(false)
  })

  it("o fluxo mudar de lugar move a câmera", () => {
    // Redraw with different geometry: the box has the same size and is no
    // longer where it was.
    expect(cabeNoEnquadrado(caixa(900, 900, 200, 200), caixa(0, 0, 200, 200))).toBe(false)
  })

  it("encolher não move a câmera", () => {
    // A smaller workflow stays within what is already visible; dragging the camera
    // to tighten the zoom would be movement without information.
    expect(cabeNoEnquadrado(caixa(50, 50, 20, 20), caixa(0, 0, 200, 200))).toBe(true)
  })
})

describe("semMovimento", () => {
  afterEach(() => { vi.unstubAllGlobals() })

  it("respeita quem pediu menos movimento", () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })))
    expect(semMovimento()).toBe(true)
  })

  it("é falso quando ninguém pediu", () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false })))
    expect(semMovimento()).toBe(false)
  })

  it("sem `matchMedia` não quebra — e não some com a animação", () => {
    // jsdom does not implement `matchMedia`, and the same goes for server
    // rendering. Without the guard this would be a TypeError mid-draw; and the
    // default has to be "there is motion", otherwise an environment without the
    // API would turn off the animation for everyone.
    vi.stubGlobal("matchMedia", undefined)
    expect(semMovimento()).toBe(false)
  })
})
