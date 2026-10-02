// desktop/src/renderer/lib/snapshot.ts
//
// O snapshot do executor chega por CONTEXTO, e não por prop.
//
// Ele é substituído por um objeto novo a cada segundo. Como prop, obrigava
// GeoSync e Ajustes — que ficam MONTADAS atrás de `hidden` para não perder
// edição não salva — a re-renderizar a árvore inteira a 1 Hz: dez cartões, três
// radiogroups e o QuadroDoModo redesenhados para atualizar quatro números que
// vivem num canto da tela. O app queimava CPU só por estar aberto e ocioso.
//
// Pelo contexto, o `memo` das duas telas segura o tick e só quem de fato lê o
// snapshot re-renderiza: a Situação do GeoSync, o Disco dos Ajustes e a barra de
// salvar.
import { createContext, useContext } from 'react'
import type { Snapshot } from '../../shared/events.js'

export const ContextoSnapshot = createContext<Snapshot | null>(null)

/** Último snapshot do executor, ou `null` com ele parado. */
export function useSnapshot(): Snapshot | null {
  return useContext(ContextoSnapshot)
}
