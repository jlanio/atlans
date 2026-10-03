// The web's session and role gate. Up to Next 15 it was `middleware.ts`;
// Next 16 renamed the convention to `proxy` and started running it in the
// Node.js runtime (the middleware ran on the Edge). The code is the same. In
// the comments here, "proxy /terra" is something else: the route handler that
// forwards calls to the API (app/terra/[...path]/route.ts).
import { auth, SESSION_HEADER, encodeSessionHeader } from "@/auth";
import { destinoDaEntrada } from "@/lib/entrada";
import { NextResponse } from "next/server";

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const { pathname } = req.nextUrl;
  const sessionError = (req.auth as { error?: string } | null)?.error;

  // The /terra API proxy is XHR, not navigation: it is NEVER redirected (the
  // route handler itself decides 401 vs. proceeding, returning JSON). It goes
  // through the middleware for a single reason — so that this is the place
  // where the session is REFRESHED and the rotated cookie is PERSISTED (the
  // `auth()` wrapper writes the Set-Cookie into the response), and handed to
  // the handler via SESSION_HEADER. Without this, the `await auth()` that
  // /terra did on its own refreshed the token, ROTATED the family on the
  // backend and DISCARDED the new cookie (next-auth's RSC path reads only the
  // body) — so every request reused the old refresh token until the backend
  // detected reuse and revoked the family: spurious logout in long
  // polling-only sessions. See the route handler in terra/[...path].
  const isApiProxy = pathname.startsWith("/terra");

  if (!isApiProxy) {
    // The files in `public/` are not pages: they pass without session or role.
    // Only STATIC ASSET extensions bypass the session/role gate. The old
    // pattern (any `.ext`) let a path like `/algo.json` slip past the gate;
    // restricting it to the allowlist closes that bypass (SEG-120).
    const pareceArquivo = /\.(?:js|mjs|css|map|png|jpe?g|gif|svg|webp|avif|ico|bmp|woff2?|ttf|otf|eot|wasm|txt|xml|webmanifest|pdf)$/i.test(pathname);

    // Without a session (or with an expired refresh token), every PAGE other than
    // the Home goes to the entry — which is the Home itself with the login modal
    // open (`/?entrar=1&callbackUrl=…`, see lib/entrada.ts), and no longer /login.
    //
    // The Home (`/`) is NEVER redirected: it opens without a session (globe,
    // hero and bar in view; login is requested on the first submit) and, with an
    // expired session, the one that clears it is SessionSync on the client
    // (signOut). Redirecting the expired one to `/?entrar=1` would be a loop:
    // the destination is INSIDE the matcher and the expired cookie would come
    // again on the next request — the old /login was outside the matcher, which
    // is why it did not loop.
    if (pathname !== "/" && !pareceArquivo && (!isLoggedIn || sessionError === "RefreshTokenExpired")) {
      return NextResponse.redirect(new URL(destinoDaEntrada("entrar", pathname), req.url));
    }

    // An already authenticated user on /login or /register lands on the Home. Both
    // routes are outside the matcher and already redirect to the Home with the
    // modal on their own; this branch is only the safety net.
    if (pathname === "/login" || pathname === "/register") {
      return NextResponse.redirect(new URL("/", req.url));
    }

    // Whoever does not administer the system only reaches the Home — FOR NOW.
    // It is the owner's direction: the Home (`/`) is the only page for non-admins,
    // and the rest of the app (/projects, /workflow, /drive, /settings/tokens,
    // /admin, /dashboard…) migrates into it gradually. It is not just an offer:
    // the route returns `/` — an old link, a typed URL or the login callbackUrl
    // land on the globe. Outside the gate: the /terra proxy (the Home lives on
    // it; handled above) and the files in `public/`, which are not pages. A
    // session without a role fails closed (the anonymous Home passes because it
    // is `/`, not because it has a role). "For now" lives only in this
    // condition — to reopen a route to non-admins, it gets an exception here.
    const role = (req.auth as { user?: { role?: string } })?.user?.role;
    if (role !== "admin" && pathname !== "/" && !pareceArquivo) {
      return NextResponse.redirect(new URL("/", req.url));
    }
  }

  // ── Session for SSR / proxy ───────────────────────────────────────────────
  // Here `req.auth` is already the REFRESHED session (the jwt callback ran and
  // this is the only point in the pipeline that can write the new cookie).
  // Handing it to the dashboard layout and to the /terra proxy keeps them from
  // calling `auth()` again on the pre-middleware cookie and firing a second
  // POST /auth/refresh per request — see SESSION_HEADER in auth.ts.
  const requestHeaders = new Headers(req.headers);
  // `delete` before `set`: a client cannot plant a forged session by sending
  // the header in the request, even if serialization fails.
  requestHeaders.delete(SESSION_HEADER);
  const sessionHeader = encodeSessionHeader(req.auth);
  if (sessionHeader) requestHeaders.set(SESSION_HEADER, sessionHeader);

  // The security headers (HSTS, X-Frame-Options, CSP...) do NOT live here: the
  // matcher below excludes the public surface (/login, /register, /share,
  // /api/auth), and on the routes it covers, users without a session get the
  // redirect up above before reaching this point — except on the Home, which
  // renders anonymously. They live in next.config.ts (`headers()`), which
  // applies to every response — including those the matcher leaves out, the
  // Home without a session and the redirects from here.
  return NextResponse.next({ request: { headers: requestHeaders } });
});

export const config = {
  // Applies the middleware to every route except static assets, the Auth.js
  // API and the CSP report collector (browser POST, no session).
  // `monaco/` are the code editor's files (public/monaco, ~13 per opening):
  // without the exclusion, each one went through auth() and came back with
  // Set-Cookie. They are the package's public files, with nothing from the
  // session.
  // The trailing `|$` was REMOVED: without it, `/` (the Home) is covered — with
  // a session, it gets the injected SESSION_HEADER; without a session, it
  // passes (the Home opens anonymously and asks for entry on the first
  // submit). With the `$`, `/` escaped the middleware and the layout fell back
  // to `auth()` on every request (the double refresh that the comment at the
  // top of this file prevents).
  matcher: [
    "/((?!share|api/auth|api/csp-report|internal|_next/static|_next/image|favicon.ico|monaco/|login|register|forgot-password|reset-password|verify-email).*)",
  ],
};
