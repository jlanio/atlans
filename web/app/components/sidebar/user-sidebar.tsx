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
 * `portalClassName`: o menu e o diálogo de Preferências são portais Radix — vão
 * ao <body>, fora da árvore de quem os abriu. A Home (sempre escura) passa
 * `home-portal`, senão os dois abriam na paleta clara do app por cima dela. É
 * prop, e não uma leitura de rota aqui dentro: a paleta é de quem HOSPEDA o
 * componente, e a casca já decide rota→sidebar uma vez só (ShellSidebar). Sem a
 * prop, o comportamento é o de sempre — o AppSidebar não passa nada.
 */
const UserSidebar = ({ portalClassName }: { portalClassName?: string } = {}) => {

  const { isMobile } = useSidebar()
  const { theme, setTheme } = useTheme()
  const { data: session } = useSession()
  const [changedThemeState, setChangedThemeState] = useState("")
  const [prefsOpen, setPrefsOpen] = useState(false)
  const textosDaCasca = useTextosDaCasca()
  const t = textosDaCasca.casca.conta
  // AGPL §13: o código-fonte desta instalação (CODIGO_FONTE_URL), quando ela
  // o declara. Abre fora: não é rota desta aplicação.
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
          {/* "Tokens de acesso" saiu daqui por decisão de produto. A página
              /settings/tokens, como toda rota fora da Home, só abre para o
              administrador do sistema (`proxy.ts` devolve `/` aos demais), e
              ele chega a ela pela paleta Ctrl+K ou pela URL. O token é
              pessoal (age em nome de quem o cria), então hoje só
              administradores têm token — é o que dizem as recusas do MCP.

              As extensões (`web/extensoes`) somam itens aqui. Cada item recebe
              a paleta do portal, porque o que ele abre também é um portal. */}
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

        {/* Sair cai na Home anônima — ela é pública, e abrir o modal de
            entrada em cima de quem acabou de sair seria insistência. */}
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
