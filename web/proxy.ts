// O portão de sessão e de papel do web. Até o Next 15 era o `middleware.ts`;
// o Next 16 renomeou a convenção para `proxy` e passou a rodá-la no runtime
// Node.js (o middleware rodava no Edge). O código é o mesmo. Nos comentários
// daqui, "proxy /terra" é outra coisa: o route handler que repassa as chamadas
// à API (app/terra/[...path]/route.ts).
import { auth, SESSION_HEADER, encodeSessionHeader } from "@/auth";
import { destinoDaEntrada } from "@/lib/entrada";
import { NextResponse } from "next/server";

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const { pathname } = req.nextUrl;
  const sessionError = (req.auth as { error?: string } | null)?.error;

  // O proxy de API /terra é XHR, não navegação: ele NUNCA é redirecionado (quem
  // decide 401 vs. seguir é o próprio route handler, que devolve JSON). Ele passa
  // pelo middleware por um único motivo — que este seja o ponto onde a sessão é
  // RENOVADA e o cookie rotacionado é PERSISTIDO (o wrapper `auth()` grava o
  // Set-Cookie na resposta), e repassada ao handler via SESSION_HEADER. Sem isto,
  // o `await auth()` que o /terra fazia por conta própria renovava o token,
  // ROTACIONAVA a família no backend e DESCARTAVA o cookie novo (o caminho RSC
  // do next-auth lê só o corpo) — então cada request reusava o refresh token
  // velho até o backend detectar reuso e revogar a família: logout espúrio em
  // sessões longas só de polling. Ver o route handler em terra/[...path].
  const isApiProxy = pathname.startsWith("/terra");

  if (!isApiProxy) {
    // Os arquivos do `public/` não são páginas: passam sem sessão e sem papel.
    // Só extensões de ASSET ESTÁTICO dispensam o portão de sessão/papel. O
    // padrão antigo (qualquer `.ext`) deixava um caminho como `/algo.json`
    // escapar do portão; restringir à allowlist fecha esse desvio (SEG-120).
    const pareceArquivo = /\.(?:js|mjs|css|map|png|jpe?g|gif|svg|webp|avif|ico|bmp|woff2?|ttf|otf|eot|wasm|txt|xml|webmanifest|pdf)$/i.test(pathname);

    // Sem sessão (ou com o refresh token expirado), toda PÁGINA fora da Home
    // vai para a entrada — que é a própria Home com o modal de login aberto
    // (`/?entrar=1&callbackUrl=…`, ver lib/entrada.ts), e não mais /login.
    //
    // A Home (`/`) NUNCA é redirecionada: ela abre sem sessão (globo, hero e
    // barra à vista; o login é pedido no primeiro envio) e, com a sessão
    // vencida, quem a limpa é o SessionSync no cliente (signOut). Redirecionar
    // a vencida para `/?entrar=1` seria um laço: o destino está DENTRO do
    // matcher e o cookie vencido viria de novo no pedido seguinte — o /login de
    // antes ficava fora do matcher, por isso não laçava.
    if (pathname !== "/" && !pareceArquivo && (!isLoggedIn || sessionError === "RefreshTokenExpired")) {
      return NextResponse.redirect(new URL(destinoDaEntrada("entrar", pathname), req.url));
    }

    // Usuário já autenticado em /login ou /register cai na Home. As duas rotas
    // estão fora do matcher e já redirecionam por conta própria para a Home
    // com o modal; este ramo é só a rede de segurança.
    if (pathname === "/login" || pathname === "/register") {
      return NextResponse.redirect(new URL("/", req.url));
    }

    // Quem não administra o sistema só alcança a Home — POR ENQUANTO. É a
    // direção do dono: a Home (`/`) é a única página de quem não é admin, e o
    // resto do app (/projects, /workflow, /drive, /settings/tokens, /admin,
    // /dashboard…) migra para ela aos poucos. Não é só oferta: a rota devolve
    // `/` — um link antigo, a URL digitada ou o callbackUrl do login caem no
    // globo. Fora do portão: o proxy /terra (a Home vive dele; tratado acima)
    // e os arquivos do `public/`, que não são páginas. Sessão sem papel falha
    // fechada (a Home anônima passa porque é `/`, não porque tem papel). "Por
    // enquanto" mora só nesta condição — para reabrir uma rota a quem não é
    // admin, ela ganha uma exceção aqui.
    const role = (req.auth as { user?: { role?: string } })?.user?.role;
    if (role !== "admin" && pathname !== "/" && !pareceArquivo) {
      return NextResponse.redirect(new URL("/", req.url));
    }
  }

  // ── Sessão para o SSR / proxy ─────────────────────────────────────────────
  // Aqui `req.auth` já é a sessão RENOVADA (o callback jwt rodou e este é o
  // único ponto do pipeline que consegue gravar o cookie novo). Repassá-la ao
  // layout do dashboard e ao proxy /terra evita que eles chamem `auth()` de novo
  // sobre o cookie pré-middleware e disparem um segundo POST /auth/refresh por
  // requisição — ver SESSION_HEADER em auth.ts.
  const requestHeaders = new Headers(req.headers);
  // `delete` antes do `set`: um cliente não pode plantar uma sessão forjada
  // mandando o cabeçalho na requisição, mesmo que a serialização falhe.
  requestHeaders.delete(SESSION_HEADER);
  const sessionHeader = encodeSessionHeader(req.auth);
  if (sessionHeader) requestHeaders.set(SESSION_HEADER, sessionHeader);

  // Os headers de segurança (HSTS, X-Frame-Options, CSP...) NÃO ficam aqui: o
  // matcher abaixo exclui a superfície pública (/login, /register, /share,
  // /api/auth), e nas rotas que ele cobre quem não tem sessão recebe o redirect
  // lá em cima antes de chegar a este ponto — menos na Home, que renderiza
  // anônima. Eles vivem em next.config.ts (`headers()`), que vale para toda
  // resposta — inclusive as que o matcher deixa de fora, a Home sem sessão e
  // os redirects daqui.
  return NextResponse.next({ request: { headers: requestHeaders } });
});

export const config = {
  // Aplica o middleware a todas as rotas exceto assets estáticos, a API do
  // Auth.js e o coletor de relatos da CSP (POST do navegador, sem sessão).
  // `monaco/` são os arquivos do editor de código (public/monaco, ~13 por
  // abertura): sem a exclusão, cada um passava pelo auth() e voltava com
  // Set-Cookie. São os arquivos públicos do pacote, sem nada da sessão.
  // O `|$` do fim SAIU: sem ele, `/` (a Home) fica coberta — com sessão, recebe
  // o SESSION_HEADER injetado; sem sessão, passa (a Home abre anônima e pede a
  // entrada no primeiro envio). Com o `$`, `/` escapava do middleware e o
  // layout caía no `auth()` a cada request (o double-refresh que o comentário do
  // topo deste arquivo evita).
  matcher: [
    "/((?!share|api/auth|api/csp-report|internal|_next/static|_next/image|favicon.ico|monaco/|login|register|forgot-password|reset-password|verify-email).*)",
  ],
};
