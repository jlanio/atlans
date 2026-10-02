"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { useTextosDaCasca } from "@/app/components/home/i18n/da-casca"
import type { IAgendamentoMeu } from "@/service/types"

export interface UseAgendamentos {
  agendamentos: IAgendamentoMeu[]
  /** Só a PRIMEIRA carga (o esqueleto). */
  carregando: boolean
  /** Recarga em voo sobre a lista já na tela — `aria-busy`, não esqueleto. */
  atualizando: boolean
  /** Já houve uma carga aceita: o bloco de erro só toma a lista antes disso. */
  jaCarregou: boolean
  erro: string | null
  /** Quantos agendamentos o servidor tem — a lista vem cortada em `LIMITE`. */
  total: number
  /** Uma página a mais em voo (o "Ver mais"). */
  carregandoMais: boolean
  /** O agendamento cujo PUT está em voo — a linha não aceita um segundo clique. */
  alternandoId: string | null
  recarregar: () => void
  /** Anexa a próxima página. Sem isto o corte em 200 era invisível. */
  carregarMais: () => void
  /** Pausa/ativa (otimista). Ao religar, o servidor zera `next_run_at` e recalcula
   *  (o fix de "religar não dispara" mora no schedule_service). */
  alternarAtivo: (item: IAgendamentoMeu) => Promise<void>
}

/** O tamanho de página que pedimos (o padrão da rota). */
const LIMITE = 200
/** O teto que o servidor apara (`LIMITE_MAXIMO` do `me_router`): pedir mais que
 *  isto numa recarga devolveria MENOS linhas do que já estão na tela. */
const TETO_DO_SERVIDOR = 500

/**
 * A falha guardada: a microcopy da casa como CHAVE, para a frase sair no idioma
 * em uso quando é mostrada (trocar de idioma nas Preferências não recarrega a
 * lista), ou o `detail` do servidor, que não se traduz.
 */
type Falha = "carregar" | "carregarMais" | { detalhe: string }

/**
 * Os agendamentos da pessoa, entre todos os workspaces (`GET /me/schedules`).
 * JSON puro, no molde do `useConversas`: `geracao` descarta respostas velhas numa
 * troca rápida. Pausar/ativar é otimista — a linha muda na hora, e recarregamos
 * para trazer o `next_run_at` recalculado pelo agendador (o `put` do
 * `updateSchedule` já invalida a leitura por época).
 *
 * Duas regras do §3 do padrão de telas moram aqui: o esqueleto é só da PRIMEIRA
 * carga (antes, pausar um agendamento piscava a lista inteira) e uma recarga que
 * falha NÃO apaga os agendamentos já na tela.
 *
 * A rota é paginada e devolve o TOTAL junto da página (o envelope de Chats e do
 * Acervo): sem ele, o teto do servidor truncava em silêncio — quem via 200
 * linhas concluía que eram todas.
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
  // O guarda de "em voo" precisa valer no MESMO tick do clique: o estado só
  // chega no render seguinte, e dois cliques rápidos passavam pelos dois.
  const emVoo = useRef<string | null>(null)
  // Quantas linhas estão na tela, sem entrar nas dependências (o `recarregar`
  // precisa ser estável para o efeito de montagem não relançar a cada carga).
  const quantidade = useRef(0)
  quantidade.current = agendamentos.length

  const recarregar = useCallback(() => {
    const minha = ++geracao.current
    if (jaCarregouRef.current) setAtualizando(true)
    else setCarregando(true)
    // Pausar/ativar recarrega: pedir só uma página encolheria a lista de quem já
    // clicou "Ver mais". Por isso a recarga pede o que está na tela.
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
        // A microcopy da casa antes do `detail` cru do backend (um 500 devolvia
        // "Erro inesperado." como se fosse texto escrito para a pessoa).
        const detalhe = res.error?.message
        setFalha(res.status >= 500 || !detalhe ? "carregar" : { detalhe })
      }
      setCarregando(false)
      setAtualizando(false)
    })
  }, [])

  useEffect(() => { recarregar() }, [recarregar])

  const carregarMais = useCallback(() => {
    // A geração NÃO avança: esta é outra página da MESMA carga, e uma recarga em
    // paralelo (o "Tentar de novo", ou a que pausar/ativar dispara) precisa
    // poder invalidá-la.
    const minha = geracao.current
    setCarregandoMais(true)
    GisFlowService.getMySchedules(LIMITE, quantidade.current).then((res) => {
      if (minha !== geracao.current) { setCarregandoMais(false); return }
      if (res.success && res.data) {
        const pagina = res.data.itens
        setAgendamentos((atual) => {
          // A ordem é por próxima execução e o agendador a recalcula a cada
          // ~30 s: entre duas páginas uma linha pode escorregar e repetir. A
          // chave é o `job_id`, não a posição.
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
    // Sem este guarda, dois cliques na rede lenta soltavam dois PUT e o erro do
    // primeiro revertia a linha para um estado que o segundo já tinha superado.
    if (emVoo.current === item.job_id) return
    emVoo.current = item.job_id
    setAlternandoId(item.job_id)
    const alvo = !item.active
    // Otimista: a linha muda já. Ao ativar, some a "próxima" até o agendador
    // recalcular (até ~30 s) — o resumo mostra "calculando" nesse meio-tempo.
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
      // Reverte ao estado anterior.
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
