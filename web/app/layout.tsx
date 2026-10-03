import { ReactNode, Suspense } from 'react';
import { Toaster } from "@/app/components/ui/sonner"
import { inter } from "./fonts/inter";
import "./globals.css";
import { cookies } from 'next/headers';
import { cn } from '@/lib/utils';
import { lerFundosDoAmbiente } from '@/lib/fundos-do-mapa';
import { FundosDoMapaProvider } from '@/app/components/share/fundos-do-mapa';
import { lerCodigoFonteDoAmbiente } from '@/lib/codigo-fonte';
import { CodigoFonteProvider } from '@/app/components/share/codigo-fonte';
import { lerNomeNaTelaDoAmbiente } from '@/lib/nome-na-tela';
import { NomeNaTelaProvider } from '@/app/components/share/nome-na-tela';

// The tab title is this installation's name (NOME_NA_TELA; "Atlans" without it),
// read on every request like the rest of the layout configuration.
export async function generateMetadata() {
  return {
    title: lerNomeNaTelaDoAmbiente(process.env),
    description: 'Spatial data factory by flow',
  };
}

// Declared instead of inherited from Next's default because of `viewportFit`:
// without it, on an iPhone with a notch the usable area stops where the system
// bar starts, and the canvas's fixed layers (toolbar, execution panel) get
// squeezed above it. With `cover` the page takes the whole screen and whatever
// needs to inset uses `env(safe-area-inset-*)` — see globals.css.
//
// `maximumScale`/`userScalable` are NOT included: locking zoom is an
// accessibility barrier, and iOS has ignored it since version 10 anyway.
export const viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover' as const,
};

// Session, notifications and command palette live in (dashboard)/layout.tsx:
// up here they were also mounted on the login and on the public /share portal,
// which loaded the next-auth client, GisFlowService and the node icons
// without needing them — and also fired a GET /api/auth/session with no session.
// The Toaster stays at the root because the login screens also emit toasts.
export default async function RootLayout(props: { children: ReactNode }) {
  const cookieStore = await cookies();
  // Dark is the platform's DEFAULT theme: without the `theme` cookie (a new user,
  // or one who never switched), the page opens dark. Whoever chose a theme keeps
  // the choice — the toggle writes the cookie (see ThemeContext), and "light" in
  // it still opens light. Resolved on the server: the `dark` class already goes
  // out on <html>, with no flash.
  const mode = cookieStore.get("theme")?.value ?? "dark";
  // This installation's tile servers (MAPA_*), read on every request: the
  // layout is already dynamic (cookies), and the web image is the same for all.
  const fundosDoMapa = lerFundosDoAmbiente(process.env);
  // The link to this installation's source code (CODIGO_FONTE_URL, AGPL §13),
  // read the same way: the sign-in screen and the account menu show it.
  const codigoFonte = lerCodigoFonteDoAmbiente(process.env);
  // The name the screen shows (NOME_NA_TELA): the sidebar wordmark and the
  // sign-in screen header. The code shows "Atlans"; the form with the
  // domain belongs to the trademark holder's installation (TRADEMARKS.md).
  const nomeNaTela = lerNomeNaTelaDoAmbiente(process.env);

  return (
    <html lang="pt-BR" suppressHydrationWarning className={cn(mode === "dark" && "dark", inter.variable)}>
      <body suppressHydrationWarning>
        <Suspense>
          <FundosDoMapaProvider fundos={fundosDoMapa}>
            <CodigoFonteProvider url={codigoFonte}>
              <NomeNaTelaProvider nome={nomeNaTela}>
                {props.children}
              </NomeNaTelaProvider>
            </CodigoFonteProvider>
          </FundosDoMapaProvider>
          <Toaster />
        </Suspense>
      </body>
    </html>
  );
}
