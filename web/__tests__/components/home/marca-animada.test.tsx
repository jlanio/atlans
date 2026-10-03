import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"

import MarcaAnimada from "@/app/components/home/assistente/marca-animada"

/** The three-node mark of the pending item: the shape and the API; the animation is CSS (`globals.css`). */
describe("MarcaAnimada", () => {
  it("é um SVG decorativo com três nós, três trilhos e três traços, no tamanho pedido", () => {
    const { container } = render(<MarcaAnimada size={20} className="x" />)
    const svg = container.querySelector("svg")!
    expect(svg.getAttribute("aria-hidden")).toBe("true")
    expect(svg.getAttribute("focusable")).toBe("false")
    expect(svg.getAttribute("width")).toBe("20")
    expect(svg.classList.contains("home-marca-anim")).toBe(true)
    expect(svg.classList.contains("x")).toBe(true)
    expect(svg.querySelectorAll("circle.no").length).toBe(3)
    expect(svg.querySelectorAll("path.trilho").length).toBe(3)
    expect(svg.querySelectorAll("path.traco").length).toBe(3)
    expect(svg.querySelector("g.respira")).toBeTruthy()
  })

  it("no tamanho padrão do ExecActivity, sem classe extra", () => {
    const { container } = render(<MarcaAnimada />)
    const svg = container.querySelector("svg")!
    expect(svg.getAttribute("width")).toBe("14")
    expect(svg.getAttribute("class")).toBe("home-marca-anim")
  })
})
