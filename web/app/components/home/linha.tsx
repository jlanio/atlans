"use client"
import { TbDots } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { useTextosDaCasca } from "./i18n/da-casca"

/**
 * A linha das três listas do grupo Meus (Chats, Agendamentos, Artefatos) — UMA
 * só, para as três falarem a mesma língua. O desenho é o que Artefatos já
 * tinha: um flex em que o principal (botão ou `<div>`) é `min-w-0 flex-1` e o
 * "⋯" é IRMÃO com `shrink-0`. Nunca `absolute`: um "⋯" absoluto com o espaço
 * reservado à mão (`pr-7`) dava folga ZERO no desktop (28px = right-1 + size-6)
 * e, no telefone, 16px de texto por baixo do botão de 40px. Irmão no flex ele
 * ocupa espaço de verdade, e no telefone só empurra o texto.
 *
 * É `<div>`, não `<li>`: nas listas comuns vai dentro de `SidebarMenuSubItem`;
 * Artefatos o reusa dentro do `div[role=listitem]` da lista virtual.
 *
 * `ativa` pinta o fundo pelo `data-active`. O `aria-current` fica no BOTÃO da
 * lista (o focável que o leitor de tela anuncia), não aqui.
 */
export function LinhaDoMeu({
  ativa = false,
  className,
  ...props
}: React.ComponentProps<"div"> & { ativa?: boolean }) {
  return (
    <div
      data-slot="linha-do-meu"
      data-active={ativa || undefined}
      className={cn(
        "group/linha flex items-center gap-1 rounded-md pl-2 pr-1 hover:bg-sidebar-accent data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium",
        className,
      )}
      {...props}
    />
  )
}

/**
 * O "⋯" da linha, filho de `DropdownMenuTrigger asChild` — o `ref` e os
 * atributos do gatilho chegam em `props`, como qualquer prop no React 19. Some
 * até o hover da LINHA (`group-hover/linha`), ao foco, no toque (`coarse:`, onde
 * não há hover para revelar) e enquanto o menu está aberto. 40px no telefone
 * (§5 do padrão de telas): ocupando espaço no flex, o alvo maior empurra o
 * texto em vez de cobri-lo.
 */
export function GatilhoDeAcoes({
  rotulo,
  className,
  ...props
}: React.ComponentProps<"button"> & { rotulo: string }) {
  const t = useTextosDaCasca().casca.linha
  return (
    <button
      type="button"
      aria-label={t.acoes(rotulo)}
      className={cn(
        "flex size-6 shrink-0 items-center justify-center rounded-md text-sidebar-foreground/60 opacity-0 transition-opacity hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:opacity-100 group-hover/linha:opacity-100 coarse:opacity-100 data-[state=open]:opacity-100 max-md:size-10",
        className,
      )}
      {...props}
    >
      <TbDots className="size-4" />
    </button>
  )
}
