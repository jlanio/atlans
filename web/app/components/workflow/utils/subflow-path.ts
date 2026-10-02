// web/app/components/workflow/utils/subflow-path.ts
//
// Endereço de um nó que executou DENTRO de um sub-fluxo.
//
// O executor republica os eventos do filho no canal do pai prefixando o id com
// o nó SubWorkflow que o chamou (`_SubWorkflowEventPublisher`, em
// flow/nodes/control/sub_workflow.py). Numa cadeia A→B→C isso se acumula: um nó
// `X` dentro de C chega ao canvas de A como `sA::sB::X`.
//
// O meta `subworkflow_parent_node` NÃO serve para descer mais de um nível: cada
// nível o SOBRESCREVE ao republicar, então ele sempre aponta para o nó
// SubWorkflow do canvas raiz. Quem carrega o caminho inteiro é o próprio id — e
// é por isso que a navegação em profundidade se resolve aqui, e não lendo o
// meta. Ids de nó são UUIDs do canvas, então `::` nunca colide com o conteúdo.

export const SEPARADOR = "::"

/** Segmentos do endereço: os nós SubWorkflow atravessados + o nó em si. */
export function segmentosDoRunNodeId(runNodeId: string): string[] {
  return runNodeId.split(SEPARADOR).filter(Boolean)
}

/**
 * Id do nó dentro do canvas em que ele de fato vive.
 *
 * É este id — e não o endereço completo — que casa com a definition do
 * sub-fluxo carregada do backend.
 */
export function idLocal(runNodeId: string): string {
  const segmentos = segmentosDoRunNodeId(runNodeId)
  return segmentos[segmentos.length - 1] ?? runNodeId
}

/**
 * Nós SubWorkflow atravessados até chegar nele. Vazio para um nó do próprio
 * fluxo aberto — é o teste de "isto veio de dentro de um sub-fluxo?".
 */
export function caminhoDeChamada(runNodeId: string): string[] {
  return segmentosDoRunNodeId(runNodeId).slice(0, -1)
}

/**
 * O nó está DIRETAMENTE dentro do nível descrito por `caminho`?
 *
 * Estrito de propósito: um nó de um sub-fluxo mais profundo compartilha o
 * prefixo, mas não pertence a este canvas — pintá-lo aqui atribuiria a um nó do
 * grafo aberto o estado de outro, com o mesmo id local por coincidência.
 */
export function pertenceAoNivel(runNodeId: string, caminho: string[]): boolean {
  const chamada = caminhoDeChamada(runNodeId)
  return (
    chamada.length === caminho.length &&
    chamada.every((segmento, i) => segmento === caminho[i])
  )
}
