import { describe, it, expect, afterEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import type { IDriveFile } from "@/service/types"
import { MetadataDialog } from "@/app/components/drive/dialogs"

/** The dialog is shared and portaled to <body>: whoever opens it from the Home passes `home-portal`. */
afterEach(cleanup)

const arquivo: IDriveFile = {
  id_hash: "drv-1", workspace_id: "ws-1", original_name: "dados.csv",
  extension: "csv", mime_type: "text/csv", size: 42,
  uploaded_by: "u1", created_at: "2026-09-08T12:00:00Z", updated_at: null,
  content_written_at: null, content_location: "minio", content_executor_id: null,
  spatial_metadata: null,
}

const montar = (className?: string) =>
  render(<MetadataDialog file={arquivo} open onClose={() => {}} className={className} />)

describe("MetadataDialog — a paleta de quem o abre", () => {
  it("repassa className ao DialogContent, sem perder a largura de sempre", () => {
    montar("home-portal")
    const dialogo = screen.getByRole("dialog")
    expect(dialogo.className).toContain("home-portal")
    expect(dialogo.className).toContain("max-w-sm")
  })

  it("sem className, o diálogo é o de sempre", () => {
    montar()
    expect(screen.getByRole("dialog").className).not.toContain("home-portal")
  })
})
