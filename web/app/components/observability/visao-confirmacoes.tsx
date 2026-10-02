"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { TbAlertTriangle, TbArrowRight, TbCircleCheck, TbInbox } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { GisFlowService } from "@/service/GisFlowService"
import { cn } from "@/lib/utils"
import { formatarDuracao, formatarInteiro, plural } from "@/lib/formatos"

// Execuções enviadas a um executor e ainda sem confirmação de recebimento.
// As atrasadas (além do limiar) merecem destaque: podem ter se perdido entre
// o servidor e o executor (conexão caiu, executor reiniciou antes de enfileirar).
export type ConfirmacaoPendente = { job_id: string; executor_id: string; elapsed_seconds: number }

export interface ConfirmacoesPendentes {
  itens: ConfirmacaoPendente[]
  limiarSegundos: number
  carregando: boolean
  atrasadas: ConfirmacaoPendente[]
  falhou: boolean
}

/**
 * Poll das confirmações pendentes (a cada 10 s, só com a aba visível). Mora
 * fora do card de propósito: a visão "Confirmações" fica fechada quase sempre,
 * e quem alimenta a pílula vermelha na barra de visões é este hook — o alerta
 * precisa aparecer justamente para quem ainda não foi olhar.
 *
 * `enabled` é o gate do admin: `/pending-acks` é admin-only, e para os demais
 * isso era um 403 a cada 10 s com um erro que ninguém podia resolver.
 */
export function usePendingAcks({ enabled }: { enabled: boolean }): ConfirmacoesPendentes {
  const [itens, setItens] = useState<ConfirmacaoPendente[]>([])
  const [limiarSegundos, setLimiar] = useState(15)
  const [carregando, setCarregando] = useState(true)
  const [falhou, setFalhou] = useState(false)
  // Assinatura da última fila aceita: sem ela cada tick trocava a identidade
  // do array e re-renderizava a página inteira só para manter um contador.
  const assinatura = useRef("")

  useEffect(() => {
    if (!enabled) {
      setCarregando(false)
      return
    }
    let vivo = true
    async function buscar() {
      const res = await GisFlowService.getPendingAcks()
      if (!vivo) return
      setCarregando(false)
      // Lista vazia por falha não é fila vazia — sem isto o card afirmava
      // "tudo confirmado" sem base nenhuma.
      if (res.error || !res.data) {
        setFalhou(true)
        return
      }
      setFalhou(false)
      const proximos = res.data.items ?? []
      // `elapsed_seconds` entra de propósito: é a coluna de tempo da lista.
      const sig = proximos.map(i => `${i.job_id}:${i.elapsed_seconds}`).join("|")
      if (sig !== assinatura.current) {
        assinatura.current = sig
        setItens(proximos)
      }
      setLimiar(res.data.threshold_overdue_seconds ?? 15)
    }
    buscar()
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") buscar()
    }, 10_000)
    const aoMudarVisibilidade = () => {
      if (document.visibilityState === "visible") buscar()
    }
    document.addEventListener("visibilitychange", aoMudarVisibilidade)
    return () => {
      vivo = false
      clearInterval(timer)
      document.removeEventListener("visibilitychange", aoMudarVisibilidade)
    }
  }, [enabled])

  const atrasadas = useMemo(() => itens.filter(i => i.elapsed_seconds >= limiarSegundos), [itens, limiarSegundos])
  return useMemo(
    () => ({ itens, limiarSegundos, carregando, atrasadas, falhou }),
    [itens, limiarSegundos, carregando, atrasadas, falhou],
  )
}

interface Props {
  acks: ConfirmacoesPendentes
  onAbrirExecucao: (runId: string) => void
  /** executor_id → nome amigável (de /metrics/executores); sem ele, o id curto. */
  nomes?: Record<string, string>
}

/** Visão "Confirmações" (spec §4.3): o card de ACK de antes, em português. */
export function VisaoConfirmacoes({ acks, onAbrirExecucao, nomes }: Props) {
  const { itens, limiarSegundos, carregando, atrasadas, falhou } = acks
  // sort + slice a cada render (o poll de ACKs corre a cada 10 s): memoizado na
  // lista para só reordenar quando os itens mudam de fato.
  const topo = useMemo(
    () => [...itens].sort((a, b) => b.elapsed_seconds - a.elapsed_seconds).slice(0, 10),
    [itens],
  )
  const haAtraso = atrasadas.length > 0

  return (
    <section aria-labelledby="confirmacoes-titulo" className="flex flex-col rounded-lg border bg-card shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 pt-4 pb-2">
        <h2 id="confirmacoes-titulo" className="flex items-center gap-2 text-sm font-semibold">
          <TbInbox size={16} className={haAtraso ? "text-red-500" : "text-muted-foreground"} aria-hidden="true" />
          Confirmações pendentes
        </h2>
        <div className="flex items-center gap-2 text-xs">
          <span className={cn(
            "rounded-full px-2 py-0.5 font-medium",
            haAtraso ? "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400" : "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
          )}>
            {plural(atrasadas.length, "atrasada")}
          </span>
          <span className="text-muted-foreground">{formatarInteiro(itens.length)} em espera</span>
        </div>
      </div>
      <div className="px-4 pb-4">
        {carregando && itens.length === 0 ? (
          <div className="flex flex-col gap-2" aria-busy="true">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ) : falhou ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-destructive/20 bg-destructive/10 p-2">
                <TbAlertTriangle className="size-4 text-destructive" aria-hidden="true" />
              </div>
              <p role="alert" className="text-sm text-muted-foreground">
                Não foi possível consultar a fila de confirmações.
                {itens.length > 0 && " Os itens abaixo são da última leitura que deu certo."}
              </p>
            </div>
            {itens.length > 0 && <ListaDeConfirmacoes itens={topo} limiar={limiarSegundos} onAbrir={onAbrirExecucao} nomes={nomes} />}
          </div>
        ) : itens.length === 0 ? (
          <div className="flex items-center gap-3 py-2">
            <div className="rounded-full border border-green-500/20 bg-green-500/10 p-2">
              <TbCircleCheck className="size-4 text-green-600" aria-hidden="true" />
            </div>
            <p className="text-sm text-muted-foreground">
              Nenhuma execução esperando confirmação. Servidor e executores em dia.
            </p>
          </div>
        ) : (
          <>
            <p className="mb-3 text-sm text-muted-foreground">
              {haAtraso
                ? `${plural(atrasadas.length, "execução enviada", "execuções enviadas")} há mais de ${formatarDuracao(limiarSegundos)} sem confirmação do executor. Pode ter se perdido no caminho, ou o executor reiniciou antes de enfileirar.`
                : `${plural(itens.length, "execução enviada", "execuções enviadas")} há pouco — conta como atrasada depois de ${formatarDuracao(limiarSegundos)}.`}
            </p>
            <ListaDeConfirmacoes itens={topo} limiar={limiarSegundos} onAbrir={onAbrirExecucao} nomes={nomes} />
            {itens.length > topo.length && (
              <p className="mt-2 text-xs text-muted-foreground">
                Mostrando as {topo.length} mais antigas de {formatarInteiro(itens.length)}.
              </p>
            )}
          </>
        )}
      </div>
    </section>
  )
}

function ListaDeConfirmacoes({ itens, limiar, onAbrir, nomes }: {
  nomes?: Record<string, string>
  itens: ConfirmacaoPendente[]
  limiar: number
  onAbrir: (runId: string) => void
}) {
  return (
    <ul className="flex flex-col overflow-hidden rounded-md border">
      {itens.map(item => {
        const atrasada = item.elapsed_seconds >= limiar
        return (
          <li key={item.job_id} className="flex items-center justify-between gap-2 px-3 py-2 text-xs transition-colors odd:bg-muted/30 hover:bg-accent/40">
            <div className="flex min-w-0 flex-col">
              <span className="truncate font-mono">{item.job_id}</span>
              <span className="truncate text-muted-foreground">
                executor <span title={item.executor_id}>{nomes?.[item.executor_id] ?? item.executor_id.slice(0, 8)}</span> · há {formatarDuracao(item.elapsed_seconds)}
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {atrasada && (
                <span className="text-[10px] font-medium tracking-wider text-red-600 uppercase dark:text-red-400">atrasada</span>
              )}
              <button
                type="button"
                onClick={() => onAbrir(item.job_id)}
                aria-label={`Abrir execução ${item.job_id}`}
                className="flex size-8 items-center justify-center rounded-md text-primary outline-none hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:size-10"
              >
                <TbArrowRight size={14} aria-hidden="true" />
              </button>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
