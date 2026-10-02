import { describe, it, expect } from "vitest"
import {
  CREDENTIAL_TYPE_STYLES,
  DEFAULT_CREDENTIAL_TYPE_STYLE,
  getCredentialTypeStyle,
} from "@/consts/CredentialTypeStyles"

/**
 * Os tipos abaixo espelham CREDENTIAL_TYPE_SCHEMAS em
 * app/core/credentials/schemas.py. Se o backend ganhar um tipo novo e ninguem
 * lembrar do mapa visual, este teste falha e aponta qual ficou de fora — a UI
 * nao quebra (cai no DEFAULT), mas a credencial apareceria com o icone generico
 * sem que ninguem percebesse.
 */
const TIPOS_DO_BACKEND = [
  "postgresql",
  "mysql",
  "s3",
  "http_bearer",
  "http_basic",
  "webhook_token",
  "smtp",
  "wfs",
  "geoserver_authkey",
]

describe("CredentialTypeStyles", () => {
  it.each(TIPOS_DO_BACKEND)("tem entrada para o tipo '%s'", tipo => {
    expect(CREDENTIAL_TYPE_STYLES[tipo]).toBeDefined()
  })

  it("nao tem entrada sobrando que o backend nao conheca", () => {
    expect(Object.keys(CREDENTIAL_TYPE_STYLES).sort()).toEqual([...TIPOS_DO_BACKEND].sort())
  })

  it.each(Object.entries(CREDENTIAL_TYPE_STYLES))(
    "'%s' tem icone e cores com variante dark",
    (_tipo, style) => {
      expect(style.icon).toBeTypeOf("function")
      expect(style.bg).toMatch(/^bg-/)
      // A variante dark: e o ponto do contraste — `text-<cor>-600` sozinho fica
      // abaixo de 4.5:1 sobre `bg-<cor>-500/10` no tema escuro.
      expect(style.fg).toContain("dark:")
    },
  )

  describe("getCredentialTypeStyle", () => {
    it("resolve um tipo conhecido", () => {
      expect(getCredentialTypeStyle("postgresql")).toBe(CREDENTIAL_TYPE_STYLES.postgresql)
    })

    it.each([["tipo-inexistente"], [""], [undefined], [null]])(
      "cai no default para %p",
      entrada => {
        expect(getCredentialTypeStyle(entrada as string)).toBe(DEFAULT_CREDENTIAL_TYPE_STYLE)
      },
    )
  })
})
