// web/app/components/workflow/utils/aplicar-proposta.ts
//
// The bridge between the definition proposed in the panel and the canvas.
//
// It exists for one reason only, and it is the one that ruins someone's work:
// the proposed definition **has no position**. `buildNodes` falls back to the
// default `{x: 180 * indice, y: 0}` (`build-canvas.ts:81`) — a horizontal row.
// Dropping that onto a twelve-node workflow would erase the layout the person
// arranged by hand, and "undo" does not bring back an arrangement built over an
// afternoon.
//
// So the rule is: whoever survived stays exactly where it was; only what is new
// gets a position, from the same `computeAutoLayout` the canvas's arrange button
// already uses. Whatever the layout places on top of a preserved card moves down
// until it fits.
//
// Pure on purpose, for two reasons. The first is being able to test position
// preservation without mounting a React Flow. The second is that the panel's
// card shows the count (`n novos · n alterados · n removidos`) BEFORE the
// click: by calling this same function, the number the person reads is
// literally derived from what the button will apply, and not from a second
// count that may diverge from it.
import { Edge } from "@xyflow/react"

import { INodeContext } from "@/context/useFlowContext"
import { INodesAPI } from "@/service/types"
import { computeAutoLayout } from "./auto-layout"
import { buildEdges, buildNodes, CanvasDefinition } from "./build-canvas"
import { measuredHeight, measuredWidth } from "./node-metrics"

/** Minimum gap between a new card and a preserved card, when resolving overlaps. */
const MARGIN = 24

/** Same grid as the auto-layout, so pushed cards stay aligned. */
const snap = (v: number) => Math.round(v / 8) * 8

export interface ProposalSummary {
  /** Proposal nodes whose `id` does not exist on the canvas. */
  novos: number
  /** Nodes present on both sides that changed type, alias or property. */
  alterados: number
  /** Canvas nodes the proposal does not have — they disappear on apply. */
  removidos: number
}

export interface ProposalResult {
  nodes: INodeContext[]
  edges: Edge[]
  resumo: ProposalSummary
  /**
   * False when the catalog has not arrived yet. `buildNodes` without a catalog
   * returns an empty list — applying at that moment would EMPTY the canvas,
   * silently. The caller disables the button based on this.
   */
  catalogoPronto: boolean
  /** Ids of the nodes that were not on the canvas before this apply. */
  idsNovos: Set<string>
  /** Ids of the edges that touch at least one new node. */
  idsArestasNovas: Set<string>
}

interface Caixa {
  x: number
  y: number
  w: number
  h: number
}

/**
 * Builds the proposal's canvas preserving the position of whatever was already there.
 *
 * @param definicao  the validated definition that came in the `proposta` frame
 * @param nodesAPI   the node catalog (`useWorkflowCatalogStore`)
 * @param atuais     the nodes currently on the canvas
 */
export function aplicarProposta(
  definicao: CanvasDefinition | undefined,
  nodesAPI: INodesAPI[] | undefined,
  atuais: INodeContext[],
): ProposalResult {
  const proposed = buildNodes(definicao, nodesAPI)
  const edges = buildEdges(definicao, proposed)

  const pedidos = definicao?.nodes?.length ?? 0
  const onScreen = new Map(atuais.map(no => [no.id, no]))

  const preservados: INodeContext[] = []
  const novos: INodeContext[] = []

  for (const proposto of proposed) {
    const atual = onScreen.get(proposto.id)
    if (atual) {
      // The position from there, not the layout's: it is the layout the person arranged.
      preservados.push({ ...proposto, position: { ...atual.position } })
    } else {
      novos.push(proposto)
    }
  }

  const placed = placeNewNodes(novos, preservados, edges, onScreen)
  const finalNodes = new Map([...preservados, ...placed].map(no => [no.id, no]))

  const idsNovos = new Set(novos.map(no => no.id))

  return {
    // Definition order, so the canvas does not shuffle on every apply.
    nodes: proposed.map(p => finalNodes.get(p.id) ?? p),
    edges,
    resumo: contar(proposed, preservados, atuais, onScreen),
    catalogoPronto: pedidos === 0 || proposed.length > 0,
    // What arrived NOW. Feeds the entry animation: without the list, the canvas
    // would have to animate everything on every draw — and a workflow that
    // flashes entirely on each added node is the opposite of watching the
    // workflow grow.
    idsNovos,
    // The edges that touch a new node. An edge between two nodes that were
    // already there is not new and should not redraw.
    idsArestasNovas: new Set(
      edges.filter(e => idsNovos.has(e.source) || idsNovos.has(e.target)).map(e => e.id),
    ),
  }
}

/**
 * Gives new nodes a position: the one from `computeAutoLayout` over the whole
 * graph, pushed down while it sits on top of an already existing card.
 *
 * The layout runs over ALL nodes (preserved ones included) because a new node on
 * its own would have nowhere to get the workflow's direction from — it is the
 * edge linking it to what already exists that says which side it comes in on.
 */
function placeNewNodes(
  novos: INodeContext[],
  preservados: INodeContext[],
  edges: Edge[],
  onScreen: Map<string, INodeContext>,
): INodeContext[] {
  if (!novos.length) return []

  const layout = computeAutoLayout([...preservados, ...novos], edges)

  // Preserved cards measured by what is ON SCREEN (React Flow has already
  // measured them); the new card, by the per-port calculation — it does not
  // exist yet.
  const occupied: Caixa[] = preservados.map(no => boxOf(no, onScreen.get(no.id)))

  return novos.map(novo => {
    const alvo = layout.get(novo.id) ?? novo.position
    const caixa = boxOf({ ...novo, position: alvo })

    // Each push moves past the bottom of every box that was in the way, so the
    // loop always advances and ends after at most one round per box.
    for (let volta = 0; volta <= occupied.length; volta++) {
      const colliding = occupied.filter(o => colide(caixa, o))
      if (!colliding.length) break
      caixa.y = snap(Math.max(...colliding.map(o => o.y + o.h)) + MARGIN)
    }

    occupied.push(caixa)
    return { ...novo, position: { x: caixa.x, y: caixa.y } }
  })
}

/** Card box. `medida` is the node on screen, when there is one: it was actually measured. */
function boxOf(node: INodeContext, medida?: INodeContext): Caixa {
  const referencia = medida ?? node
  return {
    x: node.position.x,
    y: node.position.y,
    w: measuredWidth(referencia),
    h: measuredHeight(referencia),
  }
}

/** Overlap of two boxes, with the gap counted on both sides. */
function colide(a: Caixa, b: Caixa): boolean {
  return (
    a.x < b.x + b.w + MARGIN &&
    a.x + a.w + MARGIN > b.x &&
    a.y < b.y + b.h + MARGIN &&
    a.y + a.h + MARGIN > b.y
  )
}

function contar(
  proposed: INodeContext[],
  preservados: INodeContext[],
  atuais: INodeContext[],
  onScreen: Map<string, INodeContext>,
): ProposalSummary {
  const alterados = preservados.filter(no => mudou(no, onScreen.get(no.id))).length
  const proposedIds = new Set(proposed.map(n => n.id))

  return {
    novos: proposed.length - preservados.length,
    alterados,
    removidos: atuais.filter(no => !proposedIds.has(no.id)).length,
  }
}

/**
 * Did the node really change?
 *
 * Compares only what the definition carries — source node, alias and properties.
 * Position is left out on purpose: it is precisely what this function protects,
 * and announcing "changed" because of it would make the count talk about a
 * change the person will not recognize as their own.
 */
function mudou(proposto: INodeContext, atual: INodeContext | undefined): boolean {
  if (!atual) return false
  if (proposto.data?.name !== atual.data?.name) return true
  if ((proposto.data?.alias ?? "") !== (atual.data?.alias ?? "")) return true
  return !sameProperties(proposto.data?.properties, atual.data?.properties)
}

/**
 * Compares by KEY, and not by the JSON of both whole objects: key order depends
 * on who built the node (the editor builds it from the catalog, the drawer
 * copies the whole catalog object), and a different order is not a change.
 */
function sameProperties(a: unknown, b: unknown): boolean {
  const esquerda = (a ?? {}) as Record<string, unknown>
  const direita = (b ?? {}) as Record<string, unknown>
  const chaves = new Set([...Object.keys(esquerda), ...Object.keys(direita)])

  for (const chave of chaves) {
    if (JSON.stringify(esquerda[chave]) !== JSON.stringify(direita[chave])) return false
  }
  return true
}
