/**
 * Validation of a sub-workflow port name.
 *
 * `subWorkflowResult` is the name under which the SubWorkflow node returns the
 * child's WHOLE dict to the parent, alongside the individual keys. An output
 * port with that name overwrote the envelope: whoever read `subWorkflowResult`
 * in the parent got that port's value instead of the whole set — no error, with
 * the wrong data. The executor now refuses it; here the operator sees the reason
 * while typing.
 */
import { describe, it, expect } from "vitest"

import {
  RESERVED_PORT,
  problemaNaPorta,
} from "@/app/components/workflow/nodes-configuration/sub-workflow-ports-helper"

describe("problemaNaPorta", () => {
  it("recusa o nome reservado na saída", () => {
    const problema = problemaNaPorta(RESERVED_PORT, "output", false)
    expect(problema).toContain(RESERVED_PORT)
    expect(problema).toContain("reservado")
  })

  it("aceita o mesmo nome na entrada", () => {
    // On the input side the name doesn't reach the parent — there's no envelope
    // to collide with, and blocking it there would be a rule with no cause.
    expect(problemaNaPorta(RESERVED_PORT, "input", false)).toBeNull()
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
      // The field no longer applies `trim` on every keystroke: before, the space
      // vanished while typing, as if the key didn't work, and this message
      // never got to be shown. It's the most common error and the only one with
      // an obvious fix to suggest.
      const problema = problemaNaPorta(nome, "output", false)
      expect(problema).toContain("Espaços não são aceitos")
      expect(problema).toContain("minha_porta")
    })

  it("o espaço vence a duplicata e o nome reservado", () => {
    // Two messages don't fit on the line, and there's no point talking about a
    // name collision while the name isn't even a valid identifier.
    expect(problemaNaPorta("com espaço", "output", true)).toContain("Espaços")
    expect(problemaNaPorta(`${RESERVED_PORT} `, "output", false)).toContain("Espaços")
  })

  it("aponta a duplicata", () => {
    expect(problemaNaPorta("area", "output", true)).toBe("Chave duplicada.")
  })

  it("nome inválido vence a duplicata", () => {
    // Both messages together don't fit on the line; the syntax one is the one
    // that needs fixing first, and fixing it usually undoes the duplicate.
    expect(problemaNaPorta("com espaço", "output", true)).toContain("underscore")
  })
})

describe("problemaNaPorta — nomes reservados ao executor", () => {
  it.each(["__artifact__", "__response__", "__x"])(
    "recusa %s", (nome) => {
      // The node discards every key starting with `__` BEFORE the allowlist. A
      // port like that receives nothing, and doesn't even enter the log's list
      // of discards: it disappears without leaving a trace anywhere.
      expect(problemaNaPorta(nome, "output", false)).toContain("reservados ao executor")
    })

  it("vale também na entrada — o filtro é o mesmo dos dois lados", () => {
    expect(problemaNaPorta("__x", "input", false)).toContain("reservados ao executor")
  })

  it("um underscore só continua válido", () => {
    expect(problemaNaPorta("_interno", "output", false)).toBeNull()
  })
})
