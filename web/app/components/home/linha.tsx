"use client"
import { TbDots } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { useShellTexts } from "./i18n/da-casca"

/**
 * The row of the three lists in the Mine group (Chats, Schedules, Artifacts) —
 * ONE row only, so the three speak the same language. The design is what
 * Artifacts already had: a flex in which the main element (button or `<div>`)
 * is `min-w-0 flex-1` and the "⋯" is a SIBLING with `shrink-0`. Never
 * `absolute`: an absolute "⋯" with the space reserved by hand (`pr-7`) left
 * ZERO slack on desktop (28px = right-1 + size-6) and, on the phone, 16px of
 * text under the 40px button. As a flex sibling it takes real space, and on the
 * phone it just pushes the text.
 *
 * It is a `<div>`, not an `<li>`: in the regular lists it goes inside
 * `SidebarMenuSubItem`; Artifacts reuses it inside the virtual list's
 * `div[role=listitem]`.
 *
 * `ativa` paints the background via `data-active`. The `aria-current` stays on
 * the list's BUTTON (the focusable element the screen reader announces), not here.
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
 * The row's "⋯", child of `DropdownMenuTrigger asChild` — the `ref` and the
 * trigger attributes arrive in `props`, like any prop in React 19. Hidden
 * until the ROW is hovered (`group-hover/linha`), on focus, on touch (`coarse:`,
 * where there is no hover to reveal it) and while the menu is open. 40px on the
 * phone (§5 of the screen patterns): taking space in the flex, the bigger
 * target pushes the text instead of covering it.
 */
export function GatilhoDeAcoes({
  rotulo,
  className,
  ...props
}: React.ComponentProps<"button"> & { rotulo: string }) {
  const t = useShellTexts().casca.linha
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
