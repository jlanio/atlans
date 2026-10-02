import { describe, expect, it } from "vitest"
import { corDoTom, tomDaAresta, tomDoHandle } from "@/app/components/workflow/utils/exec-colors"

describe("tomDaAresta", () => {

  it("segue o status da origem quando ele existe", () => {
    expect(tomDaAresta("started", "", false)).toBe("running")
    expect(tomDaAresta("completed", "", false)).toBe("success")
    expect(tomDaAresta("failed", "", false)).toBe("error")
  })

  it("cobre unknown, que caía no cinza enquanto o card ficava âmbar", () => {
    expect(tomDaAresta("unknown", "", false)).toBe("unknown")
  })

  it("deixa idle cair no handle, para o ramo true nascer verde", () => {
    expect(tomDaAresta("idle", "true", false)).toBe("success")
    expect(tomDaAresta("idle", "false", false)).toBe("error")
  })

  it("ignora `cancelled`: é status de workflow, nunca de nó", () => {
    // O cancelamento devolve os nós a `idle`; a aresta cai no handle/neutro.
    expect(tomDaAresta("cancelled", "", false)).toBe("idle")
  })

  it("dá o neutro ao ramo perdedor mesmo com a origem concluída", () => {
    expect(tomDaAresta("completed", "true", true)).toBe("idle")
  })

  it("cai no neutro sem status e sem handle de ramo", () => {
    expect(tomDaAresta(undefined, "", false)).toBe("idle")
    expect(tomDaAresta(undefined, "geometria", false)).toBe("idle")
  })
})

describe("corDoTom", () => {
  it("resolve para o token do tema, e não para um hex fixo", () => {
    expect(corDoTom("running")).toBe("var(--exec-running)")
    expect(corDoTom("idle")).toBe("var(--exec-idle)")
  })
})

describe("nome de porta vindo do usuário", () => {
  // `output_vars` é texto livre e as portas dinâmicas aceitam qualquer
  // identificador. Com colchete cru no mapa, `constructor` devolvia a função
  // `Object` em vez de undefined, e a cor da porta virava
  // `var(--exec-function Object() { [native code] })` — `var()` inválido, a
  // propriedade é descartada e a porta some do canvas.
  it.each(["constructor", "toString", "hasOwnProperty", "valueOf", "__proto__"])(
    "'%s' não vira tom nem cor",
    (nome) => {
      expect(tomDoHandle(nome)).toBeUndefined()
      expect(tomDaAresta(undefined, nome, false)).toBe("idle")
      expect(corDoTom(tomDaAresta(undefined, nome, false))).toBe("var(--exec-idle)")
    },
  )

  it("o mesmo vale para um status inesperado vindo do servidor", () => {
    expect(tomDaAresta("constructor", "", false)).toBe("idle")
  })

  it("não quebra o que já funcionava", () => {
    expect(tomDoHandle("true")).toBe("success")
    expect(tomDoHandle("false")).toBe("error")
    expect(tomDoHandle("saida_1")).toBeUndefined()
    expect(tomDoHandle(undefined)).toBeUndefined()
  })
})
