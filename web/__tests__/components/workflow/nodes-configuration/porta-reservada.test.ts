/**
 * Validação do nome de uma porta de sub-fluxo.
 *
 * `subWorkflowResult` é o nome sob o qual o node SubWorkflow devolve ao pai o
 * dict INTEIRO do filho, ao lado das chaves individuais. Uma porta de saída com
 * esse nome sobrescrevia o envelope: quem lesse `subWorkflowResult` no pai
 * recebia o valor daquela porta em vez do conjunto — sem erro, com o dado
 * errado. O executor passou a recusar; aqui o operador vê o motivo enquanto
 * digita.
 */
import { describe, it, expect } from "vitest"

import {
  PORTA_RESERVADA,
  problemaNaPorta,
} from "@/app/components/workflow/nodes-configuration/sub-workflow-ports-helper"

describe("problemaNaPorta", () => {
  it("recusa o nome reservado na saída", () => {
    const problema = problemaNaPorta(PORTA_RESERVADA, "output", false)
    expect(problema).toContain(PORTA_RESERVADA)
    expect(problema).toContain("reservado")
  })

  it("aceita o mesmo nome na entrada", () => {
    // Na entrada o nome não chega ao pai — não há envelope para colidir, e
    // barrar ali seria uma regra sem causa.
    expect(problemaNaPorta(PORTA_RESERVADA, "input", false)).toBeNull()
  })

  it("aceita nome normal", () => {
    expect(problemaNaPorta("area_total", "output", false)).toBeNull()
  })

  it("vazio não é erro — é a porta recém-adicionada, ainda sendo digitada", () => {
    expect(problemaNaPorta("", "output", false)).toBeNull()
  })

  it.each(["com espaço", "área", "1inicio", "traço-no-meio"])(
    "recusa %s como identificador", (nome) => {
      expect(problemaNaPorta(nome, "output", false)).toContain("underscore")
    })

  it.each(["com espaço", "espaco no fim ", " no começo", "dois  juntos"])(
    "explica o espaço em %p em vez de dar a regra genérica", (nome) => {
      // O campo deixou de aplicar `trim` a cada tecla: antes o espaço sumia
      // enquanto se digitava, como se a tecla não funcionasse, e esta mensagem
      // nunca chegava a ser exibida. É o erro mais comum e o único com uma
      // correção óbvia a sugerir.
      const problema = problemaNaPorta(nome, "output", false)
      expect(problema).toContain("Espaços não são aceitos")
      expect(problema).toContain("minha_porta")
    })

  it("o espaço vence a duplicata e o nome reservado", () => {
    // Duas mensagens não cabem na linha, e não adianta falar de colisão de nome
    // enquanto o nome nem é um identificador válido.
    expect(problemaNaPorta("com espaço", "output", true)).toContain("Espaços")
    expect(problemaNaPorta(`${PORTA_RESERVADA} `, "output", false)).toContain("Espaços")
  })

  it("aponta a duplicata", () => {
    expect(problemaNaPorta("area", "output", true)).toBe("Chave duplicada.")
  })

  it("nome inválido vence a duplicata", () => {
    // As duas mensagens juntas não cabem na linha; a de sintaxe é a que precisa
    // ser corrigida primeiro, e corrigi-la costuma desfazer a duplicata.
    expect(problemaNaPorta("com espaço", "output", true)).toContain("underscore")
  })
})

describe("problemaNaPorta — nomes reservados ao executor", () => {
  it.each(["__artifact__", "__response__", "__x"])(
    "recusa %s", (nome) => {
      // O node descarta toda chave começada por `__` ANTES da allowlist. Uma
      // porta assim não recebe nada, e nem entra na lista de descartes do log:
      // some sem deixar rastro em lugar nenhum.
      expect(problemaNaPorta(nome, "output", false)).toContain("reservados ao executor")
    })

  it("vale também na entrada — o filtro é o mesmo dos dois lados", () => {
    expect(problemaNaPorta("__x", "input", false)).toContain("reservados ao executor")
  })

  it("um underscore só continua válido", () => {
    expect(problemaNaPorta("_interno", "output", false)).toBeNull()
  })
})
