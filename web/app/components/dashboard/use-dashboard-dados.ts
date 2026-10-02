"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IResponse } from "@/service/types"
import type { IWorkflow } from "@/service/types"
import type {
  IExecutorMetrics, IObservabilityMetrics, IRunSummary, IRunsByDay,
} from "@/service/types"

/**
 * Dados do Dashboard (docs/specs/dashboard.md §3.3).
 *
 * Cinco fontes escopadas partem juntas por escopo (`Promise.allSettled`):
 * métricas (a ESPINHA — saúde + atenção + indicadores), execuções por dia
 * (gráfico), execuções recentes (atividade), executores (item "no teto" da
 * atenção) e a listagem de workflows (próximas execuções).
 *
 * Só `metrics` bloqueia: se cair na 1ª carga do escopo, `erroEspinha` toma a
 * tela; nas recargas com dado na tela ela degrada por seção (`falhas.metrics`),
 * como as demais. `executores` é a única que não vira aviso — falha → `[]`, e a
 * atenção só perde o item "executor no teto". O instante (`now`) vem só de
 * `metrics` (não do `ActiveRunsContext`, que é do workspace ativo e não serve
 * ao escopo "todos"): um poll de 30 s renova só as métricas, sem piscar a tela.
 *
 * O escopo já chega resolvido em `escopoWorkspaceId` (`null` = "todos"); trocar
 * de escopo reinicia a 1ª carga daquele escopo (skeleton). Quem decide o id a
 * partir de `?escopo=` e do workspace ativo é o `index` — assim o hook não
 * recarrega ao trocar `current` quando o escopo é "todos".
 *
 * A janela chega em `dias` (7/30/90, do `?periodo=`) e escala as três fontes de
 * período — métricas, execuções por dia e executores. Trocar só o período é uma
 * RECARGA (o botão gira, a tela fica e atualiza quando o dado novo chega), como
 * o seletor do Histórico; só a troca de escopo mostra skeleton.
 */

export interface DadosDoDashboard {
  metrics: IObservabilityMetrics | null
  dias: IRunsByDay[]
  runs: IRunSummary[]
  executores: IExecutorMetrics[]
  workflows: IWorkflow[]
  /** 1ª carga do escopo atual (skeleton). */
  carregando: boolean
  /** Recargas seguintes (o botão gira, a tela fica). */
  atualizando: boolean
  /** Por seção que falhou na última carga; o que já havia continua na tela. */
  falhas: { metrics: boolean; dias: boolean; runs: boolean; workflows: boolean }
  /** Só quando `metrics` cai na 1ª carga do escopo atual (inclui troca de escopo): bloqueia a tela. */
  erroEspinha: string | null
  /** "Atualizar" passa `force: true` para furar o cache das métricas no backend. */
  recarregar: (opts?: { force?: boolean }) => void
}

/** A saúde renova a cada 30 s com a aba visível (spec §3.3); o instante não é janela. */
export const INTERVALO_DA_SAUDE_MS = 30_000
/** Poucas linhas: a atividade recente é um resumo, não uma tabela (spec §3.7). */
export const LIMITE_DE_RUNS = 6

const ERRO_ESPINHA_PADRAO = "Não foi possível carregar o painel."

const SEM_FALHAS = { metrics: false, dias: false, runs: false, workflows: false }

/** `allSettled` nunca rejeita; o service também não — mas um `throw` inesperado não pode derrubar a tela. */
function resposta<T>(r: PromiseSettledResult<IResponse<T> | null>): IResponse<T> | null {
  return r.status === "fulfilled" ? r.value : null
}

function fusoDoNavegador(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  } catch {
    return "UTC"
  }
}

// `escopoWorkspaceId`: `null` = "todos"; um id = aquele workspace; `undefined` =
// escopo ainda indefinido (o workspace ativo está carregando) — NÃO buscar, o
// skeleton continua. Sem esse terceiro estado, o escopo "ativo" buscava "todos"
// por um instante (id ainda nulo) e piscava o painel errado antes de recarregar.
export function useDashboardDados(escopoWorkspaceId: string | null | undefined, periodo: number): DadosDoDashboard {
  const [metrics, setMetrics] = useState<IObservabilityMetrics | null>(null)
  const [dias, setDias] = useState<IRunsByDay[]>([])
  const [runs, setRuns] = useState<IRunSummary[]>([])
  const [executores, setExecutores] = useState<IExecutorMetrics[]>([])
  const [workflows, setWorkflows] = useState<IWorkflow[]>([])
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [falhas, setFalhas] = useState(SEM_FALHAS)
  const [erroEspinha, setErroEspinha] = useState<string | null>(null)

  // Carimbo de sequência: trocar de escopo duas vezes seguidas dispara duas
  // cargas, e a mais lenta pode responder por último. Só a última carga
  // pedida escreve na tela.
  const seq = useRef(0)
  // Escopo cujos dados estão NA TELA (`undefined` = nunca carregou com espinha;
  // `null` = "todos"). Separa skeleton (1ª carga do escopo) de "o botão gira".
  const escopoNaTela = useRef<string | null | undefined>(undefined)
  // O escopo corrente, lido pelo `recarregar` e pelo poll sem trocar de
  // identidade a cada render. (`undefined` = ainda indefinido — não busca.)
  const escopoRef = useRef<string | null | undefined>(escopoWorkspaceId)
  escopoRef.current = escopoWorkspaceId
  // A janela corrente (nº de dias), lida pelo `recarregar` e pelo poll da saúde
  // sem trocar de identidade a cada render. (`dias`, o estado, é a série do
  // gráfico — daí o nome `periodo` aqui.)
  const periodoRef = useRef(periodo)
  periodoRef.current = periodo
  // Quando um "Atualizar" (force) escreveu métricas frescas. Um tick de fundo
  // que começou ANTES busca o cache e, chegando depois, sobrescreveria o
  // fresco pelo velho — os dois não trocam de sequência. O tick confere este
  // carimbo e desiste (mesmo padrão de `use-projetos-dados`).
  const forcadasEm = useRef(0)
  const tz = useMemo(fusoDoNavegador, [])

  const carregar = useCallback(async (alvo: string | null, periodo: number, force: boolean) => {
    const mine = ++seq.current
    // `primeira` é por ESCOPO: a 1ª carga de um escopo mostra skeleton e esvazia
    // a seção que falha. Trocar só o período não muda `alvo` → é uma recarga
    // (o botão gira, a tela fica), como o seletor do Histórico.
    const primeira = escopoNaTela.current !== alvo
    if (primeira) setCarregando(true)
    else setAtualizando(true)

    const workspace_id = alvo ?? undefined
    const [rMetrics, rDias, rRuns, rExecutores, rWorkflows] = await Promise.allSettled([
      GisFlowService.getObservabilityMetrics(periodo, force, { workspace_id }),
      GisFlowService.getRunsByDay(periodo, { workspace_id, tz }),
      GisFlowService.getObservabilityRuns({ limit: LIMITE_DE_RUNS, workspace_id }),
      GisFlowService.getExecutorMetrics(periodo, force, { workspace_id }),
      // Com os do assistente: o painel resume o que existe, e as "Próximas
      // execuções" sem eles esconderiam justamente o que roda sozinho.
      GisFlowService.getWorkflows(workspace_id, { incluirDoAssistente: true }),
    ])
    if (mine !== seq.current) return

    const metricsRes = resposta(rMetrics)
    const diasRes = resposta(rDias)
    const runsRes = resposta(rRuns)
    const execRes = resposta(rExecutores)
    const workflowsRes = resposta(rWorkflows)

    const novasFalhas = { ...SEM_FALHAS }

    // Espinha. Sucesso limpa o erro. Falha só bloqueia na 1ª carga do escopo
    // (`primeira`, que a troca de escopo também dispara): aí a tela mostra "não
    // foi possível carregar" e o dado do escopo anterior não escapa. Numa
    // recarga do mesmo escopo, degrada por seção e o resto continua.
    if (metricsRes?.data) {
      if (force) forcadasEm.current = Date.now()
      setMetrics(metricsRes.data)
      setErroEspinha(null)
      escopoNaTela.current = alvo
    } else {
      novasFalhas.metrics = true
      if (primeira) {
        setErroEspinha(metricsRes?.error?.message ?? ERRO_ESPINHA_PADRAO)
        setMetrics(null)
      }
    }

    // As demais degradam por seção. Numa RECARGA do mesmo escopo, o que já
    // estava fica (§3.3, "nunca zerar a tela"); numa TROCA de escopo
    // (`primeira`), a seção que falha é esvaziada — exibir o dado do workspace
    // anterior sob o novo escopo confundiria a leitura (§3.10).
    if (diasRes?.data?.days) setDias(diasRes.data.days)
    else { novasFalhas.dias = true; if (primeira) setDias([]) }

    if (runsRes?.data?.runs) setRuns(runsRes.data.runs)
    else { novasFalhas.runs = true; if (primeira) setRuns([]) }

    if (workflowsRes?.data) setWorkflows(workflowsRes.data)
    else { novasFalhas.workflows = true; if (primeira) setWorkflows([]) }

    // Executores é a única opcional que não vira aviso: falha → `[]`.
    setExecutores(execRes?.data?.executores ?? [])

    setFalhas(novasFalhas)
    setCarregando(false)
    setAtualizando(false)
  }, [tz])

  // Recarrega ao trocar o escopo. Como o `index` só troca `escopoWorkspaceId`
  // quando o escopo é "ativo" e o `current` muda (no "todos" ele é sempre
  // `null`), isto já cobre a regra da spec sem o hook conhecer o context.
  //
  // `undefined` = escopo ativo ainda sem id (workspace carregando): não busca,
  // o skeleton (estado inicial `carregando=true`) fica até o id ser conhecido.
  useEffect(() => {
    if (escopoWorkspaceId === undefined) return
    carregar(escopoWorkspaceId, periodo, false)
  }, [escopoWorkspaceId, periodo, carregar])

  // Poll silencioso da saúde: só as métricas (onde `now` vive), sem ligar
  // `carregando`/`atualizando`. Não incrementa a sequência: uma carga completa
  // pedida no meio vence.
  useEffect(() => {
    if (INTERVALO_DA_SAUDE_MS <= 0) return
    let ultimo = Date.now()
    async function renovarSaude() {
      const alvo = escopoRef.current
      if (alvo === undefined) return   // escopo ainda indefinido: nada a renovar
      const mine = seq.current
      const inicio = Date.now()
      ultimo = inicio
      const res = await GisFlowService.getObservabilityMetrics(periodoRef.current, false, { workspace_id: alvo ?? undefined })
      // Falhou, chegou tarde (outra carga assumiu), ou um "Atualizar" escreveu
      // dados frescos enquanto este tick buscava o cache: fica o que havia.
      if (mine !== seq.current || forcadasEm.current > inicio || !res.data) return
      setMetrics(res.data)
      setErroEspinha(null)
      // Se a saúde do escopo se recupera por aqui (a 1ª carga dele tinha
      // falhado), o escopo passa a estar "na tela" — um "Tentar de novo" depois
      // não repete o skeleton à toa.
      escopoNaTela.current = alvo
    }
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") renovarSaude()
    }, INTERVALO_DA_SAUDE_MS)
    // Voltar à aba depois de um tempo longe renova na hora, mas não a cada alt-tab.
    const onVisibility = () => {
      if (document.visibilityState === "visible" && Date.now() - ultimo >= INTERVALO_DA_SAUDE_MS) renovarSaude()
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [])

  const recarregar = useCallback((opts: { force?: boolean } = {}) => {
    if (escopoRef.current === undefined) return   // escopo ainda indefinido
    carregar(escopoRef.current, periodoRef.current, opts.force ?? false)
  }, [carregar])

  return useMemo(() => ({
    metrics, dias, runs, executores, workflows,
    carregando, atualizando, falhas, erroEspinha, recarregar,
  }), [metrics, dias, runs, executores, workflows, carregando, atualizando, falhas, erroEspinha, recarregar])
}
