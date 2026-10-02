/**
 * Campo de fichas — a lista de colunas do Join por Atributo.
 *
 * Era um texto separado por vírgula: não mostrava o que já estava lá, e remover
 * um nome do meio significava editar a string. O formato antigo continua nas
 * definitions salvas, então o campo tem de LER os dois.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent } from "@testing-library/react"

import ChipsField, {
  fichasNovas,
  lerFichas,
} from "@/app/components/workflow/nodes-configuration/fields/chips-field"
import { INodesPropertyAPI } from "@/service/types"

afterEach(cleanup)

const campo = {
  name: "columns",
  label: "Colunas de B a trazer",
  type: "chips",
  default: [],
  description: null,
} as unknown as INodesPropertyAPI

function montar(valor: unknown) {
  const setNodeField = vi.fn()
  render(
    <ChipsField
      field={campo}
      values={{ columns: valor } as Record<string, string>}
      setNodeField={setNodeField}
    />,
  )
  return setNodeField
}

const entrada = () => screen.getByPlaceholderText(/Adicionar outra|Nome da coluna/)

describe("lerFichas", () => {
  it("lê a lista JSON que o campo grava", () => {
    expect(lerFichas('["pop","renda"]')).toEqual(["pop", "renda"])
  })

  it("lê o formato antigo, separado por vírgula", () => {
    // É o que está salvo nos workflows criados antes do campo mudar. Sem isto,
    // abrir um deles mostraria o campo vazio — e salvar apagaria a configuração.
    expect(lerFichas("pop, renda_media")).toEqual(["pop", "renda_media"])
  })

  it("lê uma lista de verdade", () => {
    expect(lerFichas(["a", " b "])).toEqual(["a", "b"])
  })

  it.each([undefined, null, "", "   ", "[]"])("%s vira lista vazia", (v) => {
    expect(lerFichas(v)).toEqual([])
  })

  it("JSON quebrado cai no formato de texto em vez de sumir com o valor", () => {
    expect(lerFichas('["pop", renda')).toEqual(['["pop"', "renda"])
  })
})

describe("fichasNovas", () => {
  it("separa uma colagem com vírgulas", () => {
    expect(fichasNovas("a, b ,c", [])).toEqual(["a", "b", "c"])
  })

  it("não repete o que já está na lista", () => {
    expect(fichasNovas("a, b", ["a"])).toEqual(["b"])
  })

  it("não repete dentro da própria colagem", () => {
    expect(fichasNovas("a, a", [])).toEqual(["a"])
  })

  it("entrada em branco não adiciona nada", () => {
    expect(fichasNovas("  , ,", [])).toEqual([])
  })
})

describe("ChipsField", () => {
  it("mostra uma ficha por coluna", () => {
    montar('["pop","renda"]')
    expect(screen.getByText("pop")).toBeInTheDocument()
    expect(screen.getByText("renda")).toBeInTheDocument()
  })

  it("Enter adiciona e grava como CSV — o formato que TODO leitor entende", () => {
    // Inclusive um executor com flow/ anterior à migração para fichas, que
    // ainda parseia com split(","): JSON-string lá virava coluna fantasma.
    const setNodeField = montar('["pop"]')
    fireEvent.change(entrada(), { target: { value: "renda" } })
    fireEvent.keyDown(entrada(), { key: "Enter" })
    expect(setNodeField).toHaveBeenCalledWith("columns", "pop, renda")
  })

  it("nome com vírgula (que o CSV nunca representou) cai no JSON", () => {
    const setNodeField = montar('["a,b"]')
    fireEvent.change(entrada(), { target: { value: "c" } })
    fireEvent.keyDown(entrada(), { key: "Enter" })
    expect(setNodeField).toHaveBeenCalledWith("columns", '["a,b","c"]')
  })

  it("a vírgula também fecha a ficha", () => {
    const setNodeField = montar("[]")
    fireEvent.change(entrada(), { target: { value: "pop" } })
    fireEvent.keyDown(entrada(), { key: "," })
    expect(setNodeField).toHaveBeenCalledWith("columns", "pop")
  })

  it("sair do campo com algo digitado adiciona", () => {
    // Perder o que se escreveu por ter clicado fora é o defeito clássico deste
    // tipo de campo.
    const setNodeField = montar("[]")
    fireEvent.change(entrada(), { target: { value: "renda" } })
    fireEvent.blur(entrada())
    expect(setNodeField).toHaveBeenCalledWith("columns", "renda")
  })

  it("o X remove só aquela coluna", () => {
    const setNodeField = montar('["pop","renda"]')
    fireEvent.click(screen.getByLabelText("Remover pop"))
    expect(setNodeField).toHaveBeenCalledWith("columns", "renda")
  })

  it("remover a última ficha grava \"\" — \"[]\" no split(\",\") antigo virava a coluna fantasma \"[]\"", () => {
    const setNodeField = montar('["pop"]')
    fireEvent.click(screen.getByLabelText("Remover pop"))
    expect(setNodeField).toHaveBeenCalledWith("columns", "")
  })

  it("Backspace no campo vazio remove a última", () => {
    const setNodeField = montar('["pop","renda"]')
    fireEvent.keyDown(entrada(), { key: "Backspace" })
    expect(setNodeField).toHaveBeenCalledWith("columns", "pop")
  })

  it("Backspace com texto digitado NÃO remove ficha", () => {
    const setNodeField = montar('["pop"]')
    fireEvent.change(entrada(), { target: { value: "re" } })
    fireEvent.keyDown(entrada(), { key: "Backspace" })
    expect(setNodeField).not.toHaveBeenCalled()
  })

  it("abre o formato antigo mostrando as fichas", () => {
    montar("pop, renda")
    expect(screen.getByText("pop")).toBeInTheDocument()
    expect(screen.getByText("renda")).toBeInTheDocument()
  })
})

describe("sugestões de coluna", () => {
  function comSugestoes(valor: unknown, sugestoes: string[]) {
    const setNodeField = vi.fn()
    render(
      <ChipsField
        field={campo}
        values={{ columns: valor } as Record<string, string>}
        setNodeField={setNodeField}
        sugestoes={sugestoes}
      />,
    )
    return setNodeField
  }

  it("oferece as colunas vistas na última execução", () => {
    comSugestoes("[]", ["populacao", "renda"])
    expect(screen.getByText(/Vistas na última execução/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "populacao" })).toBeInTheDocument()
  })

  it("clicar na sugestão adiciona a ficha", () => {
    const setNodeField = comSugestoes("[]", ["populacao"])
    fireEvent.click(screen.getByRole("button", { name: "populacao" }))
    expect(setNodeField).toHaveBeenCalledWith("columns", "populacao")
  })

  it("não oferece o que já é ficha", () => {
    // Repetir o que já foi escolhido só vira ruído na lista.
    comSugestoes('["populacao"]', ["populacao", "renda"])
    expect(screen.queryByRole("button", { name: "populacao" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "renda" })).toBeInTheDocument()
  })

  it("sem execução anterior, nenhum bloco de sugestão aparece", () => {
    // O nó nunca rodou: inventar uma lista seria pior que não mostrar nada.
    comSugestoes("[]", [])
    expect(screen.queryByText(/Vistas na última execução/)).not.toBeInTheDocument()
  })

  it("escrever um nome fora da lista continua valendo", () => {
    // É dica, não validação: o fluxo pode ter mudado desde a última execução.
    const setNodeField = comSugestoes("[]", ["populacao"])
    fireEvent.change(entrada(), { target: { value: "coluna_nova" } })
    fireEvent.keyDown(entrada(), { key: "Enter" })
    expect(setNodeField).toHaveBeenCalledWith("columns", "coluna_nova")
  })
})
