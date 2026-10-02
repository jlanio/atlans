"use client"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip"
import { useSidebar } from "../ui/sidebar"
import { useNomeNaTela } from "../share/nome-na-tela"
import TitleSidebar from "./title-sidebar"

/**
 * A marca: glifo de fluxo (dois nós ligados, ecoando o canvas de workflow) +
 * o wordmark — o nome desta instalação (NOME_NA_TELA; «Atlans» sem ela, ver
 * lib/nome-na-tela.ts). Extraída do AppSidebar para o HomeSidebar reusar o
 * MESMO bloco — a casca da Home é "como o Claude Code", com a marca no topo.
 *
 * No modo ícone o bloco some (`group-data-[collapsible=icon]:hidden`): no
 * trilho de 3rem do app só sobra o gatilho de recolher, que centraliza sozinho.
 * Com `glifoNoTrilho` fica o GLIFO e some só o wordmark — em `sr-only`, não
 * `hidden`, porque o glifo é `aria-hidden` e o `<h1>` é o nome do link. A Home
 * usa isso: ali a marca é a única navegação explícita do admin, e recolhida
 * ela sumia inteira, saída incluída. O `tooltip` (só com `href`) diz o destino
 * no trilho, do mesmo jeito que o `SidebarMenuButton` faz com os itens.
 *
 * `href` — quando presente, a marca inteira vira link. É assim que a Home a usa:
 * ali a marca é a ÚNICA navegação explícita para o resto do app (leva a
 * /projects; o menu de conta não tem atalhos, e o resto se alcança pela paleta
 * Ctrl+K). No app padrão a marca é só rótulo e vai SEM href.
 */
/**
 * Só o glifo (o quadrado terracota com os dois nós ligados), sem o wordmark.
 * Exportado porque o modal de entrada da Home o põe no cabeçalho do card —
 * fora do sidebar, sem `useSidebar`.
 */
export function GlifoDaMarca() {
  return (
    <span
      aria-hidden
      className="flex size-7 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
    >
      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2.1} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="7.3" cy="7.8" r="2.4" />
        <circle cx="16.7" cy="16.2" r="2.4" />
        <path d="M9.3 9.4 14.7 14.6" />
      </svg>
    </span>
  )
}

export default function Marca({
  href,
  glifoNoTrilho = false,
  tooltip,
}: {
  href?: string
  glifoNoTrilho?: boolean
  tooltip?: React.ComponentProps<typeof TooltipContent>
}) {
  const { state, isMobile } = useSidebar()
  const nome = useNomeNaTela()

  const glifo = <GlifoDaMarca />
  const wordmark = (
    <TitleSidebar
      title={nome}
      className={glifoNoTrilho ? "group-data-[collapsible=icon]:sr-only" : undefined}
    />
  )

  const classe = cn("flex items-center gap-2", !glifoNoTrilho && "group-data-[collapsible=icon]:hidden")

  if (!href) {
    return (
      <span className={classe}>
        {glifo}
        {wordmark}
      </span>
    )
  }

  const link = (
    <Link
      href={href}
      // Alvo clicável discreto: um leve realce no hover diz que é link, sem
      // caixa permanente competindo com a lista.
      className={cn(classe, "rounded-md transition-opacity hover:opacity-80")}
    >
      {glifo}
      {wordmark}
    </Link>
  )
  if (!tooltip) return link

  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      {/* Só no trilho: expandida, o wordmark já diz tudo; no telefone não há trilho. */}
      <TooltipContent side="right" align="center" hidden={state !== "collapsed" || isMobile} {...tooltip} />
    </Tooltip>
  )
}
