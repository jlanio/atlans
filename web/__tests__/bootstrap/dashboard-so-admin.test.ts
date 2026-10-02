/**
 * Quem não administra o sistema só alcança a Home (`/`) — por enquanto, decisão
 * do dono. O middleware devolve `/` para QUALQUER outra página (o antigo portão
 * de /admin e /dashboard é um caso particular disto); o proxy /terra nunca é
 * redirecionado e os arquivos do public/ não são páginas. Este teste tranca o
 * portão: admin passa em tudo, não-admin só na Home, sessão sem papel falha
 * fechada.
 *
 * E o portão de SESSÃO: a Home abre sem sessão (a entrada é um modal no
 * primeiro envio) e nunca é redirecionada — nem com a sessão vencida, que o
 * SessionSync limpa no cliente (redirecioná-la para `/?entrar=1`, que está
 * dentro do matcher, seria um laço). Fora dela, quem não tem sessão vai para a
 * Home com o modal aberto e o `callbackUrl` de volta.
 *
 * O mock de `next-auth` faz `auth: (fn) => fn`, então o default export do
 * middleware é o handler cru — dá para chamá-lo com uma Request falsa. `@/auth`
 * é stubado nos helpers puros (não queremos gravar SESSION_HEADER aqui).
 */
import { describe, it, expect, vi } from "vitest"

vi.mock("next-auth", () => ({
  default: () => ({ handlers: {}, signIn: vi.fn(), signOut: vi.fn(), auth: (fn: unknown) => fn }),
}))
vi.mock("next-auth/providers/credentials", () => ({ default: () => ({}) }))
vi.mock("@/auth", () => ({
  auth: (fn: unknown) => fn,
  SESSION_HEADER: "x-atlans-session",
  // null => o middleware não seta o cabeçalho de sessão; irrelevante para o portão.
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

describe("portão de papel: quem não é admin só alcança a Home", () => {
  it("não-admin em qualquer página fora de / volta para a Home", async () => {
    for (const p of ["/projects", "/workflow/abc", "/drive", "/settings/tokens", "/workspaces", "/history"]) {
      const loc = await destino(p, "user")
      expect(loc, p).toBeTruthy()
      expect(caminho(loc), p).toBe("/")
    }
  })

  it("o portão antigo de /dashboard e /admin continua valendo", async () => {
    for (const p of ["/dashboard", "/dashboard/qualquer", "/admin/users"]) {
      expect(caminho(await destino(p, "user")), p).toBe("/")
    }
  })

  it("não-admin em / passa (sem redirect)", async () => {
    // NextResponse.next() não carrega location; o middleware seguiu adiante.
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

  it("sessão sem papel falha fechada: volta para a Home", async () => {
    expect(caminho(await destino("/projects", null, { user: {} }))).toBe("/")
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
