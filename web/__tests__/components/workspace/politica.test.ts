import { describe, it, expect } from "vitest"
import {
  avisoDeMudancaDePolitica, avisoDePreFlight, capacidadeCheia, classeDoModo, contarOnline, descreverCapacidade,
  descreverPolitica, descreverQueda, disponiveisNaCadeia, membrosInativos, politicaEmAlerta, rotuloDaAcaoDePolitica,
  rotuloDoModo, rotuloDoStatus, saudeDoPool, semSinal,
} from "@/app/components/workspace/politica"
import { isolada, membro, politica } from "../../fixtures/politica"

describe("vocabulário", () => {
  it("um rótulo por modo, e a cor do tipo dedicado para quem tem dedicado", () => {
    expect(rotuloDoModo("pool")).toBe("Compartilhado")
    expect(rotuloDoModo("isolated")).toBe("Isolado")
    expect(rotuloDoModo("dedicated_pool")).toBe("Dedicado + pool")
    expect(classeDoModo("pool")).toContain("teal")
    expect(classeDoModo("isolated")).toContain("purple")
    expect(classeDoModo("dedicated_pool")).toContain("purple")
  })

  it("status do executor em português", () => {
    expect(rotuloDoStatus("revoked")).toBe("revogado")
    expect(rotuloDoStatus("pending")).toBe("pendente")
    expect(rotuloDoStatus("inactive")).toBe("inativo")
    expect(rotuloDoStatus("estranho")).toBe("estranho")
  })

  it("quem é pool ainda não tem política para \"editar\"", () => {
    expect(rotuloDaAcaoDePolitica("pool")).toBe("Restringir a executores dedicados")
    expect(rotuloDaAcaoDePolitica("isolated")).toBe("Editar política de execução")
  })

  it("conta \"N de M online\" e separa quem está sem sinal", () => {
    expect(contarOnline(1, 1)).toBe("1 de 1 online")
    expect(contarOnline(2, 3)).toBe("2 de 3 online")
    expect(contarOnline(1, 3, 1)).toBe("1 de 3 online · 1 sem sinal")
    expect(semSinal([membro(), membro({ id_hash: "b", online: null })])).toBe(1)
  })
})

describe("saúde da cadeia", () => {
  it("soma os níveis e o pool só quando o servidor o devolveu (isto é, quando é permitido)", () => {
    expect(disponiveisNaCadeia(politica())).toBe(2)
    expect(disponiveisNaCadeia(isolada())).toBe(1)
    expect(disponiveisNaCadeia(isolada({ available_primary: 0 }))).toBe(0)
    expect(disponiveisNaCadeia(isolada({
      mode: "dedicated_pool", effective_terminal: "pool", available_primary: 0, pool: { total: 3, available: 1 },
    }))).toBe(1)
  })

  it("lista os membros que não recebem execuções", () => {
    const p = isolada({ primary: [membro(), membro({ id_hash: "ex-2", name: "geo-02", status: "revoked" })] })
    expect(membrosInativos(p).map(m => m.id_hash)).toEqual(["ex-2"])
  })

  it("descreve os níveis e o último recurso por extenso", () => {
    expect(descreverPolitica(isolada({ primary: [membro(), membro({ id_hash: "ex-2" })] })))
      .toBe("Principais 1 de 2 online · sem último recurso: a execução falha")
    expect(descreverPolitica(isolada({
      mode: "dedicated_pool", effective_terminal: "pool",
      fallback: [membro({ id_hash: "ex-3", tier: 2, online: null })], available_fallback: 0,
    }))).toBe("Principais 1 de 1 online · Reserva 0 de 1 online · 1 sem sinal · último recurso: pool")
  })

  it("saúde do pool: só quando a política o usa, e por extenso quando falta gente", () => {
    expect(saudeDoPool(isolada())).toBeNull()
    expect(saudeDoPool(politica())).toBe("Pool compartilhado 2 de 2 online")
    expect(saudeDoPool(politica({ pool: { total: 0, available: 0 } }))).toBe("Nenhum executor compartilhado cadastrado")
    expect(saudeDoPool(politica({ pool: { total: 3, available: 0 } }))).toBe("Nenhum executor do pool online agora")
  })

  it("o que acontece quando o dedicado cai: só \"falha\" com a política valendo e Isolado", () => {
    expect(descreverQueda(null)).toBe("se cair, o pool assume")
    expect(descreverQueda(isolada({ policy_routing_enabled: false }))).toBe("se cair, o pool assume")
    expect(descreverQueda(isolada())).toBe("se cair, a execução falha")
    expect(descreverQueda(isolada({ mode: "dedicated_pool", effective_terminal: "pool" }))).toBe("se cair, o pool assume")
  })
})

describe("politicaEmAlerta", () => {
  it("Compartilhado nunca alerta — o pool é problema da plataforma, não do workspace", () => {
    expect(politicaEmAlerta(politica({ pool: { total: 0, available: 0 } }))).toBe(false)
  })

  it("membro inativo alerta sempre; cadeia sem ninguém online só com o roteamento ligado", () => {
    expect(politicaEmAlerta(isolada({ primary: [membro({ status: "inactive" })] }))).toBe(true)
    expect(politicaEmAlerta(isolada({ available_primary: 0 }))).toBe(true)
    // Com a flag desligada o legado ainda cai no pool: "vai falhar" seria mentira.
    expect(politicaEmAlerta(isolada({ available_primary: 0, policy_routing_enabled: false }))).toBe(false)
    expect(politicaEmAlerta(isolada())).toBe(false)
  })
})

describe("avisoDePreFlight", () => {
  it("cala quando há para onde despachar", () => {
    expect(avisoDePreFlight(politica())).toBeNull()
    expect(avisoDePreFlight(isolada())).toBeNull()
    expect(avisoDePreFlight(null)).toBeNull()
  })

  it("no Compartilhado, a única falta certa é a do próprio pool — em qualquer flag", () => {
    expect(avisoDePreFlight(politica({ pool: { total: 0, available: 0 } }))).toMatch(/cadastrado/)
    expect(avisoDePreFlight(politica({ pool: { total: 2, available: 0 }, policy_routing_enabled: false })))
      .toMatch(/aparece online agora/)
  })

  it("com dedicado, só afirma algo sobre a cadeia quando o servidor roteia por ela", () => {
    expect(avisoDePreFlight(isolada({ available_primary: 0 }))).toMatch(/isolado/)
    expect(avisoDePreFlight(isolada({
      mode: "dedicated_pool", effective_terminal: "pool", available_primary: 0, pool: { total: 1, available: 0 },
    }))).toMatch(/nem do pool/)
    expect(avisoDePreFlight(isolada({ available_primary: 0, policy_routing_enabled: false }))).toBeNull()
  })
})

describe("avisoDeMudancaDePolitica", () => {
  it("só fala quando os modos diferem e as duas políticas foram lidas", () => {
    expect(avisoDeMudancaDePolitica(politica(), politica())).toBeNull()
    expect(avisoDeMudancaDePolitica(null, politica())).toBeNull()
    expect(avisoDeMudancaDePolitica(isolada(), null)).toBeNull()
    expect(avisoDeMudancaDePolitica(isolada(), politica()))
      .toBe("A política de execução muda de Isolado para Compartilhado: o workflow passa a seguir a política do destino.")
  })
})

describe("capacidade do executor", () => {
  it("descreve a carga como o executor a publica, e cala quando não há capacidade", () => {
    expect(descreverCapacidade(null)).toBeNull()
    expect(descreverCapacidade({ queued: 0 })).toBeNull()
    expect(descreverCapacidade({ running: 1, max_concurrent: 4, queued: 0, max_queue: 50 })).toBe("1 de 4 em execução")
    expect(descreverCapacidade({ running: 4, max_concurrent: 4, queued: 2, max_queue: 50 })).toBe("4 de 4 em execução · 2 na fila")
  })

  it("cheio = execuções no teto e fila no teto (ou sem fila)", () => {
    expect(capacidadeCheia({ running: 3, max_concurrent: 4, queued: 50, max_queue: 50 })).toBe(false)
    expect(capacidadeCheia({ running: 4, max_concurrent: 4, queued: 10, max_queue: 50 })).toBe(false)
    expect(capacidadeCheia({ running: 4, max_concurrent: 4, queued: 50, max_queue: 50 })).toBe(true)
    expect(capacidadeCheia({ running: 4, max_concurrent: 4 })).toBe(true)
    expect(capacidadeCheia(null)).toBe(false)
  })
})
