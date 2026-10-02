// web/app/components/workflow/utils/enquadrar.ts
//
// Quando o canvas deve se mexer para acompanhar o fluxo sendo montado.
//
// A decisão é pura de propósito. O `fitView` do React Flow é fácil de chamar e
// difícil de calibrar: chamá-lo a cada passo reenquadra o grafo INTEIRO, e o
// zoom muda junto — o que se vê não é a tela acompanhando o fluxo crescer, é a
// tela saltando de escala a cada nó. A regra de quando NÃO mexer é o que evita
// isso, e testá-la dentro de um React Flow de mentira mediria o React Flow.

export interface Caixa {
  x: number
  y: number
  width: number
  height: number
}

/**
 * Folga, em unidades do grafo, antes de considerar que o desenho saiu do
 * quadro.
 *
 * Existe porque o auto-layout reposiciona os nós a cada passo: sem ela, uma
 * variação de poucos pixels na caixa dispararia um reenquadramento novo a cada
 * desenho, que é o salto que se está tentando remover. Menor que um nó, para
 * que um nó de verdade entrando sempre conte.
 */
export const FOLGA_DO_ENQUADRAMENTO = 40

/** Quanto dura o deslocamento da câmera, em ms. */
export const DURACAO_DO_ENQUADRAMENTO = 700

/** Teto de zoom ao enquadrar o fluxo todo. */
export const ZOOM_MAXIMO_DO_ENQUADRAMENTO = 1

/**
 * O desenho novo cabe no que já estava enquadrado?
 *
 * `anterior` nulo significa que ainda não enquadramos nada — então precisa.
 *
 * A comparação é contra a ÚLTIMA caixa enquadrada, e não contra o viewport de
 * agora, e isso é decisão e não atalho: se a pessoa arrastou o canvas para
 * olhar um nó e o fluxo não cresceu, puxá-la de volta seria tirar o controle da
 * mão dela no meio da leitura. Enquanto o desenho não passar do que já foi
 * enquadrado, ninguém se mexe.
 */
export function cabeNoEnquadrado(
  nova: Caixa,
  anterior: Caixa | null,
  folga: number = FOLGA_DO_ENQUADRAMENTO,
): boolean {
  if (!anterior) return false
  return (
    nova.x >= anterior.x - folga &&
    nova.y >= anterior.y - folga &&
    nova.x + nova.width <= anterior.x + anterior.width + folga &&
    nova.y + nova.height <= anterior.y + anterior.height + folga
  )
}

/**
 * A pessoa pediu menos movimento?
 *
 * O deslocamento da câmera é animado por JS, então o `prefers-reduced-motion`
 * do CSS não o alcança — tem de ser lido aqui. Quem pediu menos movimento
 * continua sendo levado ao fluxo novo; o que some é o trajeto até lá.
 */
export function semMovimento(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}
