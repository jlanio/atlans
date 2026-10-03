"use client"

import { useEffect, useState, useRef, useCallback, useMemo } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useSession } from "next-auth/react"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import {
  TbSearch, TbX, TbFolders, TbId, TbActivity, TbPackage,
  TbDatabaseImport, TbServer, TbLayoutDashboard, TbChevronRight,
  TbPlus, TbSettings, TbUsers, TbKey, TbSparkles,
} from "react-icons/tb"
import { NODE_ICONS } from "@/consts/WorkflowIcons"
import { cn } from "@/lib/utils"

interface CommandItem {
  id: string
  label: string
  description?: string
  icon: React.ElementType
  action: () => void
  group: string
  // Items for the system administrator only. Dashboard, Users and Settings
  // are admin routes: without this mark the palette offered them to everyone and
  // only the gate blocked — a path that ended in a redirect.
  //
  // TODAY the mark changes nothing: a non-admin only reaches the Home (`proxy.ts`
  // returns `/` on every other page), and on the Home the palette does not open
  // for them (`paletaDisponivel`) — they never see it. It stays for the day a
  // route is reopened to non-admins (the exception goes into `proxy.ts`): then
  // the palette opens for them again, and these three stay admin-only.
  admin?: boolean
}

export const STATIC_ITEMS = (router: ReturnType<typeof useRouter>): CommandItem[] => [
  { id: "dashboard",      label: "Dashboard",       icon: TbLayoutDashboard, group: "Navegar",    action: () => router.push("/dashboard"),      description: "Visão geral", admin: true },
  { id: "projects",       label: "Projetos",         icon: TbFolders,         group: "Navegar",    action: () => router.push("/projects"),       description: "Workflows" },
  { id: "observability",  label: "Histórico",         icon: TbActivity,        group: "Navegar",    action: () => router.push("/observability"),  description: "Execuções e métricas" },
  { id: "artifacts",      label: "Artefatos",        icon: TbPackage,         group: "Navegar",    action: () => router.push("/artifacts"),      description: "Outputs" },
  { id: "credentials",    label: "Credenciais",      icon: TbId,              group: "Navegar",    action: () => router.push("/credentials"),    description: "API keys" },
  { id: "tokens",         label: "Tokens de acesso", icon: TbKey,             group: "Navegar",    action: () => router.push("/settings/tokens"), description: "Agentes e integrações" },
  { id: "drive",          label: "Drive",            icon: TbDatabaseImport,  group: "Navegar",    action: () => router.push("/drive"),          description: "Arquivos" },
  { id: "executores",     label: "Executores",       icon: TbServer,           group: "Navegar",    action: () => router.push("/executores"),     description: "Máquinas de execução" },
  { id: "users",          label: "Usuários",         icon: TbUsers,           group: "Navegar",    action: () => router.push("/admin/users"),    description: "Gestão de contas", admin: true },
  { id: "settings",       label: "Configurações",    icon: TbSettings,        group: "Navegar",    action: () => router.push("/admin/settings"), description: "Admin", admin: true },
  { id: "new-workflow",   label: "Novo workflow",    icon: TbPlus,            group: "Ações",      action: () => router.push("/workflow/create"), description: "Criar" },
]

// Hides admin items from non-admins. Pure and exported for testing — the
// visibility rule depends on neither render nor session. No-op as long as
// non-admins have no palette (see the `admin` mark above).
export function itensVisiveis(itens: CommandItem[], isAdmin: boolean): CommandItem[] {
  return itens.filter(item => !item.admin || isAdmin)
}

/**
 * Does the palette open here? The Home (`/`) does not OFFER a way out to those
 * who do not administer the system — it is the owner's direction, which already
 * closed off the sidebar brand and the Schedules line.
 *
 * Why not open, instead of filtering item by item: TODAY **every** item here
 * leaves the Home. The eight static non-admin ones lead to other routes, and the
 * dynamic ones are one per workflow (`/workflow/{id}`) and one per credential
 * (`/credentials`) — these do not even go through `itensVisiveis`. Filtering
 * would leave an empty box, which is worse than not opening. As a bonus,
 * `loadItems` does not run: gone is the `getWorkflows()` that fired on every
 * Ctrl+K on the Home.
 *
 * This is NOT access control: what blocks is `proxy.ts`, which today returns
 * `/` to non-admins on EVERY page outside the Home. So, for now, a non-admin
 * never sees the palette — here it does not open, and outside here they do not
 * get. What this function decides is the OFFER, and it matters again when a
 * route is reopened to non-admins.
 *
 * EXACT equality with `"/"`, never `startsWith` — the precedent is
 * `shell-sidebar.tsx`, where a prefix would match every app route.
 */
export function paletaDisponivel(pathname: string | null | undefined, isAdmin: boolean): boolean {
  return pathname !== "/" || isAdmin
}

export default function CommandPalette() {
  const router = useRouter()
  const pathname = usePathname()
  const { data: session, status } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const [open, setOpen]     = useState(false)
  const [query, setQuery]   = useState("")
  const [items, setItems]   = useState<CommandItem[]>([])
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // Detects whether we are in the workflow editor (canvas)
  const isOnCanvas = pathname?.includes("/workflow/")
  const disponivel = paletaDisponivel(pathname, isAdmin)

  // Loads dynamic items on open
  const loadItems = useCallback(async () => {
    const staticItems = itensVisiveis(STATIC_ITEMS(router), isAdmin)
    if (status !== "authenticated") { setItems(staticItems); return }

    // Credentials and the node catalog come from workflowCatalogStore: they are
    // global to the user and stay in memory with a TTL. Before, every Ctrl+K
    // re-downloaded the whole catalog (~100 KB) and the credential list the
    // canvas next to it had just fetched. Only the workflow list is volatile
    // enough to be worth a GET per open.
    const catalogo = useWorkflowCatalogStore.getState()
    const [wfRes, credenciais, nosDoCatalogo] = await Promise.all([
      // Including the assistant's: the palette is the shortcut to open a workflow
      // by name, and not finding what the assistant created is the same as not having it.
      GisFlowService.getWorkflows(undefined, { incluirDoAssistente: true }),
      // The fetch may fail (network/session): the palette stays useful with the
      // static items, so each list falls back to empty instead of bringing down the rest.
      catalogo.ensureCredentials().catch(() => []),
      // Outside the canvas nodes do not become palette items — not worth downloading them.
      isOnCanvas ? catalogo.ensureNodesAPI().catch(() => []) : Promise.resolve([]),
    ])

    const wfItems: CommandItem[] = (wfRes?.data ?? []).map(wf => ({
      id: `wf-${wf.id_hash}`,
      label: wf.name,
      description: wf.description ?? undefined,
      // The spark instead of the folder distinguishes what the assistant created,
      // the same way as the badge in the lists — here there is no room for a badge.
      icon: wf.origem === "assistente" ? TbSparkles : TbFolders,
      group: "Workflows",
      action: () => router.push(`/workflow/${wf.id_hash}`),
    }))
    const credItems: CommandItem[] = credenciais.map(c => ({
      id: `cred-${c.id}`,
      label: c.name,
      description: c.type,
      icon: TbId,
      group: "Credenciais",
      action: () => router.push("/credentials"),
    }))

    // Workflow nodes — only appear on the canvas
    const nodeItems: CommandItem[] = isOnCanvas
      ? nosDoCatalogo.map(node => ({
          id: `node-${node.name}`,
          label: node.alias ?? node.name,
          description: node.description,
          icon: NODE_ICONS[node.name as string] ?? TbPlus,
          group: "Adicionar nó",
          action: () => {
            window.dispatchEvent(new CustomEvent("command-add-node", { detail: node }))
          },
        }))
      : []

    setItems([...staticItems, ...(isOnCanvas ? nodeItems : []), ...wfItems, ...credItems])
  }, [router, status, isOnCanvas, isAdmin])

  // Global Ctrl+K shortcut. `disponivel` is a dependency on purpose: it flips at
  // most once per session (when `useSession` resolves), so re-registering the
  // listener then is irrelevant next to what this file avoids on every KEYSTROKE
  // (the `filtered`/`selected` refs, below).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        // The `preventDefault` stays: without it the browser's Ctrl+K steals focus
        // to the address bar, which on the Home would be an odd reward for a
        // shortcut that does nothing.
        e.preventDefault()
        if (!disponivel) return
        setOpen(v => !v)
      }
      // Closing never depends on anything: a stuck Esc is worse than any rule.
      if (e.key === "Escape") setOpen(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [disponivel])

  // Opened on another route and the person navigated to the Home (an item's
  // `router.push`, or any client-side navigation): it closes. Without this, the
  // palette could survive the arrival on the Home.
  useEffect(() => {
    if (!disponivel) setOpen(false)
  }, [disponivel])

  useEffect(() => {
    if (open) {
      setQuery("")
      setSelected(0)
      loadItems()
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open, loadItems])

  // Memoized: without it filtered would be a new array on every render and, as a
  // dep of the keyboard effect below, would force remove/addEventListener on every keystroke.
  const filtered = useMemo(() => items.filter(item => {
    if (!query) return true
    const q = query.toLowerCase()
    return item.label.toLowerCase().includes(q) || item.description?.toLowerCase().includes(q) || item.group.toLowerCase().includes(q)
  }), [items, query])

  // Refs so the keyboard handler reads filtered/selected without becoming a
  // dependency of the effect — the listener registers once per open, not every render.
  const filteredRef = useRef(filtered)
  const selectedRef = useRef(selected)
  filteredRef.current = filtered
  selectedRef.current = selected

  // Keyboard navigation
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowDown") { e.preventDefault(); setSelected(s => Math.min(s + 1, filteredRef.current.length - 1)) }
      if (e.key === "ArrowUp")   { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)) }
      if (e.key === "Enter" && filteredRef.current[selectedRef.current]) {
        filteredRef.current[selectedRef.current].action()
        setOpen(false)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open])

  // groups and each item's global index derive from filtered in a single pass:
  // push (not spread) avoids the reduce's O(n²), and the Map replaces
  // filtered.indexOf (O(n²) in render) with an O(1) lookup per item.
  const { groups, indexOf } = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {}
    const indexOf = new Map<CommandItem, number>()
    filtered.forEach((item, i) => {
      const arr = groups[item.group] ??= []
      arr.push(item)
      indexOf.set(item, i)
    })
    return { groups, indexOf }
  }, [filtered])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-start justify-center pt-[15vh] bg-black/40 backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg bg-popover border border-border rounded-lg shadow-lg overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Search field */}
        <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border">
          <TbSearch size={16} className="text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0) }}
            placeholder="Buscar workflows, credenciais, páginas…"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          {query && (
            <button onClick={() => setQuery("")} className="text-muted-foreground hover:text-foreground">
              <TbX size={14} />
            </button>
          )}
          <span className="text-[10px] text-muted-foreground border border-border rounded px-1.5 py-0.5">Esc</span>
        </div>

        {/* Results — listbox semantics: the container is the list, each item is
            an option with `aria-selected`, and the groups become `role="group"` so
            the screen reader announces the band ("Navegar", "Workflows"…). */}
        <div className="max-h-80 overflow-y-auto py-1.5" role="listbox" aria-label="Resultados da busca">
          {filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">Nenhum resultado para «{query}»</p>
          ) : (
            Object.entries(groups).map(([group, groupItems]) => {
              return (
                <div key={group} role="group" aria-label={group}>
                  <p aria-hidden="true" className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium px-3 py-1.5 select-none">
                    {group}
                  </p>
                  {groupItems.map(item => {
                    // Global index via an O(1) Map (it used to be filtered.indexOf, O(n²))
                    const globalIdx = indexOf.get(item)!
                    return (
                      <button
                        key={item.id}
                        role="option"
                        aria-selected={globalIdx === selected}
                        aria-label={item.description ? `${item.label} — ${item.description}` : item.label}
                        onMouseEnter={() => setSelected(globalIdx)}
                        onClick={() => { item.action(); setOpen(false) }}
                        className={cn(
                          // Motion under motion-safe: and a ≥40px target on the phone; visible
                          // focus with the contract's standard ring.
                          "w-full flex items-center gap-3 px-3 py-2 text-left outline-none motion-safe:transition-colors max-md:min-h-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                          globalIdx === selected ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
                        )}
                      >
                        <item.icon size={15} className="text-muted-foreground shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate">{item.label}</p>
                          {item.description && (
                            <p className="text-xs text-muted-foreground truncate">{item.description}</p>
                          )}
                        </div>
                        {globalIdx === selected && <TbChevronRight size={13} className="text-muted-foreground shrink-0" />}
                      </button>
                    )
                  })}
                </div>
              )
            })
          )}
        </div>

        {/* Footer with hint */}
        <div className="border-t border-border px-3 py-1.5 flex gap-3 text-[10px] text-muted-foreground">
          <span>↑↓ navegar</span>
          <span>↵ selecionar</span>
          <span>Esc fechar</span>
        </div>
      </div>
    </div>
  )
}
