/**
 * Attachments dropped onto the Home, in the assistant box.
 *
 * Two ideas under protection here:
 *
 *  1. **What travels with the message is EXACTLY what is in view.** Only the
 *     READY ones go into `comReferencia` and `sugestaoParaAnexos`; what is still
 *     uploading and what was refused are not mentioned — telling the assistant to look for
 *     a file that never reached the Drive is a false promise.
 *  2. **The refusal is the same as on the `/drive` screen.** `recusasDe` feeds the
 *     `ResultadoDoUpload` panel, with `classifyUploadError`'s classification — the
 *     two labels never diverge because they are the same piece.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { cleanup, render, screen, fireEvent } from "@testing-library/react"

import {
  AvisoDeAnexosRecusados, ChipsDeAnexo, ConviteDeSoltura,
  anexosProntos, comReferencia, sugestaoParaAnexos, recusasDe,
} from "@/app/components/home/assistente/anexos"
import type { Anexo } from "@/app/stores/homeStore"
import { IdiomaProvider } from "@/context/IdiomaContext"

afterEach(() => cleanup())

const pronto = (nome: string, id = nome): Anexo => ({ id, nome, bytes: 2048, estado: "pronto" })
const enviando = (nome: string, id = nome): Anexo => ({ id, nome, bytes: 2048, estado: "enviando" })
const recusado = (nome: string, tipo: Anexo["tipo"], motivo: string, id = nome): Anexo =>
  ({ id, nome, bytes: 2048, estado: "recusado", tipo, motivo })

describe("o texto que viaja com a mensagem", () => {
  it("comReferencia lista SÓ os prontos, depois do texto da pessoa", () => {
    const anexos = [pronto("municipios.geojson"), enviando("subindo.csv"), recusado("x.pdf", "extension", "não permitida")]
    const saida = comReferencia("compare as bases", anexos)
    expect(saida).toContain("compare as bases")
    expect(saida).toContain("municipios.geojson")
    expect(saida).not.toContain("subindo.csv")
    expect(saida).not.toContain("x.pdf")
  })

  it("sem nada pronto, a mensagem é a mesma — nenhuma referência", () => {
    expect(comReferencia("oi", [enviando("a.csv")])).toBe("oi")
    expect(comReferencia("oi", [])).toBe("oi")
  })

  it("com texto vazio e anexo pronto, a mensagem é só a referência (não fica em branco)", () => {
    const saida = comReferencia("", [pronto("a.csv")])
    expect(saida).toContain("a.csv")
    expect(saida.trim()).not.toBe("")
  })

  it("a sugestão nomeia o arquivo — e conta o resto quando há mais de um", () => {
    expect(sugestaoParaAnexos([pronto("a.csv")])).toBe("Analise a.csv")
    expect(sugestaoParaAnexos([pronto("a.csv"), pronto("b.geojson", "b")])).toMatch(/Analise a\.csv e mais 1 arquivo/)
    expect(sugestaoParaAnexos([enviando("a.csv")])).toBeNull()
  })
})

describe("os chips na caixa", () => {
  it("mostra subindo e pronto; o × só existe depois que chegou", () => {
    const onRemover = vi.fn()
    render(<ChipsDeAnexo anexos={[pronto("chegou.geojson"), enviando("subindo.csv")]} onRemover={onRemover} />)

    expect(screen.getByText("chegou.geojson")).toBeTruthy()
    expect(screen.getByText("subindo.csv")).toBeTruthy()
    // A single × — the ready one's. What is uploading cannot be removed midway.
    const remover = screen.getAllByRole("button", { name: /Tirar/i })
    expect(remover).toHaveLength(1)
    fireEvent.click(remover[0])
    expect(onRemover).toHaveBeenCalledWith("chegou.geojson")
  })

  it("os recusados NÃO entram na fileira de chips — vão para o aviso", () => {
    render(<ChipsDeAnexo anexos={[recusado("x.pdf", "extension", "não permitida")]} onRemover={vi.fn()} />)
    expect(screen.queryByText("x.pdf")).toBeNull()
    expect(screen.queryByTestId("chips-de-anexo")).toBeNull()
  })
})

describe("o aviso dos recusados", () => {
  it("recusasDe traduz para o formato do painel /drive, mantendo o tipo", () => {
    const r = recusasDe([recusado("x.pdf", "extension", "Extensão '.pdf' não permitida."), pronto("ok.csv")])
    expect(r).toEqual([{ fileName: "x.pdf", detail: "Extensão '.pdf' não permitida.", type: "extension" }])
  })

  it("mostra o painel com o motivo do servidor e fecha no ×", () => {
    const onFechar = vi.fn()
    render(<AvisoDeAnexosRecusados anexos={[recusado("mosaico.tif", "size", "Arquivo excede 200MB.")]} onFechar={onFechar} />)
    expect(screen.getByText("«mosaico.tif»")).toBeTruthy()
    expect(screen.getByText("Arquivo excede 200MB.")).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: /Fechar o resultado do envio/i }))
    expect(onFechar).toHaveBeenCalled()
  })

  it("em inglês: o rótulo do tipo, a contagem e o × no idioma; o motivo do servidor como veio", () => {
    render(
      <IdiomaProvider inicial={{ idioma: "en", detectado: "en", escolhido: null }}>
        <AvisoDeAnexosRecusados
          anexos={[recusado("a.tif", "size", "Arquivo excede 200MB."), recusado("b.exe", "extension", "x")]}
          onFechar={vi.fn()}
        />
      </IdiomaProvider>,
    )
    expect(screen.getByText("File too large")).toBeTruthy()
    expect(screen.getByText("Extension not allowed")).toBeTruthy()
    expect(screen.getByText("2 failures")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Close the upload result" })).toBeTruthy()
    expect(screen.getByText("Arquivo excede 200MB.")).toBeTruthy()
  })

  it("sem recusados, não renderiza nada", () => {
    const { container } = render(<AvisoDeAnexosRecusados anexos={[pronto("ok.csv")]} onFechar={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })
})

describe("o convite de soltura", () => {
  it("é o único realce do arraste — texto de anexar", () => {
    render(<ConviteDeSoltura />)
    expect(screen.getByText(/Solte para anexar à conversa/i)).toBeTruthy()
  })
})

describe("anexosProntos", () => {
  it("filtra só o que chegou ao Drive", () => {
    expect(anexosProntos([pronto("a"), enviando("b"), recusado("c", "other", "x")]).map((x) => x.nome)).toEqual(["a"])
  })
})
