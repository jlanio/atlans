"use client"

// web/app/components/home/assistente/extras.tsx
//
// The blocks the `Conversa` does not know — the Home's `confirmacao`, `camada`
// and `respostas_rapidas` — drawn the SAME way in both views of the
// conversation: the side panel and the center strip. One model, two places, one
// renderer for the cards; without this the confirmation card would exist twice,
// and the "clicked, locked" rule (which lives in the store to survive
// unmounting) would have two copies to diverge.

import { useCallback } from "react"

import { useHomeStore } from "@/app/stores/homeStore"
import type { ContextoDoBloco } from "@/app/components/home/assistente/conversa"
import type { BlocoDoAssistente } from "@/app/components/home/assistente/quadros"
import type { ResultadoDaDecisao } from "@/app/hooks/home/useAssistente"
import CartaoConfirmacao from "./cartao-confirmacao"
import CartaoCamada from "./cartao-camada"
import RespostasRapidas from "./respostas-rapidas"

export type Confirmar = (
  toolUseId: string, token: string, decisao: "confirmar" | "recusar",
) => Promise<ResultadoDaDecisao> | void

export type Enviar = (mensagem: string) => Promise<void> | void

/**
 * The `Conversa`'s `extras` for the Home. `correndo` locks the cards while a
 * stream is live (the click would fire a second SSE on top of the first) and
 * hides the quick replies (the hook's `enviar` returns silently during the
 * stream, and a chip that does nothing is a dead button).
 */
export function useExtrasDoAssistente({
  confirmar, correndo, enviar,
}: { confirmar: Confirmar; correndo: boolean; enviar: Enviar }) {
  // Already-clicked confirmations live in the store, not here: collapsing the panel
  // UNMOUNTS it, and the turns (with the token) survive — a local Set revived
  // the decided card, and the second click hit an already-consumed token.
  const decididos = useHomeStore((s) => s.decididos)
  const expirados = useHomeStore((s) => s.expirados)
  const marcarDecidido = useHomeStore((s) => s.marcarDecidido)
  const desmarcarDecidido = useHomeStore((s) => s.desmarcarDecidido)
  const marcarExpirado = useHomeStore((s) => s.marcarExpirado)

  const onDecidir = useCallback(
    (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => {
      if (decididos[toolUseId] || correndo) return
      marcarDecidido(toolUseId)
      // The mark is optimistic, and the outcome decides what stays on screen: only a
      // transport failure unlocks (the action did not happen and needs another
      // chance). A 409 keeps it locked — the key was already consumed or expired,
      // and reopening the card would only offer a click that fails again.
      void Promise.resolve(confirmar(toolUseId, token, decisao)).then((resultado) => {
        if (resultado === "falhou") desmarcarDecidido(toolUseId)
        else if (resultado === "expirada") marcarExpirado(toolUseId)
      })
    },
    [decididos, correndo, confirmar, marcarDecidido, desmarcarDecidido, marcarExpirado],
  )

  return useCallback(
    (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => {
      if (bloco.tipo === "confirmacao") {
        return (
          <CartaoConfirmacao
            confirmacao={bloco.confirmacao}
            decidido={!!decididos[bloco.confirmacao.tool_use_id]}
            expirado={!!expirados[bloco.confirmacao.tool_use_id]}
            ocupado={correndo}
            onDecidir={onDecidir}
          />
        )
      }
      if (bloco.tipo === "camada") return <CartaoCamada camada={bloco.camada} />
      if (bloco.tipo === "respostas_rapidas") {
        // They hold only for that one time: only in the LAST turn and outside the
        // stream. The click sends the sentence as the next message — the new turn
        // removes the chips from the screen on its own; so does typing. On replay
        // the last turn's chips come back: the conversation IS at that point.
        if (!contexto.ultimoTurno || correndo) return null
        return <RespostasRapidas opcoes={bloco.opcoes} onEscolher={enviar} />
      }
      // `fluxo` is NOT rendered anywhere — not here, nor in the badges strip, which
      // shows the artifacts. The Home is the only page for people who do not
      // administer the system, and the assistant's workflow is not reachable from
      // here; it remains in Projetos, with the "mostrar os do assistente" toggle
      // on. The frame still arrives and gets decoded — what disappears is the
      // offer.
      return null
    },
    [decididos, expirados, correndo, onDecidir, enviar],
  )
}
