import { describe, expect, it } from "vitest"
import {
  ESCOPOS, ESCOPOS_SOMENTE_LEITURA, ESCOPO_DESCRICOES, ESCOPO_ROTULOS,
  ordenarEscopos, rotuloDeEscopo, rotuloDeStatus,
} from "@/app/components/tokens/escopo-rotulos"

describe("escopo-rotulos", () => {
  it("cobre os seis escopos do contrato, na ordem canônica", () => {
    expect(ESCOPOS).toEqual([
      "workflows:read", "workflows:write", "runs:execute", "triggers:manage", "drive:read", "drive:write",
    ])
    for (const escopo of ESCOPOS) {
      expect(ESCOPO_ROTULOS[escopo]).toBeTruthy()
      expect(ESCOPO_DESCRICOES[escopo]).toBeTruthy()
    }
  })

  it("rótulos curtos em pt-BR", () => {
    expect(rotuloDeEscopo("workflows:read")).toBe("Ler fluxos")
    expect(rotuloDeEscopo("workflows:write")).toBe("Criar e editar fluxos")
    expect(rotuloDeEscopo("runs:execute")).toBe("Executar fluxos")
    expect(rotuloDeEscopo("triggers:manage")).toBe("Gerenciar agendamentos e webhooks")
    expect(rotuloDeEscopo("drive:read")).toBe("Ler o Drive")
    expect(rotuloDeEscopo("drive:write")).toBe("Enviar arquivos ao Drive")
  })

  it("escopo desconhecido volta cru no rótulo, sem quebrar", () => {
    expect(rotuloDeEscopo("admin:everything")).toBe("admin:everything")
  })

  it("ordenarEscopos devolve a ordem canônica e ignora o que não conhece", () => {
    expect(ordenarEscopos(["drive:read", "workflows:read", "x:y"])).toEqual(["workflows:read", "drive:read"])
    expect(ordenarEscopos([])).toEqual([])
  })

  it("«Somente leitura» é ler fluxos + ler o Drive", () => {
    expect(ESCOPOS_SOMENTE_LEITURA).toEqual(["workflows:read", "drive:read"])
  })

  it("status sempre traduzido, com fallback", () => {
    expect(rotuloDeStatus("active")).toBe("Ativo")
    expect(rotuloDeStatus("expired")).toBe("Expirado")
    expect(rotuloDeStatus("revoked")).toBe("Revogado")
    expect(rotuloDeStatus(null)).toBe("—")
    expect(rotuloDeStatus("weird")).toBe("weird")
  })
})
