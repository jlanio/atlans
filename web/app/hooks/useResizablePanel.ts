"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export interface ResizablePanelOptions {
  /** Chave em localStorage. Sem ela a largura não sobrevive ao fechar o painel. */
  storageKey?: string
  defaultWidth?: number
  /**
   * Fração da janela que o painel ocupa ao abrir (0–1), quando isso for mais do
   * que `defaultWidth` — é o que faz "abrir com metade da tela" continuar
   * valendo tanto num notebook quanto num monitor grande. Só governa a
   * abertura: uma largura já escolhida pelo usuário vence, e arrastar para
   * menos que a fração é permitido.
   */
  defaultRatio?: number
  minWidth?: number
  maxWidth?: number
  /** Borda em que o painel está ancorado — define para que lado o arraste cresce. */
  side?: "left" | "right"
  /**
   * Falso não desliga só o arraste: o hook para de ler o storage e de ouvir o
   * `resize` da janela. Quem chama sempre (todo `SheetContent`, mesmo os que
   * não redimensionam) não paga por isso.
   */
  enabled?: boolean
}

/** Sobra mínima entre o painel e a borda oposta da janela. */
const VIEWPORT_MARGIN = 48
const KEY_STEP = 16
const KEY_STEP_LARGE = 64

/**
 * Largura arrastável para um painel ancorado numa borda da janela.
 *
 * O arraste usa pointer capture em vez de listeners em `window`: o ponteiro
 * continua entregando eventos ao handle mesmo depois de sair dele, e soltar
 * fora da janela ainda dispara `pointerup`/`pointercancel` — com listeners
 * globais o painel ficaria preso ao cursor.
 */
export function useResizablePanel({
  storageKey,
  defaultWidth = 640,
  defaultRatio,
  minWidth = 360,
  maxWidth = 1280,
  side = "right",
  enabled = true,
}: ResizablePanelOptions = {}) {
  const [width, setWidth] = useState(defaultWidth)
  const [isResizing, setIsResizing] = useState(false)

  // `width` em ref para que os handlers leiam o valor corrente sem entrar nas
  // dependências (um `onPointerMove` recriado a cada pixel arrastado seria
  // trocado no meio do gesto).
  const widthRef = useRef(defaultWidth)
  // A largura que o usuário escolheu, antes do clamp da viewport: estreitar a
  // janela e alargá-la de volta devolve a largura pedida em vez do resto.
  const preferredRef = useRef(defaultWidth)
  const dragRef = useRef<{ startX: number; startWidth: number } | null>(null)

  const clamp = useCallback((w: number) => {
    const ceiling = Math.max(minWidth, Math.min(maxWidth, window.innerWidth - VIEWPORT_MARGIN))
    return Math.round(Math.min(Math.max(w, minWidth), ceiling))
  }, [minWidth, maxWidth])

  const apply = useCallback((w: number) => {
    const next = clamp(w)
    widthRef.current = next
    setWidth(next)
  }, [clamp])

  const persist = useCallback(() => {
    preferredRef.current = widthRef.current
    if (!storageKey) return
    // localStorage lança em modo privado/quota cheia — a largura é preferência,
    // não vale derrubar o painel por ela.
    try {
      window.localStorage.setItem(storageKey, String(widthRef.current))
    } catch { /* preferência descartável */ }
  }, [storageKey])

  // Depende da viewport, então só existe no cliente.
  const resolveDefault = useCallback(() => {
    const porFracao = defaultRatio ? window.innerWidth * defaultRatio : 0
    return Math.max(defaultWidth, porFracao)
  }, [defaultWidth, defaultRatio])

  // Largura de abertura, no mount (não no render: `window` não existe no
  // servidor). O que o usuário arrastou antes vence a fração — ele já disse o
  // que queria.
  useEffect(() => {
    if (!enabled) return
    let saved = NaN
    if (storageKey) {
      try {
        saved = Number(window.localStorage.getItem(storageKey))
      } catch { /* sem storage legível: cai no default */ }
    }
    const inicial = Number.isFinite(saved) && saved > 0 ? saved : resolveDefault()
    preferredRef.current = inicial
    apply(inicial)
  }, [enabled, storageKey, apply, resolveDefault])

  useEffect(() => {
    if (!enabled) return
    function onWindowResize() {
      apply(preferredRef.current)
    }
    window.addEventListener("resize", onWindowResize)
    return () => window.removeEventListener("resize", onWindowResize)
  }, [enabled, apply])

  // Durante o arraste o cursor e a supressão de seleção precisam valer para a
  // página toda: o ponteiro passa por cima de texto e de outros elementos.
  useEffect(() => {
    if (!isResizing) return
    const { body } = document
    const prevCursor = body.style.cursor
    const prevSelect = body.style.userSelect
    body.style.cursor = "col-resize"
    body.style.userSelect = "none"
    return () => {
      body.style.cursor = prevCursor
      body.style.userSelect = prevSelect
    }
  }, [isResizing])

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLElement>) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.current = { startX: e.clientX, startWidth: widthRef.current }
    setIsResizing(true)
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current
    if (!drag) return
    // Delta em vez de "largura = borda até o cursor": pegar o handle pelo meio
    // não teleporta a borda para debaixo do cursor no primeiro movimento.
    const delta = side === "right" ? drag.startX - e.clientX : e.clientX - drag.startX
    apply(drag.startWidth + delta)
  }, [apply, side])

  const endDrag = useCallback((e: React.PointerEvent<HTMLElement>) => {
    if (!dragRef.current) return
    dragRef.current = null
    setIsResizing(false)
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId)
    }
    persist()
  }, [persist])

  const onKeyDown = useCallback((e: React.KeyboardEvent<HTMLElement>) => {
    const step = e.shiftKey ? KEY_STEP_LARGE : KEY_STEP
    const grow = side === "right" ? -1 : 1
    let next: number
    if (e.key === "ArrowLeft") next = widthRef.current + step * grow
    else if (e.key === "ArrowRight") next = widthRef.current - step * grow
    else if (e.key === "Home") next = minWidth
    else if (e.key === "End") next = maxWidth
    else return
    e.preventDefault()
    // O handle vive dentro de um Dialog do Radix, que escuta setas.
    e.stopPropagation()
    apply(next)
    persist()
  }, [apply, persist, side, minWidth, maxWidth])

  const onDoubleClick = useCallback(() => {
    apply(resolveDefault())
    persist()
  }, [apply, persist, resolveDefault])

  return {
    width,
    isResizing,
    /** Espalhe no elemento do handle. */
    resizeHandleProps: {
      role: "separator",
      "aria-orientation": "vertical",
      "aria-label": "Redimensionar painel",
      "aria-valuenow": width,
      "aria-valuemin": minWidth,
      "aria-valuemax": maxWidth,
      tabIndex: 0,
      title: "Arraste para redimensionar · duplo clique para restaurar",
      onPointerDown,
      onPointerMove,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
      onKeyDown,
      onDoubleClick,
    } as const,
  }
}
