/**
 * Sugestões de coluna no editor do SetFields ("redefinir campos").
 *
 * O helper substitui o renderizador de campos — onde a sugestão nasce — e por
 * isso era o único nó de coluna do fluxo que nunca via uma dica. Cada seção
 * oferece as colunas conhecidas e o clique preenche a primeira linha vazia ou
 * abre uma nova; o que já foi digitado nunca é substituído.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent, within } from "@testing-library/react"

import SetFieldsHelper from "@/app/components/workflow/nodes-configuration/set-fields-helper"

afterEach(cleanup)

function montar(
  values: Record<string, unknown>,
  sugestoes: string[] = ["cod", "nome"],
  desatualizadas = false,
) {
  const setNodeField = vi.fn()
  render(
    <SetFieldsHelper
      values={values as never}
      setNodeField={setNodeField}
      hasUnsaved={false}
      sugestoesDeColunas={sugestoes}
      sugestoesDesatualizadas={desatualizadas}
      sugestoesParciais={false}
    />,
  )
  return setNodeField
}

const secao = (titulo: RegExp) => {
  const el = screen.getByText(titulo).closest("section")
  if (!el) throw new Error("seção não encontrada")
  return within(el)
}

describe("SetFieldsHelper — sugestões", () => {
  it("clicar numa sugestão de Definir abre uma linha com o campo preenchido", () => {
    const setNodeField = montar({})
    fireEvent.click(secao(/Definir \/ Atualizar campos/i).getByRole("button", { name: "cod" }))
    expect(setNodeField).toHaveBeenCalledWith("setFields", { cod: "" })
  })

  it("linha vazia aberta é preenchida em vez de duplicada — e o valor digitado fica", () => {
    const setNodeField = montar({ setFields: { "": "{{ row.area }}" } })
    fireEvent.click(secao(/Definir \/ Atualizar campos/i).getByRole("button", { name: "nome" }))
    expect(setNodeField).toHaveBeenCalledWith("setFields", { nome: "{{ row.area }}" })
  })

  it("em Remover, o clique adiciona a ficha direto", () => {
    const setNodeField = montar({ removeFields: ["cod"] }, ["cod", "nome"])
    const remover = secao(/Remover campos/i)
    // "cod" já é ficha — só "nome" é oferecido.
    expect(remover.queryByRole("button", { name: "cod" })).not.toBeInTheDocument()
    fireEvent.click(remover.getByRole("button", { name: "nome" }))
    expect(setNodeField).toHaveBeenCalledWith("removeFields", { fields: ["cod", "nome"] })
  })

  it("em Renomear, o clique preenche o 'De' de uma linha nova", () => {
    const setNodeField = montar({})
    fireEvent.click(secao(/Renomear campos/i).getByRole("button", { name: "cod" }))
    expect(setNodeField).toHaveBeenCalledWith("renameFields", { cod: "" })
  })

  it("coluna já usada na seção some das sugestões DELA, não das outras", () => {
    montar({ setFields: { cod: "1" } }, ["cod", "nome"])
    expect(secao(/Definir/i).queryByRole("button", { name: "cod" })).not.toBeInTheDocument()
    expect(secao(/Renomear/i).getByRole("button", { name: "cod" })).toBeInTheDocument()
  })

  it("re-hidratado de run anterior, o rótulo avisa o frescor", () => {
    montar({}, ["cod"], true)
    expect(screen.getAllByText(/podem ter mudado/).length).toBeGreaterThan(0)
    expect(screen.queryByText(/Vistas na última execução —/)).not.toBeInTheDocument()
  })

  it("sem colunas conhecidas, nada de bloco de sugestão", () => {
    montar({}, [])
    expect(screen.queryByText(/Vistas/)).not.toBeInTheDocument()
  })
})
