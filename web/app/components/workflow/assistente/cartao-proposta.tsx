"use client"

// web/app/components/workflow/assistente/cartao-proposta.tsx
//
// The proposal card — and now with TWO roles.
//
// `desenhar: true` comes from `desenhar_no_canvas` and means "put it on screen now".
// The workflow appears by itself while the model builds it: that's what makes the
// construction incremental instead of a single dump at the end.
//
// `desenhar: false` comes from `validate_workflow` and carries only the verdict on
// what is already drawn. There's no button: the workflow is already there.
//
// The exception is a canvas that ALREADY HAS work. Then the conversation's first
// drawing waits for a click — and after it the conversation draws by itself,
// without interrupting again. It isn't `window.confirm`: that blocks the thread,
// and blocking the thread in the middle of a stream means stopping reading the stream.
//
// The assistant still does NOT save: drawing is a draft on the canvas, and the
// editor's Save still belongs to whoever is using it.

import { useEffect, useMemo, useRef } from "react"
import { useNodes } from "@xyflow/react"
import { TbAlertTriangle, TbCheck, TbWand } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import { INodeContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { plural } from "@/lib/formatos"
import { aplicarProposta, type ProposalResult } from "../utils/aplicar-proposta"
import type { WorkflowProposal } from "@/app/components/home/assistente/quadros"

interface Props {
  proposta: WorkflowProposal
  onAplicar: (resultado: ProposalResult) => void
  /** The conversation may now draw by itself on a canvas that had work. */
  liberado: boolean
  /** Called on the first accepted drawing, so the following ones don't ask. */
  onLiberar: () => void
}

export default function ProposalCard({ proposta, onAplicar, liberado, onLiberar }: Props) {
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  // Subscribes to the canvas HERE, not in the drawer: only this card needs to react
  // to what is drawn, and subscribing up there would re-render the whole
  // conversation on every frame of a drag.
  const nos = useNodes<INodeContext>()

  const resultado = useMemo(
    () => aplicarProposta(proposta.definicao, nodesAPI, nos),
    [proposta.definicao, nodesAPI, nos],
  )

  const { novos, alterados, removidos } = resultado.resumo

  // Empty canvas: nothing to lose, always draws. Canvas with work: only after
  // the conversation's first acceptance.
  const canvasEmpty = nos.length === 0
  const drawsAutomatically = proposta.desenhar === true
    && resultado.catalogoPronto
    && (canvasEmpty || liberado)

  // Once per card. Without the lock, any canvas re-render (a drag,
  // a zoom) would reapply the same proposal and undo what the person just
  // changed — and `resultado` changes identity on every render, so the
  // dependency list alone doesn't hold it.
  const alreadyDrew = useRef(false)
  useEffect(() => {
    if (!drawsAutomatically || alreadyDrew.current) return
    alreadyDrew.current = true
    onAplicar(resultado)
  }, [drawsAutomatically, onAplicar, resultado])
  // `ok: null` is "don't know" — the validation report couldn't be read. Treating
  // it as "passed" would mean offering to apply a workflow nobody confirmed.
  const validated = proposta.ok === true && (proposta.erros ?? 0) === 0

  return (
    <div className="mt-2 rounded-lg border bg-card p-3 shadow-xs" data-testid="cartao-proposta">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0" aria-hidden="true">
          {proposta.desenhar || validated
            ? <TbCheck size={16} className="text-green-600 dark:text-green-400" />
            : <TbAlertTriangle size={16} className="text-amber-600 dark:text-amber-400" />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">
            {proposta.desenhar
              ? (drawsAutomatically ? "Desenhado no canvas" : "Pronto para desenhar")
              : (validated ? "Validação limpa" : "Validação com pendências")}
          </p>
          {proposta.nota && (
            <p className="break-words text-xs text-muted-foreground">{proposta.nota}</p>
          )}
          <p className="text-xs tabular-nums text-muted-foreground">
            {plural(proposta.nos, "nó", "nós")} · {plural(proposta.arestas, "ligação", "ligações")}
            {proposta.avisos ? ` · ${plural(proposta.avisos, "aviso")}` : ""}
          </p>
        </div>
      </div>

      {!proposta.desenhar && !validated && (
        <p role="status" className="mt-2 rounded-md border border-amber-500/30 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
          {proposta.erros != null && proposta.erros > 0
            ? `A validação apontou ${plural(proposta.erros, "erro")}. Peça o ajuste antes de aplicar.`
            : "A validação não pôde ser lida. Peça para validar de novo antes de aplicar."}
        </p>
      )}

      {!resultado.catalogoPronto && (
        <p role="status" className="mt-2 rounded-md border border-amber-500/30 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
          O catálogo de nós ainda não carregou.
        </p>
      )}

      {/* The count of what CHANGES on the canvas. Only appears when there is a canvas:
          on an empty workflow "4 novos" tells nothing the 4 nodes don't already say. */}
      {(alterados > 0 || removidos > 0) && (
        <p className="mt-2 text-xs tabular-nums text-muted-foreground">
          {[
            novos > 0 ? `${novos} ${novos === 1 ? "novo" : "novos"}` : null,
            alterados > 0 ? `${alterados} ${alterados === 1 ? "alterado" : "alterados"}` : null,
            removidos > 0 ? `${removidos} ${removidos === 1 ? "removido" : "removidos"}` : null,
          ].filter(Boolean).join(" · ")}
          {removidos > 0 && (
            <span className="block text-destructive">
              Aplicar substitui o canvas. O que não estiver no fluxo proposto some.
            </span>
          )}
        </p>
      )}

      {/* The button only exists in the case that needs acceptance: a conversation's
          first drawing on a canvas that already had work. After it, the
          conversation draws by itself and the footer disappears — interrupting at
          every node would be the opposite of watching the workflow grow. */}
      {proposta.desenhar && !drawsAutomatically && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            className="max-md:h-10"
            disabled={!resultado.catalogoPronto}
            onClick={() => {
              // The lock BEFORE releasing: releasing makes `drawsAutomatically`
              // true, the effect fires, and without this the same drawing
              // would land on the canvas twice.
              alreadyDrew.current = true
              onLiberar()
              onAplicar(resultado)
            }}
          >
            <TbWand size={14} aria-hidden="true" />
            Desenhar no canvas
          </Button>
          <span className="min-w-0 text-[11px] text-muted-foreground">
            Desta vez em diante, esta conversa desenha sozinha. Ctrl+Z desfaz.
          </span>
        </div>
      )}

      {proposta.desenhar && drawsAutomatically && (
        <p className="mt-2 text-[11px] text-muted-foreground">
          Desenhar não salva — o Salvar continua seu.
        </p>
      )}
    </div>
  )
}
