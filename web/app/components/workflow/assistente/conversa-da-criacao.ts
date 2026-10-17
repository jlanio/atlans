// web/app/components/workflow/assistente/conversa-da-criacao.ts
//
// The create screen's conversation, handed to the editor of the workflow its
// first save created.
//
// That save reopens the editor on /workflow/<id> (`useSaveWorkflow`): another
// page, so the drawer mounts again, and its turns — state of the hook, not of
// the server — would stay behind with the old page. The server moves its half
// (`POST /assistente/editor/conversa/levar`); this module carries the half on
// screen across the remount, and with it the drawer as it was.
//
// Plain module state, not a store: nothing re-renders on it. The create screen
// writes what it shows, the save hands it over, and the new editor takes it
// once, when it mounts.
import { GisFlowService } from "@/service/GisFlowService"
import type { AssistantTurn } from "@/app/components/home/assistente/quadros"

let naTela: { turnos: AssistantTurn[]; correndo: boolean } = { turnos: [], correndo: false }
let entregue: { workflowId: string; turnos: AssistantTurn[] } | null = null

/** What the create screen's drawer shows right now. */
export function registrarConversaDaCriacao(turnos: AssistantTurn[], correndo: boolean): void {
  naTela = { turnos, correndo }
}

/**
 * Hands the create screen's conversation to the workflow its save just created.
 *
 * A turn still running is not carried: leaving the page cuts it, and the
 * server ends it by writing the transcript back under the create screen's key.
 * Carried, the panel would show a conversation the new workflow's assistant
 * does not remember. The editor still opens with the drawer as it was.
 */
export function levarConversaDaCriacao(workflowId: string): void {
  const { turnos, correndo } = naTela
  naTela = { turnos: [], correndo: false }
  const levar = !correndo && turnos.length > 0
  entregue = { workflowId, turnos: levar ? turnos : [] }
  // Fire and forget: the save is done either way, and a move that fails costs
  // the assistant's memory of the conversation, not the workflow.
  if (levar) void GisFlowService.levarConversaDoAssistente(workflowId)
}

/** The turns the create screen handed to this workflow, if it did. Does not take them. */
export function conversaQueChegou(workflowId?: string): AssistantTurn[] | null {
  return workflowId && entregue?.workflowId === workflowId ? entregue.turnos : null
}

/** Takes them: the next editor of this workflow starts on its own. */
export function receberConversa(workflowId?: string): AssistantTurn[] | null {
  const turnos = conversaQueChegou(workflowId)
  if (turnos) entregue = null
  return turnos
}
