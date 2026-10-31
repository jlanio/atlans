/**
 * Field visibility in the node form (`visibleWhen`).
 *
 * The OR (`{ any }`) exists for DataInput: "Arquivo dentro do ZIP" shows on the
 * Drive — whose file's format the form does not know — OR on the URL origin
 * when the format chosen is ZIP. With only AND, the field either showed for
 * every URL format or disappeared from the Drive.
 */
import { describe, it, expect } from "vitest"

import { campoVisivel } from "@/app/components/workflow/node-config-modal/visibilidade"
import { INodesPropertyAPI } from "@/service/types"

type VisibleWhen = INodesPropertyAPI["visibleWhen"]

const doZip: VisibleWhen = {
  any: [
    { field: "context", in: ["drive", "artifacts"] },
    { field: "expectedFormat", in: ["zip"] },
  ],
}

describe("campoVisivel", () => {
  it("shows a field without a rule", () => {
    expect(campoVisivel(undefined, {})).toBe(true)
  })

  it("a rule: the current value has to be in `in`", () => {
    expect(campoVisivel({ field: "context", in: ["url"] }, { context: "url" })).toBe(true)
    expect(campoVisivel({ field: "context", in: ["url"] }, { context: "drive" })).toBe(false)
  })

  it("a list: every rule has to hold", () => {
    const regras: VisibleWhen = [
      { field: "context", in: ["artifacts"] },
      { field: "localidade", in: ["herdar"] },
    ]
    expect(campoVisivel(regras, { context: "artifacts", localidade: "herdar" })).toBe(true)
    expect(campoVisivel(regras, { context: "artifacts", localidade: "executor" })).toBe(false)
  })

  it("any: one rule holding is enough", () => {
    expect(campoVisivel(doZip, { context: "drive", expectedFormat: "escolher" })).toBe(true)
    expect(campoVisivel(doZip, { context: "url", expectedFormat: "zip" })).toBe(true)
    expect(campoVisivel(doZip, { context: "url", expectedFormat: "csv" })).toBe(false)
    expect(campoVisivel(doZip, { context: "url", expectedFormat: "escolher" })).toBe(false)
  })

  it("a format chosen on the URL does not hide the field when the origin goes back to the Drive", () => {
    expect(campoVisivel(doZip, { context: "drive", expectedFormat: "geojson" })).toBe(true)
  })

  it("an item of `any` can be an AND list", () => {
    const vw: VisibleWhen = {
      any: [[{ field: "a", in: [1] }, { field: "b", in: [true] }], { field: "c", in: ["x"] }],
    }
    expect(campoVisivel(vw, { a: 1, b: true })).toBe(true)
    expect(campoVisivel(vw, { a: 1, b: false })).toBe(false)
    expect(campoVisivel(vw, { c: "x" })).toBe(true)
  })

  it("a shape it does not know shows the field instead of hiding it", () => {
    expect(campoVisivel({ outro: 1 } as unknown as VisibleWhen, {})).toBe(true)
  })

  it("an `any` it does not know shows the field too, instead of breaking the form", () => {
    expect(campoVisivel({ any: [{ field: "a" }] } as unknown as VisibleWhen, {})).toBe(true)
    expect(campoVisivel({ any: [[{ field: "a", in: [1] }, { in: [1] }]] } as unknown as VisibleWhen, {})).toBe(true)
    expect(campoVisivel({ any: "context" } as unknown as VisibleWhen, {})).toBe(true)
  })

  it("`any` wins over the `field`/`in` kept beside it for editors older than `any`", () => {
    // DataInput sends both: an editor from before `any` reads `field`/`in` (every
    // origin, so the field shows); this one must read `any` and hide it.
    const comLegado = { ...doZip, field: "context", in: ["drive", "artifacts", "url"] } as unknown as VisibleWhen
    expect(campoVisivel(comLegado, { context: "url", expectedFormat: "csv" })).toBe(false)
    expect(campoVisivel(comLegado, { context: "url", expectedFormat: "zip" })).toBe(true)
    expect(campoVisivel(comLegado, { context: "drive", expectedFormat: "csv" })).toBe(true)
  })
})
