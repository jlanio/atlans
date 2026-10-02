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
import type { IAgendamentoMeu } from "@/service/types"
import type { IParamSchema } from "@/service/types"
import { useAgendamentos } from "@/app/hooks/home/useAgendamentos"
import { LinhaDoMeu, GatilhoDeAcoes } from "../linha"
import { useFormatos, useIdiomaDaTela, useTextosDaCasca } from "../i18n/da-casca"
import { resumirNoIdioma } from "./resumo"

// Só a sublista some sozinha no trilho de 3rem; os blocos soltos (erro, aviso)
// precisam da classe na mão.
const SO_EXPANDIDO = "group-data-[collapsible=icon]:hidden"

/**
 * O fuso do NAVEGADOR, para decidir se vale nomear o do agendamento. Lido uma
 * vez por render da linha e não no módulo: em SSR não há Intl configurado pelo
 * usuário, e o `try` cobre os ambientes sem `resolvedOptions`.
 */
function fusoDoNavegador(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null
  } catch {
    return null
  }
}

/**
 * Uma hora de relógio escrita na descrição ("todo dia às 06:00", "seg–sex às
 * 06:00", "dia 5 às 06:00"). É o que o fuso qualifica.
 */
const TEM_HORA = /\d{1,2}:\d{2}/

/**
 * O agendamento roda no fuso que o backend guarda (padrão UTC, ou o
 * AGENDAMENTO_FUSO_PADRAO da instalação),
 * mas a "próxima execução" é formatada no fuso do navegador. Sem dizer qual é
 * qual, a linha mistura duas horas diferentes — "todo dia às 06:00 · amanhã,
 * 07:00" — e não há como saber pela tela qual é a real.
 *
 * O sufixo depende, então, de a descrição TER hora: "a cada 30 min" é a mesma
 * cadência em qualquer fuso, e "a cada 30 min (America/La_Paz)" não quer
 * dizer nada. O teste é a hora na própria descrição, e não a estratégia, porque
 * um cron de passo ("a cada N minutos") também é traduzido como cadência. A
 * expressão CRUA (`descricaoCrua`) fica de fora por outro motivo: ninguém lê o
 * fuso de um cron que a tela não soube traduzir.
 */
function sufixoDeFuso(
  timezone: string | null | undefined,
  resumo: { descricao: string; descricaoCrua: boolean } | null,
): string {
  if (!timezone || !resumo) return ""
  if (resumo.descricaoCrua || !TEM_HORA.test(resumo.descricao)) return ""
  const local = fusoDoNavegador()
  if (local && local === timezone) return ""
  return ` (${timezone})`
}

/**
 * "Meus → Agendamentos": os agendamentos da pessoa, entre todos os workspaces
 * (ativos E pausados). O menu ⋯ (só para quem é operator+ NAQUELE workspace)
 * traz Pausar/Ativar e Rodar agora.
 *
 * **A linha não leva mais ao editor.** Por decisão do dono, a Home é a única
 * página de quem não administra o sistema, e essa navegação foi uma das saídas
 * a fechar. A linha virou `<div>`: um `<button>` sem ação prometeria um clique
 * que não acontece, e o leitor de tela ainda o anunciaria como acionável. Rodar
 * e pausar seguem no menu — o que muda é ir embora da Home, não gerir o
 * agendamento.
 *
 * O papel é POR ITEM: `useWorkspace().canExecute` vale só para o workspace ativo,
 * mas esta lista cruza vários — então checa `my_role` do workspace de cada linha.
 *
 * A lista vem cortada no teto do servidor — o rodapé diz o total e oferece
 * "Ver mais", como Chats e Artefatos, porque não há outra tela de Agendamentos
 * onde procurar o que ficou de fora.
 */
export function AgendamentosLista() {
  const {
    agendamentos, carregando, atualizando, jaCarregou, erro, total, carregandoMais,
    alternandoId, recarregar, carregarMais, alternarAtivo,
  } = useAgendamentos()
  const { workspaces } = useWorkspace()
  const { refresh: refreshActiveRuns } = useActiveRuns()
  const idioma = useIdiomaDaTela()
  const textos = useTextosDaCasca()
  const t = textos.listas
  const fmt = useFormatos()

  const [executeTarget, setExecuteTarget] = useState<
    { workflowId: string; workflowName: string; schema: Record<string, IParamSchema> } | null
  >(null)
  const [preparandoId, setPreparandoId] = useState<string | null>(null)

  const podeMexer = useCallback(
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

  // Rodar agora precisa do params_schema, que `/me/schedules` não traz: busca o
  // fluxo no clique e, se tiver parâmetros, abre o diálogo; senão dispara direto.
  // Mesmo fluxo de projects/index.tsx (handleRunClick).
  const prepararRun = useCallback(
    async (item: IAgendamentoMeu) => {
      setPreparandoId(item.job_id)
      const res = await GisFlowService.getWorkflowById(item.workflow_id)
      setPreparandoId(null)
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

  // A lista vem cortada no teto do servidor: sem dizer o total, quem rola até o
  // fim conclui que viu tudo — e não há outra tela de Agendamentos onde procurar
  // o que ficou de fora.
  const faltam = total > agendamentos.length

  // O corpo é escolhido numa VARIÁVEL, não por `return` antecipado: o rodapé
  // (aviso de recarga falhada + "Ver mais") tem de viver FORA dos ramos. Com a
  // lista vazia o `return` curto saía antes dele e uma recarga que falhava não
  // tinha onde aparecer. Mesmo desenho de `artefatos/lista.tsx`.
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
    // §3: o bloco de erro só toma a lista quando nunca houve carga aceita. Com
    // agendamentos na tela, a falha vira o aviso âmbar do rodapé.
    corpo = (
      <div role="alert" className={`flex flex-col items-start gap-1 px-2 py-1.5 ${SO_EXPANDIDO}`}>
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
          // Em português é o `resumirAgendamento` do gatilho tal e qual; nos
          // outros idiomas, as mesmas regras com as frases do dicionário.
          const resumo = resumirNoIdioma(item, item.flag_ative, idioma)
          const permitido = podeMexer(item.workspace_id)
          const preparando = preparandoId === item.job_id
          const fuso = sufixoDeFuso(item.timezone, resumo)
          const linhaResumo = !resumo
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
              {/* A linha NÃO navega mais para o editor: a Home é a única página
                  de quem não administra o sistema. Por isso é um `<div>` e não
                  um `<button>` — um botão sem ação seria uma promessa falsa, e
                  o leitor de tela o anunciaria como acionável. O que se pode
                  fazer com o agendamento continua no menu `⋯` (pausar/ativar,
                  rodar agora); o realce no hover é da `LinhaDoMeu`, e é ele que
                  revela o gatilho do menu — o mesmo desenho das outras listas. */}
              <div
                title={item.workflow_name}
                className="flex min-w-0 flex-1 flex-col gap-0.5 py-1 text-sidebar-foreground max-md:min-h-10"
              >
                <span className="flex min-w-0 items-center gap-1.5">
                  {/* "Rodar agora" fecha o menu e some: o ponto de estado vira
                      spinner enquanto o params_schema é buscado, senão o clique
                      passa 1-3 s sem nenhum retorno na tela. */}
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
                {/* Segunda linha truncada com o texto inteiro no `title`: "pausado
                    — workflow inativo" cortado em "pausado — wor…" não diz nada. */}
                {linhaResumo && (
                  <span className="truncate pl-3 text-[11px] text-sidebar-foreground/55" title={linhaResumo}>
                    {linhaResumo}
                  </span>
                )}
              </div>

              {permitido && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <GatilhoDeAcoes rotulo={item.workflow_name} />
                  </DropdownMenuTrigger>
                  {/* `home-portal`: o menu é portado para o <body>, FORA da
                      árvore que declara a paleta da Home — sem a classe ele
                      abria claro sobre a Home quase preta quando o app está no
                      tema claro. Os itens ganham 40px no telefone: o gatilho já
                      era grande o bastante, o destino do toque é que não era. */}
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
                      onSelect={() => prepararRun(item)}
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

      {/* O rodapé vive FORA dos ramos: com a lista VAZIA e uma recarga que
          falhou, o aviso âmbar não tinha onde aparecer. */}
      {((erro && jaCarregou) || faltam) && (
        <div className={`flex flex-col gap-1 px-2 pb-1 ${SO_EXPANDIDO}`}>
          {/* Recarga que falhou sobre a lista pronta: aviso, não apagar a lista. */}
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
