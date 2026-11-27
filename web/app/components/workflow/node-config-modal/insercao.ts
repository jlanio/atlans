"use client"

/**
 * Click to insert (docs/specs/node-data-panels.md §6.5): the last form field
 * the person focused in the node modal is the target, and clicking a key,
 * column or JSON key in the Entradas panel inserts its expression there, at
 * the caret. Dragging still works; clicking is what a touchpad or a person who
 * never guessed the drag needs.
 *
 * One target at a time, for the whole page: there is only one node modal.
 * - Native text fields register themselves through the modal's `onFocus`
 *   capture (`alvoDoCampo`), so every field type is covered without touching it.
 * - Monaco (code and SQL) registers its own target, since its textarea is an
 *   implementation detail and the edit has to go through the editor.
 */
import { useSyncExternalStore } from "react"

export interface AlvoDeInsercao {
  /** What the person calls the field: its label, or a short fallback. */
  rotulo: string
  inserir(texto: string): void
  /** false once the field left the page (modal closed, node switched). */
  vivo(): boolean
}

let alvo: AlvoDeInsercao | null = null
const ouvintes = new Set<() => void>()

function avisar() {
  ouvintes.forEach(f => f())
}

export function definirAlvo(novo: AlvoDeInsercao | null) {
  if (alvo === novo) return
  alvo = novo
  avisar()
}

/** The current target, or null (none yet, or it left the page). */
export function alvoAtual(): AlvoDeInsercao | null {
  if (alvo && !alvo.vivo()) {
    alvo = null
  }
  return alvo
}

/** Label of the current target, for the panel's hint. Re-renders on change. */
export function useRotuloDoAlvo(): string | null {
  return useSyncExternalStore(
    (f) => { ouvintes.add(f); return () => { ouvintes.delete(f) } },
    () => alvoAtual()?.rotulo ?? null,
    () => null,
  )
}

/** Inserts into the current target. Returns its label, or null when there is none. */
export function inserirNoAlvo(texto: string): string | null {
  const atual = alvoAtual()
  if (!atual) return null
  atual.inserir(texto)
  return atual.rotulo
}

const TIPOS_DE_TEXTO = new Set(["", "text", "search", "url", "email", "tel"])

/** Whether a focused element is a field text can be inserted into. */
export function aceitaInsercao(el: EventTarget | null): el is HTMLInputElement | HTMLTextAreaElement {
  // The panels' own controls (column filter) are not form fields.
  if (el instanceof Element && el.closest("[data-sem-insercao]")) return false
  if (el instanceof HTMLTextAreaElement) {
    return !el.readOnly && !el.disabled && !el.closest(".monaco-editor")
  }
  if (el instanceof HTMLInputElement) {
    return TIPOS_DE_TEXTO.has(el.type) && !el.readOnly && !el.disabled
  }
  return false
}

function rotuloDoCampo(el: HTMLInputElement | HTMLTextAreaElement): string {
  const porLabel = el.labels?.[0]?.textContent?.trim()
  const texto = porLabel || el.getAttribute("aria-label") || el.placeholder || el.name || el.id
  const limpo = (texto || "campo").replace(/\s+/g, " ").replace(/\s*\*$/, "")
  return limpo.length > 40 ? `${limpo.slice(0, 39)}…` : limpo
}

/** A native input/textarea as a target. Goes through the element's own value
 *  setter and an `input` event, so a React-controlled field sees the change
 *  exactly as if it had been typed. */
export function alvoDoCampo(el: HTMLInputElement | HTMLTextAreaElement): AlvoDeInsercao {
  return {
    rotulo: rotuloDoCampo(el),
    vivo: () => el.isConnected && !el.disabled,
    inserir: (texto) => {
      const valor = el.value
      let ini = valor.length
      let fim = valor.length
      try {
        ini = el.selectionStart ?? valor.length
        fim = el.selectionEnd ?? ini
      } catch { /* types without a selection: append */ }
      const novo = valor.slice(0, ini) + texto + valor.slice(fim)
      const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), "value")?.set
      if (setter) setter.call(el, novo)
      else el.value = novo
      el.dispatchEvent(new Event("input", { bubbles: true }))
      el.focus()
      const caret = ini + texto.length
      try { el.setSelectionRange(caret, caret) } catch { /* ignore */ }
    },
  }
}
