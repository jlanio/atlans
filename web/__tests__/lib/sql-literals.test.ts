/**
 * Detecção de `:placeholder` no editor SQL.
 *
 * O regex varria o texto cru da query, então `WHERE obs = 'urgente:revisar'`
 * fazia o painel "Parametros detectados" oferecer um `:revisar` que não existe.
 * Quem preenchesse aquele campo mandava um parâmetro fantasma para o backend —
 * que, pelo mesmo motivo, recusava a consulta inteira.
 *
 * Mesmas regras do scanner Python (`flow/utils/sql_guard.py`), e os casos aqui
 * espelham os de `tests/unit/test_query_param_formatter.py`.
 */
import { describe, it, expect } from "vitest"
import { mascararLiteraisSql, extrairPlaceholders } from "@/lib/sql-literals"

describe("mascararLiteraisSql", () => {
  it("preserva o comprimento — é o que faz dele um mapa de posições", () => {
    const casos = [
      "SELECT * FROM t WHERE obs = 'nota:importante'",
      "SELECT 1 -- com :bairro\nFROM t",
      "SELECT /* :x */ 1 FROM t",
      'SELECT t."col:esquisita" FROM t',
      "SELECT $$texto :nome$$ FROM t",
    ]
    for (const sql of casos) {
      expect(mascararLiteraisSql(sql)).toHaveLength(sql.length)
    }
  })

  it("apaga o conteúdo do literal e mantém o código", () => {
    const m = mascararLiteraisSql("SELECT a FROM t WHERE b = 'segredo' AND c = 1")
    expect(m).not.toContain("segredo")
    expect(m).toContain("SELECT a FROM t WHERE b =")
    expect(m).toContain("AND c = 1")
  })

  it("`--` dentro de string não abre comentário", () => {
    const m = mascararLiteraisSql("SELECT * FROM t WHERE obs = 'a--b' AND id = 1")
    expect(m).toContain("AND id = 1")
  })

  it("aspa dobrada escapa dentro da string", () => {
    const m = mascararLiteraisSql("SELECT 'a''b' AS x FROM t")
    expect(m).not.toContain("b")
    expect(m).toContain("AS x FROM t")
  })

  it("comentário de bloco aninhado fecha na profundidade certa", () => {
    const m = mascararLiteraisSql("SELECT /* a /* b */ c */ 1 FROM t")
    expect(m).toContain("1 FROM t")
    expect(m).not.toContain("c")
  })

  it("bloco não fechado não quebra — o usuário ainda está digitando", () => {
    expect(() => mascararLiteraisSql("SELECT 1 /* comecei a comentar")).not.toThrow()
  })
})

describe("extrairPlaceholders", () => {
  it("acha os placeholders reais, sem repetir, na ordem de aparição", () => {
    expect(extrairPlaceholders("SELECT * FROM t WHERE a = :zz AND b = :bb AND c = :zz"))
      .toEqual(["zz", "bb"])
  })

  it("ignora o que está dentro de string", () => {
    expect(extrairPlaceholders("SELECT * FROM notas WHERE obs = 'urgente:revisar'"))
      .toEqual([])
  })

  it("ignora o que está em comentário de linha e de bloco", () => {
    expect(extrairPlaceholders("SELECT 1 -- usar :bairro\nFROM t")).toEqual([])
    expect(extrairPlaceholders("SELECT /* :bairro */ 1 FROM t")).toEqual([])
  })

  it("não confunde cast `::` com placeholder", () => {
    expect(extrairPlaceholders("SELECT id::text FROM t WHERE b = :b")).toEqual(["b"])
  })

  it("hora dentro de literal não vira parâmetro", () => {
    expect(extrairPlaceholders("SELECT * FROM t WHERE h = '08:30' AND b = :b"))
      .toEqual(["b"])
  })

  it("acha o placeholder que vem depois de um literal com dois-pontos", () => {
    expect(extrairPlaceholders("SELECT * FROM t WHERE tag = 'nota:importante' AND id = :id"))
      .toEqual(["id"])
  })
})
