"use client"
import { useCallback, useState } from "react"
import {
  TbLoader2, TbPlayerPause, TbPlayerPlay, TbPlayerPlayFilled, TbSparkles,
} from "react-icons/tb"
import {
  SidebarMenuSub, SidebarMenuSubItem, SidebarMenuSkeleton,
} from "@/app/components/ui/sidebar"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { useWorkspace, hasMinRole } from "@/context/WorkspaceContext"
import { useActiveRuns } from "@/context/ActiveRunsContext"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { AvisoAmbar } from "@/app/components/shared/estados"
import ExecuteParamsDialog from "@/app/components/workflow/execute-params-dialog"
import { cn } from "@/lib/utils"
import type { IMySchedule } from "@/service/types"
import type { IParamSchema } from "@/service/types"
import { useAgendamentos } from "@/app/hooks/home/useAgendamentos"
import { LinhaDoMeu, GatilhoDeAcoes } from "../linha"
import { useFormats, useScreenLanguage, useShellTexts } from "../i18n/da-casca"
import { resumirNoIdioma } from "./resumo"

// Only the sublist hides on its own in the 3rem rail; the standalone blocks
// (error, warning) need the class added by hand.
const EXPANDED_ONLY = "group-data-[collapsible=icon]:hidden"

/**
 * The BROWSER's time zone, to decide whether the schedule's one is worth naming.
 * Read once per row render and not at module level: in SSR there is no
 * user-configured Intl, and the `try` covers environments without `resolvedOptions`.
 */
function fusoDoNavegador(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null
  } catch {
    return null
  }
}

/**
 * A clock time written in the description ("todo dia às 06:00", "seg–sex às
 * 06:00", "dia 5 às 06:00"). That is what the time zone qualifies.
 */
const HAS_TIME = /\d{1,2}:\d{2}/

/**
 * The schedule runs in the time zone the backend stores (UTC by default, or the
 * installation's AGENDAMENTO_FUSO_PADRAO),
 * but the "próxima execução" (next run) is formatted in the browser's time zone.
 * Without saying which is which, the row mixes two different times — "todo dia
 * às 06:00 · amanhã, 07:00" — and there is no way to tell from the screen which
 * one is real.
 *
 * The suffix therefore depends on the description HAVING a time: "a cada 30 min"
 * is the same cadence in any time zone, and "a cada 30 min (America/La_Paz)"
 * means nothing. The test is the time in the description itself, not the
 * strategy, because a step cron ("a cada N minutos") is also translated as a
 * cadence. The RAW expression (`descricaoCrua`) is left out for another reason:
 * nobody reads the time zone of a cron the screen couldn't translate.
 */
function timezoneSuffix(
  timezone: string | null | undefined,
  resumo: { descricao: string; descricaoCrua: boolean } | null,
): string {
  if (!timezone || !resumo) return ""
  if (resumo.descricaoCrua || !HAS_TIME.test(resumo.descricao)) return ""
  const local = fusoDoNavegador()
  if (local && local === timezone) return ""
  return ` (${timezone})`
}

/**
 * "Meus → Agendamentos" (Mine → Schedules): the person's schedules, across all
 * workspaces (active AND paused). The ⋯ menu (only for operator+ IN THAT
 * workspace) offers Pausar/Ativar (pause/activate) and Rodar agora (run now).
 *
 * **The row no longer leads to the editor.** By the owner's decision, the Home is
 * the only page for those who don't administer the system, and this navigation
 * was one of the exits to close. The row became a `<div>`: a `<button>` with no
 * action would promise a click that doesn't happen, and the screen reader would
 * still announce it as actionable. Run and pause remain in the menu — what
 * changes is leaving the Home, not managing the schedule.
 *
 * The role is PER ITEM: `useWorkspace().canExecute` only applies to the active
 * workspace, but this list spans several — so it checks the `my_role` of each
 * row's workspace.
 *
 * The list comes cut at the server's ceiling — the footer states the total and
 * offers "Ver mais" (see more), like Chats and Artifacts, because there is no
 * other Schedules screen in which to look for what was left out.
 */
export function AgendamentosLista() {
  const {
    agendamentos, carregando, atualizando, jaCarregou, erro, total, carregandoMais,
    alternandoId, recarregar, carregarMais, alternarAtivo,
  } = useAgendamentos()
  const { workspaces } = useWorkspace()
  const { refresh: refreshActiveRuns } = useActiveRuns()
  const idioma = useScreenLanguage()
  const textos = useShellTexts()
  const t = textos.listas
  const fmt = useFormats()

  const [executeTarget, setExecuteTarget] = useState<
    { workflowId: string; workflowName: string; schema: Record<string, IParamSchema> } | null
  >(null)
  const [preparingId, setPreparingId] = useState<string | null>(null)

  const canModify = useCallback(
    (workspaceId: string | null | undefined) =>
      hasMinRole(workspaces.find((w) => w.id_hash === workspaceId)?.my_role, "operator"),
    [workspaces],
  )

  const rodar = useCallback(
    async (workflowId: string, workflowName: string, inputs: Record<string, unknown> = {}) => {
      setExecuteTarget(null)
      const res = await GisFlowService.executeWorkflow(workflowId, inputs, false)
      if (res?.error) {
        createToast.error(t.agendamentos.executarFalhou, res.error.message)
      } else {
        createToast.success(t.agendamentos.iniciou(workflowName))
        refreshActiveRuns()
      }
    },
    [refreshActiveRuns, t],
  )

  // Run now needs the params_schema, which `/me/schedules` doesn't bring: fetches
  // the workflow on click and, if it has parameters, opens the dialog; otherwise
  // fires directly. Same flow as projects/index.tsx (handleRunClick).
  const prepareRun = useCallback(
    async (item: IMySchedule) => {
      setPreparingId(item.job_id)
      const res = await GisFlowService.getWorkflowById(item.workflow_id)
      setPreparingId(null)
      if (res.error || !res.data) {
        createToast.error(
          t.agendamentos.prepararFalhou,
          res.error?.message ?? t.agendamentos.lerParametrosFalhou,
        )
        return
      }
      const schema = res.data.params_schema
      if (schema && Object.keys(schema).length > 0) {
        setExecuteTarget({ workflowId: item.workflow_id, workflowName: item.workflow_name, schema })
      } else {
        rodar(item.workflow_id, item.workflow_name)
      }
    },
    [rodar, t],
  )

  // The list comes cut at the server's ceiling: without stating the total, whoever
  // scrolls to the end concludes they saw everything — and there is no other
  // Schedules screen in which to look for what was left out.
  const faltam = total > agendamentos.length

  // The body is chosen into a VARIABLE, not via an early `return`: the footer
  // (failed-reload warning + "Ver mais") has to live OUTSIDE the branches. With
  // an empty list the short `return` exited before it and a failing reload had
  // nowhere to appear. Same design as `artefatos/lista.tsx`.
  let corpo: React.ReactNode
  if (carregando) {
    corpo = (
      <SidebarMenuSub role="status" aria-busy="true" aria-label={t.agendamentos.carregando}>
        {[0, 1, 2].map((i) => (
          <SidebarMenuSubItem key={i}>
            <SidebarMenuSkeleton />
          </SidebarMenuSubItem>
        ))}
      </SidebarMenuSub>
    )
  } else if (erro && !jaCarregou) {
    // §3: the error block only takes over the list when there was never an
    // accepted load. With schedules on screen, the failure becomes the footer's amber warning.
    corpo = (
      <div role="alert" className={`flex flex-col items-start gap-1 px-2 py-1.5 ${EXPANDED_ONLY}`}>
        <p className="text-xs text-sidebar-foreground/70">{erro}</p>
        <button
          type="button"
          onClick={recarregar}
          className="inline-flex items-center rounded-sm text-xs font-medium text-sidebar-foreground underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
        >
          {textos.comum.tentarDeNovo}
        </button>
      </div>
    )
  } else if (agendamentos.length === 0) {
    corpo = (
      <SidebarMenuSub>
        <li className="px-2 py-1.5 text-xs text-sidebar-foreground/55">{t.agendamentos.vazio}</li>
      </SidebarMenuSub>
    )
  } else {
    corpo = (
      <SidebarMenuSub aria-busy={atualizando || undefined}>
        {agendamentos.map((item) => {
          // In Portuguese it is the trigger's `resumirAgendamento` as is; in the
          // other languages, the same rules with the dictionary's sentences.
          const resumo = resumirNoIdioma(item, item.flag_ative, idioma)
          const permitido = canModify(item.workspace_id)
          const preparando = preparingId === item.job_id
          const fuso = timezoneSuffix(item.timezone, resumo)
          const summaryLine = !resumo
            ? null
            : resumo.estado === "pausado"
              ? resumo.motivoPausa
                ? t.agendamentos.pausadoPor(resumo.motivoPausa)
                : t.agendamentos.pausado
              : resumo.estado === "calculando"
                ? `${resumo.descricao}${fuso} · ${t.agendamentos.calculando}`
                : `${resumo.descricao}${fuso}${resumo.proxima ? ` · ${resumo.proxima}` : ""}`
          return (
            <SidebarMenuSubItem key={item.job_id}>
              <LinhaDoMeu>
              {/* The row NO longer navigates to the editor: the Home is the only page
                  for those who don't administer the system. That's why it is a
                  `<div>` and not a `<button>` — a button with no action would be
                  a false promise, and the screen reader would announce it as
                  actionable. What can be done with the schedule remains in the
                  `⋯` menu (pause/activate, run now); the hover highlight comes
                  from `LinhaDoMeu`, and it is what reveals the menu trigger —
                  the same design as the other lists. */}
              <div
                title={item.workflow_name}
                className="flex min-w-0 flex-1 flex-col gap-0.5 py-1 text-sidebar-foreground max-md:min-h-10"
              >
                <span className="flex min-w-0 items-center gap-1.5">
                  {/* "Rodar agora" closes the menu and disappears: the status dot becomes
                      a spinner while the params_schema is fetched, otherwise the
                      click goes 1-3 s with no feedback on screen. */}
                  {preparando ? (
                    <TbLoader2
                      className="size-3 shrink-0 animate-spin text-sidebar-foreground/60"
                      aria-label={t.agendamentos.preparando}
                    />
                  ) : (
                    <span
                      className={cn(
                        "size-1.5 shrink-0 rounded-full",
                        resumo?.estado === "ativo" ? "bg-primary" : "bg-sidebar-foreground/30",
                      )}
                      aria-hidden="true"
                    />
                  )}
                  <span className="truncate text-[13px]">{item.workflow_name}</span>
                  {item.origem === "assistente" && (
                    <TbSparkles
                      className="size-3 shrink-0 text-sidebar-foreground/50"
                      title={t.agendamentos.doAssistente}
                      aria-label={t.agendamentos.doAssistente}
                    />
                  )}
                </span>
                {/* Second line truncated with the full text in `title`: "pausado
                    — workflow inativo" cut to "pausado — wor…" says nothing. */}
                {summaryLine && (
                  <span className="truncate pl-3 text-[11px] text-sidebar-foreground/55" title={summaryLine}>
                    {summaryLine}
                  </span>
                )}
              </div>

              {permitido && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <GatilhoDeAcoes rotulo={item.workflow_name} />
                  </DropdownMenuTrigger>
                  {/* `home-portal`: the menu is portaled to <body>, OUTSIDE the
                      tree that declares the Home's palette — without the class it
                      opened light over the near-black Home when the app is in
                      the light theme. The items get 40px on phones: the trigger
                      was already big enough, it was the tap target that wasn't. */}
                  <DropdownMenuContent align="end" className="home-portal min-w-40">
                    <DropdownMenuItem
                      onSelect={() => alternarAtivo(item)}
                      disabled={alternandoId === item.job_id}
                      className="gap-2 max-md:min-h-10"
                    >
                      {item.active ? (
                        <>
                          <TbPlayerPause className="size-4" /> {t.agendamentos.pausar}
                        </>
                      ) : (
                        <>
                          <TbPlayerPlay className="size-4" /> {t.agendamentos.ativar}
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onSelect={() => prepareRun(item)}
                      disabled={preparando}
                      className="gap-2 max-md:min-h-10"
                    >
                      <TbPlayerPlayFilled className="size-4" /> {t.agendamentos.rodarAgora}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
              </LinhaDoMeu>
            </SidebarMenuSubItem>
          )
        })}
      </SidebarMenuSub>
    )
  }

  return (
    <>
      {corpo}

      {/* The footer lives OUTSIDE the branches: with an EMPTY list and a reload
          that failed, the amber warning had nowhere to appear. */}
      {((erro && jaCarregou) || faltam) && (
        <div className={`flex flex-col gap-1 px-2 pb-1 ${EXPANDED_ONLY}`}>
          {/* Reload that failed over the ready list: warn, don't erase the list. */}
          {erro && jaCarregou && (
            <AvisoAmbar
              onTentar={recarregar}
              rotuloDoBotao={textos.comum.tentarDeNovo}
            >
              {t.agendamentos.atualizarFalhou}
            </AvisoAmbar>
          )}
          {faltam && (
            <div className="flex flex-wrap items-center gap-x-2 px-1">
              <span className="text-[11px] tabular-nums text-sidebar-foreground/55">
                {t.geral.mostrando(fmt.inteiro(agendamentos.length), fmt.inteiro(total))}
              </span>
              <button
                type="button"
                onClick={carregarMais}
                disabled={carregandoMais}
                className="inline-flex items-center gap-1 rounded-sm text-[11px] font-medium text-sidebar-foreground underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-60 max-md:min-h-10"
              >
                {carregandoMais && <TbLoader2 className="size-3 animate-spin" aria-hidden="true" />}
                {t.geral.verMais}
              </button>
            </div>
          )}
        </div>
      )}

      {executeTarget && (
        <ExecuteParamsDialog
          open
          className="home-portal"
          paramsSchema={executeTarget.schema}
          onConfirm={(inputs) => rodar(executeTarget.workflowId, executeTarget.workflowName, inputs)}
          onCancel={() => setExecuteTarget(null)}
        />
      )}
    </>
  )
}
