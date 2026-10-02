import NextAuth from "next-auth";
import type { Session, User } from "next-auth";
import type { JWT } from "next-auth/jwt";
import Credentials from "next-auth/providers/credentials";

const API_URL = process.env.API_INTERNA ?? "http://localhost:8000";

/* ────────────────────────────────────────────────────────────────────────────
   Repasse da sessão do middleware para o SSR

   Por que existe: `auth()` chamado dentro de um Server Component monta a Request
   a partir de `headers()`, e o Next NÃO mescla nesse objeto os cookies que o
   middleware acabou de gravar (só em `cookies()`). Resultado: com o access_token
   vencido, o middleware renovava (POST /auth/refresh) e persistia o cookie novo,
   e logo depois o `auth()` do layout lia o cookie ANTIGO, via o mesmo
   `access_token_expires_at` vencido e disparava um SEGUNDO POST /auth/refresh —
   cujo Set-Cookie o próprio next-auth descarta no caminho RSC (`.json()`), então
   era trabalho 100% perdido.

   O sintoma: o tráfego de /auth/refresh dobra, e esse endpoint tem rate limit de
   20/min num balde único para toda a plataforma (o fetch daqui não manda XFF).
   Ao estourar, o 429 vira `token.error = "RefreshTokenExpired"` e o middleware
   manda TODO MUNDO para /login de uma vez. Havia ainda o risco de a segunda
   rotação cair fora da janela de graça do backend e revogar a família de refresh
   tokens de verdade.

   Correção: o middleware — único ponto que consegue persistir o cookie renovado
   — deposita a sessão já resolvida neste cabeçalho de request, e o layout do
   dashboard a consome em vez de chamar `auth()` outra vez.

   Não é um vetor de spoofing: o middleware SEMPRE sobrescreve o valor recebido
   do cliente (`delete` + `set`), e todas as rotas que renderizam o layout do
   dashboard estão dentro do `matcher` do middleware.
   ──────────────────────────────────────────────────────────────────────────── */

/** Cabeçalho interno onde o middleware entrega a sessão ao SSR. */
export const SESSION_HEADER = "x-atlans-session";

// Teto de segurança: cabeçalho de request muito grande derruba a requisição
// inteira no proxy/Node. Acima disso o layout cai no fallback de `auth()`.
const SESSION_HEADER_MAX_LENGTH = 6144;

/** Serializa a sessão para o cabeçalho. `null` = não cabe / não serializa. */
export function encodeSessionHeader(session: unknown): string | null {
  if (!session) return null;
  try {
    // percent-encoding em vez de JSON cru: username/email com acentos não são
    // latin-1 e quebrariam a escrita do cabeçalho.
    const encoded = encodeURIComponent(JSON.stringify(session));
    if (encoded.length > SESSION_HEADER_MAX_LENGTH) return null;
    return encoded;
  } catch {
    return null;
  }
}

/** Lê o cabeçalho. `null` quando ausente, corrompido ou sem cara de sessão. */
export function decodeSessionHeader(raw: string | null | undefined): Session | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(decodeURIComponent(raw));
    if (!parsed || typeof parsed !== "object") return null;
    const user = (parsed as { user?: { id_hash?: unknown } }).user;
    // Sem id_hash não é a sessão desta aplicação: melhor cair no fallback de
    // `auth()` do que hidratar o SessionProvider com um objeto pela metade.
    if (!user || typeof user.id_hash !== "string" || !user.id_hash) return null;
    return parsed as Session;
  } catch {
    return null;
  }
}

/** Vida útil do access token no JWT do NextAuth: 30 min do backend menos 60s de
 *  margem. Passado este ponto, o callback jwt tenta renovar. */
export const ACCESS_TTL_MS = 29 * 60 * 1000;

/** Após uma falha TRANSITÓRIA de /auth/refresh (rede, 429, 5xx), o token é
 *  mantido e uma nova tentativa é agendada para daqui a pouco — em vez de
 *  deslogar o usuário por um soluço do backend. */
export const REFRESH_BACKOFF_MS = 30 * 1000;

/** Injeção para teste: `fetch` e o relógio. */
export interface JwtCallbackDeps {
  fetchFn?: typeof fetch;
  now?: () => number;
}

/**
 * Renova o access_token quando expira, distinguindo falha TRANSITÓRIA de
 * TERMINAL — a distinção é o coração da correção do bug de logout espúrio.
 *
 * Antes, `if (!res.ok) throw` tratava QUALQUER resposta não-2xx (429 do rate
 * limit, 5xx, timeout de rede) como refresh token expirado: setava
 * `token.error = "RefreshTokenExpired"`, que o middleware e o SessionSync leem
 * para mandar o usuário ao /login. Um único 429 — e o /auth/refresh tinha um
 * balde de rate limit único para a plataforma (ver o backend) — deslogava. E
 * como o erro nunca era limpo num refresh bem-sucedido, ele grudava: a sessão
 * ficava condenada a deslogar mesmo depois de o backend se recuperar.
 *
 * Agora: só um 401 (refresh de fato inválido/expirado/reusado) é terminal.
 * Rede/429/5xx mantêm os tokens atuais e reagendam a tentativa
 * (`REFRESH_BACKOFF_MS`). Todo caminho de sucesso limpa `token.error`.
 *
 * Exportada e pura (com `deps` injetáveis) para ser testável — o callback do
 * NextAuth é um closure e não dá para exercitar em unidade.
 */
export async function jwtCallback(
  { token, user }: { token: JWT; user?: User | null },
  { fetchFn = fetch, now = Date.now }: JwtCallbackDeps = {},
): Promise<JWT> {
  // Primeiro login: popula o token com os dados do usuário.
  if (user) {
    token.id_hash = user.id_hash;
    token.username = user.username;
    token.role = user.role;
    token.agent_quota = user.agent_quota ?? 0;
    token.workspace_id = user.workspace_id;
    token.access_token = user.access_token;
    token.refresh_token = user.refresh_token;
    token.access_token_expires_at = now() + ACCESS_TTL_MS;
    delete token.error;
    return token;
  }

  // Ainda dentro da validade — retorna sem renovar.
  if (now() < token.access_token_expires_at) {
    return token;
  }

  // Access token expirado: tenta renovar com o refresh_token.
  let res: Response;
  try {
    res = await fetchFn(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refresh_token }),
    });
  } catch {
    // Erro de rede/timeout — TRANSITÓRIO. Mantém a sessão e tenta de novo em
    // breve; não desloga.
    token.access_token_expires_at = now() + REFRESH_BACKOFF_MS;
    return token;
  }

  // 401 = refresh token realmente inválido/expirado/reusado — TERMINAL.
  if (res.status === 401) {
    token.error = "RefreshTokenExpired";
    return token;
  }

  // 429 (rate limit) ou 5xx — TRANSITÓRIO. Não desloga; reagenda a tentativa.
  if (!res.ok) {
    token.access_token_expires_at = now() + REFRESH_BACKOFF_MS;
    return token;
  }

  const refreshed = await res.json();
  token.access_token = refreshed.access_token;
  token.refresh_token = refreshed.refresh_token ?? token.refresh_token;
  token.access_token_expires_at = now() + ACCESS_TTL_MS;
  // Refresh bem-sucedido limpa qualquer erro transitório anterior — sem isto o
  // erro grudava e a sessão era condenada a deslogar.
  delete token.error;
  return token;
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        access_token: {},
        refresh_token: {},
      },
      async authorize(credentials) {
        // A página já autenticou em /auth/login e nos repassa os tokens —
        // aqui apenas validamos buscando os dados do usuário (sem re-logar).
        if (!credentials?.access_token || !credentials?.refresh_token) return null;

        const meRes = await fetch(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${credentials.access_token}` },
        });

        if (!meRes.ok) return null;

        const user = await meRes.json();

        return {
          id: user.id_hash,
          id_hash: user.id_hash,
          username: user.username,
          email: user.email,
          role: user.role ?? "user",
          agent_quota: user.agent_quota ?? 0,
          workspace_id: user.workspace_id ?? null,
          access_token: credentials.access_token as string,
          refresh_token: credentials.refresh_token as string,
        };
      },
    }),
  ],

  callbacks: {
    // Renova o access_token quando expira. A lógica vive em `jwtCallback`
    // (exportada e testável); ver lá a distinção transitório × terminal.
    async jwt({ token, user }) {
      return jwtCallback({ token, user: user as User | undefined });
    },
    // Expõe os campos para useSession() no cliente
    session({ session, token }) {
      session.user.id_hash = token.id_hash as string;
      session.user.username = token.username as string;
      session.user.role = token.role as string;
      session.user.agent_quota = (token.agent_quota as number) ?? 0;
      session.user.workspace_id = token.workspace_id as string | null;
      session.user.access_token = token.access_token as string;
      if (token.error) session.error = token.error as string;
      return session;
    },
  },

  // V17: ao chamar signOut() no front, garantimos que o refresh_token e o
  // access_token sao revogados no backend ANTES do cookie de sessao ser
  // expirado. Sem isso, o backend marcaria revoke mas o cookie continuaria
  // valido na aba aberta ate expirar naturalmente; pior, se o usuario
  // fechasse a aba sem signOut, o cookie tambem ficava utilizavel ate o
  // exp natural do JWT (30 min).
  events: {
    async signOut(message) {
      // NextAuth v5: message inclui `token` em sessoes JWT.
      // O backend /auth/logout extrai 'family' do access_token e revoga a
      // familia inteira de refresh tokens — nao precisa do refresh_token no
      // body (era ignorado). Mantemos so o Authorization header.
      const token = (message as { token?: Record<string, unknown> })?.token;
      const accessToken = token?.access_token as string | undefined;
      if (!accessToken) return;
      try {
        await fetch(`${API_URL}/auth/logout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
        });
      } catch {
        // Best-effort: backend offline durante signOut nao bloqueia o flush
        // do cookie do lado do cliente.
      }
    },
  },

  // Sessao em cookies HttpOnly + SameSite=Lax (default do NextAuth v5).
  // Em producao, NEXTAUTH_URL com https:// faz o NextAuth setar Secure=true
  // automaticamente. NAO mudar para useSecureCookies=false em prod.
  pages: {
    signIn: "/login",
    error: "/login",
  },
});
