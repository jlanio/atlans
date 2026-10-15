import { describe, it, expect } from "vitest"
import { OUTPUT_ICONS, NODE_ICONS } from "@/consts/WorkflowIcons"

/**
 * The output nodes below mirror the backend registry (`flow/nodes/outputs/`,
 * `type: "output"`). Without an entry in `OUTPUT_ICONS` the card is born with the
 * error icon ("404") and the file's `satisfies` only complains when the union and
 * the map diverge from each other — not when the backend gains a node and nobody
 * remembers the icon. This test fails and points out which one was left out.
 */
const BACKEND_OUTPUTS = [
  "SaveToPostGIS",
  "SaveToPostgres",
  "SaveGeoJSON",
  "SaveToShapefile",
  "SaveToGeoParquet",
  "SaveFile",
  "SaveToS3",
  "SendEmail",
  "SendWebhook",
  "DataOutput",
  "Response",
  "PublishMap",
  "CartaImagem",
  "SubWorkflowOutput",
]

describe("OUTPUT_ICONS", () => {
  it.each(BACKEND_OUTPUTS)("tem ícone para o nó de saída '%s'", nome => {
    expect(OUTPUT_ICONS[nome as keyof typeof OUTPUT_ICONS]).toBeTypeOf("function")
  })

  it("não tem entrada sobrando que o backend não conheça", () => {
    expect(Object.keys(OUTPUT_ICONS).sort()).toEqual([...BACKEND_OUTPUTS].sort())
  })

  it("o mapa unificado do drawer enxerga a Carta imagem", () => {
    expect(NODE_ICONS["CartaImagem"]).toBe(OUTPUT_ICONS.CartaImagem)
  })
})
