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

// O título da aba é o nome desta instalação (NOME_NA_TELA; «Atlans» sem ela),
// lido a cada pedido como o resto da configuração do layout.
export async function generateMetadata() {
  return {
    title: lerNomeNaTelaDoAmbiente(process.env),
    description: 'Spatial data factory by flow',
  };
}

// Declarado em vez de herdado do default do Next por causa do `viewportFit`:
// sem ele, num iPhone com notch a área útil para de onde a barra do sistema
// começa, e as camadas fixas do canvas (toolbar, painel de execução) ficam
// espremidas acima dela. Com `cover` a página ocupa a tela inteira e quem
// precisa recuar usa `env(safe-area-inset-*)` — ver globals.css.
//
// `maximumScale`/`userScalable` NÃO entram: travar o zoom é barreira de
// acessibilidade, e o iOS ignora desde a versão 10 de qualquer forma.
export const viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover' as const,
};

// Sessão, notificações e paleta de comandos vivem em (dashboard)/layout.tsx:
// aqui em cima eles também eram montados no login e no portal público /share,
// que carregavam o cliente do next-auth, o GisFlowService e os ícones de nós
// sem precisar — e ainda disparavam um GET /api/auth/session sem sessão.
// O Toaster fica no root porque as telas de login também emitem toasts.
export default async function RootLayout(props: { children: ReactNode }) {
  const cookieStore = await cookies();
  // Dark é o tema PADRÃO da plataforma: sem o cookie `theme` (usuário novo, ou
  // que nunca trocou), a página abre no escuro. Quem escolheu um tema mantém a
  // escolha — o toggle grava o cookie (ver ThemeContext), e "light" nele
  // continua abrindo claro. Resolvido no servidor: a classe `dark` já sai no
  // <html>, sem flash.
  const mode = cookieStore.get("theme")?.value ?? "dark";
  // Os servidores de tiles desta instalação (MAPA_*), lidos a cada pedido: o
  // layout já é dinâmico (cookies), e a imagem do web é a mesma para todas.
  const fundosDoMapa = lerFundosDoAmbiente(process.env);
  // O link para o código-fonte desta instalação (CODIGO_FONTE_URL, AGPL §13),
  // lido do mesmo jeito: a tela de entrada e o menu da conta o mostram.
  const codigoFonte = lerCodigoFonteDoAmbiente(process.env);
  // O nome que a tela mostra (NOME_NA_TELA): o wordmark da barra lateral e o
  // cabeçalho da tela de entrada. O código mostra «Atlans»; a forma com o
  // domínio é da instalação do titular (TRADEMARKS.md).
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
