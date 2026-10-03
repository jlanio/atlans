import { describe, expect, it } from "vitest"
import {
  FILTROS_DOS_CHIPS, ROTULO_DA_ORDEM, ROTULO_DO_FILTRO, casaBusca, contarPorFiltro, normalizarBusca, ordenar,
  predicadoDoFiltro, temPortal, type ContextoDeFiltro,
} from "@/app/components/projects/filtros"
import { FILTROS } from "@/app/components/projects/projetos-url"
import type { ComoAnda } from "@/app/components/projects/como-anda"
import { resumirAgendamento } from "@/app/components/projects/gatilho"
import type { IWorkflow, IWorkflowGroup, IWorkflowSchedule } from "@/service/types"

function wf(extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: "wf", flag_ative: true, name: "Fluxo", description: "", version: "1", priority: 0,
    definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u1", ...extra,
  }
}

const schedule = (active: boolean): IWorkflowSchedule => ({
  active, next_run_at: active ? "2026-09-08T09:00:00Z" : null, last_run_at: null, strategy: "cron", cron_expression: "0 6 * * *",
})

const concluida: ComoAnda = { tipo: "concluida", quando: "há 3 h", instante: 3_000, erro: null, total: 10, falhas: 0, mediana: null }
const falhou: ComoAnda = { tipo: "falhou", quando: "há 40 min", instante: 5_000, erro: "boom", total: 10, falhas: 1, mediana: null }
const executando: ComoAnda = { tipo: "executando", desde: "há 4 min", instante: 9_000, origem: null, executor: null, tipica: null }

// A small shelf that goes through every predicate.
const a = wf({ id_hash: "a", name: "Consolidação de outorgas", has_schedule_trigger: true, schedule: schedule(true), group_id: "g1" })
const b = wf({ id_hash: "b", name: "Bacia do rio Doce", flag_ative: false, has_schedule_trigger: true, schedule: schedule(false) })
const c = wf({ id_hash: "c", name: "Alerta de cheia", has_webhook_trigger: true, description: "Recebe o nível pelo WEBHOOK da ANA" })
const d = wf({ id_hash: "d", name: "Recorte por município", is_subworkflow: true })
const e = wf({ id_hash: "e", name: "Mapa de risco", has_publish_map: true, portal_access: "public", updated_at: "2026-09-06T10:00:00Z" })
const f = wf({ id_hash: "f", name: "Zoneamento", has_publish_map: true, portal_access: "disabled", updated_at: "2026-09-01T10:00:00Z" })
// Created by the Home assistant: it shows up on the shelf like any other and only
// the "Assistente" chip sets it apart.
const g = wf({ id_hash: "g", name: "Embargos no Brasil", origem: "assistente" })
const todos = [a, b, c, d, e, f, g]

function contexto(): ContextoDeFiltro {
  return {
    comoAndaPorHash: new Map<string, ComoAnda>([
      ["a", concluida], ["c", executando], ["d", falhou], ["e", { tipo: "nunca" }],
    ]),
    resumoDoAgendamentoPorHash: new Map(todos.map(w => [w.id_hash, resumirAgendamento(w.schedule, w.flag_ative)])),
  }
}

describe("predicadoDoFiltro", () => {
  const ids = (filtro: Parameters<typeof predicadoDoFiltro>[0]) => todos.filter(predicadoDoFiltro(filtro, contexto())).map(w => w.id_hash)

  it("cada chip recorta o que a spec diz", () => {
    expect(ids("todos")).toEqual(["a", "b", "c", "d", "e", "f", "g"])
    expect(ids("ativos")).toEqual(["a", "c", "d", "e", "f", "g"])
    expect(ids("inativos")).toEqual(["b"])
    expect(ids("executando")).toEqual(["c"])
    expect(ids("falha")).toEqual(["d"])
    expect(ids("agendados")).toEqual(["a", "b"])
    expect(ids("webhook")).toEqual(["c"])
    expect(ids("subfluxos")).toEqual(["d"])
    expect(ids("portal")).toEqual(["e"])
    expect(ids("assistente")).toEqual(["g"])
    expect(ids("pausado")).toEqual(["b"])
    expect(ids("nunca")).toEqual(["e"])
  })

  it("portal desligado não conta como 'com portal'", () => {
    expect(temPortal(e)).toBe(true)
    expect(temPortal(f)).toBe(false)
    expect(temPortal(wf({ has_publish_map: false, portal_access: "public" }))).toBe(false)
  })

  it("'executando' lê o «como anda», não runningHashes: conta métricas-running sem run vivo", () => {
    // "a" is running according to the metrics (45 s cache window) without being
    // in runningHashes. The row shows "Em execução"; the chip/filter have to
    // agree, otherwise the count says 0 with a blue row on screen.
    const ctx: ContextoDeFiltro = {
      comoAndaPorHash: new Map<string, ComoAnda>([["a", executando]]),
      resumoDoAgendamentoPorHash: new Map(),
    }
    expect(todos.filter(predicadoDoFiltro("executando", ctx)).map(w => w.id_hash)).toEqual(["a"])
    expect(contarPorFiltro(todos, ctx).executando).toBe(1)
  })

  it("pausado sem resumo no contexto deriva do próprio item", () => {
    const vazio: ContextoDeFiltro = { comoAndaPorHash: new Map(), resumoDoAgendamentoPorHash: new Map() }
    expect(predicadoDoFiltro("pausado", vazio)(b)).toBe(true)
    expect(predicadoDoFiltro("pausado", vazio)(a)).toBe(false)
    expect(predicadoDoFiltro("pausado", vazio)(c)).toBe(false)
  })
})

describe("contarPorFiltro", () => {
  it("conta cada filtro sobre a lista inteira, inclusive os que não têm chip", () => {
    expect(contarPorFiltro(todos, contexto())).toEqual({
      todos: 7, ativos: 6, inativos: 1, executando: 1, falha: 1, agendados: 2, webhook: 1, subfluxos: 1, portal: 1,
      assistente: 1, pausado: 1, nunca: 1,
    })
  })
  it("lista vazia é zero em tudo", () => {
    const zeros = contarPorFiltro([], contexto())
    for (const f of FILTROS) expect(zeros[f]).toBe(0)
  })
  it("os chips da barra são os dez da tela, com rótulo, e toda ordem tem rótulo", () => {
    expect(FILTROS_DOS_CHIPS).toEqual(["todos", "ativos", "inativos", "executando", "falha", "agendados", "webhook", "subfluxos", "portal", "assistente"])
    expect(FILTROS_DOS_CHIPS.map(f => ROTULO_DO_FILTRO[f]))
      .toEqual(["Todos", "Ativos", "Inativos", "Em execução", "Com falha", "Agendados", "Webhook", "Sub-fluxos", "Com portal", "Assistente"])
    expect(ROTULO_DA_ORDEM).toEqual({ nome: "Nome", execucao: "Última execução", alterado: "Alterado" })
  })
})

describe("busca", () => {
  const grupos = new Map<string, IWorkflowGroup>([
    ["g1", { id: 1, id_hash: "g1", name: "Hidrologia", workflow_count: 1, created_at: "", updated_at: "" }],
  ])

  it("normaliza: sem acento, sem caixa, sem espaço nas pontas", () => {
    expect(normalizarBusca("  Consolidação de Outorgas ")).toBe("consolidacao de outorgas")
    expect(normalizarBusca("Município")).toBe("municipio")
    expect(normalizarBusca(null)).toBe("")
  })

  it("acha pelo nome sem acento e sem caixa", () => {
    expect(casaBusca(a, grupos, "CONSOLIDACAO")).toBe(true)
    expect(casaBusca(d, grupos, "municipio")).toBe(true)
    expect(casaBusca(a, grupos, "cheia")).toBe(false)
  })

  it("acha pela descrição", () => {
    expect(casaBusca(c, grupos, "webhook da ana")).toBe(true)
  })

  it("acha pelo nome do grupo: o grupo que bate mostra os seus workflows", () => {
    expect(casaBusca(a, grupos, "hidro")).toBe(true)
    expect(casaBusca(b, grupos, "hidro")).toBe(false)
    // A group the list does not know does not break the search.
    expect(casaBusca(wf({ group_id: "g-fantasma" }), grupos, "hidro")).toBe(false)
  })

  it("busca vazia casa tudo", () => {
    expect(casaBusca(b, grupos, "")).toBe(true)
    expect(casaBusca(b, grupos, "   ")).toBe(true)
  })
})

describe("ordenar", () => {
  it("por nome, em pt-BR (acento não joga para o fim; números em ordem natural)", () => {
    const lista = [wf({ id_hash: "1", name: "Lote 10" }), wf({ id_hash: "2", name: "Água" }), wf({ id_hash: "3", name: "Lote 9" }), wf({ id_hash: "4", name: "bacia" })]
    expect(ordenar(lista, "nome", contexto()).map(w => w.name)).toEqual(["Água", "bacia", "Lote 9", "Lote 10"])
  })

  it("por execução: em curso e mais recentes primeiro, sem execução por último, empate pelo nome", () => {
    const ctx = contexto()
    expect(ordenar(todos, "execucao", ctx).map(w => w.id_hash)).toEqual([
      "c",  // executando (instante 9000)
      "d",  // falhou (5000)
      "a",  // finished (3000)
      "b", "g", "e", "f",  // no timestamp (never/no metrics), by name: Bacia, Embargos, Mapa, Zoneamento
    ])
  })

  it("por alterado: updated_at desc, sem data por último", () => {
    expect(ordenar([a, e, f], "alterado", contexto()).map(w => w.id_hash)).toEqual(["e", "f", "a"])
  })

  it("devolve uma cópia — a lista original não muda", () => {
    const original = [f, e]
    ordenar(original, "nome", contexto())
    expect(original.map(w => w.id_hash)).toEqual(["f", "e"])
  })
})
