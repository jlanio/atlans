"use client"

import { useCallback, useEffect, useState } from "react"
import type { ItemDeAtencao } from "./atencao"

/**
 * "Dismiss" items from the Needs attention list — a per-browser convenience
 * (docs/specs/screen-patterns.md §5: localStorage for visitor conveniences).
 * The items are derived from live metrics, so storing a "resolved" on the
 * server would be heavy and misleading; here we only HIDE what the user has
 * already seen.
 *
 * The promise: dismissing does NOT blind. We store `chave → assinatura` (the
 * signature is the current severity, from `atencao.ts`); the item stays hidden
 * only while the signature does not change. If the problem GETS WORSE — a new
 * stuck run, one more failure, the executor's queue grows — the signature
 * changes and the alert comes back.
 *
 * On every dismissal the map is pruned to the keys present in the current read:
 * an alert that resolved itself leaves the list and its dismissal stops taking
 * space (and, if it comes back, it shows again — it is not stuck to an old
 * dismissal).
 */

const CHAVE_STORAGE = "atlans:atencao-dispensados"

type Mapa = Record<string, string>

function ler(): Mapa {
  try {
    const raw = localStorage.getItem(CHAVE_STORAGE)
    if (!raw) return {}
    const obj = JSON.parse(raw)
    return obj && typeof obj === "object" ? (obj as Mapa) : {}
  } catch {
    return {}
  }
}

function gravar(mapa: Mapa): void {
  try {
    localStorage.setItem(CHAVE_STORAGE, JSON.stringify(mapa))
  } catch {
    /* private mode / quota / storage blocked: the dismissal lasts only for this session */
  }
}

/** Prunes `mapa` to the keys present in `itens` (alerts still in effect). */
function podar(mapa: Mapa, itens: ItemDeAtencao[]): Mapa {
  const vigentes = new Set(itens.map(i => i.chave))
  const novo: Mapa = {}
  for (const chave of Object.keys(mapa)) {
    if (vigentes.has(chave)) novo[chave] = mapa[chave]
  }
  return novo
}

export interface Dispensados {
  /** The list without the dismissed items (signature still equal to the stored one). */
  ocultar: (itens: ItemDeAtencao[]) => ItemDeAtencao[]
  /** How many of the current `itens` are dismissed right now. */
  contarOcultos: (itens: ItemDeAtencao[]) => number
  /** Dispensa um item (guarda chave→assinatura, podando os resolvidos). */
  dispensar: (item: ItemDeAtencao, itens: ItemDeAtencao[]) => void
  /** Dismisses all visible `itens` at once. */
  dispensarTodos: (itens: ItemDeAtencao[]) => void
  /** Undoes all dismissals. */
  restaurar: () => void
}

export function useAtencaoDispensada(): Dispensados {
  // Starts empty (the server knows nothing of dismissals) and hydrates from
  // localStorage on the client — avoids a hydration mismatch and accessing
  // `localStorage` during SSR. A first frame shows everything; right after, the
  // dismissals are applied.
  const [mapa, setMapa] = useState<Mapa>({})
  useEffect(() => { setMapa(ler()) }, [])

  const persistir = useCallback((novo: Mapa) => {
    setMapa(novo)
    gravar(novo)
  }, [])

  const ocultar = useCallback(
    (itens: ItemDeAtencao[]) => itens.filter(i => mapa[i.chave] !== i.assinatura),
    [mapa],
  )

  const contarOcultos = useCallback(
    (itens: ItemDeAtencao[]) => itens.reduce((n, i) => (mapa[i.chave] === i.assinatura ? n + 1 : n), 0),
    [mapa],
  )

  const dispensar = useCallback((item: ItemDeAtencao, itens: ItemDeAtencao[]) => {
    persistir(podar({ ...mapa, [item.chave]: item.assinatura }, itens))
  }, [mapa, persistir])

  const dispensarTodos = useCallback((itens: ItemDeAtencao[]) => {
    const novo: Mapa = {}
    for (const i of itens) novo[i.chave] = i.assinatura
    persistir(novo)
  }, [persistir])

  const restaurar = useCallback(() => { persistir({}) }, [persistir])

  return { ocultar, contarOcultos, dispensar, dispensarTodos, restaurar }
}
