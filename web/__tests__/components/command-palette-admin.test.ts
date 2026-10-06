/**
 * Admin items of the command palette. Usuários and Configurações are system
 * administrator routes (`proxy.ts` keeps /admin for the admin) — before, the
 * palette offered them to everyone and only the middleware blocked them, ending
 * in a redirect. They carry the `admin` mark and `itensVisiveis` hides them from
 * non-admins. The Dashboard is open to everyone (the API filters its numbers).
 *
 * Tested at the pure level (the function and the list, no render): the visibility rule
 * depends on neither the session nor the DOM.
 */
import { describe, it, expect, vi } from "vitest"
import { STATIC_ITEMS, itensVisiveis, paletaDisponivel } from "@/app/components/command-palette"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const router = { push: vi.fn() } as any
const ids = (itens: { id: string }[]) => itens.map(i => i.id)

const SO_ADMIN = ["users", "settings"]

describe("itensVisiveis", () => {
  it("esconde os itens de admin de quem não é admin", () => {
    const visiveis = ids(itensVisiveis(STATIC_ITEMS(router), false))
    for (const id of SO_ADMIN) expect(visiveis).not.toContain(id)
    // The rest stays visible.
    expect(visiveis).toContain("dashboard")
    expect(visiveis).toContain("projects")
    expect(visiveis).toContain("drive")
    expect(visiveis).toContain("new-workflow")
    // "planos" is NOT here: the route no longer exists (in an install with the
    // plans, they are a modal opened from the account menu). A palette item
    // would `router.push` into nothing — and the palette does not even open on the Home for
    // non-admins.
    expect(visiveis).not.toContain("planos")
  })

  it("mostra tudo para o admin", () => {
    const visiveis = ids(itensVisiveis(STATIC_ITEMS(router), true))
    for (const id of SO_ADMIN) expect(visiveis).toContain(id)
  })

  it("exatamente Usuários e Configurações são marcados admin", () => {
    // Guards the mark: if someone marks (or unmarks) an item by mistake, this fails.
    const marcados = STATIC_ITEMS(router).filter(i => i.admin).map(i => i.id).sort()
    expect(marcados).toEqual([...SO_ADMIN].sort())
  })
})

describe("paletaDisponivel", () => {
  // The Home does not OFFER a way out to someone who does not administer the system. It is not access
  // control: what blocks is `proxy.ts`, which keeps /admin for the admin.
  it("na Home, só o admin tem paleta", () => {
    expect(paletaDisponivel("/", false)).toBe(false)
    expect(paletaDisponivel("/", true)).toBe(true)
  })

  it("fora da Home, todo mundo tem", () => {
    for (const rota of ["/projects", "/drive", "/workflow/abc", "/dashboard"]) {
      expect(paletaDisponivel(rota, false)).toBe(true)
    }
  })

  it("a Home é casamento EXATO, não prefixo", () => {
    // A `startsWith("/")` would match the whole app; and a route that merely STARTS with
    // "/" followed by more is never the Home.
    expect(paletaDisponivel("/projetos", false)).toBe(true)
    expect(paletaDisponivel("/*", false)).toBe(true)
  })

  it("pathname ausente não fecha a paleta", () => {
    // `usePathname()` can return null outside a resolved route; closing there
    // would hide the palette from the whole app because of a transient state.
    expect(paletaDisponivel(null, false)).toBe(true)
    expect(paletaDisponivel(undefined, false)).toBe(true)
  })
})
