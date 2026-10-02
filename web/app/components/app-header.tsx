"use client"

import { usePathname } from "next/navigation"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useIdiomaDaTela, useTextosDaCasca } from "./home/i18n/da-casca"
import { SidebarTrigger } from "./ui/sidebar"
import WorkspaceSwitcher from "./workspace/workspace-switcher"
import { Skeleton } from "./ui/skeleton"

/**
 * Barra sticky no topo do conteúdo do dashboard. Sempre exibe o workspace
 * ativo com identidade visual (cor + iniciais) + papel do usuário.
 *
 * Objetivo: mesmo com a sidebar colapsada, ou em scroll profundo, o usuário
 * consegue confirmar visualmente em que workspace está operando antes de
 * qualquer ação destrutiva (executar workflow, deletar drive/artefato).
 *
 * Slot direito (`right`) fica reservado pra breadcrumbs ou ações
 * page-specific em iteração futura.
 *
 * O SidebarTrigger aqui e mobile-only (`md:hidden`). No desktop o toggle vive
 * no header da propria sidebar (app-sidebar.tsx) e continua clicavel no modo
 * colapsado (`collapsible="icon"`) — dois botoes identicos lado a lado eram
 * redundantes. Abaixo de 768px a sidebar vira um <Sheet> e o botao dela fica
 * *dentro* do Sheet, ou seja, so fecha: este e o unico jeito de abrir.
 * O breakpoint casa com MOBILE_BREAKPOINT de hooks/use-mobile.ts, entao nao
 * existe largura em que ambos aparecam ou ambos sumam.
 *
 * Por isso a Home (`/`) nao devolve `null`: ela nao quer a barra, mas precisa
 * do gatilho. La o componente vira SO o gatilho flutuante mobile-only (ver
 * abaixo) — o h1 da pagina e da HomeView (`components/home/index.tsx`), e nao
 * daqui: dois <h1> na mesma rota quebram a leitura de estrutura do leitor de
 * tela, e quem sabe do que a pagina trata e a view, nao a casca.
 */

// Rotas que renderizam canvas fullscreen (ReactFlow) e nao devem ter
// chrome persistente sobreposto. O canvas usa botoes flutuantes com
// `absolute top-5` — o header sticky (z-40) sobrepunha o botao de
// adicionar no (z-10).
//
// Quem diz o workspace nessas rotas e o `WorkflowLocation`, desenhado sobre o
// proprio canvas: a sidebar nao serve mais de reserva — o seletor saiu dela, e
// o editor ainda a recolhe sozinho ao montar. Trocar de workspace de dentro do
// editor deixou de ser possivel de proposito: a troca navega para /projects e
// descartaria a edicao em curso.
const FULLSCREEN_ROUTES = [
  "/workflow/",   // /workflow/[id] e /workflow/create
]

export function AppHeader({ right }: { right?: React.ReactNode }) {
  const pathname = usePathname()
  const { loading } = useWorkspace()
  // Só a rota `/` usa: fora da Home o escopo do idioma já devolve o português.
  const textosDaBarra = useTextosDaCasca().casca.barraLateral
  const idioma = useIdiomaDaTela()

  // A Home (`/`) e full-bleed como o canvas: sem barra. Mas o header e o unico
  // lugar do app que monta um gatilho de sidebar visivel no telefone — abaixo
  // de 768px a barra vira um <Sheet> e o botao dela fica DENTRO do Sheet, ou
  // seja, so fecha. Devolver `null` aqui deixava o telefone sem Chats,
  // Agendamentos, Artefatos, troca de workspace nem SAIR: so o globo. Entao na
  // Home o header degrada para o minimo — um gatilho flutuante mobile-only, e
  // so isso. Casamento EXATO — um `startsWith("/")` casaria toda rota do app.
  if (pathname === "/") {
    return (
      <SidebarTrigger
        // Canto superior DIREITO: a esquerda e do painel de camadas
        // (`left-6 top-6`) e o painel do assistente comeca em `top-16` no
        // telefone — esta faixa e a unica livre.
        //
        // Empilhamento da Home, de cima para baixo: este gatilho (z-50) >
        // painel de camadas (z-40) > painel/barra do assistente (z-30). O
        // gatilho tem de ser o TOPO: em tela estreita o painel de camadas
        // expandido cresce para a direita e, empatados em z-40, o que vem
        // depois no DOM cobria o botao — e este e o unico jeito de abrir a
        // barra no telefone (o botao de dentro do Sheet so fecha).
        //
        // `home dark` veste a paleta quase preta no proprio botao: ele mora
        // fora da arvore da HomeView, que e quem declara os tokens.
        className="home dark app-region-no-drag fixed right-3 top-3 z-50 size-10 rounded-full border border-border bg-background/85 text-foreground shadow-lg backdrop-blur md:hidden"
        // Fora da árvore da HomeView: o `lang` dela não chega aqui.
        lang={idioma}
        aria-label={textosDaBarra.abrirMenu}
        label={textosDaBarra.alternar}
      />
    )
  }

  if (pathname && FULLSCREEN_ROUTES.some(p => pathname.startsWith(p))) {
    return null
  }

  return (
    <header
      // `app-region-drag`: no app desktop (janela sem barra de título) este
      // cabeçalho arrasta a janela; os controles abaixo levam `app-region-no-drag`
      // para seguirem clicáveis. No navegador não tem efeito (ver globals.css).
      className={[
        "app-region-drag",
        "sticky top-0 z-40 flex items-center gap-3",
        "h-12 px-4 border-b border-border",
        "bg-background/95 backdrop-blur",
      ].join(" ")}
    >
      <SidebarTrigger className="shrink-0 md:hidden app-region-no-drag" />

      <div className="h-6 w-px bg-border shrink-0 md:hidden" />

      <div className="flex-1 min-w-0">
        {loading ? (
          // Sem bloco de avatar: o gatilho do seletor mostra só nome e papel,
          // e um placeholder quadrado faria a barra saltar ao carregar.
          <div className="grid gap-1 px-2 py-1">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-2 w-20" />
          </div>
        ) : (
          <WorkspaceSwitcher />
        )}
      </div>

      {right && <div className="shrink-0 app-region-no-drag">{right}</div>}
    </header>
  )
}
