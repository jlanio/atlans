/**
 * The /terra proxy stopped calling `await auth()` (which renewed and DISCARDED the
 * rotated cookie → spurious logout): it reads the session from the SESSION_HEADER injected
 * by the middleware, and authenticates the upstream with the SERVER's (fresh) access token
 * instead of the client's possibly stale Bearer. Public paths still go without a
 * session, with the client's Bearer intact.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import type { NextRequest } from "next/server"

const authMock = vi.fn()
const decodeMock = vi.fn()
vi.mock("@/auth", () => ({
  auth: () => authMock(),
  SESSION_HEADER: "x-atlans-session",
  decodeSessionHeader: (raw: string | null) => decodeMock(raw),
}))

import { GET, POST } from "@/app/terra/[...path]/route"

const fetchMock = vi.fn()
beforeEach(() => {
  authMock.mockReset(); decodeMock.mockReset(); fetchMock.mockReset()
  fetchMock.mockResolvedValue(new Response("ok", { status: 200 }))
  vi.stubGlobal("fetch", fetchMock)
})

function req(path: string, headers: Record<string, string> = {}): NextRequest {
  return {
    url: `http://localhost/terra/${path}`,
    method: "GET",
    headers: new Headers(headers),
  } as unknown as NextRequest
}
const ctx = (path: string[]) => ({ params: Promise.resolve({ path }) })

// A state-changing request, with a resendable body (arrayBuffer) and POST method.
function post(path: string, headers: Record<string, string> = {}): NextRequest {
  return {
    url: `http://localhost/terra/${path}`,
    method: "POST",
    headers: new Headers({ "content-length": "2", ...headers }),
    arrayBuffer: async () => new TextEncoder().encode("{}").buffer,
    body: null,
  } as unknown as NextRequest
}
const authHeaderEnviado = () =>
  (fetchMock.mock.calls[0][1] as RequestInit).headers as Headers

describe("proxy /terra — autenticação", () => {
  it("path protegido sem sessão → 401 e NÃO chama o upstream", async () => {
    decodeMock.mockReturnValue(null)
    authMock.mockResolvedValue(null)
    const res = await GET(req("workflows"), ctx(["workflows"]))
    expect(res.status).toBe(401)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("path protegido: lê a sessão do SESSION_HEADER (sem chamar auth) e autentica o upstream com o token do servidor", async () => {
    decodeMock.mockReturnValue({ user: { access_token: "SERVIDOR-FRESCO" } })
    const res = await GET(
      req("workflows", { authorization: "Bearer CLIENTE-VELHO", "x-atlans-session": "HDR" }),
      ctx(["workflows"]),
    )
    expect(res.status).toBe(200)
    expect(authMock).not.toHaveBeenCalled()             // the normal path does not call auth()
    expect(decodeMock).toHaveBeenCalledWith("HDR")
    // Upstream authenticated with the server's token, not with the client's Bearer
    expect(authHeaderEnviado().get("authorization")).toBe("Bearer SERVIDOR-FRESCO")
    // and the internal header never leaks to the upstream
    expect(authHeaderEnviado().get("x-atlans-session")).toBeNull()
    // passes the path on to the upstream
    expect(String(fetchMock.mock.calls[0][0]).endsWith("/workflows")).toBe(true)
  })

  it("fallback a auth() quando o SESSION_HEADER falta (middleware não rodou)", async () => {
    decodeMock.mockReturnValue(null)
    authMock.mockResolvedValue({ user: { access_token: "VIA-AUTH" } })
    const res = await GET(req("workflows"), ctx(["workflows"]))
    expect(res.status).toBe(200)
    expect(authMock).toHaveBeenCalled()
    expect(authHeaderEnviado().get("authorization")).toBe("Bearer VIA-AUTH")
  })

  it("path público: não exige sessão, não chama auth, e preserva o Bearer do cliente", async () => {
    const res = await GET(
      req("artifacts/portal/mapa", { authorization: "Bearer CLIENTE" }),
      ctx(["artifacts", "portal", "mapa"]),
    )
    expect(res.status).toBe(200)
    expect(authMock).not.toHaveBeenCalled()
    expect(decodeMock).not.toHaveBeenCalled()
    expect(authHeaderEnviado().get("authorization")).toBe("Bearer CLIENTE")
  })
})

describe("proxy /terra — endurecimento (auditoria)", () => {
  it("SEG-18: recusa travessia de path (segmento '..') com 400, sem chamar o upstream", async () => {
    decodeMock.mockReturnValue({ user: { access_token: "T" } })
    const res = await GET(req("workflows/../admin/users"), ctx(["workflows", "..", "admin", "users"]))
    expect(res.status).toBe(400)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("SEG-15: não repassa o cabeçalho de certificado mTLS nem os demais cabeçalhos de proxy do cliente", async () => {
    decodeMock.mockReturnValue({ user: { access_token: "T" } })
    const res = await GET(
      req("workflows", {
        "x-atlans-session": "HDR",
        "x-forwarded-tls-client-cert-info": 'Subject="CN=executor-x";SerialNumber="9"',
        "x-forwarded-host": "evil.example",
        "x-real-ip": "1.2.3.4",
        forwarded: "for=1.2.3.4",
      }),
      ctx(["workflows"]),
    )
    expect(res.status).toBe(200)
    const h = authHeaderEnviado()
    expect(h.get("x-forwarded-tls-client-cert-info")).toBeNull()
    expect(h.get("x-forwarded-host")).toBeNull()
    expect(h.get("x-real-ip")).toBeNull()
    expect(h.get("forwarded")).toBeNull()
  })

  it("repassa o X-Forwarded-For: sem ele a API vê só o IP do container web e o rate limit vira um balde único", async () => {
    // The API reads XFF from right to left; Traefik appends the real IP at the
    // end, so what the client writes on the left does not change the resolved IP.
    decodeMock.mockReturnValue({ user: { access_token: "T" } })
    const res = await GET(
      req("workflows", { "x-atlans-session": "HDR", "x-forwarded-for": "9.9.9.9, 203.0.113.7, 162.158.1.1" }),
      ctx(["workflows"]),
    )
    expect(res.status).toBe(200)
    expect(authHeaderEnviado().get("x-forwarded-for")).toBe("9.9.9.9, 203.0.113.7, 162.158.1.1")
  })

  it("SEG-63: POST cross-site (Sec-Fetch-Site) é bloqueado com 403, sem chamar o upstream", async () => {
    decodeMock.mockReturnValue({ user: { access_token: "T" } })
    const res = await POST(post("workflows", { "sec-fetch-site": "cross-site", host: "atlans.example.org" }), ctx(["workflows"]))
    expect(res.status).toBe(403)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("SEG-63: POST de outra Origin é bloqueado com 403", async () => {
    decodeMock.mockReturnValue({ user: { access_token: "T" } })
    const res = await POST(post("workflows", { origin: "https://evil.example", host: "atlans.example.org" }), ctx(["workflows"]))
    expect(res.status).toBe(403)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("POST same-origin passa", async () => {
    decodeMock.mockReturnValue({ user: { access_token: "T" } })
    const res = await POST(post("workflows", { origin: "https://atlans.example.org", host: "atlans.example.org", "sec-fetch-site": "same-origin" }), ctx(["workflows"]))
    expect(res.status).toBe(200)
    expect(fetchMock).toHaveBeenCalled()
  })
})
