import NextAuth from "next-auth";
import type { Session, User } from "next-auth";
import type { JWT } from "next-auth/jwt";
import Credentials from "next-auth/providers/credentials";

const API_URL = process.env.API_INTERNA ?? "http://localhost:8000";

/* ────────────────────────────────────────────────────────────────────────────
   Handing the session from the middleware to SSR

   Why this exists: `auth()` called inside a Server Component builds the Request
   from `headers()`, and Next does NOT merge into that object the cookies the
   middleware has just written (only into `cookies()`). Result: with the
   access_token expired, the middleware refreshed it (POST /auth/refresh) and
   persisted the new cookie, and right after that the layout's `auth()` read the
   OLD cookie, saw the same expired `access_token_expires_at` and fired a SECOND
   POST /auth/refresh — whose Set-Cookie next-auth itself discards on the RSC
   path (`.json()`), so it was 100% wasted work.

   The symptom: /auth/refresh traffic doubles, and that endpoint has a rate limit
   of 20/min in a single bucket for the whole platform (the fetch from here sends
   no XFF). When it overflows, the 429 becomes `token.error = "RefreshTokenExpired"`
   and the middleware sends EVERYONE to /login at once. There was also the risk
   of the second rotation landing outside the backend's grace window and really
   revoking the refresh token family.

   Fix: the middleware — the only place that can persist the refreshed cookie —
   drops the already-resolved session into this request header, and the
   dashboard layout consumes it instead of calling `auth()` again.

   This is not a spoofing vector: the middleware ALWAYS overwrites the value
   received from the client (`delete` + `set`), and every route that renders the
   dashboard layout is inside the middleware's `matcher`.
   ──────────────────────────────────────────────────────────────────────────── */

/** Internal header where the middleware hands the session to SSR. */
export const SESSION_HEADER = "x-atlans-session";

// Safety ceiling: a very large request header takes down the whole request
// in the proxy/Node. Above this, the layout falls back to `auth()`.
const SESSION_HEADER_MAX_LENGTH = 6144;

/** Serializes the session for the header. `null` = doesn't fit / doesn't serialize. */
export function encodeSessionHeader(session: unknown): string | null {
  if (!session) return null;
  try {
    // percent-encoding instead of raw JSON: a username/email with accents is not
    // latin-1 and would break writing the header.
    const encoded = encodeURIComponent(JSON.stringify(session));
    if (encoded.length > SESSION_HEADER_MAX_LENGTH) return null;
    return encoded;
  } catch {
    return null;
  }
}

/** Reads the header. `null` when missing, corrupted or not session-shaped. */
export function decodeSessionHeader(raw: string | null | undefined): Session | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(decodeURIComponent(raw));
    if (!parsed || typeof parsed !== "object") return null;
    const user = (parsed as { user?: { id_hash?: unknown } }).user;
    // Without id_hash it is not this application's session: better to fall back
    // to `auth()` than to hydrate the SessionProvider with a half-built object.
    if (!user || typeof user.id_hash !== "string" || !user.id_hash) return null;
    return parsed as Session;
  } catch {
    return null;
  }
}

/** Lifetime of the access token in the NextAuth JWT: the backend's 30 min minus
 *  a 60s margin. Past this point, the jwt callback tries to refresh. */
export const ACCESS_TTL_MS = 29 * 60 * 1000;

/** After a TRANSIENT /auth/refresh failure (network, 429, 5xx), the token is
 *  kept and a new attempt is scheduled for shortly afterwards — instead of
 *  logging the user out over a backend hiccup. */
export const REFRESH_BACKOFF_MS = 30 * 1000;

/** Injection for tests: `fetch` and the clock. */
export interface JwtCallbackDeps {
  fetchFn?: typeof fetch;
  now?: () => number;
}

/**
 * Refreshes the access_token when it expires, distinguishing a TRANSIENT failure
 * from a TERMINAL one — that distinction is the heart of the fix for the
 * spurious logout bug.
 *
 * Before, `if (!res.ok) throw` treated ANY non-2xx response (rate limit 429,
 * 5xx, network timeout) as an expired refresh token: it set
 * `token.error = "RefreshTokenExpired"`, which the middleware and SessionSync
 * read to send the user to /login. A single 429 — and /auth/refresh had a
 * single rate-limit bucket for the platform (see the backend) — logged you out.
 * And since the error was never cleared on a successful refresh, it stuck: the
 * session was doomed to log out even after the backend recovered.
 *
 * Now: only a 401 (refresh truly invalid/expired/reused) is terminal.
 * Network/429/5xx keep the current tokens and reschedule the attempt
 * (`REFRESH_BACKOFF_MS`). Every success path clears `token.error`.
 *
 * Exported and pure (with injectable `deps`) so it is testable — the NextAuth
 * callback is a closure and cannot be exercised in a unit test.
 */
export async function jwtCallback(
  { token, user }: { token: JWT; user?: User | null },
  { fetchFn = fetch, now = Date.now }: JwtCallbackDeps = {},
): Promise<JWT> {
  // First login: populates the token with the user's data.
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

  // Still valid — return without refreshing.
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
    // Network error/timeout — TRANSIENT. Keep the session and try again
    // shortly; do not log out.
    token.access_token_expires_at = now() + REFRESH_BACKOFF_MS;
    return token;
  }

  // 401 = refresh token really invalid/expired/reused — TERMINAL.
  if (res.status === 401) {
    token.error = "RefreshTokenExpired";
    return token;
  }

  // 429 (rate limit) or 5xx — TRANSIENT. Do not log out; reschedule the attempt.
  if (!res.ok) {
    token.access_token_expires_at = now() + REFRESH_BACKOFF_MS;
    return token;
  }

  const refreshed = await res.json();
  token.access_token = refreshed.access_token;
  token.refresh_token = refreshed.refresh_token ?? token.refresh_token;
  token.access_token_expires_at = now() + ACCESS_TTL_MS;
  // A successful refresh clears any earlier transient error — without this the
  // error stuck and the session was doomed to log out.
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
        // The page has already authenticated at /auth/login and passes us the tokens —
        // here we only validate them by fetching the user's data (no re-login).
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
    // Refreshes the access_token when it expires. The logic lives in `jwtCallback`
    // (exported and testable); see there for the transient × terminal distinction.
    async jwt({ token, user }) {
      return jwtCallback({ token, user: user as User | undefined });
    },
    // Exposes the fields to useSession() on the client
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

  // V17: when signOut() is called on the front end, we make sure the
  // refresh_token and the access_token are revoked on the backend BEFORE the
  // session cookie expires. Without this, the backend would mark the revoke but
  // the cookie would stay valid in the open tab until it expired naturally;
  // worse, if the user closed the tab without signOut, the cookie also stayed
  // usable until the JWT's natural exp (30 min).
  events: {
    async signOut(message) {
      // NextAuth v5: message includes `token` in JWT sessions.
      // The backend /auth/logout extracts 'family' from the access_token and
      // revokes the whole refresh token family — it does not need the
      // refresh_token in the body (it was ignored). We keep only the
      // Authorization header.
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
        // Best-effort: a backend offline during signOut does not block flushing
        // the cookie on the client side.
      }
    },
  },

  // Session in HttpOnly + SameSite=Lax cookies (the NextAuth v5 default).
  // In production, NEXTAUTH_URL with https:// makes NextAuth set Secure=true
  // automatically. DO NOT change to useSecureCookies=false in prod.
  pages: {
    signIn: "/login",
    error: "/login",
  },
});
