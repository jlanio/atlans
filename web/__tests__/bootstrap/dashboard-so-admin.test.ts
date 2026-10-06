/**
 * Whoever does not administer the system reaches the Home (`/`) and the Workspace
 * (the rest of the app, the other side of the Chat / Workspace switcher, the
 * Dashboard included); only /admin stays for the admin, and the middleware
 * returns `/` for it. The /terra proxy is never redirected and the files in public/ are not
 * pages. This test locks the gate: admin gets through everything, non-admin
 * everything but /admin, a session with no role fails closed.
 *
 * And the SESSION gate: the Home opens without a session (sign-in is a modal on the
 * first submit) and is never redirected — not even with an expired session, which
 * SessionSync clears on the client (redirecting it to `/?entrar=1`, which is
 * inside the matcher, would be a loop). Outside it, whoever has no session goes to the
 * Home with the modal open and the `callbackUrl` to come back.
 *
 * The `next-auth` mock does `auth: (fn) => fn`, so the middleware's default export
 * is the raw handler — it can be called with a fake Request. `@/auth`
 * is stubbed in the pure helpers (we do not want to write SESSION_HEADER here).
 */
import { describe, it, expect, vi } from "vitest"

vi.mock("next-auth", () => ({
  default: () => ({ handlers: {}, signIn: vi.fn(), signOut: vi.fn(), auth: (fn: unknown) => fn }),
}))
vi.mock("next-auth/providers/credentials", () => ({ default: () => ({}) }))
vi.mock("@/auth", () => ({
  auth: (fn: unknown) => fn,
  SESSION_HEADER: "x-atlans-session",
  // null => the middleware does not set the session header; irrelevant to the gate.
  encodeSessionHeader: () => null,
}))

import middleware from "@/proxy"

type Papel = "admin" | "user"

function req(pathname: string, role: Papel | null, auth?: unknown) {
  return {
    auth: auth !== undefined ? auth : role ? { user: { role } } : null,
    nextUrl: { pathname },
    url: `http://localhost${pathname}`,
    headers: new Headers(),
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const handler = middleware as unknown as (r: any) => Promise<Response> | Response

async function destino(pathname: string, role: Papel | null, auth?: unknown): Promise<string | null> {
  const res = await handler(req(pathname, role, auth))
  return res.headers.get("location")
}

const caminho = (loc: string | null) => new URL(loc as string).pathname

describe("portão de papel: quem não é admin alcança a Home e o Workspace", () => {
  it("não-admin entra no Workspace: as páginas fora de /admin passam, o Dashboard também", async () => {
    for (const p of [
      "/dashboard", "/dashboard/qualquer", "/projects", "/workflow/abc", "/drive", "/settings/tokens", "/workspaces",
      "/credentials", "/executores", "/observability", "/artifacts",
    ]) {
      expect(await destino(p, "user"), p).toBeNull()
    }
  })

  it("/admin continua só do admin: não-admin volta para a Home", async () => {
    for (const p of ["/admin", "/admin/users", "/admin/settings"]) {
      expect(caminho(await destino(p, "user")), p).toBe("/")
    }
  })

  it("o casamento é por segmento: /administrativo não é /admin", async () => {
    expect(await destino("/administrativo", "user")).toBeNull()
  })

  it("não-admin em / passa (sem redirect)", async () => {
    // NextResponse.next() carries no location; the middleware moved on.
    expect(await destino("/", "user")).toBeNull()
  })

  it("o proxy /terra nunca é redirecionado: a Home vive dele", async () => {
    expect(await destino("/terra/assistente/estado", "user")).toBeNull()
    expect(await destino("/terra/assistente/conversa", "user")).toBeNull()
  })

  it("arquivos do public/ passam: não são páginas", async () => {
    expect(await destino("/logo.svg", "user")).toBeNull()
    expect(await destino("/icons/marca.png", "user")).toBeNull()
  })

  it("sessão sem papel falha fechada: /admin volta para a Home", async () => {
    expect(caminho(await destino("/admin/users", null, { user: {} }))).toBe("/")
  })

  it("admin passa em tudo: /projects, /dashboard, /admin", async () => {
    for (const p of ["/projects", "/dashboard", "/admin/users", "/settings/tokens"]) {
      expect(await destino(p, "admin"), p).toBeNull()
    }
  })

  it("sem sessão, o destino é a entrada (o portão de papel vem depois da autenticação)", async () => {
    expect(caminho(await destino("/projects", null))).toBe("/")
  })
})

describe("portão de sessão: a Home abre sem sessão; o resto vai para a entrada", () => {
  const query = (loc: string | null) => new URL(loc as string).searchParams

  it("sem sessão, / passa — a Home anônima", async () => {
    expect(await destino("/", null)).toBeNull()
  })

  it("sem sessão, uma página vai para a Home com o modal e o callbackUrl de volta", async () => {
    const loc = await destino("/projects", null)
    expect(caminho(loc)).toBe("/")
    expect(query(loc).get("entrar")).toBe("1")
    expect(query(loc).get("callbackUrl")).toBe("/projects")
  })

  it("sessão vencida: uma página vai para a entrada; em / passa (senão seria um laço)", async () => {
    const vencida = { user: { role: "user" }, error: "RefreshTokenExpired" }
    const loc = await destino("/projects", null, vencida)
    expect(caminho(loc)).toBe("/")
    expect(query(loc).get("entrar")).toBe("1")
    expect(query(loc).get("callbackUrl")).toBe("/projects")
    expect(await destino("/", null, vencida)).toBeNull()
  })

  it("arquivos do public/ passam sem sessão", async () => {
    expect(await destino("/logo.svg", null)).toBeNull()
    expect(await destino("/manifest.webmanifest", null)).toBeNull()
  })

  it("o proxy /terra nunca é redirecionado, nem sem sessão", async () => {
    expect(await destino("/terra/assistente/estado", null)).toBeNull()
  })
})
