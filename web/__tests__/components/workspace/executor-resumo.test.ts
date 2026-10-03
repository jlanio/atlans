import { describe, it, expect } from "vitest"
import {
  corDoPonto, descreverExecutor, emAlerta, resumirExecutor, rotularExecutor,
  MENSAGEM_ALVO_DESCONHECIDO,
} from "@/app/components/workspace/executor-resumo"
import type { IExecutor } from "@/service/types"

function executor(extra: Partial<IExecutor>): IExecutor {
  return {
    id_hash: "ex-1", name: "geo-01", description: null, status: "active",
    executor_type: "dedicated", is_default: false, capabilities: [],
    max_concurrent_jobs: 1, max_queue_size: 1, executor_version: null,
    last_seen_at: null, created_at: "", created_by: null, online: true,
    capacity: null, connected_at: null, system_info: null,
    ...extra,
  }
}

const base = { executores: [executor({})], alvoDesconhecido: false, erroExecutores: null }

describe("resumirExecutor", () => {
  it("alvo ainda não lido é carregando, não pool", () => {
    expect(resumirExecutor({ ...base, alvo: undefined })).toEqual({ estado: "carregando" })
  })

  it("null é o pool da plataforma", () => {
    expect(resumirExecutor({ ...base, alvo: null })).toEqual({ estado: "pool" })
  })

  it("alvo presente e ativo", () => {
    const r = resumirExecutor({ ...base, alvo: "ex-1" })
    expect(r.estado).toBe("ok")
    expect(emAlerta(r)).toBe(false)
  })

  it("alvo que não está na lista está sumido — mas só quando a lista foi lida", () => {
    expect(resumirExecutor({ ...base, alvo: "ex-9" })).toEqual({ estado: "sumido", alvo: "ex-9" })
    // With the listing failing, every target would look removed: it becomes "don't know".
    expect(resumirExecutor({ ...base, alvo: "ex-9", erroExecutores: "boom" }))
      .toEqual({ estado: "indefinido", mensagem: "boom" })
  })

  it("alvo encontrado mas inativo entra em alerta", () => {
    const r = resumirExecutor({ ...base, executores: [executor({ status: "revoked" })], alvo: "ex-1" })
    expect(r.estado).toBe("inativo")
    expect(emAlerta(r)).toBe(true)
  })

  it("a leitura do workspace falhando não vira pool, mesmo com alvo null", () => {
    expect(resumirExecutor({ ...base, alvo: null, alvoDesconhecido: true }))
      .toEqual({ estado: "indefinido", mensagem: MENSAGEM_ALVO_DESCONHECIDO })
  })
})

describe("textos e ponto", () => {
  it("descreve por extenso o que o status significa para as execuções", () => {
    // With no policy read (or with the flag off), legacy overflows to the pool.
    expect(descreverExecutor({ estado: "ok", executor: executor({}) }))
      .toBe("Online · dedicado a este workspace · se cair, o pool assume")
    expect(descreverExecutor({ estado: "ok", executor: executor({ online: false, executor_type: "default" }) }))
      .toBe("Offline · executor compartilhado, fixado para este workspace")
    expect(descreverExecutor({ estado: "pool" })).toMatch(/^Pool compartilhado/)
    expect(descreverExecutor({ estado: "sumido", alvo: "x" })).toMatch(/removido ou você perdeu o acesso/)
    expect(descreverExecutor({ estado: "inativo", executor: executor({ status: "inactive" }) })).toBe("Inativo · não recebe execuções")
    expect(descreverExecutor({ estado: "inativo", executor: executor({ status: "revoked" }) })).toBe("Revogado · não recebe execuções")
  })

  it("com a política valendo e Isolado, um dedicado offline vira alerta: a próxima execução falha", () => {
    const r = { estado: "ok" as const, executor: executor({ online: false }) }
    expect(descreverExecutor(r, isolada())).toBe("Offline · novas execuções vão falhar")
    expect(emAlerta(r, isolada())).toBe(true)
    expect(corDoPonto(r, isolada())).toBe("bg-amber-500")
    // Dedicado + pool: o pool assume, cinza basta.
    const dp = isolada({ mode: "dedicated_pool", effective_terminal: "pool" })
    expect(descreverExecutor(r, dp)).toBe("Offline · dedicado a este workspace · se cair, o pool assume")
    expect(emAlerta(r, dp)).toBe(false)
    // Flag off: no alert.
    expect(emAlerta(r, isolada({ policy_routing_enabled: false }))).toBe(false)
  })

  it("rotula curto para a fileira", () => {
    expect(rotularExecutor({ estado: "ok", executor: executor({}) })).toBe("geo-01")
    expect(rotularExecutor({ estado: "pool" })).toBe("Pool compartilhado")
    expect(rotularExecutor({ estado: "sumido", alvo: "x" })).toBe("Executor indisponível")
    expect(rotularExecutor({ estado: "indefinido", mensagem: "boom" })).toBe("Executor não lido")
    expect(rotularExecutor({ estado: "inativo", executor: executor({ status: "revoked" }) })).toBe("geo-01 · revogado")
  })

  it("o ponto acompanha o texto e some quando não há o que sinalizar", () => {
    expect(corDoPonto({ estado: "ok", executor: executor({}) })).toBe("bg-green-500")
    expect(corDoPonto({ estado: "ok", executor: executor({ online: false }) })).toContain("muted")
    expect(corDoPonto({ estado: "sumido", alvo: "x" })).toBe("bg-amber-500")
    expect(corDoPonto({ estado: "carregando" })).toBeNull()
    expect(corDoPonto({ estado: "indefinido", mensagem: "boom" })).toBeNull()
  })
})

// ── Policy with a group or fallback ─────────────────────────────────────────
import { isolada, membro } from "../../fixtures/politica"

describe("grupo — política EM VIGOR que não cabe no seletor rápido", () => {
  it("dois principais, ou uma reserva, viram o estado grupo — mesmo com alvo legível", () => {
    const grupo = isolada({ primary: [membro(), membro({ id_hash: "ex-2", name: "geo-02" })], available_primary: 2 })
    expect(resumirExecutor({ ...base, alvo: "ex-1", politica: grupo })).toEqual({ estado: "grupo", politica: grupo })

    const comReserva = isolada({ fallback: [membro({ id_hash: "ex-3", name: "geo-03", tier: 2 })] })
    expect(resumirExecutor({ ...base, alvo: "ex-1", politica: comReserva }).estado).toBe("grupo")
  })

  it("com a flag DESLIGADA o grupo não toma a tela: é o ponteiro legado que roteia e que o seletor mostra", () => {
    const grupo = isolada({
      primary: [membro(), membro({ id_hash: "ex-2", name: "geo-02" })], available_primary: 2,
      policy_routing_enabled: false, target_executor_id: null,
    })
    expect(resumirExecutor({ ...base, alvo: null, politica: grupo })).toEqual({ estado: "pool" })
    expect(resumirExecutor({ ...base, alvo: "ex-1", politica: grupo }).estado).toBe("ok")
  })

  it("um principal só, sem reserva, continua sendo um alvo", () => {
    expect(resumirExecutor({ ...base, alvo: "ex-1", politica: isolada() }).estado).toBe("ok")
  })

  it("membro da política que não está na MINHA lista não é 'sumido': a política traz nome e presença", () => {
    const r = resumirExecutor({ ...base, executores: [], alvo: "ex-1", politica: isolada({ primary: [membro({ online: null })] }) })
    expect(r.estado).toBe("ok")
    if (r.estado === "ok") expect(r.executor.online).toBeNull()
    // Without the policy in effect, the list is the only source: it stays missing.
    expect(resumirExecutor({ ...base, executores: [], alvo: "ex-1", politica: isolada({ policy_routing_enabled: false }) }).estado)
      .toBe("sumido")
  })

  it("a leitura falhando vence a política — continua 'não sei'", () => {
    expect(resumirExecutor({ ...base, alvo: "ex-1", alvoDesconhecido: true, politica: isolada() }).estado)
      .toBe("indefinido")
  })

  it("rotula e descreve o grupo", () => {
    const dois = isolada({ primary: [membro(), membro({ id_hash: "ex-2", name: "geo-02" })], available_primary: 1 })
    expect(rotularExecutor({ estado: "grupo", politica: dois })).toBe("2 executores")
    expect(descreverExecutor({ estado: "grupo", politica: dois }))
      .toBe("Principais 1 de 2 online · sem último recurso: a execução falha")

    const umMaisReserva = isolada({ fallback: [membro({ id_hash: "ex-3", name: "geo-03", tier: 2 })] })
    expect(rotularExecutor({ estado: "grupo", politica: umMaisReserva })).toBe("2 executores")
  })

  it("ponto e alerta seguem a saúde da cadeia", () => {
    const saudavel = isolada({ primary: [membro(), membro({ id_hash: "ex-2" })], available_primary: 2 })
    expect(corDoPonto({ estado: "grupo", politica: saudavel })).toBe("bg-green-500")
    expect(emAlerta({ estado: "grupo", politica: saudavel })).toBe(false)

    const semNinguem = isolada({ primary: [membro(), membro({ id_hash: "ex-2" })], available_primary: 0 })
    expect(corDoPonto({ estado: "grupo", politica: semNinguem })).toBe("bg-amber-500")
    expect(emAlerta({ estado: "grupo", politica: semNinguem })).toBe(true)
  })
})
