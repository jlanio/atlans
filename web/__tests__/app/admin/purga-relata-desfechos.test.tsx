import { describe, it, expect } from "vitest"
import { readFileSync } from "fs"
import { join } from "path"

// A purga precisa contar o que NÃO removeu, e por qual motivo.
//
// O diálogo reportava apenas `skipped_s3_errors`. Depois de a purga passar a
// respeitar `content_location` (o artefato que vive no disco do executor só cai
// depois que a ordem de remoção é ENTREGUE), surgiram três desfechos novos:
//
//   pending_executor     executor offline — a linha fica, a próxima passada
//                        tenta de novo
//   skipped_sem_rastro   sem executor_id/local_path: não há para quem mandar a
//                        ordem, e apagar a linha perderia o rastro do arquivo
//   skipped_catalogados  Drive catalogado: é arquivo do próprio usuário, na
//                        pasta que ele sincroniza — preservado por política
//
// Sem contá-los, o toast dizia "N removidos" e o admin concluía que o
// armazenamento tinha sido liberado, quando parte continuava lá. A distinção
// importa porque só os dois primeiros se resolvem repetindo a purga.

// O diálogo de purga mora no componente da seção «Armazenamento» (a página de
// Configurações foi fatiada na F2 da simplificação).
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
    // Juntar os dois grupos num número só diria ao admin para repetir a purga
    // de algo que a plataforma nunca vai remover.
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
    // Se todo desfecho virasse "purga parcial", uma purga limpa passaria a
    // parecer problemática.
    expect(fonte).toContain("createToast.success")
  })
})
