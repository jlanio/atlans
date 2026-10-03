"use client"

import { TbSubtask } from "react-icons/tb"

import { IWorkflow } from "@/service/types"

/**
 * Badge for a workflow that exists to be CALLED by another.
 *
 * Same icon and same color as the sub-workflow badge in the run panel: whoever
 * sees one learns the other. It sits next to the name because it says what the
 * workflow IS — the actions are on the other side of the card.
 *
 * The warning about the trigger is no detail: a sub-workflow usually has none,
 * and the list's run button fires a run that does not do what is expected.
 */
export function SeloSubFluxo({ workflow }: { workflow: Pick<IWorkflow, "is_subworkflow"> }) {
  if (!workflow.is_subworkflow) return null

  return (
    <span
      title="Sub-fluxo: declara saída de sub-workflow e existe para ser chamado por outro workflow. Costuma não ter gatilho próprio — executá-lo sozinho normalmente não faz o esperado."
      className="inline-flex shrink-0 items-center gap-1 rounded bg-indigo-500/10 px-1.5 py-px text-[10px] font-medium text-indigo-600 dark:text-indigo-400"
    >
      <TbSubtask size={11} /> Sub-fluxo
    </span>
  )
}
