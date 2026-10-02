"use client"

import { useState } from "react"
import Link from "next/link"
import {
  TbAdjustments, TbAlertTriangle, TbFolders, TbLoader2, TbLock, TbServer, TbSettings, TbUsers,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Skeleton } from "@/app/components/ui/skeleton"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select"
import { ExecutorTypeBadge } from "@/app/components/executor-type-badge"
import { getWorkspaceIdentity } from "@/lib/workspace-identity"
import { cn } from "@/lib/utils"
import type { Workspace } from "@/context/WorkspaceContext"
import { roleLabel } from "./role-labels"
import { POOL } from "./use-workspace-executors"
import { WorkspaceAvatar } from "./workspace-avatar"
import type { SectionId } from "./settings-sheet"
import {
  corDoPonto, descreverExecutor, emAlerta, resumirExecutor, rotularExecutor, type EntradaDoResumo,
} from "./executor-resumo"
import {
  classeDoModo, contarOnline, rotuloDaAcaoDePolitica, rotuloDoModo, rotuloDoStatus, saudeDoPool, semSinal,
} from "./politica"

interface Props extends EntradaDoResumo {
  workspace: Workspace
  salvandoExecutor: boolean
  podeGerenciar: boolean
  onTrocarExecutor: (valor: string) => void
  /** Abre o painel de configuração já na seção pedida. */
  onConfigurar: (secao: SectionId) => void
}

const TITULO_PREVIA = "Prévia: passa a valer quando o roteamento por política for ligado. "
  + "Hoje as execuções seguem o executor selecionado."
const TITULO_PISO = "Isolamento obrigatório: definido pelo administrador da plataforma"

/**
 * Painel do workspace ativo.
 *
 * O produto trabalha em UM workspace por vez — o cabeçalho e o editor já vivem
 * em função dele — e esta tela passou a dizer o mesmo: o ativo ganha a cor de
 * identidade, o executor com o status por extenso e os atalhos para onde o
 * trabalho de fato acontece. A troca de executor fica aqui, e só aqui: é o
 * ajuste mais frequente da tela, e o ajuste dos outros workspaces passa pelo
 * painel de configuração.
 *
 * O seletor rápido é a ação mais destrutiva da tela: voltar ao pool apaga a
 * política inteira e muda para onde os DADOS vão. Por isso ele pede
 * confirmação quando há um dedicado na mesa — a mesma cerimônia que o editor
 * exige para o "último recurso".
 */
export function WorkspaceHero({
  workspace, salvandoExecutor, podeGerenciar, onTrocarExecutor, onConfigurar, ...entrada
}: Props) {
  const identity = getWorkspaceIdentity(workspace)
  const politica = entrada.politica ?? null
  const emVigor = politica?.policy_routing_enabled === true
  const resumo = resumirExecutor(entrada)
  const alerta = emAlerta(resumo, politica)
  const ponto = corDoPonto(resumo, politica)
  const papel = workspace.my_role === "owner" ? "Proprietário" : roleLabel(workspace.my_role)
  const [confirmarPool, setConfirmarPool] = useState(false)

  // Só dedicados ativos: um executor do pool não é alvo — o item "Pool
  // compartilhado" já é o pool. O atual, se for do pool (dado antigo),
  // continua visível para o gatilho não renderizar vazio.
  const disponiveis = entrada.executores.filter(
    e => e.status === "active" && (!e.is_default || e.id_hash === entrada.alvo),
  )

  // Há um dedicado na mesa? Então "pool" apaga a política e muda o destino
  // dos dados: confirmação antes.
  const dedicadoAtual = resumo.estado === "ok" || resumo.estado === "inativo"
    ? (resumo.executor.executor_type === "dedicated" ? resumo.executor.name : null)
    : null
  const temDedicado = dedicadoAtual !== null || (politica?.primary.length ?? 0) > 0

  function escolher(valor: string) {
    if (valor === POOL && temDedicado) { setConfirmarPool(true); return }
    onTrocarExecutor(valor)
  }

  const contagemDaPolitica = politica && politica.mode !== "pool"
    ? contarOnline(
        politica.available_primary + politica.available_fallback,
        politica.primary.length + politica.fallback.length,
        semSinal([...politica.primary, ...politica.fallback]),
      )
    : null

  return (
    <section
      aria-labelledby="workspace-ativo-nome"
      className="relative overflow-hidden rounded-xl border bg-card shadow-xs motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-300"
    >
      {/* A cor de identidade entra só como friso — não como fundo chapado (que
          engoliria o texto nos dois temas) nem como brilho difuso. */}
      <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-1.5", identity.bg)} />

      <div className="relative grid gap-5 p-5 pl-6 sm:p-6 sm:pl-7 lg:grid-cols-[minmax(0,1fr)_19rem] lg:gap-8">
        <div className="min-w-0">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.1em] text-primary">
            Workspace ativo
          </p>
          <div className="flex items-center gap-3.5">
            <WorkspaceAvatar workspace={workspace} size="xl" />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <h2 id="workspace-ativo-nome" className="text-xl font-semibold leading-tight text-balance">
                  {workspace.name}
                </h2>
                {workspace.is_default && (
                  <Badge variant="secondary" className="px-1.5 py-0 text-[11px]">padrão</Badge>
                )}
              </div>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {workspace.description && (
                  <>{workspace.description} <span aria-hidden="true">·</span> </>
                )}
                {papel}
              </p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/projects"><TbFolders size={15} /> Projetos</Link>
            </Button>
            <Button variant="outline" size="sm" onClick={() => onConfigurar("membros")}>
              <TbUsers size={15} /> Membros
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/executores"><TbServer size={15} /> Executores</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onConfigurar("geral")}>
              <TbSettings size={15} /> Configurar
            </Button>
          </div>
        </div>

        {/* ── Executor ──────────────────────────────────────────────────── */}
        <div className="flex min-w-0 flex-col gap-2">
          <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            {alerta
              ? <TbAlertTriangle size={13} className="text-amber-700 dark:text-amber-400" />
              : <TbServer size={13} />}
            Executor
          </span>

          {resumo.estado === "carregando" ? (
            <Skeleton className="h-9 w-full rounded-md" />
          ) : resumo.estado === "indefinido" ? (
            // "Não consegui ler" NÃO é "pool da plataforma": afirmar pool aqui
            // seria mentir sobre para onde as execuções vão.
            <p className="text-sm text-muted-foreground">{resumo.mensagem}</p>
          ) : resumo.estado === "grupo" ? (
            // Grupo ou reserva EM VIGOR: não é um alvo só, e o seletor rápido
            // não o representa. O ajuste passa pelo editor (link abaixo).
            <div className="flex min-w-0 items-center gap-2 rounded-md border bg-background/60 px-3 py-2 text-sm">
              <span className="min-w-0 flex-1 truncate font-medium">{rotularExecutor(resumo)}</span>
            </div>
          ) : podeGerenciar ? (
            <div className="flex items-center gap-2">
              <Select
                value={entrada.alvo ?? POOL}
                onValueChange={escolher}
                // Uma segunda escolha durante a gravação era descartada em
                // silêncio; travar o gatilho diz por quê.
                disabled={salvandoExecutor}
              >
                <SelectTrigger
                  className={cn("w-full", alerta && "border-amber-500/50")}
                  aria-busy={salvandoExecutor}
                  aria-label={`Executor de ${workspace.name}`}
                >
                  <SelectValue placeholder="Selecionar executor" />
                </SelectTrigger>
                <SelectContent className="max-w-(--radix-select-content-available-width)">
                  <SelectItem value={POOL}>
                    <span className="flex min-w-0 items-center gap-1.5">
                      <span className="truncate">Pool compartilhado</span>
                      <ExecutorTypeBadge type="default" size="sm" />
                    </span>
                  </SelectItem>
                  {/* O alvo que sumiu vira um item desabilitado: sem ele o
                      gatilho renderizaria VAZIO e o aviso abaixo não teria
                      referente na tela. */}
                  {resumo.estado === "sumido" && (
                    <SelectItem value={resumo.alvo} disabled>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <TbAlertTriangle size={12} className="shrink-0 text-amber-700 dark:text-amber-400" />
                        <span className="truncate">Executor indisponível</span>
                      </span>
                    </SelectItem>
                  )}
                  {resumo.estado === "inativo" && (
                    <SelectItem value={resumo.executor.id_hash} disabled>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <TbAlertTriangle size={12} className="shrink-0 text-amber-700 dark:text-amber-400" />
                        <span className="truncate">{resumo.executor.name}</span>
                        <Badge variant="outline" className="shrink-0 px-1 py-0 text-[9px] leading-tight text-amber-700 dark:text-amber-400">
                          {rotuloDoStatus(resumo.executor.status)}
                        </Badge>
                      </span>
                    </SelectItem>
                  )}
                  {disponiveis.map(e => (
                    <SelectItem key={e.id_hash} value={e.id_hash}>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <span
                          aria-hidden="true"
                          className={cn("inline-block size-2 shrink-0 rounded-full", e.online ? "bg-green-500" : "bg-muted-foreground/40")}
                        />
                        <span className="sr-only">{e.online ? "online" : "offline"}</span>
                        <span className="truncate">{e.name}</span>
                        <ExecutorTypeBadge type={e.executor_type} size="sm" />
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {/* Slot fixo: inserir/remover o spinner encolhia o Select no
                  meio da interação. */}
              <span className="flex size-4 shrink-0 items-center justify-center">
                {salvandoExecutor && <TbLoader2 size={15} className="animate-spin text-muted-foreground" />}
              </span>
            </div>
          ) : (
            <div className="flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border bg-background/60 px-3 py-2 text-sm">
              {resumo.estado === "pool" ? (
                <>
                  <span className="text-muted-foreground">Pool compartilhado</span>
                  <ExecutorTypeBadge type="default" size="sm" />
                </>
              ) : resumo.estado === "sumido" ? (
                <span className="font-medium text-amber-700 dark:text-amber-400">Executor indisponível</span>
              ) : (
                <>
                  <span className="min-w-0 truncate font-medium">{resumo.executor.name}</span>
                  <ExecutorTypeBadge type={resumo.executor.executor_type} size="sm" />
                </>
              )}
            </div>
          )}

          {resumo.estado !== "carregando" && resumo.estado !== "indefinido" && (
            <p className={cn(
              "flex items-start gap-1.5 text-xs",
              alerta ? "text-amber-700 dark:text-amber-400" : "text-muted-foreground",
            )}>
              {ponto && <span aria-hidden="true" className={cn("mt-1 inline-block size-2 shrink-0 rounded-full", ponto)} />}
              <span>{descreverExecutor(resumo, politica)}</span>
            </p>
          )}

          {/* Uma linha só para a política: o modo que vale (ou a prévia),
              a saúde do conjunto e UM controle para o editor — onde grupo,
              reserva e último recurso são definidos. */}
          {politica && resumo.estado !== "carregando" && resumo.estado !== "indefinido" && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
              <span>Política:</span>
              <Badge
                variant="outline"
                className={cn("gap-1 px-1.5 py-0 text-[10px]", classeDoModo(politica.mode), !emVigor && "border-dashed")}
                title={politica.isolation_floor === "no_pool" ? TITULO_PISO : !emVigor ? TITULO_PREVIA : undefined}
              >
                {politica.isolation_floor === "no_pool" && <TbLock size={10} aria-hidden="true" />}
                {rotuloDoModo(politica.mode)}{!emVigor && " · prévia"}
              </Badge>
              {politica.isolation_floor === "no_pool" && <span className="sr-only">{TITULO_PISO}</span>}
              {politica.mode === "pool"
                ? (saudeDoPool(politica) && <span>{saudeDoPool(politica)}</span>)
                : (politica.primary.length + politica.fallback.length > 1 && resumo.estado !== "grupo" && contagemDaPolitica && (
                  <span>{contagemDaPolitica}</span>
                ))}
              {podeGerenciar && (
                <button
                  type="button"
                  onClick={() => onConfigurar("executor")}
                  className="inline-flex items-center gap-1 underline-offset-2 hover:text-foreground hover:underline"
                >
                  <TbAdjustments size={12} aria-hidden="true" />
                  {rotuloDaAcaoDePolitica(politica.mode)}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Voltar ao pool com um dedicado na mesa: apaga a política e muda para
          onde os dados vão. */}
      <Dialog open={confirmarPool} onOpenChange={setConfirmarPool}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Voltar ao pool compartilhado?</DialogTitle>
            <DialogDescription>
              As execuções de «{workspace.name}» deixam de ir para{" "}
              {dedicadoAtual ?? "os executores dedicados deste workspace"} e passam a rodar em
              qualquer executor compartilhado da plataforma, inclusive os dados que elas
              processam. A política de execução deste workspace (principais, reserva e último
              recurso) será apagada.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmarPool(false)}>Cancelar</Button>
            <Button onClick={() => { setConfirmarPool(false); onTrocarExecutor(POOL) }}>Usar o pool</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
