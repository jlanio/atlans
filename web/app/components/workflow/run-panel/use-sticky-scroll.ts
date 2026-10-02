import { useCallback, useEffect, useRef, useState } from "react"

const BOTTOM_TOLERANCE_PX = 40

/**
 * Auto-scroll que só acompanha quem já está no fim.
 *
 * O painel antigo chamava `scrollIntoView` a cada evento novo, sem checar a
 * posição: rolar para cima e ler qualquer coisa durante a execução era
 * impossível — a lista puxava o usuário de volta uma vez por linha.
 */
export function useStickyScroll(deps: unknown[], scrollToEnd?: () => void) {
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [stuck, setStuck] = useState(true)
  const [showJump, setShowJump] = useState(false)

  // Ref para o callback: o `onScroll` é registrado uma vez, mas o virtualizador
  // (e portanto `scrollToEnd`) muda a cada render.
  const scrollToEndRef = useRef(scrollToEnd)
  scrollToEndRef.current = scrollToEnd

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    function onScroll() {
      const node = containerRef.current
      if (!node) return
      const atBottom = node.scrollHeight - node.scrollTop - node.clientHeight <= BOTTOM_TOLERANCE_PX
      setStuck(atBottom)
      // Autoridade do botão fica aqui: com virtualização, a medição dinâmica
      // pode tirar o scroll do fim DEPOIS do efeito de auto-scroll rodar (que
      // não re-dispara num run concluído). Sem isto, o usuário ficava sem o
      // botão "↓" para voltar ao fim.
      setShowJump(!atBottom)
    }
    el.addEventListener("scroll", onScroll, { passive: true })
    return () => el.removeEventListener("scroll", onScroll)
  }, [])

  // `scrollTop = scrollHeight` em vez de `scrollIntoView`: este efeito roda a
  // cada flush do painel (a cada 120ms num run ao vivo) e o scrollIntoView
  // media a posição de um elemento no fim de uma lista de milhares de linhas
  // recém-renderizadas — layout síncrono forçado, oito vezes por segundo. O
  // ajuste também vai para um único quadro, para dois flushes seguidos não
  // pagarem o trabalho duas vezes.
  const frameRef = useRef<number | null>(null)
  useEffect(() => {
    if (!stuck) {
      setShowJump(true)
      return
    }
    if (frameRef.current != null) cancelAnimationFrame(frameRef.current)
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null
      // Virtualizado: delega ao virtualizador, cujo loop de reajuste compensa a
      // medição dinâmica (scrollTop=scrollHeight usaria a altura ESTIMADA e
      // pararia no meio). Sem virtualização, o scroll cru continua correto.
      if (scrollToEndRef.current) {
        scrollToEndRef.current()
        return
      }
      const el = containerRef.current
      if (el) el.scrollTop = el.scrollHeight
    })
    return () => {
      if (frameRef.current != null) {
        cancelAnimationFrame(frameRef.current)
        frameRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const jumpToBottom = useCallback(() => {
    setStuck(true)
    setShowJump(false)
    if (scrollToEndRef.current) {
      scrollToEndRef.current()
      return
    }
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [])

  return { containerRef, bottomRef, showJump, jumpToBottom }
}
