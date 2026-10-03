import { describe, expect, it } from "vitest"
import {
  ESCOPOS, READ_ONLY_SCOPES, SCOPE_DESCRIPTIONS, SCOPE_LABELS,
  ordenarEscopos, scopeLabel, statusLabel,
} from "@/app/components/tokens/escopo-rotulos"

describe("escopo-rotulos", () => {
  it("cobre os seis escopos do contrato, na ordem canônica", () => {
    expect(ESCOPOS).toEqual([
      "workflows:read", "workflows:write", "runs:execute", "triggers:manage", "drive:read", "drive:write",
    ])
    for (const escopo of ESCOPOS) {
      expect(SCOPE_LABELS[escopo]).toBeTruthy()
      expect(SCOPE_DESCRIPTIONS[escopo]).toBeTruthy()
    }
  })

  it("rótulos curtos em pt-BR", () => {
    expect(scopeLabel("workflows:read")).toBe("Ler fluxos")
    expect(scopeLabel("workflows:write")).toBe("Criar e editar fluxos")
    expect(scopeLabel("runs:execute")).toBe("Executar fluxos")
    expect(scopeLabel("triggers:manage")).toBe("Gerenciar agendamentos e webhooks")
    expect(scopeLabel("drive:read")).toBe("Ler o Drive")
    expect(scopeLabel("drive:write")).toBe("Enviar arquivos ao Drive")
  })

  it("escopo desconhecido volta cru no rótulo, sem quebrar", () => {
    expect(scopeLabel("admin:everything")).toBe("admin:everything")
  })

  it("ordenarEscopos devolve a ordem canônica e ignora o que não conhece", () => {
    expect(ordenarEscopos(["drive:read", "workflows:read", "x:y"])).toEqual(["workflows:read", "drive:read"])
    expect(ordenarEscopos([])).toEqual([])
  })

  it("«Somente leitura» é ler fluxos + ler o Drive", () => {
    expect(READ_ONLY_SCOPES).toEqual(["workflows:read", "drive:read"])
  })

  it("status sempre traduzido, com fallback", () => {
    expect(statusLabel("active")).toBe("Ativo")
    expect(statusLabel("expired")).toBe("Expirado")
    expect(statusLabel("revoked")).toBe("Revogado")
    expect(statusLabel(null)).toBe("—")
    expect(statusLabel("weird")).toBe("weird")
  })
})
