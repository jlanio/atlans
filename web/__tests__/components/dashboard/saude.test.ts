import { describe, expect, it } from "vitest"
import type { INowBlock, IStuckRun } from "@/service/types"
import { motivosDeSaude, tomDeSaude, veredito } from "@/app/components/dashboard/saude"

function stuck(extra: Partial<IStuckRun> = {}): IStuckRun {
  return {
    run_id: "run-1", workflow_hash: "wf", workflow_name: "Cadastro",
    agent_host: null, executor_name: null, started_at: null,
    elapsed_seconds: 1080, typical_seconds: 360, ...extra,
  }
}

function now(extra: Partial<INowBlock> = {}): INowBlock {
  return {
    running: 3, pending: 0, stuck_count: 0, stuck: [],
    executors: { online: 6, total: 6 }, queued_on_executors: 0, overdue_acks: 0, ...extra,
  }
}

describe("tomDeSaude", () => {
  it("calmo: frota inteira online, nada preso, nada na atenção", () => {
    expect(tomDeSaude(now(), false)).toBe("calmo")
    expect(tomDeSaude(null, false)).toBe("calmo")
    expect(tomDeSaude(undefined, false)).toBe("calmo")
  })

  it("crítico por execução presa", () => {
    expect(tomDeSaude(now({ stuck_count: 1, stuck: [stuck()] }), false)).toBe("critico")
  })

  it("crítico por frota inteira offline (com executores)", () => {
    expect(tomDeSaude(now({ executors: { online: 0, total: 6 } }), false)).toBe("critico")
    // Sem executores cadastrados não é crítico — não há frota para cair.
    expect(tomDeSaude(now({ executors: { online: 0, total: 0 } }), false)).toBe("calmo")
  })

  it("atenção por parte da frota offline", () => {
    expect(tomDeSaude(now({ executors: { online: 5, total: 6 } }), false)).toBe("atencao")
  })

  it("atenção por confirmações atrasadas", () => {
    expect(tomDeSaude(now({ overdue_acks: 2 }), false)).toBe("atencao")
  })

  it("atenção por haver itens na lista de atenção (temAtencao)", () => {
    expect(tomDeSaude(now(), true)).toBe("atencao")
    expect(tomDeSaude(null, true)).toBe("atencao")
  })

  it("crítico manda sobre atenção", () => {
    expect(tomDeSaude(now({ stuck_count: 1, stuck: [stuck()], executors: { online: 5, total: 6 } }), true)).toBe("critico")
  })
})

const SEM = { falhas: 0, saturado: 0 }

describe("motivosDeSaude", () => {
  it("presa no singular, com o 'há X' da mais antiga", () => {
    const m = motivosDeSaude(now({ stuck_count: 1, stuck: [stuck({ elapsed_seconds: 1080 })] }), SEM)
    expect(m[0]).toBe("1 execução presa há 18 min")
  })

  it("presas no plural usam o tempo da mais antiga (a primeira da lista)", () => {
    const m = motivosDeSaude(now({
      stuck_count: 2,
      stuck: [stuck({ run_id: "velha", elapsed_seconds: 9000 }), stuck({ run_id: "nova", elapsed_seconds: 60 })],
    }), SEM)
    expect(m[0]).toBe("2 execuções presas há 2 h 30 min")
  })

  it("frota inteira offline e frota parcial têm textos próprios", () => {
    expect(motivosDeSaude(now({ executors: { online: 0, total: 6 } }), SEM)).toContain("frota offline: 0 de 6")
    expect(motivosDeSaude(now({ executors: { online: 5, total: 6 } }), SEM)).toContain("frota parcialmente offline: 5 de 6")
  })

  it("falhas e executores no teto viram contagens específicas (não um genérico)", () => {
    expect(motivosDeSaude(now(), { falhas: 1, saturado: 0 })).toContain("1 workflow falhando")
    expect(motivosDeSaude(now(), { falhas: 2, saturado: 0 })).toContain("2 workflows falhando")
    expect(motivosDeSaude(now(), { falhas: 0, saturado: 1 })).toContain("1 executor no teto")
    expect(motivosDeSaude(now(), { falhas: 0, saturado: 3 })).toContain("3 executores no teto")
  })

  it("confirmações atrasadas no plural", () => {
    expect(motivosDeSaude(now({ overdue_acks: 1 }), SEM)).toContain("1 confirmação atrasada")
    expect(motivosDeSaude(now({ overdue_acks: 3 }), SEM)).toContain("3 confirmações atrasadas")
  })

  it("presa vem antes das falhas, sem recontar a presa (a mais grave primeiro)", () => {
    const m = motivosDeSaude(now({ stuck_count: 1, stuck: [stuck({ elapsed_seconds: 1080 })] }), { falhas: 2, saturado: 0 })
    expect(m[0]).toBe("1 execução presa há 18 min")
    expect(m[1]).toBe("2 workflows falhando")
    expect(m).toHaveLength(2) // a presa não aparece duas vezes
  })
})

describe("veredito", () => {
  it("calmo tranquiliza", () => {
    expect(veredito(now(), "calmo", SEM)).toBe("Tudo tranquilo — nada pedindo atenção agora.")
  })

  it("calmo sem nenhuma execução no período vira 'nada rodando ainda'", () => {
    expect(veredito(now(), "calmo", SEM, true)).toBe("Tudo tranquilo — nada rodando ainda.")
  })

  it("junta os 1–2 motivos mais graves com 'e' (presa + falhas, com a contagem)", () => {
    const n = now({ stuck_count: 1, stuck: [stuck({ elapsed_seconds: 1080 })] })
    expect(veredito(n, "critico", { falhas: 2, saturado: 0 }))
      .toBe("Precisa de você: 1 execução presa há 18 min e 2 workflows falhando.")
  })

  it("um só motivo não usa o 'e'", () => {
    expect(veredito(now({ executors: { online: 5, total: 6 } }), "atencao", SEM))
      .toBe("Precisa de você: frota parcialmente offline: 5 de 6.")
  })
})
