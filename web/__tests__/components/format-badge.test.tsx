import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"

import { FormatBadge } from "@/app/components/artifacts/badges"

/**
 * The image map formats (png/jpg/pdf) have their own icon in the format
 * badge — an unknown format falls back to the generic code icon. Compares
 * the drawn SVG, without importing the icons: it is what the eye sees.
 */
function svgDe(format: string): string {
  const { container } = render(<FormatBadge format={format} />)
  return container.querySelector("svg")?.innerHTML ?? ""
}

describe("FormatBadge", () => {
  it("png e jpg usam o ícone de imagem, diferente do genérico", () => {
    const generic = svgDe("xyz")
    expect(svgDe("png")).not.toBe(generic)
    expect(svgDe("jpg")).toBe(svgDe("png"))
    expect(svgDe("jpeg")).toBe(svgDe("png"))
  })

  it("pdf tem ícone próprio, diferente do de imagem e do genérico", () => {
    expect(svgDe("pdf")).not.toBe(svgDe("png"))
    expect(svgDe("pdf")).not.toBe(svgDe("xyz"))
  })

  it("os formatos do Salvar arquivo têm ícone próprio, não o genérico", () => {
    const generic = svgDe("xyz")
    for (const format of ["gpkg", "kml", "kmz", "xlsx", "csv"]) {
      expect(svgDe(format), format).not.toBe(generic)
    }
    expect(svgDe("kmz")).toBe(svgDe("kml"))
    expect(svgDe("xlsx")).not.toBe(svgDe("csv"))
  })

  it("mostra o formato em maiúsculas", () => {
    const { getByText } = render(<FormatBadge format="png" />)
    expect(getByText("PNG")).toBeTruthy()
  })
})
