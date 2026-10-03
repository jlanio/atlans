"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { useTextosDaCasca } from "@/app/components/home/i18n/da-casca"
import type { IAgendamentoMeu } from "@/service/types"

export interface UseAgendamentos {
  agendamentos: IAgendamentoMeu[]
  /** Only the FIRST load (the skeleton). */
  carregando: boolean
  /** Reload in flight over the list already on screen — `aria-busy`, not a skeleton. */
  atualizando: boolean
  /** An accepted load has already happened: the error block only takes over the list before that. */
  jaCarregou: boolean
  erro: string | null
  /** Quantos agendamentos o servidor tem — a lista vem cortada em `LIMITE`. */
  total: number
  /** One more page in flight (the "Ver mais" (see more)). */
  carregandoMais: boolean
  /** The schedule whose PUT is in flight — the row does not accept a second click. */
  alternandoId: string | null
  recarregar: () => void
  /** Appends the next page. Without this the cutoff at 200 was invisible. */
  carregarMais: () => void
  /** Pause/activate (optimistic). On re-enabling, the server clears `next_run_at`
   *  and recalculates it (the "re-enabling does not fire" fix lives in schedule_service). */
  alternarAtivo: (item: IAgendamentoMeu) => Promise<void>
}

/** The page size we request (the route's default). */
const LIMITE = 200
/** The ceiling the server trims to (`LIMITE_MAXIMO` in `me_router`): asking for
 *  more than this on a reload would return FEWER rows than are already on screen. */
const TETO_DO_SERVIDOR = 500

/**
 * The stored failure: our own microcopy as a KEY, so the sentence comes out in
 * the language in use when it is shown (switching language in Preferences does
 * not reload the list), or the server's `detail`, which is not translated.
 */
type Falha = "carregar" | "carregarMais" | { detalhe: string }

/**
 * The person's schedules, across all workspaces (`GET /me/schedules`).
 * Plain JSON, on the `useConversas` model: `geracao` discards stale responses on
 * a quick switch. Pause/activate is optimistic — the row changes right away, and
 * we reload to bring the `next_run_at` recalculated by the scheduler (the `put`
 * in `updateSchedule` already invalidates the read by epoch).
 *
 * Two rules from §3 of the screen patterns live here: the skeleton is only for
 * the FIRST load (before, pausing a schedule blinked the whole list) and a
 * reload that fails does NOT erase the schedules already on screen.
 *
 * The route is paginated and returns the TOTAL along with the page (the Chats
 * and Collection envelope): without it, the server ceiling truncated silently —
 * whoever saw 200 rows concluded those were all of them.
 */
export function useAgendamentos(): UseAgendamentos {
  const t = useTextosDaCasca().listas
  const [agendamentos, setAgendamentos] = useState<IAgendamentoMeu[]>([])
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [jaCarregou, setJaCarregou] = useState(false)
  const [falha, setFalha] = useState<Falha | null>(null)
  const [total, setTotal] = useState(0)
  const [carregandoMais, setCarregandoMais] = useState(false)
  const [alternandoId, setAlternandoId] = useState<string | null>(null)
  const geracao = useRef(0)
  const jaCarregouRef = useRef(false)
  // The "in flight" guard must apply on the SAME tick as the click: the state
  // only arrives on the next render, and two quick clicks got past both.
  const emVoo = useRef<string | null>(null)
  // How many rows are on screen, without entering the dependencies (`recarregar`
  // must be stable so the mount effect does not re-fire on every load).
  const quantidade = useRef(0)
  quantidade.current = agendamentos.length

  const recarregar = useCallback(() => {
    const minha = ++geracao.current
    if (jaCarregouRef.current) setAtualizando(true)
    else setCarregando(true)
    // Pause/activate reloads: requesting just one page would shrink the list of
    // someone who already clicked "Ver mais". So the reload requests what is on screen.
    const quantas = Math.min(TETO_DO_SERVIDOR, Math.max(LIMITE, quantidade.current))
    GisFlowService.getMySchedules(quantas).then((res) => {
      if (minha !== geracao.current) return
      if (res.success && res.data) {
        setAgendamentos(res.data.itens)
        setTotal(res.data.total)
        setFalha(null)
        jaCarregouRef.current = true
        setJaCarregou(true)
      } else {
        // Our own microcopy before the backend's raw `detail` (a 500 returned
        // "Erro inesperado." (unexpected error) as if it were text written for the person).
        const detalhe = res.error?.message
        setFalha(res.status >= 500 || !detalhe ? "carregar" : { detalhe })
      }
      setCarregando(false)
      setAtualizando(false)
    })
  }, [])

  useEffect(() => { recarregar() }, [recarregar])

  const carregarMais = useCallback(() => {
    // The generation does NOT advance: this is another page of the SAME load, and
    // a parallel reload (the "Tentar de novo", or the one pause/activate
    // triggers) must be able to invalidate it.
    const minha = geracao.current
    setCarregandoMais(true)
    GisFlowService.getMySchedules(LIMITE, quantidade.current).then((res) => {
      if (minha !== geracao.current) { setCarregandoMais(false); return }
      if (res.success && res.data) {
        const pagina = res.data.itens
        setAgendamentos((atual) => {
          // The order is by next run and the scheduler recalculates it every
          // ~30 s: between two pages a row can slip and repeat. The
          // key is the `job_id`, not the position.
          const vistos = new Set(atual.map((a) => a.job_id))
          return [...atual, ...pagina.filter((a) => !vistos.has(a.job_id))]
        })
        setTotal(res.data.total)
        setFalha(null)
      } else {
        setFalha("carregarMais")
      }
      setCarregandoMais(false)
    })
  }, [])

  const alternarAtivo = useCallback(async (item: IAgendamentoMeu) => {
    // Without this guard, two clicks on a slow network fired two PUTs and the
    // first one's error reverted the row to a state the second had already superseded.
    if (emVoo.current === item.job_id) return
    emVoo.current = item.job_id
    setAlternandoId(item.job_id)
    const alvo = !item.active
    // Optimistic: the row changes now. On activating, the "next" disappears until
    // the scheduler recalculates (up to ~30 s) — the summary shows "calculando" (calculating) meanwhile.
    setAgendamentos((atual) =>
      atual.map((a) =>
        a.job_id === item.job_id
          ? { ...a, active: alvo, next_run_at: alvo ? null : a.next_run_at }
          : a,
      ),
    )
    const res = await GisFlowService.updateSchedule(item.workflow_id, item.job_id, { active: alvo })
    emVoo.current = null
    setAlternandoId(null)
    if (res.success) {
      createToast.success(alvo ? t.agendamentos.ativou : t.agendamentos.pausou)
      recarregar()
    } else {
      // Revert to the previous state.
      setAgendamentos((atual) =>
        atual.map((a) =>
          a.job_id === item.job_id
            ? { ...a, active: item.active, next_run_at: item.next_run_at }
            : a,
        ),
      )
      createToast.error(t.agendamentos.alterarFalhou, res.error?.message ?? t.geral.tenteDeNovo)
    }
  }, [recarregar, t])

  const erro = falha == null
    ? null
    : falha === "carregar"
      ? t.agendamentos.carregarFalhou
      : falha === "carregarMais"
        ? t.agendamentos.carregarMaisFalhou
        : falha.detalhe

  return {
    agendamentos, carregando, atualizando, jaCarregou, erro, total, carregandoMais,
    alternandoId, recarregar, carregarMais, alternarAtivo,
  }
}
