"use client"

import { useCallback, useRef, useState } from "react"
import type { IResponse } from "@/service/types"
import { createToast } from "@/utils/createToast"

/** The text of a toast: the sentence, or title + description. */
export type ToastText = string | readonly [titulo: string, descricao?: string]

/** The service error, with the domain code when there is one (the policy 409). */
export type ActionError = NonNullable<IResponse<unknown>["error"]>

/**
 * What the action returns: the service response (`data` on success, `error` on
 * failure) — or nothing, for an action that only throws when it fails. Form
 * validation stays OUTSIDE the action (in the button's `disabled` and in Enter):
 * an action that returns without an error is a success.
 */
type ActionResponse<R> = { data?: R; error?: ActionError | null } | void

export interface ActionOptions<R> {
  /** Success toast: fixed text, or a function of what the server returned. `null`: no toast. */
  sucesso: ToastText | null | ((dados: R) => ToastText | null)
  /**
   * Failure toast, built from the server message (`undefined` when none
   * came). `null`: the dialog shows the error on its own screen — the policy 409
   * becomes the "anyway" warning — and no toast goes out.
   */
  erro: (mensagem: string | undefined, erro: ActionError) => ToastText | null
  /** After success, with the dialog already closed — typically reloading the list. */
  aoConcluir?: (dados: R) => void
}

export interface DialogAction {
  aberto: boolean
  /** Open/close. Closing in the middle of the action is ignored — the same lock as `bloqueado`. */
  setAberto: (aberto: boolean) => void
  /** The action is in flight: it is the DialogContent's `bloqueado` and the buttons' `disabled`. */
  executando: boolean
  /**
   * Runs the action. Called again while it is in flight — the field's Enter and
   * the button's click, a repeated Enter — it returns the SAME action, without
   * calling the service again. Resolves after the toast and `aoConcluir`.
   */
  executar: () => Promise<void>
}

/**
 * The lifecycle of an action dialog: open → running → toast → close →
 * `aoConcluir`. The dialogs of Admin › Users, Executors and the workspace trash
 * each repeated this with their own `[open, loading]`, and the copies diverged
 * where it hurt: the field called the same function as the button on Enter,
 * the function did not look at `loading` — only the button, being `disabled`,
 * was protected —, and pressing Enter twice on a slow action fired the call
 * twice. Here Enter and click go through the same `executar`, and the guard
 * applies to both.
 */
export function useAcaoDeDialogo<R = unknown>(
  fn: () => Promise<ActionResponse<R>>,
  opcoes: ActionOptions<R>,
): DialogAction {
  const [aberto, setOpenState] = useState(false)
  const [executando, setExecuting] = useState(false)
  // A ref and not just state: the second Enter can arrive before React draws
  // the "running" state — the guard has to hold already within the same tick.
  const inFlight = useRef<Promise<void> | null>(null)

  // Read from refs so `executar` has a constant identity; the value that counts
  // is the one from the render in which the action was CONFIRMED (see `executar`).
  const fnRef = useRef(fn)
  const optionsRef = useRef(opcoes)
  fnRef.current = fn
  optionsRef.current = opcoes

  const setAberto = useCallback((valor: boolean) => {
    if (!valor && inFlight.current) return
    setOpenState(valor)
  }, [])

  const executar = useCallback(() => {
    if (inFlight.current) return inFlight.current
    // The action and the texts from WHEN it was confirmed: touching the form
    // during the wait changes neither what was sent nor what the toast will say.
    const acao = fnRef.current
    const { sucesso, erro, aoConcluir } = optionsRef.current
    setExecuting(true)

    const rodada = (async () => {
      let res: ActionResponse<R>
      try {
        res = await acao()
      } catch (e) {
        res = { error: { name: "Error", message: e instanceof Error ? e.message : undefined } }
      }
      setExecuting(false)
      if (res?.error) {
        const texto = erro(res.error.message, res.error)
        if (texto) mostrar(createToast.error, texto)
        return
      }
      const dados = res?.data as R
      const texto = typeof sucesso === "function" ? sucesso(dados) : sucesso
      if (texto) mostrar(createToast.success, texto)
      setOpenState(false)
      aoConcluir?.(dados)
    })().finally(() => { inFlight.current = null })

    inFlight.current = rodada
    return rodada
  }, [])

  return { aberto, setAberto, executando, executar }
}

function mostrar(toast: (titulo: string, descricao?: string) => unknown, texto: ToastText) {
  if (typeof texto === "string") toast(texto)
  else toast(texto[0], texto[1])
}
