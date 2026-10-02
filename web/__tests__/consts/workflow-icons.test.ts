import { describe, it, expect } from "vitest"
import { OUTPUT_ICONS, NODE_ICONS } from "@/consts/WorkflowIcons"

/**
 * Os nós de saída abaixo espelham o registro do backend (`flow/nodes/outputs/`,
 * `type: "output"`). Sem entrada em `OUTPUT_ICONS` o card nasce com o ícone de
 * erro ("404") e o `satisfies` do arquivo só acusa quando o union e o mapa
 * divergem entre si — não quando o backend ganha um nó e ninguém lembra do
 * ícone. Este teste falha e aponta qual ficou de fora.
 */
const SAIDAS_DO_BACKEND = [
  "SaveToPostGIS",
  "SaveToPostgres",
  "SaveGeoJSON",
  "SaveToShapefile",
  "SaveToGeoParquet",
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
  it.each(SAIDAS_DO_BACKEND)("tem ícone para o nó de saída '%s'", nome => {
    expect(OUTPUT_ICONS[nome as keyof typeof OUTPUT_ICONS]).toBeTypeOf("function")
  })

  it("não tem entrada sobrando que o backend não conheça", () => {
    expect(Object.keys(OUTPUT_ICONS).sort()).toEqual([...SAIDAS_DO_BACKEND].sort())
  })

  it("o mapa unificado do drawer enxerga a Carta imagem", () => {
    expect(NODE_ICONS["CartaImagem"]).toBe(OUTPUT_ICONS.CartaImagem)
  })
})
