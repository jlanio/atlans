import { INodePortAPI, INodeOutputField } from "@/service/types"
import { saidasDoNo } from "./node-ports"

/**
 * Regras de resolução das chaves de uma aresta.
 *
 * Vivem aqui porque duas telas criam conexões — arrastar de um handle
 * (`handleConnectNodes` no canvas) e o botão "+" do handle, que abre o drawer e
 * já cria a aresta junto com o nó. A segunda nascia sem `from_key`, e no
 * executor isso cai em `inputs.update(parent_outputs)`: o nó filho recebe TODAS
 * as saídas do pai espalhadas, em vez da porta que o usuário escolheu.
 */

/**
 * Candidatos a `from_key` de um nó: os campos de saída da instância.
 *
 * `saidasDoNo` resolve a fonte: os campos do catálogo (`saidas`) ou, no
 * Script Python, as variáveis de `output_vars` — oferecer o "result" do
 * catálogo criava uma aresta com `from_key` que o executor não acha no
 * resultado. Ramos (`true`/`false`) nunca aparecem: roteiam a execução e não
 * são campos.
 */
export function getCandidateKeys(nodeData?: {
  saidas?: INodeOutputField[]
  dynamic_output?: boolean
  properties?: Record<string, unknown>
}): INodePortAPI[] {
  const candidates: INodePortAPI[] = []
  const seen = new Set<string>()
  for (const field of saidasDoNo(nodeData)) {
    if (!field?.name || seen.has(field.name)) continue
    seen.add(field.name)
    candidates.push(field)
  }
  return candidates
}

/**
 * `from_key` de uma conexão cujo handle de origem já é conhecido.
 *
 * Retorna `undefined` quando a escolha é ambígua — nesse caso o chamador deve
 * abrir o seletor em vez de adivinhar.
 */
export function resolveFromKey(
  sourceHandle: string | null | undefined,
  candidateKeys: INodePortAPI[],
): string | undefined {
  // Handle que é porta de dado: ele próprio é a chave.
  if (sourceHandle && candidateKeys.some(f => f.name === sourceHandle)) {
    return sourceHandle
  }
  // Candidato único: não há o que escolher.
  if (candidateKeys.length === 1) {
    return candidateKeys[0]?.name
  }
  return undefined
}


/**
 * `to_key` de uma conexão cujo handle de destino já é conhecido.
 *
 * Só preenche quando o destino declara MÚLTIPLOS inputs nomeados (ex.:
 * OverlapPercentage/AttributeJoin layerA/layerB) — com um input só, o executor
 * resolve sozinho e gravar `to_key` seria ruído. Sem o preenchimento, o
 * executor cai em `inputs[from_key]` em vez de `inputs[to_key]` e mapeia
 * errado as portas de entrada — e a sugestão de colunas POR PORTA
 * (`colunas-conhecidas` indexa por `to_key || from_key`) fica vazia.
 *
 * Puro e aqui, e não no canvas: o botão "+" do handle também cria aresta
 * (drawer) e nascia sem `to_key` — a mesma história do `from_key` que este
 * arquivo existe para impedir.
 */
export function resolveToKey(
  targetHandle: string | null | undefined,
  declaredInputs: unknown,
): string | undefined {
  if (!targetHandle) return undefined
  const inputs = (declaredInputs ?? []) as INodePortAPI[]
  if (inputs.length > 1 && inputs.some(p => p.name === targetHandle)) {
    return targetHandle
  }
  return undefined
}

/**
 * Porta de entrada padrão para uma aresta criada SEM escolha explícita de
 * destino — o botão "+" cria nó e aresta de uma vez, sem ninguém soltar a
 * linha sobre um handle.
 *
 * Mesma regra do `resolveToKey`: só há o que escolher quando o destino declara
 * mais de uma porta; aí vale a primeira, como o `from_key` já cai em
 * `candidatos[0]` no mesmo fluxo — e o badge da aresta permite trocar depois.
 */
export function portaDeEntradaPadrao(declaredInputs: unknown): string | undefined {
  const inputs = (declaredInputs ?? []) as INodePortAPI[]
  return inputs.length > 1 ? inputs[0]?.name : undefined
}

/**
 * `sourceHandle` que uma aresta deve carregar ao escolher a chave `nome` na
 * origem, mantendo a invariante `sourceHandle === from_key` dos nós multi-saída
 * sem apontar a linha para um handle que não existe.
 *
 * Só há handle NOMEADO quando o nó desenha 2+ saídas REAIS (`outputs`) — ver
 * `default-type` / `default-trigger-icon`, que renderizam um `HandleSource` por
 * `outputs[].name` apenas nesse caso, e um handle ANÔNIMO caso contrário.
 * Campo sem `port` NÃO vira handle: sincronizar o `sourceHandle` com um campo
 * sem ponto de conexão (que `getCandidateKeys` também oferece no seletor)
 * apontava a aresta para um handle inexistente, e o React Flow deixava de
 * desenhá-la — a aresta "sumia". Espelha a regra de `resolveSourceHandle`
 * (edge-persistence): porta real só com `outputs.length > 1 && nome ∈ outputs`.
 *
 *   • saída única (0/1 output)          → `null`      (handle anônimo; também
 *                                          limpa um handle fantasma já gravado)
 *   • multi-saída e `nome` é uma porta  → `nome`
 *   • multi-saída e `nome` não é porta  → `undefined` (deixa o handle como está)
 */
export function sourceHandleDaChave(
  outputs: ReadonlyArray<{ name?: string }> | undefined,
  nome: string,
): string | null | undefined {
  const saidas = outputs ?? []
  if (saidas.length <= 1) return null
  return saidas.some((o) => o?.name === nome) ? nome : undefined
}

/**
 * Nó que só aceita UMA aresta chegando — o que depende do que ele declara.
 *
 * O `SubWorkflowOutput` define o valor de retorno do sub-fluxo. Sem portas
 * declaradas ele tem um ponto de conexão anônimo: duas arestas espalham os dois
 * dicts nas mesmas chaves e a última vence, então o contrato anuncia uma saída
 * e entrega outra conforme a ordem das arestas. A partir de DUAS portas cada
 * aresta cai na sua própria chave — o editor preenche o `to_key` com o nome da
 * porta — e a disputa deixa de existir: aí várias conexões são o objetivo, e
 * não o problema.
 *
 * Uma porta só não basta: `resolveToKey` só preenche `to_key` quando o destino
 * declara MAIS DE UMA, então com uma as arestas voltariam a disputar a chave.
 *
 * O `SubWorkflowInput` era barrado por simetria e não precisava: cada aresta
 * que sai dele espalha o dict de entrada no seu próprio destino, sem disputa.
 */
export function limitadoAUmaAresta(
  nodeName: string | undefined,
  portasDeclaradas: number,
): boolean {
  return nodeName !== undefined && NOS_DE_UMA_ARESTA.has(nodeName) && portasDeclaradas < 2
}

/**
 * Os nós que só aceitam uma aresta sem portas declaradas. A Carta imagem entra
 * pelo mesmo motivo do SubWorkflowOutput: com um ponto de conexão anônimo, duas
 * camadas ligadas espalhariam os dois dicts na mesma chave (`output`), a última
 * venceria e a carta sairia com uma camada só — sem que o nó pudesse perceber
 * a perda. A partir de duas portas cada camada chega pelo nome da sua porta.
 */
const NOS_DE_UMA_ARESTA: ReadonlySet<string> = new Set(["SubWorkflowOutput", "CartaImagem"])
