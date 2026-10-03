"use client"

import {
  SidebarMenuButton,
  useSidebar
} from "../ui/sidebar"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "../ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { TbSelector, TbLogout, TbSettings, TbMoon, TbSun, TbSourceCode } from "react-icons/tb";
import { useTheme } from "@/context/ThemeContext";
import { useSession, signOut } from "next-auth/react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { UserPreferencesDialog } from "./user-preferences-dialog";
import { EXTENSOES, LimiteDaExtensao } from "@/extensoes";
import { useTextosDaCasca } from "../home/i18n/da-casca";
import { useCodigoFonte } from "../share/codigo-fonte";

/**
 * `portalClassName`: the menu and the Preferences dialog are Radix portals — they
 * go to <body>, outside the tree of whoever opened them. The Home (always dark)
 * passes `home-portal`, otherwise both opened in the app's light palette on top
 * of it. It's a prop, and not a route read in here: the palette belongs to whoever
 * HOSTS the component, and the shell already decides route→sidebar just once
 * (ShellSidebar). Without the prop, the behavior is the usual one — AppSidebar
 * passes nothing.
 */
const UserSidebar = ({ portalClassName }: { portalClassName?: string } = {}) => {

  const { isMobile } = useSidebar()
  const { theme, setTheme } = useTheme()
  const { data: session } = useSession()
  const [changedThemeState, setChangedThemeState] = useState("")
  const [prefsOpen, setPrefsOpen] = useState(false)
  const textosDaCasca = useTextosDaCasca()
  const t = textosDaCasca.casca.conta
  // AGPL §13: this installation's source code (CODIGO_FONTE_URL), when it
  // declares it. Opens outside: it isn't a route of this application.
  const codigoFonte = useCodigoFonte()

  const username = session?.user?.username ?? t.usuario
  const email = session?.user?.email ?? ""
  const initials = username.slice(0, 2).toUpperCase()

  return (
    <>
    <DropdownMenu onOpenChange={() => setChangedThemeState("")}>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton
          size="lg"
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
        >
          <Avatar className="h-8 w-8 rounded-lg">
            <AvatarImage src={""} alt={username} />
            <AvatarFallback className="rounded-lg">{initials}</AvatarFallback>
          </Avatar>
          <div className="grid flex-1 text-left text-sm leading-tight">
            <span className="truncate font-medium">{username}</span>
            <span className="truncate text-xs">{email}</span>
          </div>
          <TbSelector className="ml-auto size-4" />
        </SidebarMenuButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className={cn("w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg", portalClassName)}
        side={isMobile ? "bottom" : "right"}
        align="end"
        sideOffset={4}
      >
        <DropdownMenuLabel className="p-0 font-normal">
          <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
            <Avatar className="h-8 w-8 rounded-lg">
              <AvatarImage src={""} alt={username} />
              <AvatarFallback className="rounded-lg">{initials}</AvatarFallback>
            </Avatar>
            <div className="grid flex-1 text-left text-sm leading-tight">
              <span className="truncate font-medium">{username}</span>
              <span className="truncate text-xs">{email}</span>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuItem
          onSelect={(event) => {
            event.preventDefault();
            const value = theme === "dark" ? "light" : "dark"
            setTheme(value)
            setChangedThemeState(value)
          }}
        >
          <div className="flex items-center relative w-[15px]">
            <TbMoon
              data-theme={theme}
              data-changedtheme={changedThemeState}
              className={
                cn(
                  "opacity-0 duration-500 absolute transition",
                  "data-[theme=dark]:opacity-100 data-[changedtheme=dark]:animate-theme-appear data-[changedtheme=light]:animate-theme-disappear"
                )}
            />
            <TbSun
              data-theme={theme}
              data-changedtheme={changedThemeState}
              className={
                cn(
                  "opacity-0 duration-500 absolute transition",
                  "data-[theme=light]:opacity-100 data-[changedtheme=light]:animate-theme-appear data-[changedtheme=dark]:animate-theme-disappear",
                )}
            />
          </div>
          {t.tema(theme === 'dark')}
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuGroup>
          {/* "Tokens de acesso" left here by product decision. The
              /settings/tokens page, like every route outside the Home, only opens
              for the system administrator (`proxy.ts` sends the others to `/`),
              and they reach it via the Ctrl+K palette or the URL. The token is
              personal (it acts on behalf of whoever creates it), so today only
              administrators have tokens — which is what the MCP refusals say.

              The extensions (`web/extensoes`) add items here. Each item gets
              the portal palette, because what it opens is also a portal. */}
          <DropdownMenuItem onSelect={() => setPrefsOpen(true)}>
            <TbSettings />
            {t.configuracoes}
          </DropdownMenuItem>
          {EXTENSOES.flatMap(extensao =>
            (extensao.itensDaConta ?? []).map((Item, i) => (
              <LimiteDaExtensao key={`${extensao.nome}:${i}`} nome={extensao.nome}>
                <Item portalClassName={portalClassName} />
              </LimiteDaExtensao>
            )),
          )}
          {codigoFonte && (
            <DropdownMenuItem asChild>
              <a href={codigoFonte} target="_blank" rel="noopener noreferrer">
                <TbSourceCode />
                {textosDaCasca.comum.codigoFonte}
              </a>
            </DropdownMenuItem>
          )}
        </DropdownMenuGroup>

        <DropdownMenuSeparator />

        {/* Signing out lands on the anonymous Home — it's public, and opening the
            sign-in modal on top of someone who just left would be pushy. */}
        <DropdownMenuItem onSelect={() => signOut({ callbackUrl: "/" })}>
          <TbLogout />
          {t.sair}
        </DropdownMenuItem>

      </DropdownMenuContent>
    </DropdownMenu>

    <UserPreferencesDialog open={prefsOpen} onOpenChange={setPrefsOpen} className={portalClassName} />
    </>
  )
}

export default UserSidebar
