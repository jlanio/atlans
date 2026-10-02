"use client"

import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { VariantProps, cva } from "class-variance-authority"
import { PanelLeftIcon } from "lucide-react"

import { useIsMobile } from "@/hooks/use-mobile"
import { cn } from "@/lib/utils"
import { Button } from "@/app/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/app/components/ui/sheet"
import { Skeleton } from "@/app/components/ui/skeleton"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/app/components/ui/tooltip"

const SIDEBAR_COOKIE_NAME = "sidebar_state"
const SIDEBAR_COOKIE_MAX_AGE = 60 * 60 * 24 * 7
// `SIDEBAR_WIDTH = "16rem"` saiu: a largura agora vem em px (um arrasto é em
// px), e o mesmo número é `SIDEBAR_WIDTH_PADRAO` logo abaixo.
// A largura ESCOLHIDA pela pessoa, em px, no mesmo molde do `sidebar_state`: o
// layout a lê no servidor e a devolve como `defaultWidth`, então ela sobrevive
// ao F5 e não pisca no primeiro quadro.
const SIDEBAR_WIDTH_COOKIE_NAME = "sidebar_width"
/** 16rem — o padrão, e o destino do duplo clique no separador. */
export const SIDEBAR_WIDTH_PADRAO = 256
// Abaixo de 180px a sublista de Artefatos não cabe (ícone + nome + gatilho de
// ações); acima de 480px a barra passa a competir com o globo, que é o conteúdo.
export const SIDEBAR_WIDTH_MIN = 180
export const SIDEBAR_WIDTH_MAX = 480

/** Mantém a largura dentro dos limites — o arrasto e o teclado passam por aqui. */
export function limitarLargura(px: number): number {
  // `Math.max(min, Math.min(max, NaN))` é NaN, e `--sidebar-width: NaNpx` não
  // é uma largura — a barra sumia. O valor vem de um cookie, que é entrada do
  // cliente, então a guarda mora aqui e não em quem chama.
  if (!Number.isFinite(px)) return SIDEBAR_WIDTH_PADRAO
  return Math.round(Math.max(SIDEBAR_WIDTH_MIN, Math.min(SIDEBAR_WIDTH_MAX, px)))
}
const SIDEBAR_WIDTH_MOBILE = "18rem"
const SIDEBAR_WIDTH_ICON = "3rem"
const SIDEBAR_KEYBOARD_SHORTCUT = "b"

type SidebarContextProps = {
  state: "expanded" | "collapsed"
  open: boolean
  setOpen: (open: boolean) => void
  openMobile: boolean
  setOpenMobile: (open: boolean) => void
  isMobile: boolean
  toggleSidebar: () => void
  /** Largura atual da barra, em px (desktop; no telefone é um Sheet). */
  width: number
  setWidth: (px: number) => void
}

const SidebarContext = React.createContext<SidebarContextProps | null>(null)

function useSidebar() {
  const context = React.useContext(SidebarContext)
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider.")
  }

  return context
}

function SidebarProvider({
  defaultOpen = true,
  open: openProp,
  onOpenChange: setOpenProp,
  defaultWidth = SIDEBAR_WIDTH_PADRAO,
  className,
  style,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  defaultOpen?: boolean
  /** Largura inicial em px, lida do cookie `sidebar_width` pelo layout. */
  defaultWidth?: number
  open?: boolean
  onOpenChange?: (open: boolean) => void
}) {
  const isMobile = useIsMobile()
  const [openMobile, setOpenMobile] = React.useState(false)

  // This is the internal state of the sidebar.
  // We use openProp and setOpenProp for control from outside the component.
  const [_open, _setOpen] = React.useState(defaultOpen)
  const open = openProp ?? _open
  const setOpen = React.useCallback(
    (value: boolean | ((value: boolean) => boolean)) => {
      const openState = typeof value === "function" ? value(open) : value
      if (setOpenProp) {
        setOpenProp(openState)
      } else {
        _setOpen(openState)
      }

      // This sets the cookie to keep the sidebar state.
      document.cookie = `${SIDEBAR_COOKIE_NAME}=${openState}; path=/; max-age=${SIDEBAR_COOKIE_MAX_AGE}`
    },
    [setOpenProp, open]
  )

  // A largura escolhida. Gravada no mesmo molde do `sidebar_state`: um cookie,
  // porque quem precisa dela ANTES do primeiro quadro é o servidor (o layout a
  // injeta como `defaultWidth`) — em localStorage a barra nasceria com 16rem e
  // saltaria para a largura da pessoa no primeiro efeito.
  const [width, _setWidth] = React.useState(() => limitarLargura(defaultWidth))
  const setWidth = React.useCallback((px: number) => {
    const v = limitarLargura(px)
    _setWidth(v)
    document.cookie = `${SIDEBAR_WIDTH_COOKIE_NAME}=${v}; path=/; max-age=${SIDEBAR_COOKIE_MAX_AGE}`
  }, [])

  // Helper to toggle the sidebar.
  const toggleSidebar = React.useCallback(() => {
    return isMobile ? setOpenMobile((open) => !open) : setOpen((open) => !open)
  }, [isMobile, setOpen, setOpenMobile])

  // Adds a keyboard shortcut to toggle the sidebar.
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.key === SIDEBAR_KEYBOARD_SHORTCUT &&
        (event.metaKey || event.ctrlKey)
      ) {
        event.preventDefault()
        toggleSidebar()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [toggleSidebar])

  // We add a state so that we can do data-state="expanded" or "collapsed".
  // This makes it easier to style the sidebar with Tailwind classes.
  const state = open ? "expanded" : "collapsed"

  const contextValue = React.useMemo<SidebarContextProps>(
    () => ({
      state,
      open,
      setOpen,
      isMobile,
      openMobile,
      setOpenMobile,
      toggleSidebar,
      width,
      setWidth,
    }),
    [state, open, setOpen, isMobile, openMobile, setOpenMobile, toggleSidebar, width, setWidth]
  )

  return (
    <SidebarContext.Provider value={contextValue}>
      <TooltipProvider delayDuration={0}>
        <div
          data-slot="sidebar-wrapper"
          style={
            {
              // Em px, não em rem: a largura vem de um arrasto, que é em px.
              // O `SIDEBAR_WIDTH` de 16rem continua sendo o padrão, agora via
              // `SIDEBAR_WIDTH_PADRAO` (o mesmo número).
              "--sidebar-width": `${width}px`,
              "--sidebar-width-icon": SIDEBAR_WIDTH_ICON,
              ...style,
            } as React.CSSProperties
          }
          className={cn(
            "group/sidebar-wrapper has-data-[variant=inset]:bg-sidebar flex min-h-svh w-full",
            className
          )}
          {...props}
        >
          {children}
        </div>
      </TooltipProvider>
    </SidebarContext.Provider>
  )
}

function Sidebar({
  side = "left",
  variant = "sidebar",
  collapsible = "offcanvas",
  mobileTitle = "Barra lateral",
  mobileDescription = "Navegação lateral, aberta como painel.",
  className,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  side?: "left" | "right"
  variant?: "sidebar" | "floating" | "inset"
  collapsible?: "offcanvas" | "icon" | "none"
  /** Nome e descrição do painel do telefone para leitor de tela (a Home traduzida passa os dela). */
  mobileTitle?: string
  mobileDescription?: string
}) {
  const { isMobile, state, openMobile, setOpenMobile } = useSidebar()

  if (collapsible === "none") {
    return (
      <div
        data-slot="sidebar"
        className={cn(
          "bg-sidebar text-sidebar-foreground flex h-full w-(--sidebar-width) flex-col",
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }

  if (isMobile) {
    return (
      <Sheet open={openMobile} onOpenChange={setOpenMobile} {...props}>
        <SheetContent
          data-sidebar="sidebar"
          data-slot="sidebar"
          data-mobile="true"
          // O `className` do <Sidebar> TEM de chegar aqui: no telefone o painel
          // é este SheetContent (portado para o <body>), e é ele quem pinta o
          // fundo. Sem repassar, uma barra temática como a da Home declarava a
          // paleta só nos filhos — texto quase branco sobre o `--sidebar` do
          // tema do app, ilegível no tema claro.
          className={cn(
            "bg-sidebar text-sidebar-foreground w-(--sidebar-width) p-0 [&>button]:hidden",
            className
          )}
          style={
            {
              "--sidebar-width": SIDEBAR_WIDTH_MOBILE,
            } as React.CSSProperties
          }
          side={side}
        >
          <SheetHeader className="sr-only">
            <SheetTitle>{mobileTitle}</SheetTitle>
            <SheetDescription>{mobileDescription}</SheetDescription>
          </SheetHeader>
          <div className="flex h-full w-full flex-col">{children}</div>
        </SheetContent>
      </Sheet>
    )
  }

  return (
    <div
      className="group peer text-sidebar-foreground hidden md:block"
      data-state={state}
      data-collapsible={state === "collapsed" ? collapsible : ""}
      data-variant={variant}
      data-side={side}
      data-slot="sidebar"
    >
      {/* This is what handles the sidebar gap on desktop */}
      <div
        data-slot="sidebar-gap"
        className={cn(
          "relative w-(--sidebar-width) bg-transparent transition-[width] duration-200 ease-linear",
          // Arrastando, a transição perseguiria o ponteiro com 200ms de atraso
          // — a barra parecia elástica. Ancorado no GRUPO, e não neste div:
          // `has-data-[arrastando]` aqui nunca casava, porque o separador vive
          // no `sidebar-container`, que é IRMÃO deste. E é justamente este div
          // que reserva o espaço e empurra o <main> — sem a regra certa, o
          // conteúdo ficava 200ms atrás da borda durante o gesto.
          "group-has-data-[arrastando]:transition-none",
          "group-data-[collapsible=offcanvas]:w-0",
          "group-data-[side=right]:rotate-180",
          variant === "floating" || variant === "inset"
            ? "group-data-[collapsible=icon]:w-[calc(var(--sidebar-width-icon)+(--spacing(4)))]"
            : "group-data-[collapsible=icon]:w-(--sidebar-width-icon)"
        )}
      />
      <div
        data-slot="sidebar-container"
        className={cn(
          "fixed inset-y-0 z-10 hidden h-svh w-(--sidebar-width) transition-[left,right,width] duration-200 ease-linear md:flex",
          // No grupo também, por simetria com o gap acima: os dois têm de
          // parar de animar no mesmo quadro, senão um persegue o outro.
          "group-has-data-[arrastando]:transition-none",
          side === "left"
            ? "left-0 group-data-[collapsible=offcanvas]:left-[calc(var(--sidebar-width)*-1)]"
            : "right-0 group-data-[collapsible=offcanvas]:right-[calc(var(--sidebar-width)*-1)]",
          // Adjust the padding for floating and inset variants.
          variant === "floating" || variant === "inset"
            ? "p-2 group-data-[collapsible=icon]:w-[calc(var(--sidebar-width-icon)+(--spacing(4))+2px)]"
            : "group-data-[collapsible=icon]:w-(--sidebar-width-icon) group-data-[side=left]:border-r group-data-[side=right]:border-l",
          className
        )}
        {...props}
      >
        <div
          data-sidebar="sidebar"
          data-slot="sidebar-inner"
          className="bg-sidebar group-data-[variant=floating]:border-sidebar-border flex h-full w-full flex-col group-data-[variant=floating]:rounded-lg group-data-[variant=floating]:border group-data-[variant=floating]:shadow-sm"
        >
          {children}
        </div>
      </div>
    </div>
  )
}

function SidebarTrigger({
  className,
  onClick,
  label = "Alternar barra lateral",
  ...props
}: React.ComponentProps<typeof Button> & { label?: string }) {
  const { toggleSidebar } = useSidebar()

  return (
    <Button
      data-sidebar="trigger"
      data-slot="sidebar-trigger"
      variant="ghost"
      size="icon"
      className={cn("size-7 [&_svg:not([class*='size-'])]:size-4 ", className)}
      onClick={(event) => {
        onClick?.(event)
        toggleSidebar()
      }}
      {...props}
    >
      <PanelLeftIcon />
      <span className="sr-only">{label}</span>
    </Button>
  )
}

/**
 * A borda da barra. Ela SEMPRE mostrou o cursor de redimensionar
 * (`cursor-w-resize`) e só sabia RECOLHER — a interface prometia um arrasto que
 * não existia, e quem tentava alargar para ler o nome inteiro de um artefato
 * via a barra fechar na cara. Agora ela faz as duas coisas, cada uma no estado
 * em que faz sentido:
 *
 * - **Expandida**: é um separador (`role="separator"`, o padrão WAI-ARIA de
 *   janela). Arrastar redimensiona; ←/→ ajustam pelo teclado (com Shift, em
 *   passos maiores); Home/End vão aos limites; duplo clique volta ao padrão.
 * - **Recolhida**: continua o botão que expande, que é o único jeito de voltar
 *   do trilho de 3rem por aqui.
 *
 * Recolher não se perdeu: o `SidebarTrigger` do cabeçalho e o Ctrl/Cmd+B
 * continuam fazendo isso, e são as duas formas anunciadas.
 */
/** Os rótulos do trilho. O padrão é o português da administração; a Home passa os do idioma dela. */
export interface TextosDoTrilho {
  expandir: string
  redimensionar: string
  dica: string
}

export const TEXTOS_DO_TRILHO_PT: TextosDoTrilho = {
  expandir: "Expandir barra lateral",
  redimensionar: "Redimensionar a barra lateral",
  dica: "Arraste para redimensionar · duplo clique volta ao padrão",
}

function SidebarRail({
  className,
  textos = TEXTOS_DO_TRILHO_PT,
  ...props
}: React.ComponentProps<"button"> & { textos?: TextosDoTrilho }) {
  const { toggleSidebar, state, width, setWidth } = useSidebar()
  const recolhida = state === "collapsed"
  const ref = React.useRef<HTMLButtonElement>(null)
  const [arrastando, setArrastando] = React.useState(false)

  // O lado importa para a conta: à esquerda a barra começa em x=0, à direita
  // ela termina na borda da janela. Lido do DOM (o `data-side` do grupo) em vez
  // de virar prop — o componente não recebe `side`, quem o recebe é o <Sidebar>.
  const larguraDoPonteiro = React.useCallback((clientX: number) => {
    const grupo = ref.current?.closest<HTMLElement>('[data-slot="sidebar"]')
    const direita = grupo?.dataset.side === "right"
    return direita ? window.innerWidth - clientX : clientX
  }, [])

  // Durante o gesto o React fica FORA do caminho: a largura vai direto na
  // variável de CSS do envoltório, e o estado só recebe o valor no fim.
  //
  // Medido antes de escrever isto: com `setWidth` a cada `pointermove`, um
  // segundo de arrasto custava 60 renders de CADA consumidor de `useSidebar`
  // (são nove, a lista virtualizada de Artefatos entre eles) e 60 escritas
  // síncronas em `document.cookie`. Agora é um render e um cookie por gesto.
  const larguraViva = React.useRef(width)
  const envoltorio = React.useCallback(
    () => ref.current?.closest<HTMLElement>('[data-slot="sidebar-wrapper"]'),
    [],
  )

  function aoApontar(e: React.PointerEvent<HTMLButtonElement>) {
    if (recolhida || e.button !== 0) return
    // O ponteiro fica preso ao separador: sair de cima dele (ou passar sobre um
    // iframe, como o do globo) não interrompe o arrasto no meio.
    ref.current?.setPointerCapture(e.pointerId)
    larguraViva.current = width
    setArrastando(true)
  }
  function aoMover(e: React.PointerEvent<HTMLButtonElement>) {
    if (!arrastando) return
    e.preventDefault()
    larguraViva.current = limitarLargura(larguraDoPonteiro(e.clientX))
    envoltorio()?.style.setProperty("--sidebar-width", `${larguraViva.current}px`)
  }
  function aoSoltar(e: React.PointerEvent<HTMLButtonElement>) {
    if (!arrastando) return
    ref.current?.releasePointerCapture(e.pointerId)
    setArrastando(false)
    // Aqui, e só aqui: o estado (com ele o `aria-valuenow`) e o cookie.
    setWidth(larguraViva.current)
  }
  function aoTeclar(e: React.KeyboardEvent<HTMLButtonElement>) {
    if (recolhida) return
    // A barra à direita cresce para o outro lado: ← e → trocam de papel, senão
    // a seta "para fora" encolheria.
    const paraDireita = ref.current?.closest<HTMLElement>('[data-slot="sidebar"]')?.dataset.side !== "right"
    const passo = (e.shiftKey ? 48 : 16) * (paraDireita ? 1 : -1)
    if (e.key === "ArrowRight") { e.preventDefault(); setWidth(width + passo) }
    else if (e.key === "ArrowLeft") { e.preventDefault(); setWidth(width - passo) }
    else if (e.key === "Home") { e.preventDefault(); setWidth(SIDEBAR_WIDTH_MIN) }
    else if (e.key === "End") { e.preventDefault(); setWidth(SIDEBAR_WIDTH_MAX) }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setWidth(SIDEBAR_WIDTH_PADRAO) }
  }

  return (
    <button
      ref={ref}
      data-sidebar="rail"
      data-slot="sidebar-rail"
      data-arrastando={arrastando || undefined}
      // Recolhida é um botão que expande; expandida é um separador que
      // redimensiona. O papel e o rótulo acompanham, senão o leitor de tela
      // anunciaria uma coisa e a tecla faria outra.
      {...(recolhida
        ? { "aria-label": textos.expandir, tabIndex: -1, onClick: toggleSidebar, title: textos.expandir }
        : {
            role: "separator",
            "aria-orientation": "vertical",
            "aria-label": textos.redimensionar,
            "aria-valuenow": width,
            "aria-valuemin": SIDEBAR_WIDTH_MIN,
            "aria-valuemax": SIDEBAR_WIDTH_MAX,
            tabIndex: 0,
            title: textos.dica,
            onPointerDown: aoApontar,
            onPointerMove: aoMover,
            onPointerUp: aoSoltar,
            onPointerCancel: aoSoltar,
            onDoubleClick: () => setWidth(SIDEBAR_WIDTH_PADRAO),
            onKeyDown: aoTeclar,
          })}
      className={cn(
        "hover:after:bg-sidebar-border absolute inset-y-0 z-20 hidden w-4 -translate-x-1/2 transition-all ease-linear group-data-[side=left]:-right-4 group-data-[side=right]:left-0 after:absolute after:inset-y-0 after:left-1/2 after:w-[2px] sm:flex",
        "in-data-[side=left]:cursor-w-resize in-data-[side=right]:cursor-e-resize",
        "[[data-side=left][data-state=collapsed]_&]:cursor-e-resize [[data-side=right][data-state=collapsed]_&]:cursor-w-resize",
        "hover:group-data-[collapsible=offcanvas]:bg-sidebar group-data-[collapsible=offcanvas]:translate-x-0 group-data-[collapsible=offcanvas]:after:left-full",
        "[[data-side=left][data-collapsible=offcanvas]_&]:-right-2",
        "[[data-side=right][data-collapsible=offcanvas]_&]:-left-2",
        // Expandida o cursor é o de coluna (redimensionar para os dois lados),
        // e não o `w-resize` de "empurrar para fechar".
        !recolhida && "in-data-[side=left]:cursor-col-resize in-data-[side=right]:cursor-col-resize",
        // Enquanto arrasta, a linha fica acesa e o foco do teclado também a
        // mostra — sem isso o separador é invisível para quem chega por Tab.
        "focus-visible:outline-none focus-visible:after:bg-sidebar-border data-[arrastando]:after:bg-sidebar-border",
        className
      )}
      {...props}
    />
  )
}

function SidebarHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-header"
      data-sidebar="header"
      className={cn("flex flex-col gap-2 p-2", className)}
      {...props}
    />
  )
}

function SidebarFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-footer"
      data-sidebar="footer"
      className={cn("flex flex-col gap-2 p-2", className)}
      {...props}
    />
  )
}

function SidebarContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-content"
      data-sidebar="content"
      className={cn(
        "flex min-h-0 flex-1 flex-col gap-2 overflow-auto group-data-[collapsible=icon]:overflow-hidden",
        className
      )}
      {...props}
    />
  )
}

function SidebarGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-group"
      data-sidebar="group"
      className={cn("relative flex w-full min-w-0 flex-col p-2", className)}
      {...props}
    />
  )
}

function SidebarGroupLabel({
  className,
  asChild = false,
  ...props
}: React.ComponentProps<"div"> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "div"

  return (
    <Comp
      data-slot="sidebar-group-label"
      data-sidebar="group-label"
      className={cn(
        "text-sidebar-foreground/70 ring-sidebar-ring flex h-8 shrink-0 items-center rounded-md px-2 text-xs font-medium outline-hidden transition-[margin,opacity] duration-200 ease-linear focus-visible:ring-2 [&>svg]:size-4 [&>svg]:shrink-0",
        "group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:pointer-events-none group-data-[collapsible=icon]:opacity-0",
        className
      )}
      {...props}
    />
  )
}

function SidebarGroupContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-group-content"
      data-sidebar="group-content"
      className={cn("w-full text-sm", className)}
      {...props}
    />
  )
}

function SidebarMenu({ className, ...props }: React.ComponentProps<"ul">) {
  return (
    <ul
      data-slot="sidebar-menu"
      data-sidebar="menu"
      className={cn("flex w-full min-w-0 flex-col gap-1", className)}
      {...props}
    />
  )
}

function SidebarMenuItem({ className, ...props }: React.ComponentProps<"li">) {
  return (
    <li
      data-slot="sidebar-menu-item"
      data-sidebar="menu-item"
      className={cn("group/menu-item relative", className)}
      {...props}
    />
  )
}

const sidebarMenuButtonVariants = cva(
  "peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm outline-hidden ring-sidebar-ring transition-[width,height,padding] hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-data-[sidebar=menu-action]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground group-data-[collapsible=icon]:size-8! group-data-[collapsible=icon]:p-2! [&>span:last-child]:truncate [&>svg]:size-4 [&>svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        outline:
          "bg-background shadow-[0_0_0_1px_hsl(var(--sidebar-border))] hover:bg-sidebar-accent hover:text-sidebar-accent-foreground hover:shadow-[0_0_0_1px_hsl(var(--sidebar-accent))]",
      },
      size: {
        default: "h-8 text-sm",
        sm: "h-7 text-xs",
        lg: "h-12 text-sm group-data-[collapsible=icon]:p-0!",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function SidebarMenuButton({
  asChild = false,
  isActive = false,
  variant = "default",
  size = "default",
  tooltip,
  className,
  ...props
}: React.ComponentProps<"button"> & {
  asChild?: boolean
  isActive?: boolean
  tooltip?: string | React.ComponentProps<typeof TooltipContent>
} & VariantProps<typeof sidebarMenuButtonVariants>) {
  const Comp = asChild ? Slot : "button"
  const { isMobile, state } = useSidebar()

  const button = (
    <Comp
      data-slot="sidebar-menu-button"
      data-sidebar="menu-button"
      data-size={size}
      data-active={isActive}
      className={cn(sidebarMenuButtonVariants({ variant, size }), className)}
      {...props}
    />
  )

  if (!tooltip) {
    return button
  }

  if (typeof tooltip === "string") {
    tooltip = {
      children: tooltip,
    }
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent
        side="right"
        align="center"
        hidden={state !== "collapsed" || isMobile}
        {...tooltip}
      />
    </Tooltip>
  )
}

function SidebarMenuSkeleton({
  className,
  showIcon = false,
  ...props
}: React.ComponentProps<"div"> & {
  showIcon?: boolean
}) {
  // Random width between 50 to 90%.
  const width = React.useMemo(() => {
    return `${Math.floor(Math.random() * 40) + 50}%`
  }, [])

  return (
    <div
      data-slot="sidebar-menu-skeleton"
      data-sidebar="menu-skeleton"
      className={cn("flex h-8 items-center gap-2 rounded-md px-2", className)}
      {...props}
    >
      {showIcon && (
        <Skeleton
          className="size-4 rounded-md"
          data-sidebar="menu-skeleton-icon"
        />
      )}
      <Skeleton
        className="h-4 max-w-(--skeleton-width) flex-1"
        data-sidebar="menu-skeleton-text"
        style={
          {
            "--skeleton-width": width,
          } as React.CSSProperties
        }
      />
    </div>
  )
}

function SidebarMenuSub({ className, ...props }: React.ComponentProps<"ul">) {
  return (
    <ul
      data-slot="sidebar-menu-sub"
      data-sidebar="menu-sub"
      className={cn(
        "border-sidebar-border mx-3.5 flex min-w-0 translate-x-px flex-col gap-1 border-l px-2.5 py-0.5",
        "group-data-[collapsible=icon]:hidden",
        className
      )}
      {...props}
    />
  )
}

function SidebarMenuSubItem({
  className,
  ...props
}: React.ComponentProps<"li">) {
  return (
    <li
      data-slot="sidebar-menu-sub-item"
      data-sidebar="menu-sub-item"
      className={cn("group/menu-sub-item relative", className)}
      {...props}
    />
  )
}

export {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
}
