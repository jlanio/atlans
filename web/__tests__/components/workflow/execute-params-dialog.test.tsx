import { describe, it, expect, afterEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import ExecuteParamsDialog from "@/app/components/workflow/execute-params-dialog"

/** The dialog is shared and portaled to <body>: whoever opens it from Home passes `home-portal`. */
afterEach(cleanup)

const montar = (className?: string) =>
  render(
    <ExecuteParamsDialog
      open
      paramsSchema={{ area: { type: "string", required: true } }}
      onConfirm={() => {}}
      onCancel={() => {}}
      className={className}
    />,
  )

describe("ExecuteParamsDialog — a paleta de quem o abre", () => {
  it("repassa className ao DialogContent", () => {
    montar("home-portal")
    expect(screen.getByRole("dialog").className).toContain("home-portal")
  })

  it("sem className, o diálogo é o de sempre", () => {
    montar()
    expect(screen.getByRole("dialog").className).not.toContain("home-portal")
  })
})
