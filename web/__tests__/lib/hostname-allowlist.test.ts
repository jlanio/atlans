/**
 * Espelha `tests/unit/test_workspace_notifications_router.py` e as regras de
 * `app/core/utils/allowlist.py`.
 *
 * O preview da tela de notificações calcula "quais workflows esta allowlist
 * bloquearia" no cliente, para responder ANTES de salvar. Se este port divergir
 * do Python, a tela promete um resultado e a execução entrega outro — que é
 * exatamente o modo de falha silencioso que a tela existe para acabar.
 */
import { describe, it, expect } from "vitest"
import {
  hostnameMatchesAllowlist,
  isHostAllowed,
  validateAllowlistPattern,
} from "@/lib/hostname-allowlist"

describe("hostnameMatchesAllowlist", () => {
  it("casa o host exato", () => {
    expect(hostnameMatchesAllowlist("exemplo.com", ["exemplo.com"])).toBe(true)
    expect(hostnameMatchesAllowlist("evil.com", ["exemplo.com"])).toBe(false)
  })

  it("ignora caixa e espaços dos dois lados", () => {
    expect(hostnameMatchesAllowlist("  Exemplo.COM ", [" exemplo.com "])).toBe(true)
  })

  it("curinga cobre subdomínios em qualquer profundidade", () => {
    expect(hostnameMatchesAllowlist("api.exemplo.com", ["*.exemplo.com"])).toBe(true)
    expect(hostnameMatchesAllowlist("a.b.exemplo.com", ["*.exemplo.com"])).toBe(true)
  })

  it("curinga NÃO cobre o domínio nu", () => {
    // A regra mais fácil de perder ao portar — no Python é `hostname != suffix[1:]`.
    expect(hostnameMatchesAllowlist("exemplo.com", ["*.exemplo.com"])).toBe(false)
  })

  it("não casa sufixo colado sem o ponto", () => {
    // "malexemplo.com" termina com "exemplo.com", mas não é subdomínio dele.
    expect(hostnameMatchesAllowlist("malexemplo.com", ["*.exemplo.com"])).toBe(false)
  })

  it("host vazio nunca casa", () => {
    expect(hostnameMatchesAllowlist("", ["exemplo.com"])).toBe(false)
  })

  it("padrões vazios na lista são ignorados", () => {
    expect(hostnameMatchesAllowlist("exemplo.com", ["", "  ", "exemplo.com"])).toBe(true)
  })
})

describe("isHostAllowed", () => {
  it("allowlist vazia libera tudo", () => {
    // Semântica invertida da coluna: sem lista, não há política adicional.
    expect(isHostAllowed("qualquer.host", [])).toBe(true)
  })

  it("com allowlist, só o que casa passa", () => {
    expect(isHostAllowed("api.exemplo.com", ["*.exemplo.com"])).toBe(true)
    expect(isHostAllowed("evil.com", ["*.exemplo.com"])).toBe(false)
  })
})

describe("validateAllowlistPattern", () => {
  it("aceita as duas formas suportadas", () => {
    expect(validateAllowlistPattern("exemplo.com")).toBeNull()
    expect(validateAllowlistPattern("*.exemplo.com")).toBeNull()
  })

  it.each([
    "https://exemplo.com/hook",  // o engano óbvio: colar a URL inteira
    "exemplo.com/hook",
    "exemplo.com:8443",
    "user@exemplo.com",
  ])("rejeita o que não é hostname: %s", entrada => {
    expect(validateAllowlistPattern(entrada)).not.toBeNull()
  })

  it.each(["*", "*exemplo.com", "*.com", "localhost"])(
    "rejeita padrão que o matcher ignoraria: %s",
    entrada => {
      expect(validateAllowlistPattern(entrada)).not.toBeNull()
    },
  )

  it("rejeita entrada vazia", () => {
    expect(validateAllowlistPattern("   ")).not.toBeNull()
  })
})
