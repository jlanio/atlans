"use client"
import { useEffect, useId, useState } from "react"
import {
  Sidebar, SidebarHeader, SidebarContent, SidebarFooter, SidebarGroup,
  SidebarGroupContent, SidebarGroupLabel, SidebarMenu, SidebarMenuItem,
  SidebarMenuButton, SidebarRail, SidebarTrigger, useSidebar,
} from "../ui/sidebar"
import { TbCalendarClock, TbPackage, TbMessages, TbPencilPlus, TbChevronRight, TbLogin2, TbUserPlus } from "react-icons/tb"
import { useSession } from "next-auth/react"
import { cn } from "@/lib/utils"
import Marca from "./marca"
import UserSidebar from "./user-sidebar"
import { ChatsLista } from "../home/chats/lista"
import { AgendamentosLista } from "../home/agendamentos/lista"
import { ArtefatosLista } from "../home/artefatos/lista"
import { useHomeStore, type ItemDoMeu } from "@/app/stores/homeStore"
import { useFormatos, useIdiomaDaTela, useTextosDaCasca } from "../home/i18n/da-casca"
import { CATALOGO, ORGAOS_FEDERAIS, ORGAOS_REGIONAIS, PAISES, type BaseCitada } from "@/lib/catalogo"
import type { ModoDeEntrada } from "@/lib/entrada"

/**
 * A casca lateral da Home, no estilo Claude Code: marca no topo, "Nova conversa"
 * logo abaixo, e o grupo **Meus → Agendamentos, Artefatos, Chats** (decisão 9),
 * cada um uma lista viva. O rodapé é o `UserSidebar` de sempre, sem atalho de
 * navegação (decisão 16).
 *
 * **Sem sessão** (a Home abre anônima; a entrada é um modal no primeiro envio)
 * a casca encolhe: marca e gatilho no topo, a **vitrine do catálogo** no corpo
 * (`VitrineDoCatalogo`, abaixo) e, no rodapé, **Entrar** e **Criar conta** —
 * botões que pedem o modal pela store, não links. O grupo Meus não MONTA (não é
 * só `hidden`): o Chats faz o GET na montagem, e um `atlans:home:meu` lembrado
 * de outra pessoa no mesmo navegador deixaria Agendamentos/Artefatos abertos,
 * cada um com o seu GET. A vitrine, pelo mesmo motivo, é toda constante.
 *
 * **A marca só é LINK para o admin do sistema.** Ela era a única navegação
 * explícita da Home para o resto do app (`/projects`); por decisão do dono, quem
 * não é admin fica na Home, e a marca vira rótulo — o `Marca` sem `href` já
 * renderiza um `<span>` inerte, sem realce de hover, então some também a
 * AFORDÂNCIA, não só o destino. E ela FICA no trilho de 3rem (`glifoNoTrilho`):
 * recolhida, a barra escondia a marca inteira, e com ela a única saída do admin.
 *
 * Isto não é controle de acesso: `/projects` continua aberta a qualquer pessoa
 * autenticada, e a paleta Ctrl+K continua global. O que muda é o que a Home
 * OFERECE.
 *
 * `className="home dark"` veste a paleta quase preta. O wrapper interno repete
 * a classe — e AGORA também `bg-sidebar`: no telefone quem pinta o painel é o
 * `<SheetContent>`, e mesmo com o `className` repassado (ui/sidebar.tsx) este
 * fundo aqui é a rede de segurança que impede texto quase branco sobre o
 * `--sidebar` claro do tema do app.
 *
 * O wrapper também é a landmark nomeada da Home: sem ele a página só teria o
 * `<main>` anônimo, e navegar por regiões não distinguia globo de barra.
 *
 * **Superfícies em portal** (menu, diálogo, tooltip): todo Radix renderiza no
 * `<body>`, FORA desta árvore, e por isso saía no tema do app — branco sobre a
 * Home quase preta quando a pessoa escolhe o tema claro. A saída central é a
 * classe `home-portal` (globals.css): ela traz `.home` + `.dark` de uma vez.
 * Use-a em todo `*Content` aberto a partir da Home — os tooltips abaixo, o menu
 * de conta e as Preferências (`portalClassName` do `UserSidebar`), e os
 * diálogos que as listas abrem.
 */
export default function HomeSidebar() {
  const t = useTextosDaCasca().casca.barraLateral
  // A barra é irmã da HomeView, não filha: o `lang` dela não chega aqui, e o
  // do <html> só troca num efeito, depois da hidratação. Sem o próprio, o HTML
  // do servidor punha o inglês da barra sob o `lang="pt-BR"` da raiz.
  const idioma = useIdiomaDaTela()
  const { isMobile, setOpenMobile } = useSidebar()
  const novaConversa = useHomeStore((s) => s.novaConversa)
  const hidratar = useHomeStore((s) => s.hidratar)
  // O HomeView também hidrata; aqui de novo é idempotente e tira a dependência
  // da ordem de montagem — o aberto/fechado do grupo Meus vem desta leitura.
  useEffect(() => { hidratar() }, [hidratar])
  // Mesma leitura do `AppSidebar` (`:112`). Enquanto a sessão carrega, `data` é
  // nulo e a marca fica inerte — falha FECHADA, que é a direção certa para
  // errar: o contrário piscaria um link que some no render seguinte.
  const { data: session, status } = useSession()
  const isAdmin = session?.user?.role === "admin"
  // Sem sessão — ou com a sessão vencida, no instante entre o render e o
  // `signOut` do SessionSync — a casca é a anônima (a mesma leitura da
  // HomeView): nada aqui pode disparar uma requisição.
  const anonimo = status === "unauthenticated" || session?.error === "RefreshTokenExpired"
  const pedirEntrada = useHomeStore((s) => s.pedirEntrada)
  function entrar(modo: ModoDeEntrada) {
    if (isMobile) setOpenMobile(false)
    pedirEntrada(modo)
  }

  return (
    <Sidebar
      // No desktop o `lang` cai no contêiner da barra (o nav e o trilho); no
      // telefone o painel é um Sheet no <body>, montado só depois da
      // hidratação — o nav leva o dele.
      lang={idioma}
      collapsible="icon"
      className="home dark border-sidebar-border"
      mobileTitle={t.painelTitulo}
      mobileDescription={t.painelDescricao}
    >
      <nav
        lang={idioma}
        aria-label={t.rotulo}
        className="home dark bg-sidebar text-sidebar-foreground flex h-full w-full flex-col"
      >
        <SidebarHeader>
          {/* Marca + gatilho de recolher. No trilho de 3rem os dois EMPILHAM
              (`flex-col`): glifo (28px) e gatilho (28px) não cabem lado a lado
              nos 32px úteis, e o glifo fica porque para o admin ele é o link
              para Projetos. */}
          <div className="app-region-drag flex items-center gap-2 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:justify-center">
            <Marca
              href={isAdmin ? "/projects" : undefined}
              glifoNoTrilho
              tooltip={{ children: t.projetos, className: "home-portal" }}
            />
            <div className="flex-1 group-data-[collapsible=icon]:hidden" />
            {/* `max-md:size-10`: no telefone o alvo tem de ter 40px (§5 do
                padrão de telas) — o size-7 do gatilho dá 28px. */}
            <SidebarTrigger className="app-region-no-drag max-md:size-10" size="sm" label={t.alternar} />
          </div>
          {!anonimo && (
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => { novaConversa(); if (isMobile) setOpenMobile(false) }}
                  tooltip={{ children: t.novaConversa, className: "home-portal" }}
                  className="h-9 max-md:h-10 bg-sidebar-accent/40 font-medium hover:bg-sidebar-accent"
                >
                  <TbPencilPlus />
                  <span>{t.novaConversa}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          )}
        </SidebarHeader>

        <SidebarContent>
          {anonimo ? (
            <SidebarGroup className="group-data-[collapsible=icon]:hidden">
              <SidebarGroupLabel className="font-mono text-[11px] uppercase tracking-[0.12em] text-sidebar-foreground/55">
                {t.noCatalogo}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <VitrineDoCatalogo />
              </SidebarGroupContent>
            </SidebarGroup>
          ) : (
            <SidebarGroup>
              {/* "Meus", e não "Meu": o rótulo encabeça três itens no plural
                  (Agendamentos, Artefatos, Chats) e quem lê monta "meu
                  agendamentos". A chave persistida continua `atlans:home:meu`
                  (homeStore) — renomeá-la zeraria o aberto/fechado de quem já
                  usa o produto, e ninguém vê o nome dela. */}
              <SidebarGroupLabel className="font-mono text-[11px] uppercase tracking-[0.12em] text-sidebar-foreground/55">
                {t.meus}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <ItemColapsavel nome="agendamentos" icone={TbCalendarClock} label={t.agendamentos}>
                    <AgendamentosLista />
                  </ItemColapsavel>
                  <ItemColapsavel nome="artefatos" icone={TbPackage} label={t.artefatos}>
                    <ArtefatosLista />
                  </ItemColapsavel>
                  <ItemColapsavel nome="chats" icone={TbMessages} label={t.chats}>
                    <ChatsLista />
                  </ItemColapsavel>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )}
        </SidebarContent>

        <SidebarFooter>
          <SidebarMenu>
            {anonimo ? (
              <>
                {/* Botões, não links: o modal de entrada é da Home e abre pela store. */}
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => entrar("entrar")}
                    tooltip={{ children: t.entrar, className: "home-portal" }}
                    className="h-9 max-md:h-10 bg-sidebar-accent/40 font-medium hover:bg-sidebar-accent"
                  >
                    <TbLogin2 />
                    <span>{t.entrar}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => entrar("cadastro")}
                    tooltip={{ children: t.criarConta, className: "home-portal" }}
                    className="h-9 max-md:h-10"
                  >
                    <TbUserPlus />
                    <span>{t.criarConta}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </>
            ) : (
              /* Reusado (decisão 16): Tema, Configurações, Sair. O menu e as
                 Preferências são portais, fora desta árvore — sem a classe
                 abriam claros sobre a Home quase preta. */
              <SidebarMenuItem>
                <UserSidebar portalClassName="home-portal" />
              </SidebarMenuItem>
            )}
          </SidebarMenu>
        </SidebarFooter>
      </nav>
      {/* A borda arrastável/clicável que reexpande o trilho — o molde do shadcn,
          que faltava aqui. Só no desktop: entre 640 e 767px o `sm:flex` dele o
          mostraria dentro do Sheet, sem o `group[data-side]` que o posiciona. */}
      {!isMobile && <SidebarRail textos={t.trilho} />}
    </Sidebar>
  )
}

/**
 * Um item do grupo Meus que abre/fecha uma sublista. Três decisões, cada uma
 * por um defeito que existiu:
 *
 * 1. **O aberto/fechado vive na store** (`meu`, persistido), não num `useState`:
 *    o estado local morria a cada abertura da gaveta no telefone, ao sair de
 *    `/` e voltar, e ao cruzar 768px.
 * 2. **No trilho de 3rem o clique expande a barra E abre o item.** A sublista
 *    está em `display:none` no modo ícone (o próprio `SidebarMenuSub` se
 *    esconde), então alternar às cegas era um clique morto que ainda CORROMPIA
 *    o estado: ao expandir, o item estava no oposto do que a pessoa deixou.
 *    `aria-expanded` só vale expandido — recolhido, não há nada que expanda.
 * 3. **Fechar ESCONDE, não desmonta.** `{aberto && children}` refazia as
 *    requisições a cada reabertura e perdia as páginas do "Ver mais", o erro e
 *    a rolagem. A lista monta na primeira abertura e fica (`hidden` quando
 *    fechada); o wrapper existe sempre, porque é o alvo do `aria-controls`.
 *    E monta só DEPOIS de hidratar, em EFEITO: no telefone o primeiro render
 *    ainda é o ramo desktop (`useIsMobile` começa indefinido), e montar ali
 *    disparava um GET que ia para o lixo quando o Sheet assumia — em efeito, a
 *    montagem cai na mesma leva de `isMobile`, e o Sheet assume sem lista.
 *
 * Sem Radix Collapsible (não há wrapper no projeto e não vale uma dependência
 * por isto): `aria-controls` + `hidden` à mão dão o mesmo ao leitor de tela.
 */
function ItemColapsavel({
  nome,
  icone: Icone,
  label,
  children,
}: {
  nome: ItemDoMeu
  icone: React.ElementType
  label: string
  children: React.ReactNode
}) {
  const { state, isMobile, setOpen } = useSidebar()
  const hidratado = useHomeStore((s) => s.hidratado)
  const aberto = useHomeStore((s) => s.meu[nome])
  const alternar = useHomeStore((s) => s.alternarItemDoMeu)
  const abrir = useHomeStore((s) => s.abrirItemDoMeu)
  const idDaLista = useId()
  const noTrilho = state === "collapsed" && !isMobile

  const [montado, setMontado] = useState(false)
  useEffect(() => { if (hidratado && aberto) setMontado(true) }, [hidratado, aberto])

  function aoClicar() {
    if (noTrilho) {
      setOpen(true)
      abrir(nome)
      return
    }
    alternar(nome)
  }

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        onClick={aoClicar}
        tooltip={{ children: label, className: "home-portal" }}
        aria-expanded={noTrilho ? undefined : aberto}
        aria-controls={idDaLista}
        // 40px no telefone (§5 do padrão de telas); 36px no ponteiro fino.
        className="h-9 max-md:h-10"
      >
        <Icone />
        <span>{label}</span>
        <TbChevronRight
          className={cn(
            "ml-auto size-4 shrink-0 transition-transform group-data-[collapsible=icon]:hidden",
            aberto && "rotate-90",
          )}
        />
      </SidebarMenuButton>
      <div id={idDaLista} hidden={!aberto} className="group-data-[collapsible=icon]:hidden">
        {montado && children}
      </div>
    </SidebarMenuItem>
  )
}

/**
 * A VITRINE DO CATÁLOGO: o que a barra mostra a quem ainda não entrou.
 *
 * O que estava aqui era uma frase — "Entre para ver seus chats, artefatos e
 * agendamentos" — e 500px de vazio até o rodapé. Ela falhava duas vezes: pedia
 * a conta antes de dar qualquer motivo, e usava três palavras (chats,
 * artefatos, agendamentos) que não querem dizer nada para quem chegou agora.
 *
 * No lugar, a prova que o produto já tem: o tamanho do catálogo e quem está
 * nele — vinte e cinco mil camadas de dado público, indexadas com atributos, de
 * IBGE a INEA. É o argumento que fala com quem já perdeu uma tarde
 * adivinhando `url` e `typeName` de um WFS — e é verificável, o que uma
 * promessa de recurso não é. Os números e os nomes vêm de `lib/catalogo.ts`,
 * constantes presas à semente por um teste; nada aqui faz requisição, que é a
 * regra da casca anônima (ver o topo deste arquivo).
 *
 * **Fitas, não lista.** Em 256px uma lista estática mostra seis siglas e corta
 * o resto; as três fitas mostram dezesseis órgãos e dez países no mesmo espaço,
 * porque o tempo faz o trabalho da altura. O custo é movimento ao lado de um
 * globo que já gira — daí as durações desencontradas do `.home-fita` e a parada
 * completa em `prefers-reduced-motion`.
 *
 * **Os rótulos BRASIL e FORA DO BRASIL não são enfeite.** Sem eles "Equador"
 * sai na mesma pílula que "Embrapa" e vira um órgão chamado Equador. A
 * alternativa era resolver no texto ("em 11 países"), que a segunda linha já
 * diz — os dois juntos custam duas linhas e tiram a ambiguidade de vez.
 *
 * Tudo isto some no trilho de 3rem: o grupo inteiro é
 * `group-data-[collapsible=icon]:hidden` (quem chama), como era o convite.
 */
function VitrineDoCatalogo() {
  const t = useTextosDaCasca().casca.barraLateral
  const f = useFormatos()
  // Os países mudam de nome com o idioma; os órgãos (IBGE, INEA…) são nomes próprios.
  const paises = PAISES.map((base) => ({ ...base, rotulo: t.paises[base.pasta] ?? base.rotulo }))
  return (
    <div className="flex flex-col">
      <p className="flex items-baseline gap-[7px] px-2">
        {/* Figuras proporcionais, não tabulares: é um número solto, não uma
            coluna — `tabular-nums` daria a todo dígito a largura do zero e
            abriria buracos no meio de "25.492". */}
        <span className="text-[27px] font-semibold leading-none tracking-[-0.02em] text-sidebar-foreground">
          {f.inteiro(CATALOGO.camadas)}
        </span>
        <span className="text-xs text-sidebar-foreground/60">{t.camadas}</span>
      </p>
      <p className="px-2 pt-1.5 text-xs leading-relaxed text-sidebar-foreground/60">
        {t.doCatalogo(CATALOGO.instituicoes, CATALOGO.paises)}
      </p>

      <div className="flex flex-col gap-1.5 pt-3">
        <RotuloDaFita>{t.brasil}</RotuloDaFita>
        <Fita bases={ORGAOS_FEDERAIS} />
        <Fita bases={ORGAOS_REGIONAIS} volta />
        <RotuloDaFita className="pt-1">{t.foraDoBrasil}</RotuloDaFita>
        <Fita bases={paises} devagar />
      </div>

      <div className="mx-2 mt-4 h-px bg-sidebar-border" />
      <p className="px-2 pt-2.5 text-xs leading-relaxed text-sidebar-foreground/60">
        {t.convite}
      </p>
    </div>
  )
}

function RotuloDaFita({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("px-2 font-mono text-[10px] uppercase tracking-[0.1em] text-sidebar-foreground/50", className)}>
      {children}
    </span>
  )
}

/**
 * Uma fita. O conteúdo vai DUPLICADO porque a emenda do laço depende disso (ver
 * `.home-fita` em globals.css): a animação anda até -50%, onde a segunda cópia
 * está no lugar exato em que a primeira começou.
 *
 * A duplicata é `aria-hidden`: são nomes de verdade, não decoração, então o
 * leitor de tela lê a lista — uma vez, não duas. É também por isso que não há
 * `role="img"` com um `aria-label` recitando tudo: o texto já está aqui.
 */
function Fita({
  bases,
  volta = false,
  devagar = false,
}: {
  bases: readonly BaseCitada[]
  /** Anda para o outro lado — é o que impede as faixas de parecerem uma tabela. */
  volta?: boolean
  /** 34s em vez de 26s, para a fita dos países. */
  devagar?: boolean
}) {
  return (
    <div className="home-fita">
      <div className={cn("home-fita-trilho", volta && "volta", devagar && "devagar")}>
        {bases.map((base) => (
          <Pilula key={base.pasta} rotulo={base.rotulo} />
        ))}
        {bases.map((base) => (
          <Pilula key={`eco-${base.pasta}`} rotulo={base.rotulo} aria-hidden />
        ))}
      </div>
    </div>
  )
}

function Pilula({ rotulo, ...resto }: { rotulo: string } & React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className="shrink-0 rounded-full border border-sidebar-border bg-sidebar-accent/45 px-2 py-[3px] text-[11px] text-sidebar-foreground/80"
      {...resto}
    >
      {rotulo}
    </span>
  )
}
