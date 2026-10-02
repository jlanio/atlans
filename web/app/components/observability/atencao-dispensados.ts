"use client"

import { useCallback, useEffect, useState } from "react"
import type { ItemDeAtencao } from "./atencao"

/**
 * "Dispensar" itens da lista Precisa de atenção — uma conveniência por
 * navegador (docs/specs/padrao-telas.md §5: localStorage para conveniências do
 * visitante). Os itens são derivados de métricas ao vivo, então guardar um
 * "resolvido" no servidor seria pesado e enganoso; aqui só ESCONDEMOS o que o
 * usuário já viu.
 *
 * A promessa: dispensar NÃO cega. Guardamos `chave → assinatura` (a assinatura é
 * a gravidade do momento, de `atencao.ts`); o item fica oculto apenas enquanto a
 * assinatura não muda. Se o problema PIORA — nova execução presa, mais uma
 * falha, a fila do executor cresce — a assinatura muda e o alerta volta.
 *
 * O mapa é podado para as chaves presentes na leitura atual a cada dispensa:
 * um alerta que se resolveu some da lista e sua dispensa deixa de ocupar espaço
 * (e, se voltar, aparece de novo — não fica preso a uma dispensa antiga).
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
    /* modo privado / cota / storage bloqueado: dispensa vira só desta sessão */
  }
}

/** Poda `mapa` para as chaves presentes em `itens` (alertas ainda vigentes). */
function podar(mapa: Mapa, itens: ItemDeAtencao[]): Mapa {
  const vigentes = new Set(itens.map(i => i.chave))
  const novo: Mapa = {}
  for (const chave of Object.keys(mapa)) {
    if (vigentes.has(chave)) novo[chave] = mapa[chave]
  }
  return novo
}

export interface Dispensados {
  /** A lista sem os itens dispensados (assinatura ainda igual à guardada). */
  ocultar: (itens: ItemDeAtencao[]) => ItemDeAtencao[]
  /** Quantos dos `itens` atuais estão dispensados agora. */
  contarOcultos: (itens: ItemDeAtencao[]) => number
  /** Dispensa um item (guarda chave→assinatura, podando os resolvidos). */
  dispensar: (item: ItemDeAtencao, itens: ItemDeAtencao[]) => void
  /** Dispensa todos os `itens` visíveis de uma vez. */
  dispensarTodos: (itens: ItemDeAtencao[]) => void
  /** Desfaz todas as dispensas. */
  restaurar: () => void
}

export function useAtencaoDispensada(): Dispensados {
  // Começa vazio (o servidor não sabe de dispensas) e hidrata do localStorage
  // no cliente — evita divergência de hidratação e o acesso a `localStorage` no
  // SSR. Um quadro inicial mostra tudo; logo em seguida aplica as dispensas.
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
