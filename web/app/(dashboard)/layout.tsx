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

// Proteção de rotas feita via proxy.ts (Auth.js)
//
// A sessão é resolvida no servidor e entregue pronta ao SessionProvider: era ela
// o primeiro salto do waterfall de carregamento (session → workspaces →
// workflows/runs). Este é o único grupo de rotas que precisa de sessão,
// notificações e paleta de comandos — daí os Providers morarem aqui e não no
// layout raiz.
//
// A Home (`/`) renderiza também SEM sessão: o middleware não a redireciona, o
// cabeçalho vem vazio, o `auth()` de reserva devolve `null` e o SessionProvider
// nasce "unauthenticated" — a casca abre anônima e a entrada (login/cadastro) é
// um modal sobre o globo (components/home/entrada).
//
// Quem resolve a sessão é o MIDDLEWARE, que já rodou e a deposita em
// SESSION_HEADER (ver auth.ts). Chamar `auth()` aqui lia o cookie ANTERIOR ao
// middleware e disparava um segundo POST /auth/refresh a cada carregamento com
// token vencido, contra um rate limit de 20/min que é balde único da plataforma.
// O `auth()` fica só como rede de segurança para o caso de o middleware não ter
// rodado (rota fora do matcher, dev sem middleware).
export default async function Layout(props: { children: React.ReactNode }) {
  const requestHeaders = await headers();
  const session =
    decodeSessionHeader(requestHeaders.get(SESSION_HEADER)) ?? (await auth());

  // Estado inicial da barra lateral, lido do cookie `sidebar_state` que o
  // SidebarProvider grava (ui/sidebar.tsx). Sem isto o cookie era escrito e
  // nunca lido — recolher a barra não sobrevivia ao F5. Padrão: aberta, exceto
  // quando o cookie diz explicitamente "false".
  const cookieStore = await cookies();
  const sidebarAberta = cookieStore.get("sidebar_state")?.value !== "false";
  // A largura escolhida no separador, pelo mesmo motivo: lida AQUI, no servidor,
  // a barra já nasce na medida da pessoa. Num efeito do cliente ela nasceria com
  // 16rem e saltaria no primeiro quadro. O valor é saneado no provider
  // (`limitarLargura`), então um cookie adulterado não estica nada.
  const larguraDaBarra = Number(cookieStore.get("sidebar_width")?.value);

  // O idioma da Home, resolvido AQUI pelo mesmo motivo do tema e da largura: a
  // primeira pintura já sai no idioma certo. Escolha explícita (cookie) >
  // navegador > país da conexão (Cloudflare) > padrão — ver lib/idioma.ts. Vale
  // para a casca e para a Home; as páginas de administração seguem em português.
  const idioma = resolverIdioma({
    cookie: cookieStore.get(COOKIE_DO_IDIOMA)?.value,
    acceptLanguage: requestHeaders.get("accept-language"),
    pais: requestHeaders.get("cf-ipcountry"),
  });

  // O cliente de consultas (react-query) envolve tudo, os próprios provedores
  // inclusive: os contextos que ainda buscam à mão (notificações, execuções
  // ativas, workspaces) podem migrar sem mudar de lugar na árvore.
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
