/**
 * Catch-all proxy: /terra/:path* → API_INTERNA/:path*
 *
 * Reads API_INTERNA at runtime (not at build time), so it works regardless of
 * where the image runs.
 *
 * Security: every path requires a valid NextAuth session, except those
 * listed in PUBLIC_PREFIXES / PUBLIC_SUFFIXES (public map portal).
 */
import { type NextRequest, NextResponse } from "next/server"
import { auth, SESSION_HEADER, decodeSessionHeader } from "@/auth"

const UPSTREAM = process.env.API_INTERNA ?? "http://localhost:8000"

// Paths accessible without authentication (public map portal and healthcheck)
const PUBLIC_PREFIXES = ["artifacts/portal/", "artifacts/tiles/", "auth/"]
const PUBLIC_SUFFIXES = ["/download"]

// Headers that must not be forwarded to the upstream
const HOP_BY_HOP = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
  "te", "trailer", "transfer-encoding", "upgrade", "host",
  // Lets Node.js fetch manage compression — avoids content-encoding conflicts
  "accept-encoding",
])

// TRUST headers that the client must NOT be able to inject. The API trusts the
// mTLS certificate header when the peer is in TRUSTED_PROXIES — and the web
// container IS. If /terra forwarded that header coming from the browser, an
// authenticated user could forge an executor's mTLS identity
// (X-Forwarded-Tls-Client-Cert-Info). They are removed here, always; Traefik is
// what legitimately injects them on the API's direct routes.
//
// X-Forwarded-For is the exception and DOES go on to the API. web-prod is only
// reachable through Traefik (no published port), which rewrites the XFF coming
// from a peer outside the Cloudflare ranges and, coming from them, appends its
// peer's IP; the API reads the header right to left (`get_client_ip`), skipping
// our infra and at most ONE Cloudflare edge — the next IP is the one Cloudflare
// appended, and whatever the client (or a Worker) writes to the left does not
// change the resolved one. Without the XFF, the API saw only the web container's
// IP and all users shared a single rate-limit bucket.
function isCabecalhoDeConfianca(k: string): boolean {
  if (k === "x-forwarded-for") return false
  return (
    k.startsWith("x-forwarded-") ||
    k === "forwarded" ||
    k === "x-real-ip" ||
    k === "cf-connecting-ip" ||
    k === "x-client-cert" ||
    k === "ssl-client-cert" ||
    k === "x-ssl-client-cert"
  )
}

// Suspicious path segment: empty, "." or "..", or with a backslash /
// control characters. fetch's URL parser treats "\" as "/" and strips
// TAB/LF, so a reconstructed "..\\" or ".%09." would escape the public prefix
// list and reach routes not published in Traefik (/openapi.json, /docs).
function segmentoSuspeito(seg: string): boolean {
  return (
    seg === "" || seg === "." || seg === ".." ||
    seg.includes("\\") || /[\u0000-\u001f\u007f]/.test(seg) || seg.includes("/")
  )
}

// CSRF: /terra turns the session cookie into a Bearer for the upstream, without
// checking the origin. A top-level POST from another site (an auto-submitted
// form) would arrive authenticated. For state-changing methods, it requires a
// same origin: blocks cross-site Sec-Fetch-Site and an Origin from another host.
function csrfBloqueado(req: NextRequest): boolean {
  const secFetchSite = req.headers.get("sec-fetch-site")
  if (secFetchSite === "cross-site") return true
  // Modern browsers assert same-origin: trust it and avoid comparing Host
  // (which a proxy may rewrite), while still blocking cross-site above.
  if (secFetchSite === "same-origin" || secFetchSite === "same-site") return false
  const origin = req.headers.get("origin")
  if (origin) {
    try {
      // Compares against the public host when the proxy preserves it (x-forwarded-host),
      // falling back to the direct Host.
      const alvo = req.headers.get("x-forwarded-host") || req.headers.get("host")
      if (alvo && new URL(origin).host !== alvo) return true
    } catch {
      return true
    }
  }
  return false
}

async function proxy(
  req: NextRequest,
  params: Promise<{ path: string[] }>,
): Promise<NextResponse> {
  const { path } = await params

  // Rejects path traversal BEFORE building the upstream URL or testing the
  // public prefixes (SEG-18).
  if (path.some(segmentoSuspeito)) {
    return NextResponse.json({ detail: "Caminho inválido" }, { status: 400 })
  }
  const pathStr = path.join("/")

  const isPublic =
    PUBLIC_PREFIXES.some((p) => pathStr.startsWith(p)) ||
    PUBLIC_SUFFIXES.some((s) => pathStr.endsWith(s))

  // CSRF on state-changing methods, outside the public paths (auth/ has
  // NextAuth's own CSRF; the portal is read-only).
  const mudaEstado = req.method !== "GET" && req.method !== "HEAD" && req.method !== "OPTIONS"
  if (mudaEstado && !isPublic && csrfBloqueado(req)) {
    return NextResponse.json({ detail: "Origem não permitida" }, { status: 403 })
  }

  // Access token the upstream is authenticated with (only on protected paths).
  let accessToken: string | null = null
  if (!isPublic) {
    // The session comes from the middleware via SESSION_HEADER — already RENEWED and
    // with the rotated cookie PERSISTED there. `await auth()` is only a safety net
    // for the rare case of the header missing (middleware did not run); on the
    // normal path it is NOT called, so this handler no longer fires the refresh
    // that rotated the family and discarded the cookie (the cause of the spurious
    // logout). Same pattern as the dashboard layout.
    const session = decodeSessionHeader(req.headers.get(SESSION_HEADER)) ?? (await auth())
    if (!session) {
      return NextResponse.json({ detail: "Não autenticado" }, { status: 401 })
    }
    accessToken = session.user?.access_token ?? null
  }

  const { search } = new URL(req.url)
  const upstream = `${UPSTREAM}/${pathStr}${search}`

  const headers = new Headers()
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase()
    if (HOP_BY_HOP.has(k)) return
    if (isCabecalhoDeConfianca(k)) return // does not let the client forge the mTLS cert
    headers.set(key, value)
  })
  // SESSION_HEADER is for internal use (middleware → handler): it never leaks to the upstream.
  headers.delete(SESSION_HEADER)
  // Authenticates the upstream with the SERVER's access token (renewed by the
  // middleware), and not with the client's Authorization — which, in a long
  // polling-only session, goes stale until useSession refreshes it, producing a
  // 401 in the backend even without a logout.
  // On public paths the client's Bearer (when present) passes through intact.
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)

  // A small body (known content-length, ≤32MB) is BUFFERED; the rest
  // goes as a stream.
  //
  // The buffer is a safety net against the trailing-slash redirect. The API's
  // canonical URL has NO slash (collection routes declared as "" in the
  // routers), aligned with Next, which strips the slash from the browser (308) —
  // on the normal path there is no redirect at all. But if a new route is born
  // with "/", FastAPI answers 307; an already consumed streamed body cannot be
  // resent and the mutation would become a 502 (which Cloudflare presents as
  // "invalid or incomplete response" — it was a real incident in 2026-09). An
  // ArrayBuffer can be resent, so the 307 is followed and the request works.
  //
  // Streaming remains for large/non-JSON bodies (Drive uploads): buffering
  // there cost 3× the file size in Node's memory and no byte reached FastAPI
  // before the upload finished going up to Next.
  // `duplex: "half"` is mandatory for a streamed body (Node runtime).
  // Buffer ceiling: above it not even JSON is buffered (memory protection for
  // web-prod, which runs with a 512MB limit) — it goes as a stream and, if a
  // redirect shows up, falls into the guard that fails loudly.
  const BUFFER_MAX = 33_554_432 // 32MB
  let body: BodyInit | null = null
  let bodyReenviavel = false
  if (req.method !== "GET" && req.method !== "HEAD") {
    const contentLength = Number(req.headers.get("content-length") ?? NaN)
    if (Number.isFinite(contentLength) && contentLength <= BUFFER_MAX) {
      body = await req.arrayBuffer()
      bodyReenviavel = true
    } else {
      body = req.body
    }
  }
  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers,
    redirect: "manual",
    ...(body != null ? { body, duplex: "half" as const } : {}),
  }

  let res: Response
  try {
    res = await fetch(upstream, init)

    // Manual follow of the redirect.
    // SEC: validates that the redirect stays on the same upstream (prevents SSRF).
    if (res.status >= 300 && res.status < 400) {
      const location = res.headers.get("location")
      if (location) {
        const redirectUrl = location.startsWith("http")
          ? location
          : new URL(location, upstream).toString()

        // Blocks redirects to hosts other than the upstream
        try {
          const upstreamHost = new URL(UPSTREAM).hostname
          const redirectHost = new URL(redirectUrl).hostname
          if (redirectHost !== upstreamHost) {
            console.warn(`[terra] redirect bloqueado: ${redirectUrl} (upstream: ${upstreamHost})`)
            return NextResponse.json({ detail: "Redirect para host externo bloqueado" }, { status: 400 })
          }
        } catch {
          return NextResponse.json({ detail: "URL de redirect inválida" }, { status: 400 })
        }

        // Resending the body is only legitimate on 307/308 (they preserve method+body).
        // A 303 requires switching to GET, and 301/302 on a POST become GET in
        // browsers — following those with the body re-POSTed would be inventing
        // semantics. A streamed body has already been consumed and cannot be
        // resent anyway. In both cases, fail loudly instead of sending the
        // browser a Location pointing to the internal host.
        const preservaMetodoECorpo = res.status === 307 || res.status === 308
        if (body != null && (!bodyReenviavel || !preservaMetodoECorpo)) {
          console.warn(`[terra] redirect ${res.status} em ${req.method} com corpo não reenviável: ${redirectUrl}`)
          return NextResponse.json({ detail: "Redirect não suportado neste método" }, { status: 502 })
        }

        const reinit: RequestInit & { duplex?: "half" } = {
          method: req.method,
          headers,
          redirect: "manual",
          ...(body != null ? { body, duplex: "half" as const } : {}),
        }
        res = await fetch(redirectUrl, reinit)
      }
    }
  } catch (err) {
    console.error(`[terra] falha ao conectar em ${upstream}:`, err)
    return NextResponse.json({ detail: "Serviço indisponível" }, { status: 502 })
  }

  // undici's fetch automatically decompresses gzip/br/deflate responses,
  // but keeps the original headers. Forwarding Content-Encoding to the browser
  // causes ERR_CONTENT_DECODING_FAILED — it tries to decompress an already
  // plain-text body. Content-Length is also wrong for the same reason.
  const STRIP_AFTER_DECODE = new Set(["content-encoding", "content-length"])

  const resHeaders = new Headers()
  res.headers.forEach((value, key) => {
    const k = key.toLowerCase()
    if (HOP_BY_HOP.has(k)) return
    if (STRIP_AFTER_DECODE.has(k)) return
    resHeaders.set(key, value)
  })

  return new NextResponse(res.body, { status: res.status, headers: resHeaders })
}

type Ctx = { params: Promise<{ path: string[] }> }

export async function GET    (req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params) }
export async function POST   (req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params) }
export async function PUT    (req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params) }
export async function PATCH  (req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params) }
export async function DELETE (req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params) }
export async function HEAD   (req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params) }
export async function OPTIONS(req: NextRequest, ctx: Ctx) { return proxy(req, ctx.params) }
