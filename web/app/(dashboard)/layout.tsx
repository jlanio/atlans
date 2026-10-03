import * as React from 'react';
import { headers, cookies } from 'next/headers';
import "../globals.css";
import { auth, SESSION_HEADER, decodeSessionHeader } from '@/auth';
import Providers from '../components/providers';
import { ProvedorDeConsultas } from '../components/provedor-de-consultas';
import SidebarRoot from '../components/sidebar';
import { ThemeProvider } from '@/context/ThemeContext';
import { WorkspaceProvider } from '@/context/WorkspaceContext';
import { ActiveRunsProvider } from '@/context/ActiveRunsContext';
import { EscopoPelaRota, IdiomaProvider } from '@/context/IdiomaContext';
import { COOKIE_DO_IDIOMA, resolverIdioma } from '@/lib/idioma';

// Route protection done via proxy.ts (Auth.js)
//
// The session is resolved on the server and handed ready to the SessionProvider:
// it was the first hop of the loading waterfall (session → workspaces →
// workflows/runs). This is the only route group that needs session,
// notifications and the command palette — hence the Providers living here and
// not in the root layout.
//
// The Home (`/`) also renders WITHOUT a session: the middleware does not
// redirect it, the header comes empty, the fallback `auth()` returns `null` and
// the SessionProvider starts "unauthenticated" — the shell opens anonymous and
// the sign-in (login/sign-up) is a modal over the globe (components/home/entrada).
//
// What resolves the session is the MIDDLEWARE, which has already run and puts it
// in SESSION_HEADER (see auth.ts). Calling `auth()` here read the cookie from
// BEFORE the middleware and fired a second POST /auth/refresh on every load with
// an expired token, against a 20/min rate limit that is a single bucket for the
// whole platform. `auth()` stays only as a safety net in case the middleware
// did not run (route outside the matcher, dev without middleware).
export default async function Layout(props: { children: React.ReactNode }) {
  const requestHeaders = await headers();
  const session =
    decodeSessionHeader(requestHeaders.get(SESSION_HEADER)) ?? (await auth());

  // Initial state of the sidebar, read from the `sidebar_state` cookie that the
  // SidebarProvider writes (ui/sidebar.tsx). Without this the cookie was written
  // and never read — collapsing the bar did not survive F5. Default: open, except
  // when the cookie explicitly says "false".
  const cookieStore = await cookies();
  const sidebarAberta = cookieStore.get("sidebar_state")?.value !== "false";
  // The width chosen at the separator, for the same reason: read HERE, on the
  // server, the bar is born at the person's size. In a client effect it would
  // be born at 16rem and jump on the first frame. The value is sanitized in the
  // provider (`limitarLargura`), so a tampered cookie stretches nothing.
  const larguraDaBarra = Number(cookieStore.get("sidebar_width")?.value);

  // The Home's language, resolved HERE for the same reason as the theme and the
  // width: the first paint already comes out in the right language. Explicit
  // choice (cookie) > browser > connection country (Cloudflare) > default — see
  // lib/idioma.ts. Applies to the shell and the Home; the admin pages stay in
  // Portuguese.
  const idioma = resolverIdioma({
    cookie: cookieStore.get(COOKIE_DO_IDIOMA)?.value,
    acceptLanguage: requestHeaders.get("accept-language"),
    pais: requestHeaders.get("cf-ipcountry"),
  });

  // The query client (react-query) wraps everything, the providers themselves
  // included: the contexts that still fetch by hand (notifications, active
  // runs, workspaces) can migrate without moving in the tree.
  return (
    <ProvedorDeConsultas>
      <Providers session={session}>
        <IdiomaProvider inicial={idioma}>
          <EscopoPelaRota>
            <ThemeProvider>
              <WorkspaceProvider>
                <ActiveRunsProvider>
                  <SidebarRoot
                    defaultOpen={sidebarAberta}
                    defaultWidth={Number.isFinite(larguraDaBarra) ? larguraDaBarra : undefined}
                  >
                    {props.children}
                  </SidebarRoot>
                </ActiveRunsProvider>
              </WorkspaceProvider>
            </ThemeProvider>
          </EscopoPelaRota>
        </IdiomaProvider>
      </Providers>
    </ProvedorDeConsultas>
  );
}
