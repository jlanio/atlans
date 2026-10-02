import { describe, it, expect, afterEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

import { NomeDeArquivo } from "@/app/components/home/nome-de-arquivo"

afterEach(cleanup)

describe("NomeDeArquivo — a elipse cai no MEIO", () => {
  it("o fim do nome fica num pedaço que não encolhe", () => {
    // `truncate` comia justamente a versão e a extensão: numa lista de
    // `…_v1`, `…_v2`, `…_v3` todas as linhas viravam o mesmo prefixo.
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
    // `nome.slice` cortava o par substituto no meio e os dois pedaços saíam
    // com "\uFFFD". O Drive aceita emoji em nome de arquivo.
    const nome = "relatorio🔥🔥🔥🔥🔥🔥🔥final"
    // Substituto SOLTO — um alto sem o baixo, ou um baixo sem o alto. Um emoji
    // inteiro é um par de substitutos, então casar a classe toda acusaria os
    // legítimos também.
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
