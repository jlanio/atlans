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
import SeletorDeModo from "./seletor-de-modo"
import UserSidebar from "./user-sidebar"
import { ChatsLista } from "../home/chats/lista"
import { AgendamentosLista } from "../home/agendamentos/lista"
import { ArtefatosLista } from "../home/artefatos/lista"
import { useHomeStore, type MyItem } from "@/app/stores/homeStore"
import { useFormats, useScreenLanguage, useShellTexts } from "../home/i18n/da-casca"
import { CATALOGO, ORGAOS_FEDERAIS, ORGAOS_REGIONAIS, PAISES, type CitedBase } from "@/lib/catalogo"
import type { EntryMode } from "@/lib/entrada"

/**
 * The Home's side shell, in Claude Code style: brand at the top, "Nova conversa"
 * right below, and the group **Meus → Agendamentos, Artefatos, Chats** (decision 9),
 * each one a live list. The footer is the usual `UserSidebar`, with no navigation
 * shortcut (decision 16).
 *
 * **Without a session** (the Home opens anonymous; sign-in is a modal on the first
 * send) the shell shrinks: brand and trigger at the top, the **catalog showcase**
 * in the body (`CatalogShowcase`, below) and, in the footer, **Entrar** and
 * **Criar conta** — buttons that request the modal through the store, not links.
 * The Meus group does not MOUNT (it isn't just `hidden`): Chats does its GET on
 * mount, and an `atlans:home:meu` remembered from another person in the same
 * browser would leave Schedules/Artifacts open, each with its own GET. The
 * showcase, for the same reason, is entirely constant.
 *
 * **The brand is only a LINK for the system admin.** It was the Home's only
 * explicit navigation to the rest of the app (`/projects`); by the owner's
 * decision, for whoever isn't admin the brand is a label (their way to the rest
 * of the app is the Chat / Workspace switcher right below) —
 * `Marca` without `href` already renders an inert `<span>`, with no hover
 * highlight, so the AFFORDANCE goes away too, not just the destination. And it
 * STAYS on the 3rem rail (`glifoNoTrilho`): collapsed, the bar hid the whole
 * brand, and with it the admin's only way out.
 *
 * This is not access control: `/projects` remains open to any authenticated
 * person, and the Ctrl+K palette remains global. What changes is what the Home
 * OFFERS.
 *
 * `className="home dark"` puts on the nearly black palette. The inner wrapper
 * repeats the class — and NOW also `bg-sidebar`: on the phone what paints the
 * panel is the `<SheetContent>`, and even with the `className` passed along
 * (ui/sidebar.tsx) this background here is the safety net that prevents nearly
 * white text over the app theme's light `--sidebar`.
 *
 * The wrapper is also the Home's named landmark: without it the page would only
 * have the anonymous `<main>`, and navigating by regions didn't tell globe from bar.
 *
 * **Portaled surfaces** (menu, dialog, tooltip): every Radix renders into
 * `<body>`, OUTSIDE this tree, and so came out in the app theme — white over the
 * nearly black Home when the person picks the light theme. The central fix is
 * the `home-portal` class (globals.css): it brings `.home` + `.dark` at once.
 * Use it on every `*Content` opened from the Home — the tooltips below, the
 * account menu and Preferences (`portalClassName` of `UserSidebar`), and the
 * dialogs the lists open.
 */
export default function HomeSidebar() {
  const t = useShellTexts().casca.barraLateral
  // The bar is a sibling of HomeView, not a child: its `lang` doesn't reach here,
  // and the <html> one only changes in an effect, after hydration. Without its
  // own, the server HTML put the bar's English under the root's `lang="pt-BR"`.
  const idioma = useScreenLanguage()
  const { isMobile, setOpenMobile } = useSidebar()
  const novaConversa = useHomeStore((s) => s.novaConversa)
  const hidratar = useHomeStore((s) => s.hidratar)
  // HomeView also hydrates; doing it here again is idempotent and removes the
  // dependency on mount order — the Meus group's open/closed comes from this read.
  useEffect(() => { hidratar() }, [hidratar])
  // Same read as `AppSidebar` (`:112`). While the session loads, `data` is
  // null and the brand stays inert — fail CLOSED, which is the right direction
  // to err in: the opposite would flash a link that disappears on the next render.
  const { data: session, status } = useSession()
  const isAdmin = session?.user?.role === "admin"
  // Without a session — or with an expired session, in the instant between the
  // render and SessionSync's `signOut` — the shell is the anonymous one (the same
  // read as HomeView): nothing here may fire a request.
  const anonimo = status === "unauthenticated" || session?.error === "RefreshTokenExpired"
  const pedirEntrada = useHomeStore((s) => s.pedirEntrada)
  function entrar(modo: EntryMode) {
    if (isMobile) setOpenMobile(false)
    pedirEntrada(modo)
  }

  return (
    <Sidebar
      // On desktop the `lang` lands on the bar's container (the nav and the rail); on
      // the phone the panel is a Sheet in <body>, mounted only after
      // hydration — the nav carries its own.
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
          {/* Brand + collapse trigger. On the 3rem rail the two STACK
              (`flex-col`): glyph (28px) and trigger (28px) don't fit side by side
              in the 32px available, and the glyph stays because for the admin it
              is the link to Projects. */}
          <div className="app-region-drag flex items-center gap-2 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:justify-center">
            <Marca
              href={isAdmin ? "/projects" : undefined}
              glifoNoTrilho
              tooltip={{ children: t.projetos, className: "home-portal" }}
            />
            <div className="flex-1 group-data-[collapsible=icon]:hidden" />
            {/* `max-md:size-10`: on the phone the target must be 40px (§5 of the
                screen patterns) — the trigger's size-7 gives 28px. */}
            <SidebarTrigger className="app-region-no-drag max-md:size-10" size="sm" label={t.alternar} />
          </div>
          {/* Chat / Workspace: the way out of the Home, for every signed-in person. */}
          {!anonimo && <SeletorDeModo modo="chat" portalClassName="home-portal" />}
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
                <CatalogShowcase />
              </SidebarGroupContent>
            </SidebarGroup>
          ) : (
            <SidebarGroup>
              {/* "Meus", not "Meu": the label heads three plural items
                  (Agendamentos, Artefatos, Chats) and the reader assembles "meu
                  agendamentos". The persisted key remains `atlans:home:meu`
                  (homeStore) — renaming it would reset the open/closed state of
                  existing users, and nobody sees its name. */}
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
                {/* Buttons, not links: the sign-in modal belongs to the Home and opens via the store. */}
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
              /* Reused (decision 16): Theme, Settings, Sign out. The menu and
                 Preferences are portals, outside this tree — without the class
                 they opened light over the nearly black Home. */
              <SidebarMenuItem>
                <UserSidebar portalClassName="home-portal" />
              </SidebarMenuItem>
            )}
          </SidebarMenu>
        </SidebarFooter>
      </nav>
      {/* The draggable/clickable edge that re-expands the rail — the shadcn template,
          which was missing here. Desktop only: between 640 and 767px its `sm:flex`
          would show it inside the Sheet, without the `group[data-side]` that
          positions it. */}
      {!isMobile && <SidebarRail textos={t.trilho} />}
    </Sidebar>
  )
}

/**
 * An item of the Meus group that opens/closes a sublist. Three decisions, each
 * one because of a defect that existed:
 *
 * 1. **Open/closed lives in the store** (`meu`, persisted), not in a `useState`:
 *    local state died on every opening of the drawer on the phone, on leaving
 *    `/` and coming back, and on crossing 768px.
 * 2. **On the 3rem rail the click expands the bar AND opens the item.** The
 *    sublist is `display:none` in icon mode (`SidebarMenuSub` hides itself), so
 *    toggling blindly was a dead click that still CORRUPTED the state: on
 *    expanding, the item was the opposite of what the person had left.
 *    `aria-expanded` only applies when expanded — collapsed, nothing expands.
 * 3. **Closing HIDES, it doesn't unmount.** `{aberto && children}` redid the
 *    requests on every reopen and lost the "Ver mais" pages, the error and the
 *    scroll. The list mounts on first open and stays (`hidden` when closed);
 *    the wrapper always exists, because it is the `aria-controls` target.
 *    And it mounts only AFTER hydrating, in an EFFECT: on the phone the first
 *    render is still the desktop branch (`useIsMobile` starts undefined), and
 *    mounting there fired a GET that was thrown away when the Sheet took over —
 *    in an effect, the mount lands in the same batch as `isMobile`, and the
 *    Sheet takes over with no list.
 *
 * No Radix Collapsible (there is no wrapper in the project and it's not worth a
 * dependency for this): `aria-controls` + `hidden` by hand give the screen
 * reader the same.
 */
function ItemColapsavel({
  nome,
  icone: Icone,
  label,
  children,
}: {
  nome: MyItem
  icone: React.ElementType
  label: string
  children: React.ReactNode
}) {
  const { state, isMobile, setOpen } = useSidebar()
  const hidratado = useHomeStore((s) => s.hidratado)
  const aberto = useHomeStore((s) => s.meu[nome])
  const alternar = useHomeStore((s) => s.alternarItemDoMeu)
  const abrir = useHomeStore((s) => s.abrirItemDoMeu)
  const listId = useId()
  const inRail = state === "collapsed" && !isMobile

  const [montado, setMounted] = useState(false)
  useEffect(() => { if (hidratado && aberto) setMounted(true) }, [hidratado, aberto])

  function aoClicar() {
    if (inRail) {
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
        aria-expanded={inRail ? undefined : aberto}
        aria-controls={listId}
        // 40px on the phone (§5 of the screen patterns); 36px with a fine pointer.
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
      <div id={listId} hidden={!aberto} className="group-data-[collapsible=icon]:hidden">
        {montado && children}
      </div>
    </SidebarMenuItem>
  )
}

/**
 * THE CATALOG SHOWCASE: what the bar shows to someone who hasn't signed in yet.
 *
 * What was here was a sentence — "Entre para ver seus chats, artefatos e
 * agendamentos" — and 500px of emptiness down to the footer. It failed twice: it
 * asked for the account before giving any reason, and used three words (chats,
 * artifacts, schedules) that mean nothing to someone who just arrived.
 *
 * In its place, the proof the product already has: the size of the catalog and
 * who is in it — twenty-five thousand layers of public data, indexed with
 * attributes, from IBGE to INEA. It's the argument that speaks to whoever has
 * already lost an afternoon guessing a WFS's `url` and `typeName` — and it's
 * verifiable, which a feature promise isn't. The numbers and names come from
 * `lib/catalogo.ts`, constants pinned to the seed by a test; nothing here makes
 * a request, which is the rule of the anonymous shell (see the top of this file).
 *
 * **Tickers, not a list.** At 256px a static list shows six acronyms and cuts
 * the rest; the three tickers show sixteen agencies and ten countries in the same
 * space, because time does the work of height. The cost is motion next to a
 * globe that already spins — hence the mismatched durations of `.home-fita` and
 * the full stop under `prefers-reduced-motion`.
 *
 * **The BRASIL and OUTSIDER DO BRASIL labels are not decoration.** Without them
 * "Equador" comes out in the same pill as "Embrapa" and becomes an agency called
 * Ecuador. The alternative was to solve it in the text ("em 11 países"), which
 * the second line already says — the two together cost two lines and remove the
 * ambiguity for good.
 *
 * All of this disappears on the 3rem rail: the whole group is
 * `group-data-[collapsible=icon]:hidden` (set by the caller), as the invitation was.
 */
function CatalogShowcase() {
  const t = useShellTexts().casca.barraLateral
  const f = useFormats()
  // Countries change name with the language; agencies (IBGE, INEA…) are proper names.
  const paises = PAISES.map((base) => ({ ...base, rotulo: t.paises[base.pasta] ?? base.rotulo }))
  return (
    <div className="flex flex-col">
      <p className="flex items-baseline gap-[7px] px-2">
        {/* Proportional figures, not tabular: it's a loose number, not a
            column — `tabular-nums` would give every digit the width of zero and
            open gaps in the middle of "25.492". */}
        <span className="text-[27px] font-semibold leading-none tracking-[-0.02em] text-sidebar-foreground">
          {f.inteiro(CATALOGO.camadas)}
        </span>
        <span className="text-xs text-sidebar-foreground/60">{t.camadas}</span>
      </p>
      <p className="px-2 pt-1.5 text-xs leading-relaxed text-sidebar-foreground/60">
        {t.doCatalogo(CATALOGO.instituicoes, CATALOGO.paises)}
      </p>

      <div className="flex flex-col gap-1.5 pt-3">
        <RibbonLabel>{t.brasil}</RibbonLabel>
        <Ribbon bases={ORGAOS_FEDERAIS} />
        <Ribbon bases={ORGAOS_REGIONAIS} volta />
        <RibbonLabel className="pt-1">{t.foraDoBrasil}</RibbonLabel>
        <Ribbon bases={paises} devagar />
      </div>

      <div className="mx-2 mt-4 h-px bg-sidebar-border" />
      <p className="px-2 pt-2.5 text-xs leading-relaxed text-sidebar-foreground/60">
        {t.convite}
      </p>
    </div>
  )
}

function RibbonLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("px-2 font-mono text-[10px] uppercase tracking-[0.1em] text-sidebar-foreground/50", className)}>
      {children}
    </span>
  )
}

/**
 * A ticker. The content goes in DUPLICATED because the loop's seam depends on it
 * (see `.home-fita` in globals.css): the animation runs to -50%, where the second
 * copy is at the exact spot where the first one started.
 *
 * The duplicate is `aria-hidden`: these are real names, not decoration, so the
 * screen reader reads the list — once, not twice. That's also why there is no
 * `role="img"` with an `aria-label` reciting everything: the text is already here.
 */
function Ribbon({
  bases,
  volta = false,
  devagar = false,
}: {
  bases: readonly CitedBase[]
  /** Runs the other way — that's what keeps the strips from looking like a table. */
  volta?: boolean
  /** 34s instead of 26s, for the countries ticker. */
  devagar?: boolean
}) {
  return (
    <div className="home-fita">
      <div className={cn("home-fita-trilho", volta && "volta", devagar && "devagar")}>
        {bases.map((base) => (
          <Pill key={base.pasta} rotulo={base.rotulo} />
        ))}
        {bases.map((base) => (
          <Pill key={`eco-${base.pasta}`} rotulo={base.rotulo} aria-hidden />
        ))}
      </div>
    </div>
  )
}

function Pill({ rotulo, ...resto }: { rotulo: string } & React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className="shrink-0 rounded-full border border-sidebar-border bg-sidebar-accent/45 px-2 py-[3px] text-[11px] text-sidebar-foreground/80"
      {...resto}
    >
      {rotulo}
    </span>
  )
}
