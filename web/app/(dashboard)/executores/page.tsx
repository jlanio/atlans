"use client"

import { useState, useEffect, useMemo, useRef } from "react"
import { useSession } from "next-auth/react"
import { GisFlowService, IExecutor, IExecutorMetrics } from "@/service/GisFlowService"
import { useFetchData } from "@/app/hooks/useFetchData"
import { useExecutorLocal } from "@/app/hooks/useExecutorLocal"
import { reconciliarExecutores } from "./reconciliar-executores"
import { type FiltroDeTipo, OPCOES_DE_TIPO } from "./filtro-de-tipo"
import { estiloDoTipo } from "@/consts/ExecutorTypeStyles"
import { cn } from "@/lib/utils"
import PageRoot from "@/app/components/page-root"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/app/components/ui/tooltip"
import { TbRefresh, TbInfoCircle } from "react-icons/tb"
import { formatarInteiro, plural } from "@/lib/formatos"
import { CreateAgentDialog } from "@/app/components/executores/dialogs"
import { GrupoDeToggle } from "@/app/components/executores/grupo-de-toggle"
import { CabecalhoDoTrilho, ExecutorRow } from "@/app/components/executores/trilho"
import {
  SkeletonDeExecutores,
  ErroDosExecutores,
  VazioDeExecutores,
  SemResultado,
  AvisoDeMetricas,
} from "@/app/components/executores/estados"

// ── Filtro por estado ao vivo ────────────────────────────────────────────────

type StatusFilter = "all" | "online" | "offline"

const OPCOES_DE_STATUS: { valor: StatusFilter; rotulo: string }[] = [
  { valor: "all",     rotulo: "Todos" },
  { valor: "online",  rotulo: "Online" },
  { valor: "offline", rotulo: "Offline" },
]

/**
 * Subtítulo com os contadores ao vivo (contrato §1): "10 executores · 6 online
 * · 2 dedicados". O zero some — "0 dedicados" não ajuda —, e o plural correto
 * de "executor" é "executores" (o default `+s` daria "executors").
 */
function textoDoSubtitulo({ total, online, dedicados }: { total: number; online: number; dedicados: number }): string {
  if (total === 0) return "Nenhum executor ainda"
  const partes = [plural(total, "executor", "executores")]
  if (online > 0) partes.push(`${formatarInteiro(online)} online`)
  if (dedicados > 0) partes.push(plural(dedicados, "dedicado"))
  return partes.join(" · ")
}

export default function AgentsPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const currentUserId = session?.user?.id_hash
  const quota = session?.user?.agent_quota ?? 0
  const canCreate = isAdmin || quota > 0

  // Dentro do app desktop, marca na lista qual executor é ESTA máquina. No
  // navegador comum é `null` (ver useExecutorLocal / lib/desktop).
  const executorLocal = useExecutorLocal()
  const idExecutorLocal = executorLocal?.vinculado ? executorLocal.executorId : null

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
  const [tipoFiltro, setTipoFiltro] = useState<FiltroDeTipo>("todos")
  // Ver o <Tooltip> do cabeçalho: no telefone não há hover nem foco de teclado,
  // e sem controlar a abertura a dica não tinha como ser lida ali.
  const [dicaAberta, setDicaAberta] = useState(false)

  const { data, firstLoad, loading, refreshing, error, refetch, recarregarEmFundo } = useFetchData(
    () => isAdmin ? GisFlowService.getAgents() : GisFlowService.getMyAgents(),
    "Erro ao carregar executores."
  )
  const { data: metricsData, error: metricsError, refetch: refetchMetrics } = useFetchData(
    () => GisFlowService.getExecutorMetrics(),
    "Erro ao carregar métricas."
  )

  // `useMemo` em tudo o que é derivado: sem eles, cada tick do auto-refresh
  // reconstruía o mapa de métricas e as varreduras da lista, e as props dos
  // cards trocavam de identidade à toa.
  //
  // Reconciliação por conteúdo (ver reconciliar-executores.ts): sem ela, o
  // React.memo do ExecutorRow nunca acertava, porque cada tick de 15s traz
  // objetos novos do JSON mesmo para executores que não mudaram em nada.
  const anterioresRef = useRef<IExecutor[]>([])
  const executores: IExecutor[] = useMemo(() => {
    anterioresRef.current = reconciliarExecutores(anterioresRef.current, data ?? [])
    return anterioresRef.current
  }, [data])

  const metricsMap = useMemo(() => {
    const mapa: Record<string, IExecutorMetrics> = {}
    for (const m of metricsData?.executores ?? []) {
      // A linha "Sem executor" (falhas de despacho) não tem host: não é de ninguém.
      if (!m.agent_host) continue
      const id = m.agent_host.startsWith("executor:") ? m.agent_host.slice("executor:".length) : m.agent_host
      mapa[id] = m
    }
    return mapa
  }, [metricsData])

  // Auto-refresh a cada 15s para manter carga em tempo real — só com a aba em
  // foco, e com atualização imediata ao retomar o foco (mesmo gate de
  // workspaces/page.tsx). Aba oculta não tem quem leia o resultado. É recarga
  // de fundo: com a 1ª carga em erro, o cartão fica na tela durante a
  // tentativa, em vez de sair e voltar (e ser anunciado de novo) a cada tique.
  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === "visible") recarregarEmFundo()
    }, 15_000)
    const onVisibility = () => {
      if (document.visibilityState === "visible") recarregarEmFundo()
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearInterval(id)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [recarregarEmFundo])

  // Admin: getAgents() retorna todos; não-admin: getMyAgents() já retorna apenas acessíveis
  const visibleAgents = executores

  // Executores criados pelo próprio usuário (usado para calcular cota restante)
  const ownedCount = useMemo(
    () => (currentUserId ? visibleAgents.filter(a => a.created_by === currentUserId).length : 0),
    [visibleAgents, currentUserId],
  )

  // Contadores ao vivo do subtítulo. "Online" conta só executores ATIVOS que
  // estão online — casa com o LED verde que o usuário vê no trilho (um online
  // de status revogado/inativo não é capacidade real). "Dedicados" conta os
  // dedicados vigentes (status ativo), não os já revogados/inativos.
  const online = useMemo(() => visibleAgents.filter(a => a.status === "active" && a.online).length, [visibleAgents])
  const dedicados = useMemo(() => visibleAgents.filter(a => a.executor_type === "dedicated" && a.status === "active").length, [visibleAgents])

  const filteredAgents = useMemo(() => visibleAgents.filter(a => {
    if (statusFilter === "online")   return a.online
    if (statusFilter === "offline")  return a.status === "active" && !a.online
    return true
  }), [visibleAgents, statusFilter])

  const agentesVisiveis = useMemo(
    () => tipoFiltro === "todos" ? filteredAgents : filteredAgents.filter(a => a.executor_type === tipoFiltro),
    [filteredAgents, tipoFiltro],
  )

  // Em "Todos" a lista mistura tipos, então ganha cabeçalhos de grupo e a
  // coluna de tipo. Com um tipo escolhido os dois viram redundância.
  const agrupado = tipoFiltro === "todos"
  const grupos = useMemo<{ tipo: IExecutor["executor_type"]; itens: IExecutor[] }[]>(() => {
    if (!agrupado) return [{ tipo: tipoFiltro as IExecutor["executor_type"], itens: agentesVisiveis }]
    // Enumerar `["default","dedicated"]` fixo escondia qualquer outro
    // `executor_type` que a API viesse a mandar: ele entrava na contagem e
    // passava pelo guard de lista vazia, mas nenhum grupo o renderizava — o
    // trilho ficava com cabeçalho e sem linha. Agrupar pelos tipos que
    // EXISTEM na resposta cobre isso, e `estiloDoTipo` já tem o neutro.
    const ordem = ["default", "dedicated"]
    const presentes = [...new Set(agentesVisiveis.map(a => a.executor_type))]
      .sort((x, y) => {
        const ix = ordem.indexOf(x), iy = ordem.indexOf(y)
        return (ix < 0 ? ordem.length : ix) - (iy < 0 ? ordem.length : iy)
      })
    return presentes.map(t => ({ tipo: t, itens: agentesVisiveis.filter(a => a.executor_type === t) }))
  }, [agrupado, tipoFiltro, agentesVisiveis])

  function limparFiltros() {
    setStatusFilter("all")
    setTipoFiltro("todos")
  }

  // Métricas são uma fonte SECUNDÁRIA: se caírem, o trilho continua completo,
  // só sem os números de histórico — vira aviso âmbar, não erro de tela.
  const metricasFalharam = metricsData === null && metricsError != null

  return (
    <PageRoot>
      {/* ── Cabeçalho (contrato §1) ─────────────────────────────────────────── */}
      {/* `flex-wrap`: sem ele o título e a fila de ações disputam a mesma linha
          num telefone, e o `shrink-0` das ações espremia "Executores" até virar
          reticências. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold text-foreground">Executores</h1>
            <TooltipProvider delayDuration={100}>
              {/* Controlado, e o clique abre: o Radix abre tooltip por hover e
                  por foco de teclado, e o telefone não tem nem um nem outro —
                  a instrução de como subir o executor era inalcançável ali.
                  Fecha no toque fora, como qualquer camada do Radix. */}
              <Tooltip open={dicaAberta} onOpenChange={setDicaAberta}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="Como executar um executor"
                    onClick={() => setDicaAberta(true)}
                    // `p-1 -m-1`: alvo de toque maior sem mexer no alinhamento
                    // do ícone com o título.
                    className="mt-0.5 -m-1 rounded-sm p-1 text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
                  >
                    <TbInfoCircle size={17} aria-hidden="true" />
                  </button>
                </TooltipTrigger>
                <TooltipContent
                  side="right"
                  collisionPadding={16}
                  // `max-w-sm` fixo (384px) é mais largo que a tela de 360px, e
                  // o conteúdo vazava por baixo da borda.
                  className="max-w-[min(24rem,calc(100vw-2rem))] space-y-2 border border-border bg-popover p-3 text-popover-foreground shadow-md"
                >
                  <p className="text-xs font-semibold">Executar um executor</p>
                  <p className="text-xs text-muted-foreground">
                    Após criar e configurar o executor, execute a partir da raiz do repositório:
                  </p>
                  <pre className="select-all whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-[11px] leading-relaxed text-foreground">
                    {`python -m executor.main`}
                  </pre>
                  <p className="text-[11px] text-muted-foreground">
                    Certifique-se de preencher <code>executor/.env</code> antes de iniciar.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          {/* Enquanto não há o que contar (1ª carga), o subtítulo vira esqueleto
              — nunca escreve "— online". */}
          {data !== null ? (
            <p className="text-sm font-medium text-muted-foreground">
              {textoDoSubtitulo({ total: visibleAgents.length, online, dedicados })}
            </p>
          ) : (
            <Skeleton className="mt-1 h-4 w-64" />
          )}
        </div>

        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={refetch}
            disabled={loading}
            aria-label="Atualizar a lista de executores"
            className="gap-1.5 max-md:h-10"
          >
            {/* `loading` cobre a 1ª carga E as recargas (inclusive o tick de
                15s) — é o único sinal de que a lista está sendo recarregada,
                já que as linhas não esmaecem mais. */}
            <TbRefresh size={14} className={loading ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
            Atualizar
          </Button>
          {canCreate && (
            <CreateAgentDialog
              onCreated={refetch}
              executores={executores}
              isAdmin={isAdmin}
              quota={quota}
              ownedCount={ownedCount}
            />
          )}
        </div>
      </div>

      {/* Aviso de pool compartilhado — orienta o usuário final sobre os tipos */}
      {!isAdmin && visibleAgents.length > 0 && (
        <div className="flex items-start gap-2 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          <TbInfoCircle size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>
            Executores marcados como <span className="font-medium text-foreground">Padrão</span> fazem parte de um{" "}
            <span className="font-medium text-foreground">pool compartilhado</span> entre todos os usuários.
            Executores <span className="font-medium text-foreground">Dedicados</span> são exclusivos do seu acesso.
          </span>
        </div>
      )}

      {/* Filtros — dois grupos de toggle padrão (contrato §1). Só aparecem quando
          há lista; num vazio de primeiro uso não há o que filtrar. */}
      {data !== null && visibleAgents.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <GrupoDeToggle
            rotulo="Tipo de executor"
            valor={tipoFiltro}
            onChange={setTipoFiltro}
            opcoes={OPCOES_DE_TIPO}
          />
          <GrupoDeToggle
            rotulo="Estado do executor"
            valor={statusFilter}
            onChange={setStatusFilter}
            opcoes={OPCOES_DE_STATUS}
          />
        </div>
      )}

      {/* ── Estados (contrato §3): carregando → erro (só sem carga aceita) →
             primeiro uso → conteúdo; dentro do conteúdo, sem-resultado e o
             aviso de métricas. ─────────────────────────────────────────────── */}
      {firstLoad ? (
        <SkeletonDeExecutores />
      ) : data === null ? (
        <ErroDosExecutores mensagem={error ?? "Erro ao carregar executores."} onTentar={refetch} />
      ) : visibleAgents.length === 0 ? (
        <VazioDeExecutores
          isAdmin={isAdmin}
          acao={canCreate ? (
            <CreateAgentDialog
              onCreated={refetch}
              executores={executores}
              isAdmin={isAdmin}
              quota={quota}
              ownedCount={ownedCount}
            />
          ) : undefined}
        />
      ) : (
        <div className="flex flex-col gap-4">
          {metricasFalharam && <AvisoDeMetricas onTentar={refetchMetrics} />}

          {agentesVisiveis.length === 0 ? (
            <SemResultado onLimpar={limparFiltros} />
          ) : (
            // Trilho — variante deliberada (tabela densa). Uma <section> com a
            // moldura de cartão e um h2 (sr-only, pois o cabeçalho de colunas já
            // rotula visualmente); `aria-busy` na recarga.
            <section
              aria-labelledby="executores-trilho-titulo"
              aria-busy={refreshing}
              className="flex min-w-0 flex-col overflow-hidden rounded-lg border bg-card shadow-xs"
            >
              <h2 id="executores-trilho-titulo" className="sr-only">Executores registrados</h2>
              <CabecalhoDoTrilho mostrarTipo={agrupado} />
              {grupos.map(grupo => {
                const estilo = estiloDoTipo(grupo.tipo)
                const IconeGrupo = estilo.icone
                return (
                  <div key={grupo.tipo}>
                    {agrupado && (
                      <div className={cn(
                        "flex items-center gap-1.5 border-b border-border bg-muted/40 px-3 py-1",
                        "font-mono text-[10px] uppercase tracking-wider", estilo.texto,
                      )}>
                        <IconeGrupo size={11} aria-hidden="true" />
                        <span>{estilo.grupo}</span>
                        <span className="tabular-nums opacity-60">· {grupo.itens.length}</span>
                      </div>
                    )}
                    {grupo.itens.map(executor => (
                      <ExecutorRow
                        key={executor.id_hash}
                        executor={executor}
                        metrics={metricsMap[executor.id_hash]}
                        onRefresh={refetch}
                        isAdmin={isAdmin}
                        currentUserId={currentUserId}
                        mostrarTipo={agrupado}
                        ehEsteComputador={!!idExecutorLocal && idExecutorLocal === executor.id_hash}
                      />
                    ))}
                  </div>
                )
              })}
            </section>
          )}
        </div>
      )}
    </PageRoot>
  )
}
