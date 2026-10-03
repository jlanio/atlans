/**
 * How many incoming edges `SubWorkflowOutput` accepts.
 *
 * It defines the sub-workflow's return value. Without declared ports it has an
 * anonymous connection point, and two edges would spread both dicts over the
 * same keys: the last one would win, and the contract would announce one output
 * while delivering another depending on the order of the edges. From TWO ports
 * on, the editor fills each edge's `to_key` with the port name, each source lands
 * in its own key, and multiple connections become precisely the goal — it's how
 * the sub-workflow returns more than one value without a funnel node assembling
 * the dict.
 *
 * `SubWorkflowInput` was blocked by the same rule, for symmetry, and didn't need
 * to be: each edge leaving it spreads the input dict into its own target, with
 * no contention.
 */
import { describe, it, expect } from "vitest"

import { limitadoAUmaAresta } from "@/app/components/workflow/utils/resolve-edge-keys"

describe("limitadoAUmaAresta", () => {
  it("SubWorkflowOutput sem portas continua aceitando uma só", () => {
    expect(limitadoAUmaAresta("SubWorkflowOutput", 0)).toBe(true)
  })

  it("uma porta só também não libera", () => {
    // `resolveToKey` only fills `to_key` when the target declares MORE THAN ONE
    // port. With one, the two edges would go back to competing for the same key —
    // exactly the defect the rule exists to avoid.
    expect(limitadoAUmaAresta("SubWorkflowOutput", 1)).toBe(true)
  })

  it.each([2, 3, 7])("com %i portas aceita várias arestas", (n) => {
    expect(limitadoAUmaAresta("SubWorkflowOutput", n)).toBe(false)
  })

  it("a Carta imagem segue a mesma regra: sem portas, ou com uma, aceita uma aresta só", () => {
    // With an anonymous connection point, two connected layers would spread
    // both dicts over the same key (`output`) and the map would come out with a
    // single layer — without the node being able to notice the loss.
    expect(limitadoAUmaAresta("CartaImagem", 0)).toBe(true)
    expect(limitadoAUmaAresta("CartaImagem", 1)).toBe(true)
  })

  it.each([2, 3])("a Carta imagem com %i portas recebe uma camada por porta", (n) => {
    expect(limitadoAUmaAresta("CartaImagem", n)).toBe(false)
  })

  it("SubWorkflowInput NÃO é restrito", () => {
    // What the user asked for earlier: branching from the sub-workflow's input,
    // as is already possible with the Web Trigger.
    expect(limitadoAUmaAresta("SubWorkflowInput", 0)).toBe(false)
  })

  it.each(["PythonScript", "AttributeJoin", "WebhookTrigger", "Merge", undefined])(
    "%s aceita várias", (nome) => {
      expect(limitadoAUmaAresta(nome, 0)).toBe(false)
    })
})
