"use client"

/**
 * Visibilidade global de execuções em andamento.
 *
 * Faz polling de /observability/runs?status=running (leve — só runs vivos, e o
 * backend já escopa pelo usuário) e, cruzando com os workflows do workspace atual,
 * expõe quais estão "rodando agora". Um único mecanismo alimenta três coisas:
 *   - o pill ao vivo no card de cada workflow (runningHashes)
 *   - o indicador "N execuções" no sidebar (runningRuns / runningCount)
 *   - a notificação ao concluir em background
 *
 * Conclusão é detectada quando um run some do conjunto "running"; o status final
 * (sucesso/falha) vem de um getRunDetail pontual (só nesse momento, raro), evitando
 * baixar centenas de registros a cada tick só para achar terminais.
 *
 * O workflow_name é admin-only em /observability/runs, por isso cruzamos com
 * getWorkflows para ter os nomes (e para escopar ao workspace atual).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useNotifications } from "@/context/NotificationsContext"

export interface RunningRun {
  runId: string
  workflowHash: string
  name: string
  /** ISO de `started_at`; nulo enquanto o run está na fila. */
  startedAt: string | null
  /** `trigger_source` do run (manual, schedule, webhook, retry). */
  triggerSource: string | null
  /** Nome amigável do executor; nulo sem host. */
  executorName: string | null
}

// O que se guarda de cada run vivo entre um poll e outro. Além do nome, os
// três campos que a lista de Projetos mostra na linha "em execução" (spec
// projetos §2.3) — `/observability/runs` já os devolve, então custam zero.
type RunVivo = Pick<RunningRun, "name" | "startedAt" | "triggerSource" | "executorName"> & { hash: string }

interface ActiveRunsValue {
  /** Set de id_hash dos workflows com run vivo no workspace. */
  runningHashes: Set<string>
  /** Runs vivos do workspace atual, com nome resolvido. */
  runningRuns: RunningRun[]
  /** Nº de execuções em andamento. */
  runningCount: number
  /** Força um poll imediato (ex.: logo após um disparo rápido na lista). */
  refresh: () => void
}

const ActiveRunsContext = createContext<ActiveRunsValue | undefined>(undefined)

// Cadência com a aba em foco e algum run vivo — é quando o usuário está de fato
// esperando o resultado aparecer.
const POLL_MS = 10_000
// Cadência quando não há run algum rodando, que é o caso comum. Este provider
// vive no layout do dashboard, então roda em TODAS as telas: sem o degrau, uma
// aba ociosa esquecida gerava ~8.600 requests/dia sozinha.
const IDLE_POLL_MS = 30_000
const LIMIT = 200
const TERMINAL = new Set(["success", "failed"])

export function ActiveRunsProvider({ children }: { children: ReactNode }) {
  const { current } = useWorkspace()
  const { addNotification } = useNotifications()
  const workspaceId = current?.id_hash

  const [runningHashes, setRunningHashes] = useState<Set<string>>(new Set())
  const [runningRuns, setRunningRuns] = useState<RunningRun[]>([])

  // Poll manual sem esperar o intervalo (setado dentro do efeito).
  const pollRef = useRef<() => void>(() => {})

  useEffect(() => {
    if (!workspaceId) {
      setRunningHashes(new Set())
      setRunningRuns([])
      return
    }

    let alive = true
    let timer: ReturnType<typeof setTimeout> | null = null
    let namesByHash = new Map<string, string>()
    // Hashes que já tentamos resolver e continuam ausentes de namesByHash. O
    // poll traz runs de TODOS os workspaces do usuário (o backend escopa por
    // usuário), mas namesByHash só tem os workflows do workspace ATIVO — então
    // um run vivo de OUTRO workspace nunca entra no mapa e, sem esta memória,
    // forçava um getWorkflows() completo a cada tick enquanto vivesse.
    //
    // `hash -> instante da tentativa`, com TTL (não `Set` permanente): um
    // workflow recém-criado pode ainda não constar no getWorkflows (consistência
    // eventual). Sem expirar, ele ficaria sem nome pelo resto da sessão; com o
    // TTL, um tick posterior re-tenta e o nome aparece assim que o backend o lista.
    const tentados = new Map<string, number>()
    const TENTADO_TTL_MS = 60_000
    // run_id -> {hash, name} dos runs vivos no ÚLTIMO poll. Reconstruído a cada
    // tick → tamanho limitado ao nº de runs vivos (não cresce indefinidamente).
    let prevLive = new Map<string, RunVivo>()
    // O primeiro poll apenas semeia prevLive (não notifica runs que já haviam
    // terminado antes do app abrir / antes de trocar de workspace).
    let seeded = false
    // Assinatura do conjunto vivo — evita re-render dos consumidores quando nada muda.
    let sig = ""

    async function loadNames(): Promise<boolean> {
      // Inclui os fluxos do assistente: um run vivo de um fluxo do assistente
      // (escondido das listagens por padrão) precisa do NOME para o pill, senão
      // aparece sem rótulo. Aqui é resolução de nome, não a lista que o dono vê.
      const res = await GisFlowService.getWorkflows(workspaceId, { incluirDoAssistente: true })
      if (!alive) return false
      // Erro transitório NÃO zera os nomes já resolvidos: sobrescrever com um
      // mapa vazio faria todo pill perder o nome até a próxima carga bem-sucedida
      // — que, com o hash já dado como "tentado", nem chegaria a acontecer.
      if (!res.data) return false
      namesByHash = new Map(res.data.map((w) => [w.id_hash, w.name]))
      return true
    }

    async function notifyIfCompleted(runId: string, name: string) {
      // Confirma o estado terminal antes de notificar — evita falso-positivo se o
      // run saiu do conjunto por outro motivo que não conclusão.
      const detail = await GisFlowService.getRunDetail(runId)
      if (!alive || !detail.data) return
      const st = detail.data.status
      if (!TERMINAL.has(st)) return
      addNotification({
        type: st === "success" ? "success" : "error",
        title: st === "success" ? "Workflow concluído" : "Workflow falhou",
        message: name || undefined,
      })
    }

    async function poll() {
      const resp = await GisFlowService.getObservabilityRuns({ status: "running", limit: LIMIT })
      if (!alive || !resp.data) return   // erro transitório → mantém estado (sem piscar)

      const raw = resp.data.runs ?? []
      // Workflow recém-criado ainda não está no mapa de nomes → recarrega uma
      // vez por hash inédito. Runs de outro workspace ficam em `tentados` (com
      // TTL) e não voltam a disparar loadNames() nos ticks seguintes.
      const agora = Date.now()
      const inéditos = raw.filter((r) =>
        r.workflow_hash
        && !namesByHash.has(r.workflow_hash)
        && agora - (tentados.get(r.workflow_hash) ?? 0) > TENTADO_TTL_MS
      )
      if (inéditos.length > 0) {
        const ok = await loadNames()
        if (!alive) return
        // Só marca "já tentei e não achei" quando a carga SUCEDEU e o hash ainda
        // assim não veio (outro workspace, ou ainda não replicado). Uma falha de
        // rede não condena o hash: o próximo tick tenta de novo.
        if (ok) {
          for (const r of inéditos) {
            if (!namesByHash.has(r.workflow_hash!)) tentados.set(r.workflow_hash!, agora)
          }
        }
      }

      // Escopa ao workspace atual (só workflows que ele conhece).
      const nextLive = new Map<string, RunVivo>()
      for (const r of raw) {
        const hash = r.workflow_hash
        if (!hash || !namesByHash.has(hash)) continue
        nextLive.set(r.run_id, {
          hash,
          name: namesByHash.get(hash) ?? "Workflow",
          startedAt: r.started_at ?? null,
          triggerSource: r.trigger_source ?? null,
          executorName: r.executor_name ?? null,
        })
      }

      // Conclusões: run que estava vivo antes e sumiu agora.
      if (seeded) {
        for (const [runId, info] of prevLive) {
          if (!nextLive.has(runId)) void notifyIfCompleted(runId, info.name)
        }
      }
      prevLive = nextLive
      seeded = true

      // Atualiza o estado só quando o conjunto vivo muda (evita re-render a cada 10s).
      const nextSig = [...nextLive.keys()].sort().join(",")
      if (nextSig !== sig) {
        sig = nextSig
        setRunningRuns([...nextLive].map(([runId, i]) => ({
          runId, workflowHash: i.hash, name: i.name,
          startedAt: i.startedAt, triggerSource: i.triggerSource, executorName: i.executorName,
        })))
        setRunningHashes(new Set([...nextLive.values()].map((i) => i.hash)))
      }
    }

    // Serializa as chamadas: há três gatilhos (tick agendado, retorno de foco e
    // refresh manual via pollRef) e nada impedia que se sobrepusessem.
    let inFlight = false
    const pollOnce = async () => {
      if (inFlight) return
      inFlight = true
      try {
        await poll()
      } catch {
        // rede intermitente — mantém o estado anterior; próximo tick tenta de novo
      } finally {
        inFlight = false
      }
    }

    pollRef.current = () => { void pollOnce() }

    // Agenda o próximo tick em vez de usar setInterval de período fixo: assim a
    // cadência acompanha o estado (aba oculta = não consulta; nada rodando =
    // consulta menos). Com setInterval a decisão só poderia ser "pular o tick",
    // o que mantém o timer acordando à toa a cada 10s.
    const scheduleNext = () => {
      if (!alive) return
      const intervalo = prevLive.size > 0 ? POLL_MS : IDLE_POLL_MS
      timer = setTimeout(async () => {
        // Aba oculta não precisa de dado fresco: ninguém está olhando, e o
        // `visibilitychange` abaixo dispara um poll imediato ao voltar o foco.
        if (document.visibilityState === "visible") {
          await pollOnce()
        }
        scheduleNext()
      }, intervalo)
    }

    // Ao voltar para a aba, atualiza na hora — sem isso o usuário encararia
    // dado velho por até IDLE_POLL_MS depois de retomar o foco.
    //
    // A trava de in-flight importa aqui: alternar abas em sequência dispara um
    // `visibilitychange` por alternância, e sem ela cada alt-tab viraria um
    // request — trabalhando contra o objetivo de reduzir carga. O tick agendado
    // e o refresh manual (pollRef) passam pela mesma trava.
    const onVisibility = () => {
      if (document.visibilityState === "visible") void pollOnce()
    }
    document.addEventListener("visibilitychange", onVisibility)

    ;(async () => {
      try {
        await loadNames()
      } catch {
        // sem os nomes o poll ainda funciona (filtra pelo que conhece); tenta de novo no tick
      }
      if (!alive) return
      await pollOnce()
      if (!alive) return
      scheduleNext()
    })()

    return () => {
      alive = false
      if (timer) clearTimeout(timer)
      document.removeEventListener("visibilitychange", onVisibility)
      pollRef.current = () => {}
    }
  }, [workspaceId, addNotification])

  // O refresh atravessa o ref, então é estável de propósito: o valor do context
  // só muda quando o conjunto de runs vivos muda. Antes, cada render deste
  // provider (que fica na raiz do dashboard) criava um objeto novo e propagava
  // re-render para todas as telas abaixo, mesmo com o poll sem novidade.
  const refresh = useCallback(() => { pollRef.current() }, [])

  const value = useMemo<ActiveRunsValue>(
    () => ({ runningHashes, runningRuns, runningCount: runningRuns.length, refresh }),
    [runningHashes, runningRuns, refresh],
  )

  return (
    <ActiveRunsContext.Provider value={value}>
      {children}
    </ActiveRunsContext.Provider>
  )
}

export function useActiveRuns(): ActiveRunsValue {
  const ctx = useContext(ActiveRunsContext)
  if (!ctx) throw new Error("useActiveRuns precisa estar dentro de <ActiveRunsProvider>")
  return ctx
}
