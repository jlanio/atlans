"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import {
  TbAlertTriangle, TbExternalLink, TbInfoCircle, TbLoader2, TbLock, TbPlus, TbRefresh, TbServer, TbX,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { GisFlowService, IExecutor } from "@/service/GisFlowService"
import type { IPolicyMember, IWorkspacePolicy, PolicyTerminal } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import { ExecutorTypeBadge } from "@/app/components/executor-type-badge"
import { useFetchData } from "@/app/hooks/useFetchData"
import { SheetSection } from "./section-shell"
import {
  capacidadeCheia, classeDoModo, contarOnline, descreverCapacidade, descreverPolitica, politicaEmAlerta,
  rotuloDoModo, rotuloDoStatus, saudeDoPool, semSinal, type Capacidade,
} from "../politica"

interface Props {
  workspaceId: string
  canManage: boolean
  /** Sinaliza política em alerta (membro inativo, cadeia sem ninguém online) para a navegação. */
  onAlertChange?: (hasAlert: boolean) => void
}

/** Uma operação em voo por vez: incluir/remover/terminal se atropelariam na mesma política. */
type Operacao = `incluir:${string}` | `remover:${string}` | "terminal"

/**
 * Editor da política de execução do workspace
 * (docs/specs/executor-isolation-routing.md, §9).
 *
 * Três blocos: os executores principais, a reserva opcional e o último
 * recurso — o que acontece quando nenhum deles está disponível: falhar
 * (padrão) ou o pool. Escolher o pool pede confirmação porque muda onde os
 * DADOS rodam; sob piso do administrador da plataforma ela nem é oferecida.
 * Remover o último principal também pede confirmação: apaga a reserva e
 * devolve o workspace ao pool.
 *
 * Enquanto o servidor não roteia pela política (flag desligada), o editor é
 * uma prévia e diz isso ANTES de qualquer outra coisa: prometer isolamento
 * que a próxima execução não tem seria pior do que não ter a tela.
 */
export function ExecutorSection({ workspaceId, canManage, onAlertChange }: Props) {
  // A carga é o `useFetchData`: cargas concorrentes (Atualizar duas vezes,
  // tentar de novo, trocar de workspace) — só a mais recente escreve, e a
  // anterior chegando depois não troca uma política recém-lida por um
  // instantâneo velho. A guarda de geração, que esta seção escrevia à mão, é a
  // dele. `firstLoad` é o skeleton; na recarga a política fica na tela.
  const { data, loading, firstLoad, error, refetch: load, setData } = useFetchData(
    async () => {
      const [polRes, myRes] = await Promise.all([
        GisFlowService.getWorkspacePolicy(workspaceId),
        GisFlowService.getMyAgents(),
      ])
      if (polRes.error || !polRes.data || myRes.error) {
        return { error: { message: polRes.error?.message ?? myRes.error?.message } }
      }
      // Mantém todos (inclui pending/revoked): é a lista que diz o NOME do
      // ponteiro legado na prévia e o porquê de não haver candidatos.
      return { data: { politica: polRes.data, executores: myRes.data ?? [] } }
    },
    "Não foi possível carregar a política de execução.",
    [workspaceId],
  )
  const politica = data?.politica ?? null
  const executores = useMemo<IExecutor[]>(() => data?.executores ?? [], [data])
  /** A política que uma gravação devolveu (ou a releitura): troca só ela. */
  const setPolitica = (nova: IWorkspacePolicy) => setData(atual => atual && { ...atual, politica: nova })
  const [operacao, setOperacao] = useState<Operacao | null>(null)
  const [confirmarPool, setConfirmarPool] = useState(false)
  const [confirmarRemocao, setConfirmarRemocao] = useState<IPolicyMember | null>(null)

  const alerta = politica ? politicaEmAlerta(politica) : false
  useEffect(() => {
    if (!loading && !error) onAlertChange?.(alerta)
  }, [alerta, loading, error, onAlertChange])

  const emVigor = politica?.policy_routing_enabled === true
  const sufixoPrevia = emVigor ? "" : " (vale quando o roteamento por política for ativado)"

  /** Relê só a política — o DELETE responde 204, sem a política recalculada. */
  async function relerPolitica(): Promise<IWorkspacePolicy | null> {
    const res = await GisFlowService.getWorkspacePolicy(workspaceId)
    if (res.error || !res.data) {
      // A remoção deu certo; só a releitura falhou. O toast de sucesso já
      // saiu — a tela pede uma recarga em vez de virar um erro inteiro.
      createToast.error("Não foi possível reler a política", "Clique em Atualizar.")
      return null
    }
    setPolitica(res.data)
    return res.data
  }

  async function incluir(executor: IExecutor, tier: 1 | 2) {
    if (operacao) return
    setOperacao(`incluir:${executor.id_hash}`)
    const res = await GisFlowService.addWorkspacePolicyMember(workspaceId, executor.id_hash, tier)
    setOperacao(null)
    if (res.error || !res.data) {
      createToast.error("Erro ao incluir o executor", res.error?.message)
      return
    }
    setPolitica(res.data)
    createToast.success(
      tier === 1
        ? `${executor.name} incluído entre os principais.`
        : `${executor.name} incluído como reserva.`,
    )
  }

  function pedirRemocao(membro: IPolicyMember) {
    if (!politica) return
    const ultimoPrincipal = membro.tier === 1 && politica.primary.length === 1
    // O último principal derruba a reserva e devolve o workspace ao pool: é
    // a direção sensível (nada → tudo em máquinas compartilhadas).
    if (ultimoPrincipal) { setConfirmarRemocao(membro); return }
    remover(membro)
  }

  async function remover(membro: IPolicyMember) {
    if (operacao || !politica) return
    setConfirmarRemocao(null)
    const eraUltimoPrincipal = membro.tier === 1 && politica.primary.length === 1
    const tinhaReserva = politica.fallback.length > 0
    setOperacao(`remover:${membro.id_hash}`)
    const res = await GisFlowService.removeWorkspacePolicyMember(workspaceId, membro.id_hash)
    if (res.error) {
      setOperacao(null)
      createToast.error("Erro ao remover o executor", res.error.message)
      return
    }
    // Esvaziar o principal derruba a reserva junto (spec §4.3): só a
    // releitura mostra o que sobrou.
    await relerPolitica()
    setOperacao(null)
    if (eraUltimoPrincipal) {
      createToast.success(
        `${membro.name} removido. O workspace voltou a usar o pool compartilhado.`
        + (tinhaReserva ? " Os executores de reserva também saíram." : ""),
      )
    } else {
      createToast.success(`${membro.name} removido da política.`)
    }
  }

  async function definirTerminal(terminal: PolicyTerminal, confirmado = false) {
    if (!politica || operacao) return
    if (terminal === politica.effective_terminal) return
    if (terminal === "pool" && !confirmado) { setConfirmarPool(true); return }
    setConfirmarPool(false)
    setOperacao("terminal")
    const res = await GisFlowService.setWorkspaceFallback(workspaceId, terminal)
    setOperacao(null)
    if (res.error || !res.data) {
      createToast.error("Erro ao alterar o último recurso", res.error?.message)
      return
    }
    setPolitica(res.data)
    createToast.success(
      (terminal === "pool"
        ? "O pool compartilhado passa a ser o último recurso."
        : "Sem último recurso: a execução falha quando nenhum executor da política estiver disponível.")
      + sufixoPrevia,
    )
  }

  const naPolitica = new Set(
    [...(politica?.primary ?? []), ...(politica?.fallback ?? [])].map(m => m.id_hash),
  )
  // Candidatos: os MEUS executores dedicados ativos que ainda não estão em
  // nível algum. O pool não é um nível (spec Q3): `is_default` fica de fora.
  const dedicados = executores.filter(e => !e.is_default)
  const candidatos = dedicados.filter(e => e.status === "active" && !naPolitica.has(e.id_hash))
  const temPrincipal = (politica?.primary.length ?? 0) > 0
  const sobPiso = politica?.isolation_floor === "no_pool"
  const ocupado = operacao !== null

  // Nome do ponteiro legado, para a prévia dizer o que vale HOJE. Entre aspas:
  // um executor chamado "executor" deixava a frase sem sentido.
  const nomeLegado = politica?.target_executor_id
    ? executores.find(e => e.id_hash === politica.target_executor_id)?.name
    : undefined
  const legado = politica?.target_executor_id
    ? (nomeLegado
      ? `o executor «${nomeLegado}»`
      : "um executor que não está mais na sua lista (removido ou sem acesso)")
    : "o pool compartilhado"

  // Compartilhado sem candidato: uma mensagem só, em vez de cinco blocos
  // desabilitados. A tela inteira do editor pressupõe um dedicado.
  const semNadaParaEditar = politica?.mode === "pool" && candidatos.length === 0 && !sobPiso

  return (
    <>
      <SheetSection
        title="Política de execução"
        description={
          <>
            Em quais executores os workflows deste workspace rodam, e o que acontece quando eles caem.{" "}
            <span className="font-medium text-teal-600 dark:text-teal-400">Compartilhado</span> usa o
            pool da plataforma.{" "}
            <span className="font-medium text-purple-600 dark:text-purple-400">Isolado</span> roda só
            nos executores principais e de reserva deste workspace e falha quando nenhum está disponível.{" "}
            <span className="font-medium text-purple-600 dark:text-purple-400">Dedicado + pool</span>{" "}
            tenta os dedicados e usa o pool como último recurso.
            {!canManage && " Apenas administradores podem alterar."}
          </>
        }
        // Duas ações largas (o link "Gerenciar executores" + Atualizar) no
        // canto superior direito espremiam o título num painel estreito;
        // descem para uma linha própria, abaixo da descrição.
        actionBelow
        action={
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={load}
              // Travado durante uma gravação: recarregar no meio de uma troca
              // sobrescrevia o valor em voo e o toast de sucesso mentia.
              disabled={loading || ocupado}
              aria-label="Atualizar política"
              title="Atualizar"
            >
              <TbRefresh className={`size-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button variant="ghost" size="sm" asChild className="gap-1 text-xs text-muted-foreground">
              <Link href="/executores">
                Gerenciar executores
                <TbExternalLink className="size-3.5" />
              </Link>
            </Button>
          </div>
        }
        loading={firstLoad}
        error={error}
        onRetry={load}
      >
        {politica && (
          <div className="space-y-5">
            {/* ── Prévia: ANTES de tudo, porque muda o sentido de tudo ──── */}
            {!emVigor && (
              <p
                role="note"
                className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-foreground"
              >
                <TbInfoCircle className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
                <span>
                  <span className="font-semibold">Ainda não está em vigor.</span> Hoje as execuções
                  deste workspace vão para {legado}. O que você configurar aqui fica salvo e passa a
                  valer quando o administrador da plataforma ativar o roteamento por política.
                </span>
              </p>
            )}

            {/* ── Resumo ─────────────────────────────────────────────────── */}
            <div
              className={cn(
                "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
                alerta && "border-amber-500/40 bg-amber-500/5",
              )}
            >
              <div
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-md",
                  alerta ? "bg-amber-500/15 text-amber-700 dark:text-amber-400" : "bg-accent",
                )}
              >
                {alerta
                  ? <TbAlertTriangle className="size-4" aria-hidden="true" />
                  : <TbServer className="size-4" aria-hidden="true" />}
              </div>
              <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1">
                <Badge
                  variant="outline"
                  className={cn("gap-1 px-1.5 py-0 text-[10px]", classeDoModo(politica.mode), !emVigor && "border-dashed")}
                >
                  {sobPiso && <TbLock size={10} aria-hidden="true" />}
                  {rotuloDoModo(politica.mode)}{!emVigor && " · prévia"}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {politica.mode === "pool"
                    ? (saudeDoPool(politica) ?? "Pool compartilhado")
                    : sobPiso && !temPrincipal
                      ? "Sem executor principal: nada roda até você incluir um"
                      : descreverPolitica(politica)}
                </span>
              </div>
              {ocupado && (
                <TbLoader2 className="size-4 shrink-0 animate-spin text-muted-foreground" aria-hidden="true" />
              )}
            </div>

            {sobPiso && (
              <p className="flex items-start gap-2 text-xs text-muted-foreground">
                <TbLock className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                <span>
                  <span className="font-medium text-foreground">Isolamento obrigatório.</span> O
                  administrador da plataforma definiu que este workspace nunca usa o pool
                  compartilhado; o último recurso fica fixo em «Falhar a execução».
                </span>
              </p>
            )}

            {semNadaParaEditar ? (
              <div className="space-y-3 rounded-md border border-dashed px-4 py-4 text-sm">
                <p>
                  Este workspace usa o pool compartilhado: qualquer executor compartilhado assume as
                  execuções. Para isolar as execuções em máquinas só suas, você precisa de um{" "}
                  <span className="font-medium">executor dedicado</span>
                  {dedicados.length > 0 && " ativo"}.
                </p>
                {dedicados.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Seus executores dedicados não estão ativos ({dedicados.map(e => `${e.name}: ${rotuloDoStatus(e.status)}`).join(", ")}).
                    Só executores ativos entram na política.
                  </p>
                )}
                {canManage && (
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/executores">
                      <TbPlus size={14} aria-hidden="true" />
                      {dedicados.length > 0 ? "Ver meus executores" : "Criar executor dedicado"}
                    </Link>
                  </Button>
                )}
              </div>
            ) : (
              <>
                {/* ── Níveis ─────────────────────────────────────────────── */}
                <Nivel
                  titulo="Executores principais"
                  rotulo="principal"
                  membros={politica.primary}
                  disponiveis={politica.available_primary}
                  vazio={emVigor
                    ? "Nenhum executor principal: o workspace é Compartilhado e tudo roda no pool."
                    : "Nenhum executor principal. Inclua um abaixo para começar a política."}
                  canManage={canManage}
                  ocupado={ocupado}
                  operacao={operacao}
                  onRemover={pedirRemocao}
                />
                {temPrincipal ? (
                  <Nivel
                    titulo="Executores de reserva"
                    rotulo="reserva"
                    membros={politica.fallback}
                    disponiveis={politica.available_fallback}
                    vazio="Sem reserva: se nenhum principal estiver disponível, vale o último recurso abaixo."
                    canManage={canManage}
                    ocupado={ocupado}
                    operacao={operacao}
                    onRemover={pedirRemocao}
                  />
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Reserva e último recurso aparecem depois que houver um executor principal.
                  </p>
                )}

                {/* ── Último recurso ─────────────────────────────────────── */}
                {temPrincipal && (
                  <div className="space-y-1.5">
                    <div className="flex items-baseline justify-between gap-2">
                      <h4
                        id={`terminal-${workspaceId}`}
                        className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                      >
                        Último recurso
                      </h4>
                      <span className="text-xs text-muted-foreground">Quando nenhum deles estiver disponível</span>
                    </div>
                    <GrupoDeTerminal
                      labelledBy={`terminal-${workspaceId}`}
                      selecionado={politica.effective_terminal}
                      disabled={!canManage || ocupado}
                      poolBloqueado={sobPiso}
                      detalhePool={saudeDoPool(politica) ?? undefined}
                      onEscolher={definirTerminal}
                    />
                    {sobPiso && (
                      <p className="text-xs text-amber-700 dark:text-amber-400">
                        Bloqueado pelo administrador da plataforma.
                      </p>
                    )}
                  </div>
                )}

                {/* ── Candidatos ─────────────────────────────────────────── */}
                {canManage && (
                  <div className="space-y-1.5">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Incluir executor
                    </h4>
                    {candidatos.length === 0 ? (
                      <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
                        {dedicados.length === 0
                          ? "Você não tem executores dedicados. Crie um em Executores para isolar este workspace."
                          : dedicados.some(e => e.status === "active")
                            ? "Todos os seus executores dedicados ativos já estão na política."
                            : `Seus executores dedicados não estão ativos (${dedicados.map(e => rotuloDoStatus(e.status)).join(", ")}). Só executores ativos entram na política.`}
                      </p>
                    ) : (
                      <ul className="divide-y rounded-md border">
                        {candidatos.map(e => (
                          <li key={e.id_hash} className="flex items-center gap-2 px-3 py-1.5 text-sm">
                            <PontoDePresenca online={e.online} />
                            <span className="min-w-0 flex-1 truncate">{e.name}</span>
                            <Carga capacidade={e.capacity} />
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 gap-1 text-xs"
                              disabled={ocupado}
                              onClick={() => incluir(e, 1)}
                              aria-label={`Incluir ${e.name} entre os principais`}
                            >
                              {operacao === `incluir:${e.id_hash}`
                                ? <TbLoader2 size={12} className="animate-spin" aria-hidden="true" />
                                : <TbPlus size={12} aria-hidden="true" />}
                              Principal
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 gap-1 text-xs"
                              disabled={ocupado || !temPrincipal}
                              title={!temPrincipal ? "Defina um executor principal antes." : undefined}
                              onClick={() => incluir(e, 2)}
                              aria-label={`Incluir ${e.name} como reserva`}
                            >
                              <TbPlus size={12} aria-hidden="true" />
                              Reserva
                            </Button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </SheetSection>

      {/* Confirmação: "pool" muda onde os DADOS deste workspace podem rodar. */}
      <Dialog open={confirmarPool} onOpenChange={setConfirmarPool}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Usar o pool como último recurso?</DialogTitle>
            <DialogDescription>
              Quando nenhum executor da política estiver disponível, as execuções deste workspace
              — e os dados que elas processam — poderão rodar em executores compartilhados da
              plataforma. Você pode voltar para «Falhar a execução» quando quiser.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmarPool(false)}>Cancelar</Button>
            <Button onClick={() => definirTerminal("pool", true)}>Permitir o pool</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmação: o último principal leva a reserva junto e devolve o
          workspace ao pool. */}
      <Dialog open={confirmarRemocao !== null} onOpenChange={o => { if (!o) setConfirmarRemocao(null) }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Remover o último executor principal?</DialogTitle>
            <DialogDescription>
              Sem executor principal, este workspace volta a ser Compartilhado: tudo roda no pool
              da plataforma.
              {(politica?.fallback.length ?? 0) > 0 && (
                <> Os executores de reserva ({politica?.fallback.map(m => m.name).join(", ")}) também
                saem da política.</>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmarRemocao(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={() => confirmarRemocao && remover(confirmarRemocao)}>
              Remover
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ── Peças ────────────────────────────────────────────────────────────────────

function Nivel({
  titulo, rotulo, membros, disponiveis, vazio, canManage, ocupado, operacao, onRemover,
}: {
  titulo: string
  /** Como o nível é chamado no rótulo do botão de remover. */
  rotulo: string
  membros: IPolicyMember[]
  disponiveis: number
  vazio: string
  canManage: boolean
  ocupado: boolean
  operacao: Operacao | null
  onRemover: (m: IPolicyMember) => void
}) {
  return (
    <section aria-label={titulo} className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {titulo}
        </h4>
        {membros.length > 0 && (
          <span className={cn(
            "text-xs tabular-nums",
            disponiveis === 0 ? "font-medium text-amber-700 dark:text-amber-400" : "text-muted-foreground",
          )}>
            {contarOnline(disponiveis, membros.length, semSinal(membros))}
          </span>
        )}
      </div>
      {membros.length === 0 ? (
        <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">{vazio}</p>
      ) : (
        <ul className="divide-y rounded-md border">
          {membros.map(m => {
            const inativo = m.status !== "active"
            return (
              <li
                key={m.id_hash}
                className={cn("flex items-center gap-2 px-3 py-1.5 text-sm", inativo && "bg-amber-500/5")}
              >
                <PontoDePresenca online={m.online} />
                <span className="min-w-0 flex-1 truncate font-medium">{m.name}</span>
                <Carga capacidade={m.capacity} />
                <ExecutorTypeBadge type={m.executor_type} size="sm" />
                {inativo && (
                  <Badge
                    variant="outline"
                    className="border-amber-500/40 px-1 py-0 text-[9px] leading-tight text-amber-700 dark:text-amber-400"
                  >
                    {rotuloDoStatus(m.status)}
                  </Badge>
                )}
                {canManage && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 shrink-0"
                    disabled={ocupado}
                    onClick={() => onRemover(m)}
                    aria-label={`Remover ${m.name} do nível ${rotulo}`}
                    title="Remover"
                  >
                    {operacao === `remover:${m.id_hash}`
                      ? <TbLoader2 className="size-3.5 animate-spin" aria-hidden="true" />
                      : <TbX className="size-3.5" aria-hidden="true" />}
                  </Button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

/**
 * Ponto de presença em três estados: online, offline e SEM SINAL (Redis fora
 * ou reconectando). O terceiro existe para não pintar "offline" um executor
 * que só não pôde ser consultado.
 */
function PontoDePresenca({ online }: { online: boolean | null }) {
  const texto = online === true ? "online" : online === false ? "offline" : "sem sinal"
  return (
    <span
      className={cn(
        "inline-block size-2 shrink-0 rounded-full",
        online === true && "bg-green-500",
        online === false && "bg-muted-foreground/40",
        online === null && "border border-dashed border-muted-foreground/70",
      )}
      title={texto}
    >
      <span className="sr-only">{texto}</span>
    </span>
  )
}

/**
 * Carga do executor, como ele a publica: é o que dá sentido a "online" — um
 * executor online e cheio não recebe o próximo job agora. Some quando não há
 * capacidade publicada (offline, sem sinal, versão antiga).
 */
function Carga({ capacidade }: { capacidade: Capacidade }) {
  const texto = descreverCapacidade(capacidade)
  if (!texto) return null
  const cheio = capacidadeCheia(capacidade)
  return (
    <span
      className={cn(
        "hidden shrink-0 text-xs tabular-nums sm:inline",
        cheio ? "font-medium text-amber-700 dark:text-amber-400" : "text-muted-foreground",
      )}
      title={cheio ? "Sem folga: execuções e fila no teto" : "Execuções em andamento / teto do executor"}
    >
      {texto}{cheio && " · cheio"}
    </span>
  )
}

const OPCOES: { valor: PolicyTerminal; titulo: string; descricao: string }[] = [
  {
    valor: "fail",
    titulo: "Falhar a execução",
    descricao: "Nada sai deste workspace: a execução falha e você é avisado. Modo Isolado.",
  },
  {
    valor: "pool",
    titulo: "Usar o pool compartilhado",
    descricao: "A execução vai para um executor compartilhado da plataforma. Modo Dedicado + pool.",
  },
]

/**
 * Grupo de rádio de verdade: setas movem a escolha, um só ponto de tabulação.
 * Cartões em vez de bolinhas porque cada opção precisa de uma frase de
 * consequência — mas o teclado tem de funcionar como num rádio.
 */
function GrupoDeTerminal({
  labelledBy, selecionado, disabled, poolBloqueado, detalhePool, onEscolher,
}: {
  labelledBy: string
  selecionado: PolicyTerminal
  disabled: boolean
  poolBloqueado: boolean
  detalhePool?: string
  onEscolher: (t: PolicyTerminal) => void
}) {
  function habilitada(valor: PolicyTerminal) {
    return !disabled && !(valor === "pool" && poolBloqueado)
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return
    e.preventDefault()
    const outra: PolicyTerminal = selecionado === "fail" ? "pool" : "fail"
    if (habilitada(outra)) onEscolher(outra)
  }

  return (
    <div
      role="radiogroup"
      aria-labelledby={labelledBy}
      onKeyDown={aoTeclar}
      className="grid gap-2 sm:grid-cols-2"
    >
      {OPCOES.map(o => {
        const ativa = selecionado === o.valor
        const bloqueada = o.valor === "pool" && poolBloqueado
        return (
          <button
            key={o.valor}
            type="button"
            role="radio"
            aria-checked={ativa}
            aria-disabled={!habilitada(o.valor) || undefined}
            disabled={disabled}
            tabIndex={ativa ? 0 : -1}
            onClick={() => habilitada(o.valor) && onEscolher(o.valor)}
            className={cn(
              "flex flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left text-sm transition-colors",
              ativa ? "border-primary bg-primary/5" : "hover:bg-muted/60",
              (disabled || bloqueada) && "cursor-not-allowed opacity-70 hover:bg-transparent",
            )}
          >
            <span className="flex items-center gap-1.5 font-medium">
              {bloqueada && <TbLock size={12} aria-hidden="true" />}
              {o.titulo}
              {o.valor === "fail" && (
                <span className="rounded border px-1 text-[9px] font-normal uppercase tracking-wide text-muted-foreground">
                  padrão
                </span>
              )}
            </span>
            <span className="text-xs text-muted-foreground">{o.descricao}</span>
            {o.valor === "pool" && detalhePool && !bloqueada && (
              <span className="text-xs tabular-nums text-muted-foreground">{detalhePool}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
