import { describe, it, expect, afterEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

import { NomeDeArquivo } from "@/app/components/home/nome-de-arquivo"

afterEach(cleanup)

describe("NomeDeArquivo — a elipse cai no MEIO", () => {
  it("o fim do nome fica num pedaço que não encolhe", () => {
    // `truncate` ate precisely the version and the extension: in a list of
    // `…_v1`, `…_v2`, `…_v3` all rows became the same prefix.
    const { container } = render(<NomeDeArquivo nome="focos_calor_MT_2024_consolidado_v3.geojson" />)
    const [cabeca, cauda] = Array.from(container.firstElementChild!.children) as HTMLElement[]
    expect(cabeca.className).toContain("truncate")
    expect(cauda.className).toContain("shrink-0")
    expect(cauda.textContent).toBe("_v3.geojson")
    expect(cabeca.textContent).toBe("focos_calor_MT_2024_consolidado")
  })

  it("o nome inteiro continua no DOM — leitor de tela e cópia não perdem nada", () => {
    const nome = "áreas_prioritárias_conservação_cerrado.geojson"
    const { container } = render(<NomeDeArquivo nome={nome} />)
    expect(container.textContent).toBe(nome)
  })

  it("nome curto não é cortado: a cabeça fica vazia e o fim leva tudo", () => {
    const { container } = render(<NomeDeArquivo nome="mt.shp" />)
    const [cabeca, cauda] = Array.from(container.firstElementChild!.children) as HTMLElement[]
    expect(cabeca.textContent).toBe("")
    expect(cauda.textContent).toBe("mt.shp")
  })

  it("não parte emoji ao meio: o corte conta pontos de código, não UTF-16", () => {
    // `nome.slice` cut the surrogate pair in the middle and both pieces came out
    // with "�". The Drive accepts emoji in file names.
    const nome = "relatorio🔥🔥🔥🔥🔥🔥🔥final"
    // A LONE surrogate — a high one without the low, or a low one without the high. A whole
    // emoji is a surrogate pair, so matching the entire class would flag the
    // legitimate ones too.
    const SOLTO = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/
    const { container } = render(<NomeDeArquivo nome={nome} />)
    expect(container.textContent).toBe(nome)
    for (const pedaco of Array.from(container.firstElementChild!.children)) {
      expect(pedaco.textContent, pedaco.textContent ?? "").not.toMatch(SOLTO)
    }
  })

  it("recorta no envoltório: a cauda não vaza por cima do que vem depois", () => {
    const { container } = render(<NomeDeArquivo nome="um_nome_bem_longo_de_artefato.geojson" />)
    expect((container.firstElementChild as HTMLElement).className).toContain("overflow-hidden")
  })
})
