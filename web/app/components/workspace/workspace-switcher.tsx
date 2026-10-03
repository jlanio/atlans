"use client";

import { useState } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { usePathname, useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";
import { TbCheck, TbChevronDown, TbCrown, TbHome, TbPlus, TbSettings, TbUserCheck } from "react-icons/tb";
import { cn } from "@/lib/utils";
import { useSession } from "next-auth/react";
import { WorkspaceBadge } from "./workspace-badge";
import { roleLabel } from "./role-labels";

export default function WorkspaceSwitcher() {
  const { workspaces, current, setCurrent } = useWorkspace();
  const { data: session } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const userId = session?.user?.id_hash ?? null;
  // Same rule as WorkspaceBadge: `my_role` distinguishes the five roles, and the
  // `owner_id` comparison remains as a fallback. Without it, an admin of a
  // shared workspace showed up as "Convidado" (Guest) on every row.
  function roleOf(ws: { my_role: string | null; owner_id: string | null }) {
    const dono =
      ws.my_role === "owner" || !!(ws.owner_id && userId && ws.owner_id === userId);
    return {
      dono,
      rotulo: dono ? "Proprietário" : ws.my_role ? roleLabel(ws.my_role) : "Convidado",
    };
  }

  // When a workspace is selected in the dropdown, redirects to /projects.
  // Goal: immediately show the new workspace's workflows — avoids the user
  // switching while on /observability and seeing no visible change beyond the
  // header. If already on /projects, router.push does not change the URL but
  // the list's useEffect refetches via its dependency on current.id_hash
  // (projects/index.tsx:127).
  //
  // /workflow/[id] is no longer in this list: there the header is not rendered
  // (see FULLSCREEN_ROUTES in app-header) and this picker is not mounted.
  // Whoever needs to switch leaves the editor — switching mid-edit would
  // discard it.
  //
  // The exception is /workspaces: there the switch ALREADY has a visible effect
  // (the active card changes), and someone configuring a workspace was thrown
  // off the screen mid-task. Home (/) is the same case: the Artifacts list
  // re-scopes by current.id_hash right away, so pushing to /projects would take
  // the person off the globe for no gain — the change already shows where they are.
  const handleSelect = (wsId: string) => {
    const ws = workspaces.find((w) => w.id_hash === wsId);
    if (!ws) return;
    setCurrent(ws);
    setOpen(false);
    if (pathname !== "/workspaces" && pathname !== "/") router.push("/projects");
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        {/* A plain button, not `SidebarMenuButton`: the picker left the sidebar and
            now lives in the header, where the sidebar primitive would bring full
            width and a menu item's height. */}
        <button
          type="button"
          // The workspace name comes from WorkspaceBadge, but `aria-label` on the
          // button REPLACES the content in the accessible name computation: with
          // a fixed label, screen reader users heard "clique para trocar" and
          // never which workspace was active — the only thing this header
          // exists to say.
          aria-label={
            current
              ? `Workspace ativo: ${current.name}. Clique para trocar.`
              : "Nenhum workspace ativo. Clique para escolher."
          }
          // `app-region-no-drag`: in the desktop app the AppHeader drags the window;
          // this button must stay clickable. No effect in the browser.
          className="app-region-no-drag flex min-w-0 max-w-xs items-center gap-2 rounded-md px-2 py-1 text-left transition-colors hover:bg-accent focus-visible:ring-ring data-[state=open]:bg-accent focus-visible:ring-2 focus-visible:outline-none"
        >
          {/* Identity chip ON: the workspace's deterministic color is the
              fastest signal of "which scope am I in" — and this header exists
              precisely to answer that before a destructive action. It used to
              be off because it looked redundant next to the name; the color,
              however, is recognizable at a glance in a way the text is not. */}
          <WorkspaceBadge
            workspace={current}
            size="md"
            showName
            showRole
            showAvatar
            currentUserId={userId}
            className="min-w-0"
          />
          <TbChevronDown className="size-4 shrink-0 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        // Its own width, not the trigger's: in the header the button shrinks to the
        // workspace name, and tying the menu to it squeezed the list to the point
        // of cutting the names. It grows with the content up to a ceiling that
        // still fits on a phone screen.
        // The minimum also gives way on narrow screens: `min-width` beats
        // `max-width`, so a raw `min-w-72` would overflow again below ~312px.
        className="min-w-[min(18rem,calc(100vw-1.5rem))] max-w-[min(24rem,calc(100vw-1.5rem))] rounded-lg"
        align="start"
        sideOffset={4}
        // Without collision padding the menu touched the phone's edge and ate its
        // own padding — the last workspace's role was cut off on screen.
        collisionPadding={12}
      >
        <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          Workspaces
        </DropdownMenuLabel>

        {workspaces.map((ws) => {
          const isActive = current?.id_hash === ws.id_hash;
          const papel = roleOf(ws);
          return (
            <DropdownMenuItem
              key={ws.id_hash}
              onSelect={() => handleSelect(ws.id_hash)}
              // `data-active` was not read by any CSS: the active workspace had no
              // mark at all in the list. It is now marked with surface, weight,
              // a check AND the terracotta bar on the left — the same "current"
              // idiom as sidebar A's active item.
              className={cn(
                "gap-2",
                isActive &&
                  "bg-accent font-medium before:absolute before:left-1 before:top-1/2 before:h-4 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-primary before:content-['']",
              )}
            >
              <WorkspaceBadge workspace={ws} size="sm" />
              {/* `truncate` must sit on the element that contains the TEXT: on the
                  flex container it clips nothing, and the long name ran over
                  the check and the role instead of turning into an ellipsis. */}
              <span className="flex min-w-0 flex-1 items-center gap-1">
                {ws.is_default && <TbHome className="size-3 shrink-0 text-muted-foreground" />}
                <span className="truncate">{ws.name}</span>
              </span>
              {isActive && <TbCheck className="size-3.5 shrink-0 text-primary" />}
              <span className={`flex shrink-0 items-center gap-0.5 text-xs ${
                papel.dono ? "text-amber-700 dark:text-amber-400" : "text-muted-foreground"
              }`}>
                {papel.dono ? <TbCrown className="size-3" /> : <TbUserCheck className="size-3" />}
                {papel.rotulo}
              </span>
            </DropdownMenuItem>
          );
        })}

        <DropdownMenuSeparator />

        <DropdownMenuItem
          className="group/act gap-2"
          onSelect={() => { router.push("/workspaces"); setOpen(false); }}
        >
          <div className="flex size-6 items-center justify-center rounded-md border bg-background transition-colors group-hover/act:border-primary/50">
            <TbSettings className="size-4 text-muted-foreground transition-colors group-hover/act:text-primary" />
          </div>
          <span>Gerenciar workspaces</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          className="group/act gap-2"
          onSelect={() => { router.push("/workspaces?new=1"); setOpen(false); }}
        >
          <div className="flex size-6 items-center justify-center rounded-md border bg-background transition-colors group-hover/act:border-primary/50">
            <TbPlus className="size-4 text-muted-foreground transition-colors group-hover/act:text-primary" />
          </div>
          <span>Novo workspace</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
