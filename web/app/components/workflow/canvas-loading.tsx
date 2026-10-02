"use client"

import { useEffect, useRef, useState } from "react"
import { useStore } from "@xyflow/react"
import { CAMADA_SO_LEITURA } from "./canvas-layers"

/** Espera antes de mostrar a animação: uma carga que termina antes disso não
 *  merece indicador — ele só piscaria. */
export const ATRASO_PARA_MOSTRAR_MS = 150

/** Tendo aparecido, fica pelo menos isto. Sumir logo depois de aparecer é o
 *  mesmo piscar, visto do outro lado. */
export const EXIBICAO_MINIMA_MS = 450

/** Quanto tempo a classe de revelação fica no canvas (cobre a animação de
 *  entrada do grafo, em globals.css). */
const DURACAO_DA_REVELACAO_MS = 700

/**
 * Traduz "o canvas está carregando" em "a animação está visível", com as duas
 * folgas acima. Se a carga volta a ficar pendente enquanto a animação ainda
 * está no ar (troca rápida de workflow), ela simplesmente continua.
 */
export function useCarregamentoVisivel(carregando: boolean): boolean {
  const [visivel, setVisivel] = useState(false)
  const mostradoEm = useRef(0)

  useEffect(() => {
    if (carregando) {
      if (visivel) return
      const timer = setTimeout(() => {
        mostradoEm.current = Date.now()
        setVisivel(true)
      }, ATRASO_PARA_MOSTRAR_MS)
      return () => clearTimeout(timer)
    }
    if (!visivel) return
    const restante = Math.max(0, EXIBICAO_MINIMA_MS - (Date.now() - mostradoEm.current))
    const timer = setTimeout(() => setVisivel(false), restante)
    return () => clearTimeout(timer)
  }, [carregando, visivel])

  return visivel
}

interface Props {
  /** A rota tem id e o grafo ainda não foi hidratado no canvas. */
  carregando: boolean
}

/**
 * O que o canvas mostra enquanto o workflow não chega.
 *
 * Antes, nada: a página abria com o canvas vazio, a trilha dizendo "Sem nome"
 * e o botão de adicionar nó pulsando como se o workflow fosse novo — durante a
 * busca, a tela afirmava coisas que não eram verdade.
 *
 * Um mini fluxo de três nós no centro: um pacote na cor da marca percorre as
 * ligações e cada nó acende ao ser alcançado. É um pedaço do editor, não um
 * spinner por cima dele. Os estilos moram em globals.css ("Canvas em espera").
 *
 * Também marca o contêiner `.react-flow` com `rf-carregando` — é o que esmaece
 * as colunas de botões sem que cada uma precise saber da carga — e, ao
 * terminar, com `rf-revelando`, que faz o grafo entrar em fade em vez de corte.
 * Mesmo mecanismo do CanvasViewLayer para o realce de caminho.
 *
 * Renderizar como filho de `<ReactFlow>`.
 */
export default function CanvasLoading({ carregando }: Props) {
  const domNode = useStore(s => s.domNode)
  const visivel = useCarregamentoVisivel(carregando)
  const estavaCarregando = useRef(false)

  useEffect(() => {
    if (!domNode) return
    domNode.classList.toggle("rf-carregando", carregando)

    if (carregando) {
      estavaCarregando.current = true
      return
    }
    // Só revela o que de fato esperou: abrir a tela de criação, ou trocar de
    // workflow com o grafo já em mãos, não é chegada de nada.
    if (!estavaCarregando.current) return
    estavaCarregando.current = false
    domNode.classList.add("rf-revelando")
    const timer = setTimeout(() => domNode.classList.remove("rf-revelando"), DURACAO_DA_REVELACAO_MS)
    return () => {
      clearTimeout(timer)
      domNode.classList.remove("rf-revelando")
    }
  }, [domNode, carregando])

  if (!visivel) return null

  return (
    <div
      role="status"
      aria-live="polite"
      data-role="canvas-loading"
      className={`${CAMADA_SO_LEITURA} inset-0 flex items-center justify-center`}
    >
      <div className="canvas-carregando -mt-6 flex flex-col items-center gap-3.5">
        <svg viewBox="0 0 232 64" width="232" height="64" aria-hidden="true">
          <path className="lig" d="M52 32H88" />
          <path className="lig" d="M144 32H180" />
          <rect className="no" x="8" y="20" width="44" height="24" rx="6" />
          <rect className="no" x="94" y="20" width="44" height="24" rx="6" />
          <rect className="no" x="180" y="20" width="44" height="24" rx="6" />
          <circle className="pk" r="3.5">
            <animateMotion dur="1.8s" repeatCount="indefinite" path="M30 32H202" />
          </circle>
        </svg>
        <span className="text-xs text-muted-foreground">Carregando workflow…</span>
      </div>
    </div>
  )
}
