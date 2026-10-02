/**
 * Quantas arestas o `SubWorkflowOutput` aceita chegando.
 *
 * Ele define o valor de retorno do sub-fluxo. Sem portas declaradas tem um
 * ponto de conexão anônimo, e duas arestas espalhariam os dois dicts nas mesmas
 * chaves: a última venceria, e o contrato anunciaria uma saída entregando
 * outra conforme a ordem das arestas. A partir de DUAS portas o editor preenche
 * o `to_key` de cada aresta com o nome da porta, cada origem cai na sua própria
 * chave, e várias conexões passam a ser justamente o objetivo — é como o
 * sub-fluxo devolve mais de um valor sem um nó-funil montando o dict.
 *
 * O `SubWorkflowInput` era barrado pela mesma regra, por simetria, e não
 * precisava: cada aresta que sai dele espalha o dict de entrada no seu próprio
 * destino, sem disputa.
 */
import { describe, it, expect } from "vitest"

import { limitadoAUmaAresta } from "@/app/components/workflow/utils/resolve-edge-keys"

describe("limitadoAUmaAresta", () => {
  it("SubWorkflowOutput sem portas continua aceitando uma só", () => {
    expect(limitadoAUmaAresta("SubWorkflowOutput", 0)).toBe(true)
  })

  it("uma porta só também não libera", () => {
    // `resolveToKey` só preenche `to_key` quando o destino declara MAIS DE UMA
    // porta. Com uma, as duas arestas voltariam a disputar a mesma chave —
    // exatamente o defeito que a regra existe para evitar.
    expect(limitadoAUmaAresta("SubWorkflowOutput", 1)).toBe(true)
  })

  it.each([2, 3, 7])("com %i portas aceita várias arestas", (n) => {
    expect(limitadoAUmaAresta("SubWorkflowOutput", n)).toBe(false)
  })

  it("a Carta imagem segue a mesma regra: sem portas, ou com uma, aceita uma aresta só", () => {
    // Com um ponto de conexão anônimo, duas camadas ligadas espalhariam os
    // dois dicts na mesma chave (`output`) e a carta sairia com uma camada só —
    // sem que o nó pudesse perceber a perda.
    expect(limitadoAUmaAresta("CartaImagem", 0)).toBe(true)
    expect(limitadoAUmaAresta("CartaImagem", 1)).toBe(true)
  })

  it.each([2, 3])("a Carta imagem com %i portas recebe uma camada por porta", (n) => {
    expect(limitadoAUmaAresta("CartaImagem", n)).toBe(false)
  })

  it("SubWorkflowInput NÃO é restrito", () => {
    // O que o usuário pediu antes: ramificar a partir da entrada do sub-fluxo,
    // como já dá para fazer com o Gatilho por Web.
    expect(limitadoAUmaAresta("SubWorkflowInput", 0)).toBe(false)
  })

  it.each(["PythonScript", "AttributeJoin", "WebhookTrigger", "Merge", undefined])(
    "%s aceita várias", (nome) => {
      expect(limitadoAUmaAresta(nome, 0)).toBe(false)
    })
})
