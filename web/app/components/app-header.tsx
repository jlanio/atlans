"use client"

import { usePathname } from "next/navigation"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useScreenLanguage, useShellTexts } from "./home/i18n/da-casca"
import { SidebarTrigger } from "./ui/sidebar"
import WorkspaceSwitcher from "./workspace/workspace-switcher"
import { Skeleton } from "./ui/skeleton"

/**
 * Sticky bar at the top of the dashboard content. Always shows the active
 * workspace with visual identity (color + initials) + the user's role.
 *
 * Goal: even with the sidebar collapsed, or deep in a scroll, the user can
 * visually confirm which workspace they are operating in before any
 * destructive action (running a workflow, deleting a drive file/artifact).
 *
 * The right slot (`right`) is reserved for breadcrumbs or page-specific
 * actions in a future iteration.
 *
 * The SidebarTrigger here is mobile-only (`md:hidden`). On desktop the toggle
 * lives in the sidebar's own header (app-sidebar.tsx) and stays clickable in
 * collapsed mode (`collapsible="icon"`) — two identical buttons side by side
 * were redundant. Below 768px the sidebar becomes a <Sheet> and its button sits
 * *inside* the Sheet, that is, it only closes: this is the only way to open it.
 * The breakpoint matches MOBILE_BREAKPOINT from hooks/use-mobile.ts, so there
 * is no width at which both appear or both disappear.
 *
 * That is why the Home (`/`) does not return `null`: it does not want the bar,
 * but it needs the trigger. There the component becomes ONLY the mobile-only
 * floating trigger (see below) — the page's h1 belongs to HomeView
 * (`components/home/index.tsx`), not here: two <h1>s on the same route break
 * the screen reader's reading of the structure, and what knows what the page is
 * about is the view, not the shell.
 */

// Routes that render a fullscreen canvas (ReactFlow) and must not have
// persistent chrome on top. The canvas uses floating buttons with
// `absolute top-5` — the sticky header (z-40) covered the add-node
// button (z-10).
//
// What tells the workspace on these routes is `WorkflowLocation`, drawn over the
// canvas itself: the sidebar no longer serves as a fallback — the selector left
// it, and the editor still collapses it on its own on mount. Switching workspace
// from inside the editor was made impossible on purpose: the switch navigates to
// /projects and would discard the edit in progress.
const FULLSCREEN_ROUTES = [
  "/workflow/",   // /workflow/[id] e /workflow/create
]

export function AppHeader({ right }: { right?: React.ReactNode }) {
  const pathname = usePathname()
  const { loading } = useWorkspace()
  // Only the `/` route uses it: outside the Home the language scope already returns Portuguese.
  const sidebarTexts = useShellTexts().casca.barraLateral
  const idioma = useScreenLanguage()

  // The Home (`/`) is full-bleed like the canvas: no bar. But the header is the only
  // place in the app that mounts a sidebar trigger visible on the phone — below
  // 768px the bar becomes a <Sheet> and its button sits INSIDE the Sheet, that
  // is, it only closes. Returning `null` here left the phone without Chats,
  // Schedules, Artifacts, workspace switching or SIGN OUT: only the globe. So on
  // the Home the header degrades to the minimum — a mobile-only floating trigger,
  // and only that. EXACT match — a `startsWith("/")` would match every app route.
  if (pathname === "/") {
    return (
      <SidebarTrigger
        // Top RIGHT corner: the left belongs to the layers panel
        // (`left-6 top-6`) and the assistant panel starts at `top-16` on the
        // phone — this strip is the only free one.
        //
        // Home stacking, top to bottom: this trigger (z-50) >
        // layers panel (z-40) > assistant panel/bar (z-30). The
        // trigger has to be on TOP: on a narrow screen the expanded layers
        // panel grows to the right and, tied at z-40, whichever came later in
        // the DOM covered the button — and this is the only way to open the
        // bar on the phone (the button inside the Sheet only closes).
        //
        // `home dark` puts the near-black palette on the button itself: it lives
        // outside the HomeView tree, which is what declares the tokens.
        className="home dark app-region-no-drag fixed right-3 top-3 z-50 size-10 rounded-full border border-border bg-background/85 text-foreground shadow-lg backdrop-blur md:hidden"
        // Outside the HomeView tree: its `lang` does not reach here.
        lang={idioma}
        aria-label={sidebarTexts.abrirMenu}
        label={sidebarTexts.alternar}
      />
    )
  }

  if (pathname && FULLSCREEN_ROUTES.some(p => pathname.startsWith(p))) {
    return null
  }

  return (
    <header
      // `app-region-drag`: in the desktop app (window without a title bar) this
      // header drags the window; the controls below carry `app-region-no-drag`
      // to stay clickable. In the browser it has no effect (see globals.css).
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
          // No avatar block: the selector's trigger shows only name and role,
          // and a square placeholder would make the bar jump on load.
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
