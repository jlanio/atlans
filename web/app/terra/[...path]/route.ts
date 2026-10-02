/**
 * Proxy catch-all: /terra/:path* → API_INTERNA/:path*
 *
 * Lê API_INTERNA em runtime (não em build time), portanto funciona
 * independentemente de onde a imagem é executada.
 *
 * Segurança: todos os paths exigem sessão NextAuth válida, exceto os
 * listados em PUBLIC_PREFIXES / PUBLIC_SUFFIXES (portal público de mapas).
 */
import { type NextRequest, NextResponse } from "next/server"
import { auth, SESSION_HEADER, decodeSessionHeader } from "@/auth"

const UPSTREAM = process.env.API_INTERNA ?? "http://localhost:8000"

// Paths acessíveis sem autenticação (portal público de mapas e healthcheck)
const PUBLIC_PREFIXES = ["artifacts/portal/", "artifacts/tiles/", "auth/"]
const PUBLIC_SUFFIXES = ["/download"]

// Headers que não devem ser repassados ao upstream
const HOP_BY_HOP = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
  "te", "trailer", "transfer-encoding", "upgrade", "host",
  // Deixa o fetch do Node.js gerenciar compressão — evita conflito de content-encoding
  "accept-encoding",
])

// Cabeçalhos de CONFIANÇA que o cliente NÃO pode injetar. A API confia no
// cabeçalho de certificado mTLS quando o peer está em TRUSTED_PROXIES — e o
// container web ESTÁ. Se o /terra repassasse esse cabeçalho vindo do browser,
// um usuário autenticado forjaria a identidade mTLS de um executor
// (X-Forwarded-Tls-Client-Cert-Info). São removidos aqui, sempre; o Traefik é
// quem legitimamente os injeta nas rotas diretas da API.
//
// O X-Forwarded-For é a exceção e SEGUE para a API. O web-prod só é alcançável
// pelo Traefik (sem porta publicada), que reescreve o XFF vindo de peer fora
// das faixas da Cloudflare e, vindo delas, anexa o IP do seu peer; a API lê o
// header da direita para a esquerda (`get_client_ip`), pulando a nossa infra e
// no máximo UM edge da Cloudflare — o IP seguinte é o que a Cloudflare anexou,
// e o que o cliente (ou um Worker) escreve à esquerda não muda o resolvido. Sem
// o XFF, a API via só o IP do container web e todos os usuários dividiam um
// único balde de rate limit.
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

// Segmento de path suspeito: vazio, "." ou "..", ou com barra invertida /
// caracteres de controle. O parser de URL do fetch trata "\" como "/" e remove
// TAB/LF, então "..\\" ou ".%09." reconstruído escaparia da lista de prefixos
// públicos e alcançaria rotas não publicadas no Traefik (/openapi.json, /docs).
function segmentoSuspeito(seg: string): boolean {
  return (
    seg === "" || seg === "." || seg === ".." ||
    seg.includes("\\") || /[\u0000-\u001f\u007f]/.test(seg) || seg.includes("/")
  )
}

// CSRF: o /terra transforma o cookie de sessão em Bearer para o upstream, sem
// checar origem. Um POST top-level de outro site (formulário auto-submetido)
// chegaria autenticado. Para métodos que mudam estado, exige origem própria:
// bloqueia Sec-Fetch-Site cross-site e Origin de outro host.
function csrfBloqueado(req: NextRequest): boolean {
  const secFetchSite = req.headers.get("sec-fetch-site")
  if (secFetchSite === "cross-site") return true
  // Navegadores modernos afirmam a origem própria: confia e evita comparar Host
  // (que um proxy pode reescrever), sem deixar de barrar o cross-site acima.
  if (secFetchSite === "same-origin" || secFetchSite === "same-site") return false
  const origin = req.headers.get("origin")
  if (origin) {
    try {
      // Compara com o host público quando o proxy o preserva (x-forwarded-host),
      // caindo no Host direto.
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

  // Rejeita travessia de path ANTES de montar a URL do upstream ou testar os
  // prefixos públicos (SEG-18).
  if (path.some(segmentoSuspeito)) {
    return NextResponse.json({ detail: "Caminho inválido" }, { status: 400 })
  }
  const pathStr = path.join("/")

  const isPublic =
    PUBLIC_PREFIXES.some((p) => pathStr.startsWith(p)) ||
    PUBLIC_SUFFIXES.some((s) => pathStr.endsWith(s))

  // CSRF em métodos que mudam estado, fora dos paths públicos (auth/ tem CSRF
  // próprio do NextAuth; portal é leitura).
  const mudaEstado = req.method !== "GET" && req.method !== "HEAD" && req.method !== "OPTIONS"
  if (mudaEstado && !isPublic && csrfBloqueado(req)) {
    return NextResponse.json({ detail: "Origem não permitida" }, { status: 403 })
  }

  // Token de acesso com que o upstream é autenticado (só em paths protegidos).
  let accessToken: string | null = null
  if (!isPublic) {
    // A sessão vem do middleware via SESSION_HEADER — já RENOVADA e com o cookie
    // rotacionado PERSISTIDO lá. `await auth()` é só rede de segurança para o
    // caso raro de o header faltar (middleware não rodou); no caminho normal ele
    // NÃO é chamado, então este handler não dispara mais o refresh que rotacionava
    // a família e descartava o cookie (a causa do logout espúrio). Mesmo padrão
    // do layout do dashboard.
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
    if (isCabecalhoDeConfianca(k)) return // não deixa o cliente forjar o cert mTLS
    headers.set(key, value)
  })
  // SESSION_HEADER é de uso interno (middleware → handler): nunca vaza ao upstream.
  headers.delete(SESSION_HEADER)
  // Autentica o upstream com o access token do SERVIDOR (renovado pelo middleware),
  // e não com o Authorization do cliente — que, numa sessão longa só de polling,
  // fica velho até o useSession refazer, gerando 401 no backend mesmo sem logout.
  // Em paths públicos o Bearer do cliente (quando houver) segue intacto.
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)

  // Corpo pequeno (content-length conhecido, ≤32MB) é BUFFERIZADO; o resto
  // segue em stream.
  //
  // O buffer é rede de segurança contra o redirect de barra final. A URL
  // canônica da API é SEM barra (rotas de coleção declaradas como "" nos
  // routers), alinhada com o Next, que remove a barra do browser (308) — no
  // caminho normal não há redirect nenhum. Mas se uma rota nova nascer com "/",
  // o FastAPI responde 307; um corpo em stream já consumido não pode ser
  // reenviado e a mutação viraria 502 (que o Cloudflare apresenta como "invalid
  // or incomplete response" — foi um incidente real em 2026-09). Um ArrayBuffer
  // é reenviável, então o 307 é seguido e a requisição funciona.
  //
  // O streaming continua para corpos grandes/sem JSON (uploads do Drive):
  // bufferizar ali custava 3× o tamanho do arquivo na memória do Node e nenhum
  // byte chegava ao FastAPI antes do upload terminar de subir para o Next.
  // `duplex: "half"` é obrigatório para body em stream (runtime Node).
  // Teto do buffer: acima disso nem JSON é bufferizado (proteção de memória do
  // web-prod, que roda com limite de 512MB) — segue em stream e, se um redirect
  // aparecer, cai no guard que falha alto.
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

    // Follow manual do redirect.
    // SEG: valida que o redirect permanece no mesmo upstream (previne SSRF).
    if (res.status >= 300 && res.status < 400) {
      const location = res.headers.get("location")
      if (location) {
        const redirectUrl = location.startsWith("http")
          ? location
          : new URL(location, upstream).toString()

        // Bloqueia redirects para hosts diferentes do upstream
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

        // Reenviar o corpo só é legítimo em 307/308 (preservam método+corpo).
        // Um 303 exige virar GET, e 301/302 num POST viram GET nos browsers —
        // seguir esses com o corpo re-POSTado seria inventar semântica. Corpo
        // em stream já foi consumido e não há como reenviá-lo de todo modo.
        // Nos dois casos, falha alto em vez de mandar ao browser um Location
        // apontando para o host interno.
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

  // O fetch do undici descomprime automaticamente respostas gzip/br/deflate,
  // mas mantém os headers originais. Repassar Content-Encoding ao browser causa
  // ERR_CONTENT_DECODING_FAILED — ele tenta descomprimir um body já em texto.
  // Content-Length também fica errado pelo mesmo motivo.
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
