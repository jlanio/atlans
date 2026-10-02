// web/app/components/workflow/utils/node-ports.ts
//
// Portas de entrada de um nó — declaradas no catálogo ou pelo usuário.
//
// A maioria dos nós declara as entradas no próprio schema (`inputs`), e elas são
// as mesmas para toda instância. Uns poucos (`dynamic_inputs`) deixam a lista
// para quem monta o fluxo, na propriedade `ports` — é o caso do Script Python,
// onde os nomes viram as VARIÁVEIS do script.
//
// Isso existe porque o nome que chega ao script vem do `to_key` da aresta, e o
// editor só preenche `to_key` quando o nó de destino declara mais de uma porta.
// Sem declarar, duas arestas escrevem na mesma chave e a segunda sobrescreve a
// primeira — o script recebe UMA entrada e reclama de uma variável indefinida,
// sem nada dizendo que a outra foi perdida.
import { INodePortAPI, INodesAPI } from "@/service/types"

/**
 * Valores aceitos como nome de porta.
 *
 * Mesma regra do SubWorkflowPortsHelper: identificador saudável. O nome vira
 * variável dentro do script Python, então espaço ou acento produziriam código
 * inválido — e o erro apareceria como SyntaxError no meio do script do usuário,
 * longe da causa.
 */
export const NOME_DE_PORTA = /^[A-Za-z_][A-Za-z0-9_]*$/

/** Lê a propriedade `ports`, tolerando lista, JSON em string, ou ausência. */
export function lerPortas(bruto: unknown): string[] {
  if (Array.isArray(bruto)) {
    return bruto.filter((x): x is string => typeof x === "string" && x.trim() !== "")
  }
  if (typeof bruto === "string" && bruto.trim()) {
    try {
      const parsed = JSON.parse(bruto)
      return Array.isArray(parsed)
        ? parsed.filter((x): x is string => typeof x === "string" && x.trim() !== "")
        : []
    } catch {
      return []
    }
  }
  return []
}

/**
 * Pontos de conexão de entrada de UMA instância de nó.
 *
 * Nó comum: as portas do catálogo. Nó de entradas dinâmicas: as que o usuário
 * definiu — e a ausência delas devolve lista vazia, que é o que mantém o nó com
 * um ponto de conexão anônimo, exatamente como antes de `ports` existir.
 */
export function portasDeEntrada(
  def: Pick<INodesAPI, "inputs" | "dynamic_inputs"> | undefined,
  properties: Record<string, unknown> | undefined,
): INodePortAPI[] {
  if (!def) return []
  if (!def.dynamic_inputs) return def.inputs ?? []
  // Sem repetidos: dois pontos de conexão com o mesmo id deixam o React Flow
  // sem saber em qual a aresta encosta, e a segunda entrada sobrescreveria a
  // primeira no script — que é exatamente o defeito que as portas existem para
  // resolver. O campo já marca o nome repetido em vermelho; aqui é a garantia
  // de que o canvas não entra num estado ambíguo enquanto ele é corrigido.
  return [...new Set(lerPortas(properties?.ports))].map(name => ({ name }))
}

/**
 * Pontos de conexão de SAÍDA de UMA instância de nó.
 *
 * Simétrico a `portasDeEntrada`: um nó `outputs_from_ports` (o SubWorkflowInput)
 * expõe como saídas as portas que o usuário declarou em `ports` — cada porta
 * vira um handle de saída próprio, e a aresta que sai dela leva `from_key` = o
 * nome da porta, então o próximo nó recebe só aquela chave. A ausência de portas
 * devolve lista vazia, que mantém o ponto de saída anônimo (modo espalhar) —
 * exatamente o comportamento legado.
 */
export function portasDeSaida(
  def: Pick<INodesAPI, "outputs" | "outputs_from_ports" | "branches"> | undefined,
  properties: Record<string, unknown> | undefined,
): INodePortAPI[] {
  if (!def) return []
  if (def.outputs_from_ports) {
    return [...new Set(lerPortas(properties?.ports))].map(name => ({ name }))
  }
  // Nó de ramo: os pontos de saída roteiam a execução, não carregam campo.
  if (def.branches) return [{ name: "true" }, { name: "false" }]
  // Campos com ponto de conexão próprio (`port`). Nenhum marcado ⇒ ponto de
  // saída anônimo (modo espalhar) — a mesma regra de sempre.
  return (def.outputs ?? [])
    .filter(c => c.port)
    .map(c => ({ name: c.name, description: c.description }))
}

/**
 * Onde a linha de uma aresta encosta no nó de destino, ao recarregar o fluxo.
 *
 * `to_key` é o NOME DO DADO para o executor; `targetHandle` é ONDE A LINHA
 * ENCOSTA na tela. Só há handle NOMEADO (`id={port.name}`) quando o nó declara
 * 2+ portas — `default-type` desenha um `HandleTarget` por porta apenas nesse
 * caso; com UMA porta só, o handle é ANÔNIMO (sem id). Devolver o nome de uma
 * porta única como `targetHandle` aponta a aresta para um id que não existe na
 * tela: o React Flow não a desenha, ela SOME do canvas continuando a executar
 * (o `to_key` sobrevive em `data`, então o executor ainda roteia pela chave), e
 * sem linha desenhada o botão de excluir é inalcançável — não dá nem para
 * refazer a conexão.
 *
 * Por isso o `> 1` espelha o limiar de `resolveSourceHandle` e da renderização:
 * com uma porta, a aresta ancora no handle anônimo (e desenha); com 2+, no
 * handle nomeado que existe. `data.to_key` é preservado nos dois casos.
 */
export function handleDeEntrada(
  edge: { target: string; to_key?: string },
  portasPorNo: Map<string, string[]>,
): string | undefined {
  const portas = portasPorNo.get(edge.target)
  return edge.to_key && portas && portas.length > 1 && portas.includes(edge.to_key)
    ? edge.to_key
    : undefined
}

/** Forma mínima de aresta que a re-ancoragem precisa enxergar. */
interface ArestaComHandles {
  source: string
  target: string
  sourceHandle?: string | null
  targetHandle?: string | null
  data?: { from_key?: string; to_key?: string }
}

/**
 * Re-ancora, para UM nó, as arestas cujo handle se perdeu no load.
 *
 * `buildEdges` resolve o handle a partir do `to_key`/`from_key` só se o nó já
 * declara aquela porta. O nó SubWorkflow (invoke) recebe as portas de um
 * contrato ASSÍNCRONO (~300 ms depois da hidratação), então na primeira montagem
 * `handleDeEntrada`/`resolveSourceHandle` devolvem `undefined` e o React Flow
 * prende todas as arestas no primeiro handle — o colapso "tudo na primeira
 * entrada" ao dar F5. Quando as portas chegam, esta função devolve cada aresta
 * ao seu ponto: a `data` preservou `to_key` (entrada) e `from_key` (saída), e
 * agora esses nomes casam com uma porta declarada.
 *
 * Devolve o MESMO array quando nada muda — proteção anti-laço de quem chama de
 * dentro de um efeito com `setEdges` (mesma regra de `reconciliarPortas`).
 */
export function reancorarArestasDoNo<E extends ArestaComHandles>(
  edges: E[],
  nodeId: string,
  inputs: string[],
  outputs: string[],
): E[] {
  const nomesEntrada = new Set(inputs)
  const nomesSaida = new Set(outputs)
  let mudou = false
  const proximos = edges.map(e => {
    let ne = e
    // `> 1` pelo mesmo motivo de `handleDeEntrada`/`resolveSourceHandle`: com uma
    // porta só, o handle é anônimo (sem id) — ancorar no nome dela apontaria para
    // um id inexistente e a aresta sumiria. Com 2+, o handle nomeado existe.
    if (e.target === nodeId && !e.targetHandle && inputs.length > 1 && e.data?.to_key && nomesEntrada.has(e.data.to_key)) {
      ne = { ...ne, targetHandle: e.data.to_key }
    }
    if (e.source === nodeId && !e.sourceHandle && outputs.length > 1 && e.data?.from_key && nomesSaida.has(e.data.from_key)) {
      ne = { ...ne, sourceHandle: e.data.from_key }
    }
    if (ne !== e) mudou = true
    return ne
  })
  return mudou ? proximos : edges
}

/**
 * O que o catálogo declara sobre o contrato de um nó, pronto para entrar no
 * `data` da instância no canvas.
 *
 * Existe porque o `data` é montado em DOIS lugares — ao abrir um fluxo salvo e
 * ao colar/duplicar um nó — cada um campo a campo. Um campo novo esquecido num
 * deles produz um defeito de sintoma bizarro: funciona no nó recém-criado e
 * some ao recarregar a página. Aconteceu com `dynamic_inputs` e de novo com
 * `dynamic_output`; concentrar aqui é o que impede a terceira vez.
 */
export function contratoDoNo(
  def: Pick<INodesAPI, "inputs" | "outputs" | "dynamic_inputs" | "dynamic_output" | "outputs_from_ports" | "branches"> | undefined,
  properties: Record<string, unknown> | undefined,
) {
  return {
    inputs: portasDeEntrada(def, properties),
    outputs: portasDeSaida(def, properties),
    dynamic_inputs: def?.dynamic_inputs,
    dynamic_output: def?.dynamic_output,
    outputs_from_ports: def?.outputs_from_ports,
    branches: def?.branches,
    saidas: def?.outputs,
  }
}

/**
 * Campos de saída de UMA instância de nó.
 *
 * A maioria declara no catálogo (`saidas`, os `outputs` tipados do nó). O
 * Script Python declara `dynamic_output` e as saídas de verdade estão em
 * `output_vars` — o painel mostrava sempre "result", o nome do catálogo,
 * mesmo depois de a pessoa ter renomeado as variáveis. E o badge da aresta
 * oferecia esse mesmo "result" como chave, que o executor não encontra.
 *
 * A derivação exige `output_vars`: nós como o ReadGeoJSON também declaram
 * `dynamic_output` — no sentido de que a FORMA do dado varia — mas não têm a
 * propriedade, e para eles vale o catálogo.
 */
export function saidasDoNo(
  data: {
    dynamic_output?: boolean
    outputs_from_ports?: boolean
    saidas?: { name: string; type?: string; description?: string }[]
    properties?: Record<string, unknown>
  } | undefined,
): { name: string; type?: string; description?: string }[] {
  const bruto = data?.properties?.output_vars
  if (data?.dynamic_output && typeof bruto === "string") {
    const nomes = bruto.split(",").map(v => v.trim()).filter(Boolean)
    if (nomes.length) {
      return [...new Set(nomes)].map(name => ({
        name,
        description: "Variável definida em 'Variável de saída'",
      }))
    }
  }
  // SubWorkflowInput: as saídas SÃO as portas declaradas pelo usuário — o
  // catálogo declara [] de propósito. Sem este ramo, o seletor de chave e o
  // badge da aresta ficavam sem candidatos e a aresta nascia sem from_key.
  if (data?.outputs_from_ports) {
    return [...new Set(lerPortas(data?.properties?.ports))].map(name => ({ name }))
  }
  return data?.saidas ?? []
}

/** Forma mínima de nó que a reconciliação precisa enxergar. */
interface NoComPortas {
  data?: {
    dynamic_inputs?: boolean
    outputs_from_ports?: boolean
    properties?: Record<string, unknown>
    inputs?: { name: string }[]
    outputs?: { name: string }[]
  }
}

/** As portas atuais já batem com a lista declarada? (por nome e ordem) */
function mesmasPortas(atuais: { name: string }[] | undefined, nomes: string[]): boolean {
  const lista = atuais ?? []
  return lista.length === nomes.length && lista.every((p, i) => p.name === nomes[i])
}

/**
 * Traz `data.inputs`/`data.outputs` de volta ao que a propriedade `ports` diz,
 * nos nós de portas dinâmicas — `dynamic_inputs` popula as entradas (Script
 * Python, SubWorkflowOutput) e `outputs_from_ports` popula as saídas
 * (SubWorkflowInput). Devolve o MESMO array quando nada mudou.
 *
 * A identidade referencial é parte do contrato, não detalhe: quem chama é um
 * efeito que depende do estado dos nós, e devolver um array novo a cada
 * passagem o faria se realimentar sem parar.
 */
export function reconciliarPortas<T extends NoComPortas>(nos: T[]): T[] {
  let mudou = false
  const proximos = nos.map(n => {
    const d = n.data
    if (!d?.dynamic_inputs && !d?.outputs_from_ports) return n

    const portas = [...new Set(lerPortas(d.properties?.ports))]
    let proximo = n

    if (d.dynamic_inputs && !mesmasPortas(d.inputs, portas)) {
      proximo = { ...proximo, data: { ...proximo.data, inputs: portas.map(name => ({ name })) } }
    }
    if (d.outputs_from_ports && !mesmasPortas(proximo.data?.outputs, portas)) {
      proximo = { ...proximo, data: { ...proximo.data, outputs: portas.map(name => ({ name })) } }
    }

    if (proximo !== n) mudou = true
    return proximo
  })
  return mudou ? proximos : nos
}
