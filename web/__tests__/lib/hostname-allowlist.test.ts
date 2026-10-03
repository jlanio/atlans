/**
 * Mirrors `tests/unit/test_workspace_notifications_router.py` and the rules of
 * `app/core/utils/allowlist.py`.
 *
 * The notifications screen's preview computes "which workflows this allowlist
 * would block" on the client, to answer BEFORE saving. If this port diverges
 * from the Python, the screen promises one result and the run delivers another —
 * which is exactly the silent failure mode the screen exists to end.
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
    // The easiest rule to lose when porting — in Python it's `hostname != suffix[1:]`.
    expect(hostnameMatchesAllowlist("exemplo.com", ["*.exemplo.com"])).toBe(false)
  })

  it("não casa sufixo colado sem o ponto", () => {
    // "malexemplo.com" ends with "exemplo.com", but isn't a subdomain of it.
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
    // Inverted column semantics: no list means no additional policy.
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
    "https://exemplo.com/hook",  // the obvious mistake: pasting the whole URL
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
