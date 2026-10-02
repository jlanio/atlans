import type { IWorkflow } from "@/service/types"
import type { IWorkflowMetricsRow } from "@/service/types"
import type { RunningRun } from "@/context/ActiveRunsContext"
import { fromBackend, dayjs } from "@/lib/dayjs"
import { formatarDecorridoGrosso, formatarQuando, rotuloDaOrigem } from "@/lib/formatos"

/**
 * "Como anda": a última execução de um workflow (docs/specs/projects.md
 * §3.5). Puro — cruza a linha de métricas (janela de 30 dias, cache de 45 s)
 * com o run vivo do `ActiveRunsContext` (10 s), que vence por ser mais
 * fresco. Devolve strings prontas onde a tela só mostra ("quando", "desde")
 * e números crus onde ela formata ("61 execuções em 30 d · 3 falhas").
 */

/** Janela das métricas da listagem (`days=30`), a mesma que separa "nunca" de "sem execuções". */
export const JANELA_EM_DIAS = 30

export type ComoAnda =
  | {
      tipo: "executando"
      /** "há 4 min"; vazio quando o run ainda não tem `started_at`. */
      desde: string
      /** Instante (ms) do início, para ordenar por execução; agora quando não se sabe. */
      instante: number
      origem: string | null
      executor: string | null
      /** Mediana (s) das execuções na janela: "costuma levar 7 min". */
      tipica: number | null
    }
  | {
      tipo: "concluida" | "falhou" | "cancelada"
      /** "há 3 h" / "hoje, 18:00" / "ontem, 06:00" / "4 set, 03:00". */
      quando: string
      /** Instante (ms) da última execução, para ordenar. */
      instante: number
      /** Só em `falhou`; nulo nos demais. */
      erro: string | null
      total: number
      falhas: number
      mediana: number | null
    }
  /** Sem linha de métricas na janela (ou `last_run_at` nulo) e o workflow tem mais de 30 dias. */
  | { tipo: "sem-execucoes" }
  /** `total_runs` 0 e criado há menos de 30 dias: "execute uma vez para validar". */
  | { tipo: "nunca" }
  /** As métricas falharam. */
  | { tipo: "indisponivel" }

export function derivarComoAnda(
  wf: Pick<IWorkflow, "created_at">,
  metrica: IWorkflowMetricsRow | undefined,
  emExecucao: RunningRun | undefined,
  metricasIndisponiveis: boolean,
  agora: Date = new Date(),
): ComoAnda {
  // O run vivo vence tudo, inclusive a falta de métricas: ele vem de outro
  // endpoint, com cadência de 10 s, e é o que a pessoa está esperando ver.
  if (emExecucao) {
    const inicio = fromBackend(emExecucao.startedAt)
    return {
      tipo: "executando",
      desde: inicio ? formatarDecorridoGrosso(Math.max(0, dayjs(agora).diff(inicio, "second"))) : "",
      instante: inicio ? inicio.valueOf() : agora.getTime(),
      origem: rotuloDaOrigem(emExecucao.triggerSource),
      executor: emExecucao.executorName,
      tipica: metrica?.p50_seconds ?? null,
    }
  }

  if (metricasIndisponiveis) return { tipo: "indisponivel" }

  const ultima = fromBackend(metrica?.last_run_at)
  if (!metrica || !ultima || !metrica.last_status) return nuncaOuSemExecucoes(wf, metrica, agora)

  // Métricas dizem "rodando" mas o contexto não tem o run: ou o contexto
  // ainda não fez o primeiro poll, ou o run acabou há menos de 45 s (cache).
  // Mostrar "em execução" com o que se sabe é mais honesto que chutar um
  // status final que ninguém informou.
  if (metrica.last_status === "running" || metrica.last_status === "pending") {
    return {
      tipo: "executando",
      desde: formatarDecorridoGrosso(Math.max(0, dayjs(agora).diff(ultima, "second"))),
      instante: ultima.valueOf(),
      origem: null,
      executor: null,
      tipica: metrica.p50_seconds ?? null,
    }
  }

  const base = {
    quando: formatarQuando(metrica.last_run_at, agora),
    instante: ultima.valueOf(),
    erro: null,
    total: metrica.total_runs ?? 0,
    falhas: metrica.failed_runs ?? 0,
    mediana: metrica.p50_seconds ?? null,
  }
  switch (metrica.last_status) {
    case "failed":
    case "error":
      return { ...base, tipo: "falhou", erro: metrica.last_error?.trim() || null }
    case "cancelled":
      return { ...base, tipo: "cancelada" }
    default:
      // `success` e qualquer status terminal que o backend venha a criar: a
      // execução acabou sem erro registrado.
      return { ...base, tipo: "concluida" }
  }
}

function nuncaOuSemExecucoes(
  wf: Pick<IWorkflow, "created_at">,
  metrica: IWorkflowMetricsRow | undefined,
  agora: Date,
): ComoAnda {
  // "Nunca" é o convite ao workflow novo ("execute uma vez para validar");
  // passada a janela, não dá para saber se rodou antes dela — e o texto
  // vira o neutro "sem execuções em 30 dias". Sem `created_at` não há como
  // afirmar que é novo.
  const criado = fromBackend(wf.created_at)
  const semRuns = (metrica?.total_runs ?? 0) === 0
  const recente = criado != null && dayjs(agora).diff(criado, "day") < JANELA_EM_DIAS
  return semRuns && recente ? { tipo: "nunca" } : { tipo: "sem-execucoes" }
}
