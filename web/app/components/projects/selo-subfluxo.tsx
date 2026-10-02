"use client"

import { TbSubtask } from "react-icons/tb"

import { IWorkflow } from "@/service/types"

/**
 * Selo de workflow que existe para ser CHAMADO por outro.
 *
 * Mesmo ícone e mesma cor do selo de sub-fluxo no painel de execução: quem vê
 * um aprende o outro. Fica colado ao nome porque diz o que o workflow É — as
 * ações ficam do outro lado do card.
 *
 * O aviso sobre o gatilho não é detalhe: um sub-fluxo em geral não tem um, e o
 * botão de executar da lista dispara um run que não faz o que se espera.
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
