// web/app/components/workflow/utils/aplicar-proposta.ts
//
// A ponte entre a definição proposta no painel e o canvas.
//
// Ela existe por uma razão só, e é a que estraga o trabalho de alguém: a
// definição proposta **não tem posição**. `buildNodes` cai no default
// `{x: 180 * indice, y: 0}` (`build-canvas.ts:81`) — uma fila horizontal. Jogar
// isso num fluxo de doze nós apagaria o desenho que a pessoa arrumou à mão, e
// "desfazer" não devolve um arranjo feito ao longo de uma tarde.
//
// Então a regra é: quem sobreviveu fica exatamente onde estava; só o que é novo
// ganha posição, pelo mesmo `computeAutoLayout` que o botão de organizar do
// canvas já usa. O que o layout colocar em cima de um card preservado desce até
// caber.
//
// Pura de propósito, e por dois motivos. O primeiro é poder testar a
// preservação de posição sem montar um React Flow. O segundo é que o cartão do
// painel mostra a contagem (`n novos · n alterados · n removidos`) ANTES do
// clique: chamando esta mesma função, o número que a pessoa lê é literalmente
// derivado do que o botão vai aplicar, e não de uma segunda contagem que pode
// divergir dele.
import { Edge } from "@xyflow/react"

import { INodeContext } from "@/context/useFlowContext"
import { INodesAPI } from "@/service/types"
import { computeAutoLayout } from "./auto-layout"
import { buildEdges, buildNodes, CanvasDefinition } from "./build-canvas"
import { measuredHeight, measuredWidth } from "./node-metrics"

/** Folga mínima entre um card novo e um card preservado, na resolução de choque. */
const FOLGA = 24

/** Mesma grade do auto-layout, para os cards empurrados continuarem alinhados. */
const snap = (v: number) => Math.round(v / 8) * 8

export interface ResumoDaProposta {
  /** Nós da proposta cujo `id` não existe no canvas. */
  novos: number
  /** Nós que existem nos dois lados e mudaram de tipo, apelido ou propriedade. */
  alterados: number
  /** Nós do canvas que a proposta não tem — somem ao aplicar. */
  removidos: number
}

export interface ResultadoDaProposta {
  nodes: INodeContext[]
  edges: Edge[]
  resumo: ResumoDaProposta
  /**
   * Falso quando o catálogo ainda não chegou. `buildNodes` sem catálogo devolve
   * lista vazia — aplicar nesse instante ESVAZIARIA o canvas, em silêncio. Quem
   * chama desliga o botão por aqui.
   */
  catalogoPronto: boolean
  /** Ids dos nós que não estavam no canvas antes desta aplicação. */
  idsNovos: Set<string>
  /** Ids das arestas que tocam pelo menos um nó novo. */
  idsArestasNovas: Set<string>
}

interface Caixa {
  x: number
  y: number
  w: number
  h: number
}

/**
 * Monta o canvas da proposta preservando a posição de quem já estava lá.
 *
 * @param definicao  a definição validada que veio no quadro `proposta`
 * @param nodesAPI   o catálogo de nós (`useWorkflowCatalogStore`)
 * @param atuais     os nós que estão no canvas neste momento
 */
export function aplicarProposta(
  definicao: CanvasDefinition | undefined,
  nodesAPI: INodesAPI[] | undefined,
  atuais: INodeContext[],
): ResultadoDaProposta {
  const propostos = buildNodes(definicao, nodesAPI)
  const edges = buildEdges(definicao, propostos)

  const pedidos = definicao?.nodes?.length ?? 0
  const naTela = new Map(atuais.map(no => [no.id, no]))

  const preservados: INodeContext[] = []
  const novos: INodeContext[] = []

  for (const proposto of propostos) {
    const atual = naTela.get(proposto.id)
    if (atual) {
      // A posição de lá, e não a do layout: é o desenho que a pessoa arrumou.
      preservados.push({ ...proposto, position: { ...atual.position } })
    } else {
      novos.push(proposto)
    }
  }

  const colocados = posicionarOsNovos(novos, preservados, edges, naTela)
  const finais = new Map([...preservados, ...colocados].map(no => [no.id, no]))

  const idsNovos = new Set(novos.map(no => no.id))

  return {
    // Ordem da definição, para o canvas não embaralhar a cada aplicação.
    nodes: propostos.map(p => finais.get(p.id) ?? p),
    edges,
    resumo: contar(propostos, preservados, atuais, naTela),
    catalogoPronto: pedidos === 0 || propostos.length > 0,
    // Quem chegou AGORA. Serve à animação de entrada: sem a lista, o canvas
    // teria de animar tudo a cada desenho — e um fluxo que pisca inteiro a cada
    // nó acrescentado é o oposto de ver o fluxo crescer.
    idsNovos,
    // As arestas que tocam um nó novo. Uma aresta entre dois nós que já
    // estavam ali não é novidade e não deve se redesenhar.
    idsArestasNovas: new Set(
      edges.filter(e => idsNovos.has(e.source) || idsNovos.has(e.target)).map(e => e.id),
    ),
  }
}

/**
 * Dá posição aos nós novos: a do `computeAutoLayout` sobre o grafo inteiro,
 * empurrada para baixo enquanto estiver em cima de um card que já existe.
 *
 * O layout roda sobre TODOS os nós (preservados inclusive) porque um nó novo
 * sozinho não teria de onde tirar o sentido do fluxo — é a aresta que o liga ao
 * que já existe que diz de que lado ele entra.
 */
function posicionarOsNovos(
  novos: INodeContext[],
  preservados: INodeContext[],
  edges: Edge[],
  naTela: Map<string, INodeContext>,
): INodeContext[] {
  if (!novos.length) return []

  const layout = computeAutoLayout([...preservados, ...novos], edges)

  // Os cards preservados medidos pelo que está NA TELA (o React Flow já os
  // mediu); o card novo, pelo cálculo por portas — ele ainda não existe.
  const ocupadas: Caixa[] = preservados.map(no => caixaDe(no, naTela.get(no.id)))

  return novos.map(novo => {
    const alvo = layout.get(novo.id) ?? novo.position
    const caixa = caixaDe({ ...novo, position: alvo })

    // Cada empurrão desce para além do fundo de todas as caixas que barravam,
    // então o laço avança sempre e termina em no máximo uma volta por caixa.
    for (let volta = 0; volta <= ocupadas.length; volta++) {
      const batendo = ocupadas.filter(o => colide(caixa, o))
      if (!batendo.length) break
      caixa.y = snap(Math.max(...batendo.map(o => o.y + o.h)) + FOLGA)
    }

    ocupadas.push(caixa)
    return { ...novo, position: { x: caixa.x, y: caixa.y } }
  })
}

/** Caixa do card. `medida` é o nó que está na tela, quando houver: ele foi medido de verdade. */
function caixaDe(node: INodeContext, medida?: INodeContext): Caixa {
  const referencia = medida ?? node
  return {
    x: node.position.x,
    y: node.position.y,
    w: measuredWidth(referencia),
    h: measuredHeight(referencia),
  }
}

/** Sobreposição de duas caixas, com a folga contada dos dois lados. */
function colide(a: Caixa, b: Caixa): boolean {
  return (
    a.x < b.x + b.w + FOLGA &&
    a.x + a.w + FOLGA > b.x &&
    a.y < b.y + b.h + FOLGA &&
    a.y + a.h + FOLGA > b.y
  )
}

function contar(
  propostos: INodeContext[],
  preservados: INodeContext[],
  atuais: INodeContext[],
  naTela: Map<string, INodeContext>,
): ResumoDaProposta {
  const alterados = preservados.filter(no => mudou(no, naTela.get(no.id))).length
  const idsPropostos = new Set(propostos.map(n => n.id))

  return {
    novos: propostos.length - preservados.length,
    alterados,
    removidos: atuais.filter(no => !idsPropostos.has(no.id)).length,
  }
}

/**
 * O nó mudou de verdade?
 *
 * Compara só o que a definição carrega — nó de origem, apelido e propriedades.
 * Posição fica de fora de propósito: é justamente o que esta função protege, e
 * anunciar "alterado" por causa dela faria a contagem falar de uma mudança que
 * a pessoa não vai reconhecer como sua.
 */
function mudou(proposto: INodeContext, atual: INodeContext | undefined): boolean {
  if (!atual) return false
  if (proposto.data?.name !== atual.data?.name) return true
  if ((proposto.data?.alias ?? "") !== (atual.data?.alias ?? "")) return true
  return !mesmasPropriedades(proposto.data?.properties, atual.data?.properties)
}

/**
 * Compara por CHAVE, e não pelo JSON dos dois objetos inteiros: a ordem das
 * chaves depende de quem montou o nó (o editor monta pelo catálogo, o drawer
 * copia o objeto do catálogo inteiro), e ordem diferente não é mudança.
 */
function mesmasPropriedades(a: unknown, b: unknown): boolean {
  const esquerda = (a ?? {}) as Record<string, unknown>
  const direita = (b ?? {}) as Record<string, unknown>
  const chaves = new Set([...Object.keys(esquerda), ...Object.keys(direita)])

  for (const chave of chaves) {
    if (JSON.stringify(esquerda[chave]) !== JSON.stringify(direita[chave])) return false
  }
  return true
}
