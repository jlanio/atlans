/**
 * Numeric node field (`number` and `integer`).
 *
 * Clearing the input used to store 0: `Number("")` is 0, so an optional field
 * (limit, timeout, tolerance) could not be left blank — it snapped back to "0"
 * and the node ran with a silent zero. Empty is stored as "", which the
 * executor's parameter validation reads as "use the declared default".
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, fireEvent } from "@testing-library/react"

import NumericField from "@/app/components/workflow/nodes-configuration/fields/numeric-field"
import { INodesPropertyAPI } from "@/service/types"

afterEach(cleanup)

const campo = {
  name: "limit",
  label: "Limite",
  type: "integer",
  default: 100,
  description: null,
} as unknown as INodesPropertyAPI

function montar(valor: number | string, variant: "number" | "integer" = "integer") {
  const setNodeField = vi.fn()
  const { container } = render(
    <NumericField field={campo} values={{ limit: valor }} setNodeField={setNodeField} variant={variant} />,
  )
  return { setNodeField, input: container.querySelector("input") as HTMLInputElement }
}

describe("NumericField", () => {
  it.each(["integer", "number"] as const)("esvaziar o campo (%s) desfaz o valor em vez de gravar 0", (variant) => {
    const { setNodeField, input } = montar(25, variant)

    fireEvent.change(input, { target: { value: "" } })

    expect(setNodeField).toHaveBeenCalledWith("limit", "")
    expect(setNodeField).not.toHaveBeenCalledWith("limit", 0)
  })

  it("um valor vazio aparece vazio, não como 0", () => {
    expect(montar("").input.value).toBe("")
  })

  it("0 digitado de propósito continua sendo 0", () => {
    const { setNodeField, input } = montar(25)
    fireEvent.change(input, { target: { value: "0" } })
    expect(setNodeField).toHaveBeenCalledWith("limit", 0)
  })

  it("inteiro arredonda; decimal passa como digitado", () => {
    const inteiro = montar(1, "integer")
    fireEvent.change(inteiro.input, { target: { value: "2.6" } })
    expect(inteiro.setNodeField).toHaveBeenCalledWith("limit", 3)
    cleanup()

    const decimal = montar(1, "number")
    fireEvent.change(decimal.input, { target: { value: "2.6" } })
    expect(decimal.setNodeField).toHaveBeenCalledWith("limit", 2.6)
  })
})
