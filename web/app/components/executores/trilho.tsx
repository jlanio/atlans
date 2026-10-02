"use client"

// O "trilho" — tabela densa de executores, mantida como VARIANTE DELIBERADA do
// contrato (serve à comparação vertical entre máquinas; não vira lista de
// cartões). Aqui ficam a grade de colunas, o cabeçalho, a linha (ExecutorRow) e
// os medidores que ela abre. A padronização foi de apresentação: tokens de
// status (green no lugar de emerald), `tabular-nums` nos números, foco visível,
// alvos de toque ≥40px no telefone e formatação via `lib/formatos`.

import React, { useCallback, useEffect, useMemo, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IExecutor, IExecutorMetrics } from "@/service/GisFlowService"
import type { IExecutorUserAssignment } from "@/service/types"
import { estiloDoTipo } from "@/consts/ExecutorTypeStyles"
import { cn } from "@/lib/utils"
import { fromBackend } from "@/lib/dayjs"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { createToast } from "@/utils/createToast"
import {
  TbCopy, TbCheck, TbDots, TbServer,
  TbTag, TbLayoutGrid, TbClock,
  TbStar, TbUsers, TbUserMinus, TbUserPlus, TbSearch,
  TbCpu, TbDeviceDesktop, TbDatabase, TbChevronDown, TbChevronRight,
  TbShieldLock,
} from "react-icons/tb"
import { formatarPercentual, formatarDuracao, formatarQuando, plural } from "@/lib/formatos"
import { successRateColor } from "@/utils/formatters"
import { EnrollmentOtpDialog } from "./enroll"
import { EditAgentDialog, RevokeAgentDialog, DeleteAgentDialog } from "./dialogs"

// ── Helpers ────────────────────────────────────────────────────────────────────

// Rótulo pt-BR do status do EXECUTOR. Distinto de `rotuloDoStatus` (shared),
// que traduz status de EXECUÇÃO (success/failed/running…): os vocabulários não
// se sobrepõem — "pending" de um executor é "aguardando enrollment", não "na
// fila" — então a tradução do executor mora aqui, no seu domínio.
const ROTULO_STATUS_EXECUTOR: Record<IExecutor["status"], string> = {
  active:   "Ativo",
  pending:  "Pendente",
  inactive: "Inativo",
  revoked:  "Revogado",
}

/** Tempo no ar em segundos, para formatar por extenso via `formatarDuracao`. */
function uptimeEmSegundos(connectedAt: string | null): number | null {
  if (!connectedAt) return null
  const start = fromBackend(connectedAt)?.valueOf()
  if (!start) return null
  return Math.max(0, Math.floor((Date.now() - start) / 1000))
}

// ── Grade do trilho ───────────────────────────────────────────────────────────
// A grade é declarada UMA vez e usada pelo cabeçalho e por cada linha. Foi o
// que faltava no card empilhado: a faixa de hardware era `flex-wrap`, então
// RAM e disco pousavam num x diferente por executor e nada era comparável na
// vertical.
//
// Uma vez, mas em TRÊS larguras. As colunas fixas somavam 360px (492px com a de
// tipo) e não cabiam nem num tablet com a sidebar aberta — muito menos num
// telefone, onde o `overflow-x: clip` do body CORTA o que vaza em vez de rolar:
// o menu de ações de cada linha ficava fora da tela, sem caminho até ele.
//
//   < md   telefone — duas linhas por executor, sem colunas (ver ExecutorRow)
//   md     trilho enxuto — tipo e versão saem; o nome é o que distingue as linhas
//   lg     trilho inteiro
const TRILHO_COLUNAS = cn(
  "grid-cols-[1.25rem_minmax(0,1fr)_auto]",
  "md:grid-cols-[1.25rem_minmax(0,1fr)_6rem_5rem_2rem]",
  "lg:grid-cols-[1.25rem_minmax(0,1fr)_6rem_4.5rem_5rem_2rem]",
)
/** Coluna de tipo — só no trilho inteiro. Na faixa `md` o cabeçalho do grupo já
 *  nomeia o tipo, e repeti-lo por linha custava 120px que faltavam ao nome. */
const TRILHO_COLUNAS_TIPO = "lg:grid-cols-[1.25rem_minmax(0,1fr)_7.5rem_6rem_4.5rem_5rem_2rem]"

/** Cabeçalho de colunas do trilho. */
export function CabecalhoDoTrilho({ mostrarTipo }: { mostrarTipo: boolean }) {
  return (
    // `hidden md:grid`: no telefone a linha não tem colunas, e um cabeçalho de
    // colunas sobre um empilhamento rotularia o que não existe.
    // font-mono aqui é intencional — rótulos de coluna em caixa-alta dão o tom
    // "terminal" do trilho; não são números (ver o contrato §5 sobre tabular-nums).
    <div className={cn("hidden md:grid gap-3", TRILHO_COLUNAS, mostrarTipo && TRILHO_COLUNAS_TIPO,
      "items-center px-3 py-1.5 bg-muted/50 border-b border-border",
      "font-mono text-[10px] uppercase tracking-wider text-muted-foreground select-none")}>
      <span />
      <span className="flex items-center gap-1"><TbServer size={11} className="opacity-75" aria-hidden="true" />executor</span>
      {mostrarTipo && <span className="hidden lg:flex items-center gap-1"><TbTag size={11} className="opacity-75" aria-hidden="true" />tipo</span>}
      <span className="flex items-center gap-1"><TbLayoutGrid size={11} className="opacity-75" aria-hidden="true" />slots</span>
      <span className="hidden lg:flex items-center justify-end gap-1"><TbTag size={11} className="opacity-75" aria-hidden="true" />versão</span>
      <span className="flex items-center justify-end gap-1"><TbClock size={11} className="opacity-75" aria-hidden="true" />atividade</span>
      <span />
    </div>
  )
}

/** LED de estado — um sinal só.
 *
 *  O card dizia o estado quatro vezes: faixa colorida na borda, cor do ícone,
 *  badge de texto e a frase "Conectado há…". E os quatro podiam discordar —
 *  `status: "active"` com `online: false` dava faixa âmbar, ícone cinza e badge
 *  verde "Ativo" ao mesmo tempo. */
export function EstadoDoExecutor({ status, online, className }: {
  status: IExecutor["status"]; online: boolean; className?: string
}) {
  const { classe, titulo } =
    status === "revoked"  ? { classe: "bg-destructive/70",                        titulo: "Revogado" } :
    status === "pending"  ? { classe: "ring-1 ring-inset ring-muted-foreground",  titulo: "Aguardando enrollment" } :
    status === "inactive" ? { classe: "ring-1 ring-inset ring-muted-foreground",  titulo: "Inativo" } :
    online                ? { classe: "bg-green-500 shadow-[0_0_0_3px] shadow-green-500/20", titulo: "Ativo e conectado" } :
                            { classe: "ring-[1.5px] ring-inset ring-amber-500",   titulo: "Ativo, sem contato" }
  return (
    <span className={cn("flex justify-center", className)} title={titulo}>
      <span aria-label={titulo} role="img" className={cn("block size-2 rounded-full", classe)} />
    </span>
  )
}

/** Ocupação em células, uma por vaga.
 *
 *  `running` e `max_concurrent` são contagens DISCRETAS. A `LoadBar` desenhava
 *  uma barra contínua, e ali 4/4 e 4/4-com-seis-na-fila viravam a mesma barra
 *  cheia. As células da fila ficam ALÉM do limite, mostrando o excesso. */
export function MedidorDeSlots({ running, queued, maxConcurrent, online }: {
  running: number; queued: number; maxConcurrent: number; online: boolean
}) {
  if (!online) return <span className="hidden md:inline text-[11px] tabular-nums text-muted-foreground">—</span>

  // Teto de células: `max_concurrent` é configurável e uma máquina com 64 vagas
  // esticaria a coluna. Acima disso o número basta.
  // Teto baixo de propósito: a coluna tem largura fixa, e o alinhamento
  // vertical é a razão de existir do trilho. Com 8 vagas + 3 de fila as
  // células passavam de 110px numa faixa de 96px e invadiam "versão",
  // quebrando justamente o que a grade veio garantir. O número ao lado
  // continua exato.
  const TETO = 5
  const vagas = Math.max(0, Math.min(maxConcurrent, TETO))
  const naFila = Math.min(queued, 2)

  return (
    <span className="flex items-center gap-[2px] min-w-0 overflow-hidden" title={`${running} de ${maxConcurrent} em execução${queued > 0 ? `, ${queued} na fila` : ""}`}>
      {Array.from({ length: vagas }).map((_, i) => (
        <span key={i} className={cn("block w-[5px] h-3 rounded-[2px]",
          i < running ? "bg-blue-500" : "bg-muted-foreground/25")} />
      ))}
      {Array.from({ length: naFila }).map((_, i) => (
        <span key={`f${i}`} className="block w-[5px] h-3 rounded-[2px] ring-[1.5px] ring-inset ring-blue-500/55" />
      ))}
      <span className="ml-1 text-[10px] tabular-nums text-muted-foreground">
        {running}/{maxConcurrent}{queued > 0 && ` +${queued}`}
      </span>
    </span>
  )
}

// ── Barra de carga (na gaveta) ────────────────────────────────────────────────

export function LoadBar({ running, queued, maxConcurrent, maxQueue }: {
  running: number
  queued: number
  maxConcurrent: number
  maxQueue: number
}) {
  const usedPct  = Math.min((running / maxConcurrent) * 100, 100)
  const queuePct = Math.min((queued / Math.max(maxQueue, 1)) * 100, 100)

  return (
    <div className="flex flex-col gap-1 min-w-[120px]">
      {/* Execução */}
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground w-14 shrink-0">Rodando</span>
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-500 motion-safe:transition-all"
            style={{ width: `${usedPct}%` }}
          />
        </div>
        <span className="text-[10px] tabular-nums text-muted-foreground w-10 text-right shrink-0">
          {running}/{maxConcurrent}
        </span>
      </div>
      {/* Fila */}
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground w-14 shrink-0">Na fila</span>
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={cn("h-full rounded-full motion-safe:transition-all", queued > 0 ? "bg-amber-500" : "bg-muted-foreground/20")}
            style={{ width: `${queuePct}%` }}
          />
        </div>
        <span className="text-[10px] tabular-nums text-muted-foreground w-10 text-right shrink-0">
          {queued}/{maxQueue}
        </span>
      </div>
    </div>
  )
}

// ── Bloco de métricas históricas ─────────────────────────────────────────────

export function ExecutorHistoricMetrics({ metrics }: { metrics: IExecutorMetrics }) {
  return (
    <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
      <span>
        <span className="font-medium tabular-nums text-foreground">{metrics.total_runs}</span> execuções
      </span>
      <span>
        {/* Percentual em pt-BR: "96,4%" com vírgula (formatarPercentual), não
            "96.4%" com ponto. A cor segue a regra unificada de successRate. */}
        <span className={cn("font-medium tabular-nums", successRateColor(metrics.success_rate, "amber"))}>
          {formatarPercentual(metrics.success_rate)}
        </span> sucesso
      </span>
      {metrics.avg_duration_seconds != null && (
        <span>
          <span className="font-medium tabular-nums text-foreground">{formatarDuracao(metrics.avg_duration_seconds)}</span> média
        </span>
      )}
      {metrics.last_run_at && (
        <span className="tabular-nums">última {formatarQuando(metrics.last_run_at)}</span>
      )}
    </div>
  )
}

// ── Seção de usuários atribuídos ao executor ─────────────────────────────────

// A seção fica atrás de um disclosure porque ela era montada em TODO card de
// executor dedicado: abrir /executores como admin disparava um
// GET /executores/{id}/users por card, dezenas de requisições em paralelo
// disputando as 6 conexões do browser só para preencher um bloco que quase
// ninguém abre. Agora a busca só acontece quando o admin de fato expande.
export function AgentUsersSection({ agentId }: { agentId: string }) {
  const [aberto, setAberto]       = useState(false)
  const [users, setUsers]         = useState<IExecutorUserAssignment[]>([])
  const [loading, setLoading]     = useState(false)
  const [email, setEmail]         = useState("")
  const [searching, setSearching] = useState(false)
  const [results, setResults]     = useState<{ id_hash: string; username: string; email: string }[]>([])
  const [assigning, setAssigning] = useState(false)
  const [removingId, setRemovingId] = useState<string | null>(null)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    const res = await GisFlowService.getAgentUsers(agentId)
    if (res.data) setUsers(res.data)
    setLoading(false)
  }, [agentId])

  useEffect(() => { if (aberto) loadUsers() }, [aberto, loadUsers])

  async function handleSearch() {
    if (email.length < 3) return
    setSearching(true)
    setResults([])
    const res = await GisFlowService.searchUsersByEmail(email)
    if (res.data) setResults(res.data)
    setSearching(false)
  }

  async function handleAssign(userId: string, username: string) {
    setAssigning(true)
    const res = await GisFlowService.assignAgentToUser(agentId, userId)
    setAssigning(false)
    if (res.error) {
      createToast.error("Erro ao atribuir executor.")
    } else {
      createToast.success(`Executor atribuído a ${username}.`)
      setEmail("")
      setResults([])
      loadUsers()
    }
  }

  async function handleRemove(userId: string, username: string) {
    setRemovingId(userId)
    const res = await GisFlowService.removeAgentUser(agentId, userId)
    setRemovingId(null)
    if (res.error) {
      createToast.error("Erro ao remover atribuição.")
    } else {
      createToast.success(`Atribuição de ${username} removida.`)
      loadUsers()
    }
  }

  // Memoizado: sem isto o Set era reconstruído a cada render — inclusive a cada
  // tecla na busca de e-mail. Só muda quando a lista de atribuídos muda.
  const assignedIds = useMemo(() => new Set(users.map(u => u.user_id)), [users])

  return (
    <div className="border-t border-border pt-3 mt-1 flex flex-col gap-3">
      <button
        type="button"
        onClick={() => setAberto(v => !v)}
        aria-expanded={aberto}
        className="flex items-center gap-1.5 self-start rounded-sm text-xs font-medium text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
      >
        {aberto ? <TbChevronDown size={13} aria-hidden="true" /> : <TbChevronRight size={13} aria-hidden="true" />}
        <TbUsers size={13} aria-hidden="true" />
        <span>Usuários atribuídos</span>
        {aberto && !loading && <span className="tabular-nums text-foreground">({users.length})</span>}
      </button>

      {!aberto ? null : loading ? (
        <div className="text-xs italic text-muted-foreground">Carregando…</div>
      ) : users.length === 0 ? (
        <div className="text-xs italic text-muted-foreground">Nenhum usuário atribuído.</div>
      ) : (
        <ul className="flex flex-col gap-1">
          {users.map(u => (
            <li key={u.user_id} className="flex items-center justify-between gap-2 text-xs">
              <div className="min-w-0 truncate">
                <span className="font-medium text-foreground">{u.username}</span>
                <span className="ml-1.5 text-muted-foreground">{u.email}</span>
              </div>
              <button
                type="button"
                onClick={() => handleRemove(u.user_id, u.username)}
                disabled={removingId === u.user_id}
                aria-label={`Remover atribuição de ${u.username}`}
                title="Remover atribuição"
                className="shrink-0 rounded p-1 text-muted-foreground outline-none transition-colors hover:text-destructive focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10 max-md:min-w-10"
              >
                <TbUserMinus size={14} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Busca e atribuição */}
      {aberto && (
        <div className="flex gap-2">
          <Input
            placeholder="Buscar usuário por e-mail…"
            value={email}
            onChange={e => { setEmail(e.target.value); setResults([]) }}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            className="h-8 text-xs max-md:h-10"
          />
          <Button size="sm" variant="outline" onClick={handleSearch} disabled={searching || email.length < 3} className="h-8 shrink-0 px-2 max-md:h-10 max-md:w-10" aria-label="Buscar usuário">
            <TbSearch size={14} aria-hidden="true" />
          </Button>
        </div>
      )}

      {aberto && results.length > 0 && (
        <ul className="flex flex-col gap-1 overflow-hidden rounded-md border border-border">
          {results.map(r => (
            <li key={r.id_hash} className="flex items-center justify-between gap-2 px-3 py-1.5 text-xs hover:bg-muted/50">
              <div className="min-w-0 truncate">
                <span className="font-medium text-foreground">{r.username}</span>
                <span className="ml-1.5 text-muted-foreground">{r.email}</span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleAssign(r.id_hash, r.username)}
                disabled={assigning || assignedIds.has(r.id_hash)}
                className="h-6 shrink-0 px-2 text-xs max-md:h-10"
              >
                {assignedIds.has(r.id_hash) ? (
                  <><TbCheck size={12} className="mr-1 text-green-500" aria-hidden="true" /> Atribuído</>
                ) : (
                  <><TbUserPlus size={12} className="mr-1" aria-hidden="true" /> Atribuir</>
                )}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Linha de executor ─────────────────────────────────────────────────────────

// React.memo: o auto-refresh de 15s traz objetos novos do JSON, mas só alguns
// executores mudam de fato. Sem o memo (e com `onRefresh` já estabilizado pelo
// useFetchData), a lista inteira era recriada a cada ciclo. A reconciliação por
// conteúdo (ver reconciliar-executores.ts) é o que faz a comparação rasa do
// memo de fato economizar.
export const ExecutorRow = React.memo(function ExecutorRow({ executor, metrics, onRefresh, isAdmin, currentUserId, mostrarTipo, ehEsteComputador }: {
  executor: IExecutor
  metrics: IExecutorMetrics | undefined
  onRefresh: () => void
  isAdmin: boolean
  currentUserId?: string
  /** O selo de tipo só informa quando a lista mistura tipos — sob um filtro de
   *  categoria seria a mesma palavra em toda linha. */
  mostrarTipo: boolean
  /** Este executor é a máquina onde o app desktop está rodando (só no desktop). */
  ehEsteComputador?: boolean
}) {
  // Detalhe fechado por padrão: hardware, histórico e usuários eram o que
  // fazia cada executor ocupar ~200px de altura, e é justamente o que não se
  // compara entre máquinas — some da varredura e volta sob demanda.
  const [aberto, setAberto] = useState(false)
  const estiloTipo = estiloDoTipo(executor.executor_type)
  const IconeTipo = estiloTipo.icone
  const isOnline = executor.online
  const cap = executor.capacity
  const uptimeSecs = uptimeEmSegundos(executor.connected_at)
  // Dono = criou o executor (created_by). Pode gerar OTP e revogar/remover o próprio executor,
  // mas não tem ações exclusivas de admin (editar, pool padrão).
  const isOwner = !isAdmin && !!currentUserId && executor.created_by === currentUserId
  const canManage = isAdmin || isOwner

  async function handleSetDefault() {
    const res = await GisFlowService.setDefaultAgent(executor.id_hash)
    if (res.error) {
      createToast.error("Erro ao adicionar ao pool padrão.")
    } else {
      createToast.success("Executor adicionado ao pool padrão.")
      onRefresh()
    }
  }

  async function handleUnsetDefault() {
    const res = await GisFlowService.unsetDefaultAgent(executor.id_hash)
    if (res.error) {
      createToast.error("Erro ao remover do pool padrão.")
    } else {
      createToast.success("Executor removido do pool padrão.")
      onRefresh()
    }
  }

  return (
    <div className="border-b border-border/60 last:border-b-0">
      {/* Linha compacta — a grade é a MESMA do cabeçalho de colunas (ver
          CabecalhoDoTrilho), e é o que faz a memória de todos os executores
          cair no mesmo x. */}
      <div
        onClick={() => setAberto(v => !v)}
        className={cn("grid gap-x-3 gap-y-1.5 md:gap-3", TRILHO_COLUNAS, mostrarTipo && TRILHO_COLUNAS_TIPO,
          "items-center px-3 py-2 min-h-[2.75rem] cursor-pointer transition-colors hover:bg-accent/50")}
      >
        {/* Estado — um LED só, no lugar de faixa + ícone + badge dizendo o
            mesmo. No telefone as três células da primeira linha são posicionadas
            à mão — estado, nome e ações — e o resto desce para a segunda. */}
        <EstadoDoExecutor
          status={executor.status}
          online={isOnline}
          className="col-start-1 row-start-1 md:col-auto md:row-auto"
        />

        {/* Identidade */}
        <div className="min-w-0 col-start-2 row-start-1 md:col-auto md:row-auto">
          <div className="flex items-center gap-1.5 min-w-0">
            {/* O nome É o botão da gaveta. A linha inteira também alterna no
                clique, mas por conveniência de mouse: transformá-la em
                `role="button"` seria inválido, porque o menu de ações é um
                botão dentro dela — e sem um controle real nada disto (carga,
                hardware, métricas, usuários) tinha caminho por teclado. */}
            <button
              type="button"
              aria-expanded={aberto}
              onClick={e => { e.stopPropagation(); setAberto(v => !v) }}
              className="flex min-w-0 cursor-pointer items-center gap-1 rounded-sm text-left outline-none
                         focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <TbChevronRight
                size={12}
                className={cn("shrink-0 text-muted-foreground transition-transform", aberto && "rotate-90")}
                aria-hidden="true"
              />
              <span className="font-medium text-sm truncate">{executor.name}</span>
            </button>
            {executor.is_default && (
              <span className="shrink-0 rounded bg-primary/10 px-1 text-[9px] font-semibold text-primary">pool</span>
            )}
            {ehEsteComputador && (
              <span className="shrink-0 rounded bg-green-500/15 px-1 text-[9px] font-semibold text-green-700 dark:text-green-400">este computador</span>
            )}
          </div>
          <span className="block font-mono text-[10px] text-muted-foreground truncate">
            {executor.status !== "active" && (
              <span className="font-sans font-medium text-foreground/80">{ROTULO_STATUS_EXECUTOR[executor.status]} · </span>
            )}
            {executor.system_info?.hostname ?? executor.description ?? "—"}
            {executor.system_info?.cpu_cores != null && ` · ${executor.system_info.cpu_cores}c`}
            {executor.system_info?.container && " · container"}
          </span>
        </div>

        {/* `md:contents` é o que permite UM só markup para as duas formas: no
            telefone este div é a segunda linha (tipo, slots, versão e
            atividade lado a lado, embaixo do nome); de `md` para cima ele
            desaparece do layout e os filhos voltam a ser células da grade. */}
        <div className="col-start-2 col-end-4 row-start-2 flex flex-wrap items-center gap-x-3 gap-y-1 md:contents">
          {/* Tipo — só quando a lista mistura tipos */}
          {mostrarTipo && (
            <span className={cn(
              "inline-flex items-center gap-1 w-fit text-[10px] font-medium px-1.5 py-0.5 rounded",
              // some na faixa `md` junto com a coluna (ver TRILHO_COLUNAS_TIPO);
              // no telefone continua visível, que ali sobra largura na 2ª linha.
              "md:hidden lg:inline-flex",
              estiloTipo.fundo, estiloTipo.texto,
            )}>
              <IconeTipo size={11} aria-hidden="true" /> {estiloTipo.nome}
            </span>
          )}

          {/* Slots — célula por vaga. */}
          <MedidorDeSlots
            running={cap?.running ?? 0}
            queued={cap?.queued ?? 0}
            maxConcurrent={cap?.max_concurrent ?? executor.max_concurrent_jobs}
            online={isOnline}
          />

          <span
            className={cn(
              "text-[11px] tabular-nums text-muted-foreground text-right truncate md:hidden lg:block",
              // Mesmo motivo do traço dos slots: sem versão reportada, no telefone
              // não sobra nada além de um "—" sem rótulo.
              !executor.executor_version && "hidden",
            )}
            // A do executor Docker leva o commit (v2.15.0+3f02f44) e não cabe
            // inteira na coluna: o corte é o mesmo da coluna ao lado, e a
            // versão completa fica no title.
            title={executor.executor_version ? `v${executor.executor_version}` : undefined}
          >
            {executor.executor_version ? `v${executor.executor_version}` : "—"}
          </span>

          {/* Uptime e "visto em" são grandezas OPOSTAS e cabiam na mesma
              coluna sem rótulo: "2 h 15 min" num executor conectado lia como
              duas horas SEM contato, o contrário do que é. O prefixo desambigua. */}
          <span className="text-[11px] tabular-nums text-muted-foreground text-right truncate">
            {isOnline && uptimeSecs != null ? `no ar ${formatarDuracao(uptimeSecs)}`
              : executor.last_seen_at ? `visto ${formatarQuando(executor.last_seen_at)}`
              : "nunca"}
          </span>
        </div>

        {canManage && (
          // `stopPropagation`: o clique no menu não pode alternar a gaveta da
          // linha — abrir o dropdown e ver o detalhe expandir junto seria um
          // efeito colateral que ninguém pediu.
          <div
            className="shrink-0 justify-self-end col-start-3 row-start-1 md:col-auto md:row-auto"
            onClick={e => e.stopPropagation()}
          >
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="icon" variant="ghost" className="max-md:size-10" aria-label={`Ações de ${executor.name}`}>
                  <TbDots className="text-muted-foreground" aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => {
                    navigator.clipboard.writeText(executor.id_hash)
                    createToast.success("Agent ID copiado.")
                  }}
                >
                  <TbCopy className="mr-2" aria-hidden="true" /> Copiar Agent ID
                </DropdownMenuItem>
                {executor.status !== "revoked" && (
                  <EnrollmentOtpDialog
                    agentId={executor.id_hash}
                    agentStatus={executor.status}
                    trigger={
                      <DropdownMenuItem onSelect={e => e.preventDefault()}>
                        <TbShieldLock className="mr-2" aria-hidden="true" /> Gerar OTP de enrollment
                      </DropdownMenuItem>
                    }
                  />
                )}
                {isAdmin && executor.status !== "revoked" && (
                  <EditAgentDialog executor={executor} onUpdated={onRefresh} />
                )}
                {isAdmin && !executor.is_default && executor.status === "active" && (
                  <DropdownMenuItem onClick={handleSetDefault}>
                    <TbStar className="mr-2" aria-hidden="true" /> Adicionar ao pool padrão
                  </DropdownMenuItem>
                )}
                {isAdmin && executor.is_default && executor.status === "active" && (
                  <DropdownMenuItem onClick={handleUnsetDefault}>
                    <TbStar className="mr-2 text-muted-foreground" aria-hidden="true" /> Remover do pool padrão
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                {executor.status !== "revoked" && (
                  <RevokeAgentDialog executor={executor} onRevoked={onRefresh} />
                )}
                {executor.status === "revoked" && (
                  <DeleteAgentDialog executor={executor} onDeleted={onRefresh} />
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>

      {/* Gaveta — tudo o que não se compara entre máquinas e por isso não
          merece coluna própria. */}
      {aberto && (
      <div className="flex flex-col gap-3 px-3 pb-3 pt-1 bg-muted/25">

      {/* A descrição é escrita pelo usuário e sumia por completo quando o
          executor reportava hostname — a sublinha mostra um ou outro, nunca os
          dois. Aqui ela tem lugar garantido. */}
      {executor.description && (
        <p className="text-xs text-muted-foreground">{executor.description}</p>
      )}

      {executor.capabilities.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {executor.capabilities.map(c => (
            <span key={c} className="px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground border border-border">
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Linha de métricas — sempre visível se online ou com histórico */}
      {isOnline || metrics ? (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-border pt-3">
          {isOnline && (
            <LoadBar
              running={cap?.running ?? 0}
              queued={cap?.queued ?? 0}
              maxConcurrent={cap?.max_concurrent ?? executor.max_concurrent_jobs}
              maxQueue={cap?.max_queue ?? executor.max_queue_size}
            />
          )}
          {metrics && metrics.total_runs > 0 && (
            <ExecutorHistoricMetrics metrics={metrics} />
          )}
        </div>
      ) : null}

      {/* Informações de hardware */}
      {executor.system_info && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border pt-2 text-xs text-muted-foreground">
          {executor.system_info.os_name && (
            <span className="flex items-center gap-1">
              <TbDeviceDesktop size={14} aria-hidden="true" />
              {executor.system_info.os_name} {executor.system_info.os_version}
            </span>
          )}
          {executor.system_info.cpu_cores != null && (
            <span className="flex items-center gap-1 tabular-nums">
              <TbCpu size={14} aria-hidden="true" />
              {plural(executor.system_info.cpu_cores, "core")}
            </span>
          )}
          {executor.system_info.ram_total_gb != null && (
            <span className="flex items-center gap-1 tabular-nums">
              <TbServer size={14} aria-hidden="true" />
              {executor.system_info.ram_available_gb != null
                ? `${executor.system_info.ram_available_gb} / ${executor.system_info.ram_total_gb} GB RAM`
                : `${executor.system_info.ram_total_gb} GB RAM`}
            </span>
          )}
          {executor.system_info.disk_total_gb != null && (
            <span className="flex items-center gap-1 tabular-nums">
              <TbDatabase size={14} aria-hidden="true" />
              {executor.system_info.disk_free_gb != null
                ? `${executor.system_info.disk_free_gb} / ${executor.system_info.disk_total_gb} GB disco`
                : `${executor.system_info.disk_total_gb} GB disco`}
            </span>
          )}
          {executor.system_info.hostname && (
            <span className="font-mono text-[11px]">
              {executor.system_info.hostname}
              {executor.system_info.container && (
                <span className="ml-1 rounded bg-blue-500/10 px-1 py-0.5 text-[10px] font-sans text-blue-500">
                  container
                </span>
              )}
            </span>
          )}
        </div>
      )}

      {/* Usuários atribuídos — admin + executor dedicated */}
      {isAdmin && executor.executor_type === "dedicated" && (
        <AgentUsersSection agentId={executor.id_hash} />
      )}

      </div>
      )}
    </div>
  )
})
