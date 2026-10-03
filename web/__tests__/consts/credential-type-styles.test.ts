import { describe, it, expect } from "vitest"
import {
  CREDENTIAL_TYPE_STYLES,
  DEFAULT_CREDENTIAL_TYPE_STYLE,
  getCredentialTypeStyle,
} from "@/consts/CredentialTypeStyles"

/**
 * The types below mirror CREDENTIAL_TYPE_SCHEMAS in
 * app/core/credentials/schemas.py. If the backend gains a new type and nobody
 * remembers the visual map, this test fails and points out which one was left
 * out — the UI doesn't break (it falls back to DEFAULT), but the credential would
 * show up with the generic icon without anyone noticing.
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
      // The dark: variant is the point of the contrast — `text-<cor>-600` alone falls
      // below 4.5:1 over `bg-<cor>-500/10` in the dark theme.
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
