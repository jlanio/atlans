"use client"

import type { IconType } from "react-icons"
import { TbBolt, TbChevronRight, TbClock, TbFile, TbMapPin, TbSubtask } from "react-icons/tb"
import { cn } from "@/lib/utils"
import type { IWorkflow } from "@/service/types"
import { derivarGatilho, resumirAgendamento, type TipoDeGatilho } from "../projects/gatilho"
import { SeloAssistente } from "../shared/selo-assistente"
import type { EstadoDoEscopo } from "./dashboard-url"

interface Props {
  /** Já filtrados e cortados por `proximas()`; a lista só desenha. */
  workflows: IWorkflow[]
  escopo: EstadoDoEscopo
  /** Nome do workspace do item, só usado no escopo "todos"; `null` some. */
  nomeDoWorkspace?: (workspaceId: string | null | undefined) => string | null
  onAbrir: (id: string) => void
  /** Aquece a rota do editor antes do clique (o editor é a rota mais pesada). */
  onPrefetch?: (id: string) => void
}

// Ícone por tipo de gatilho, as mesmas escolhas de `linha-workflow.tsx`. Só o
// agendado tende a aparecer aqui (é o que tem `next_run_at`), mas os demais
// existem para o webhook/arquivo com agendamento secundário não ficarem sem cara.
const ICONE: Record<TipoDeGatilho, IconType> = {
  agendado: TbClock,
  webhook: TbBolt,
  arquivo: TbFile,
  geofence: TbMapPin,
  manual: TbClock,
  subfluxo: TbSubtask,
}

/**
 * "Próximas execuções" (docs/specs/dashboard.md §3.6): a única tela que
 * responde "o que vai rodar". Recebe os workflows já filtrados por
 * `proximas()` (agendados, ativos, com a próxima no futuro, cortados em 5) e
 * desenha cada um com o ícone do gatilho, o nome (que abre o editor) e o texto
 * do agendamento de `projects/gatilho.ts`. No escopo "todos", a etiqueta do
 * workspace aparece; no escopo de um só, ela some (é redundante).
 */
export function ProximasLista({ workflows, escopo, nomeDoWorkspace, onAbrir, onPrefetch }: Props) {
  return (
    <section
      aria-labelledby="proximas-titulo"
      className="flex min-w-0 flex-col rounded-lg border bg-card shadow-xs"
    >
      <div className="px-4 pt-4 pb-1">
        <h2 id="proximas-titulo" className="text-sm font-semibold">Próximas execuções</h2>
        <p className="text-xs text-muted-foreground">agendadas, por horário</p>
      </div>
      {workflows.length === 0 ? (
        <p className="px-4 pt-2 pb-5 text-sm text-muted-foreground">Nenhuma execução agendada.</p>
      ) : (
        <ul className="flex flex-col gap-0.5 px-2 pt-1 pb-2">
          {workflows.map(wf => (
            <Item
              key={wf.id_hash}
              workflow={wf}
              escopo={escopo}
              nomeDoWorkspace={nomeDoWorkspace}
              onAbrir={onAbrir}
              onPrefetch={onPrefetch}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function Item({ workflow, escopo, nomeDoWorkspace, onAbrir, onPrefetch }: {
  workflow: IWorkflow
  escopo: EstadoDoEscopo
  nomeDoWorkspace?: (id: string | null | undefined) => string | null
  onAbrir: (id: string) => void
  onPrefetch?: (id: string) => void
}) {
  const gatilho = derivarGatilho(workflow)
  const Icone = ICONE[gatilho.tipo]
  const resumo = resumirAgendamento(workflow.schedule, workflow.flag_ative)
  // Só no "todos" a etiqueta importa; no escopo de um workspace ela é redundante.
  const workspace = escopo === "todos" ? nomeDoWorkspace?.(workflow.workspace_id) : null

  return (
    <li>
      <button
        type="button"
        onClick={() => onAbrir(workflow.id_hash)}
        onPointerEnter={onPrefetch ? () => onPrefetch(workflow.id_hash) : undefined}
        aria-label={`Abrir ${workflow.name} no editor`}
        className={cn(
          "grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2.5 rounded-md px-2 py-2 text-left max-md:min-h-10",
          "outline-none transition-colors hover:bg-accent/60 focus-visible:bg-accent/60 focus-visible:ring-[3px] focus-visible:ring-ring/50",
        )}
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <Icone size={15} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="flex min-w-0 items-center gap-1.5">
            <span className="truncate text-[13px] font-medium">{workflow.name}</span>
            <SeloAssistente origem={workflow.origem} />
            {workspace && (
              <span className="shrink-0 rounded bg-muted px-1.5 py-px text-[10px] font-medium text-muted-foreground">
                {workspace}
              </span>
            )}
          </span>
          {resumo && (
            <span className="truncate text-xs text-muted-foreground">
              {resumo.descricaoCrua
                ? <code className="rounded bg-muted px-1 font-mono text-[11px]">{resumo.descricao}</code>
                : resumo.descricao}
              {resumo.proxima && <> · próxima {resumo.proxima}</>}
            </span>
          )}
        </span>
        <TbChevronRight size={14} className="shrink-0 text-muted-foreground coarse:opacity-40" aria-hidden="true" />
      </button>
    </li>
  )
}
