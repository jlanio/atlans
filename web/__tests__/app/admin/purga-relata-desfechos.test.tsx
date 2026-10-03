import { describe, it, expect } from "vitest"
import { readFileSync } from "fs"
import { join } from "path"

// The purge has to count what it did NOT remove, and for what reason.
//
// The dialog reported only `skipped_s3_errors`. After the purge started
// respecting `content_location` (an artifact that lives on the executor's disk is only dropped
// after the removal order is DELIVERED), three new outcomes appeared:
//
//   pending_executor     executor offline — the row stays, the next pass
//                        tries again
//   skipped_sem_rastro   no executor_id/local_path: there is no one to send the
//                        order to, and deleting the row would lose the file's trace
//   skipped_catalogados  cataloged Drive: it is the user's own file, in the
//                        folder they sync — preserved by policy
//
// Without counting them, the toast said "N removidos" (N removed) and the admin concluded that
// the storage had been freed, when part of it was still there. The distinction
// matters because only the first two are resolved by repeating the purge.

// The purge dialog lives in the component for the "Armazenamento" (storage) section (the
// Settings page was split up in F2 of the simplification).
const SECAO = join(
  __dirname, "..", "..", "..", "app", "components", "admin", "settings", "armazenamento.tsx",
)
const TIPOS = join(__dirname, "..", "..", "..", "service", "types.ts")

describe("purga de armazenamento — relato dos desfechos", () => {
  const fonte = readFileSync(SECAO, "utf8")

  it("soma os desfechos que se resolvem repetindo a purga", () => {
    expect(fonte).toContain("skipped_s3_errors")
    expect(fonte, "executor offline também é 'tente de novo'").toContain("pending_executor")
  })

  it("relata separadamente o que foi preservado por política", () => {
    // Merging the two groups into a single number would tell the admin to repeat the purge
    // for something the platform will never remove.
    expect(fonte).toContain("skipped_catalogados")
    expect(fonte).toContain("skipped_sem_rastro")
    expect(fonte).toContain("preservado")
  })

  it("os contadores existem no tipo da resposta", () => {
    const tipos = readFileSync(TIPOS, "utf8")
    for (const campo of ["pending_executor", "skipped_sem_rastro", "skipped_catalogados"]) {
      expect(tipos, `IStoragePurgeResult sem ${campo}`).toContain(campo)
    }
  })

  it("o caminho de sucesso total continua existindo", () => {
    // If every outcome became a "partial purge", a clean purge would start
    // looking problematic.
    expect(fonte).toContain("createToast.success")
  })
})
