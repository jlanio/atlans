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
  // Itens só do administrador do sistema. Dashboard, Usuários e Configurações
  // são rotas de admin: sem esta marca a paleta os oferecia a todos e só o
  // portão barrava — um caminho que terminava em redirect.
  //
  // HOJE a marca não muda nada: quem não é admin só alcança a Home (`proxy.ts`
  // devolve `/` em toda outra página), e na Home a paleta não abre para ele
  // (`paletaDisponivel`) — ele nunca a vê. Ela fica para o dia em que uma rota
  // for reaberta a quem não é admin (a exceção entra em `proxy.ts`): aí a
  // paleta volta a abrir para ele, e estes três continuam só do admin.
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

// Esconde os itens de admin de quem não é admin. Puro e exportado para teste — a
// regra de visibilidade não depende de render nem de sessão. No-op enquanto
// quem não é admin não tiver paleta (ver a marca `admin` acima).
export function itensVisiveis(itens: CommandItem[], isAdmin: boolean): CommandItem[] {
  return itens.filter(item => !item.admin || isAdmin)
}

/**
 * A paleta abre aqui? A Home (`/`) não OFERECE saída a quem não administra o
 * sistema — é a direção do dono, que já fechou a marca do sidebar e a linha de
 * Agendamentos.
 *
 * Por que não abrir, em vez de filtrar item a item: HOJE **todo** item daqui sai
 * da Home. Os oito estáticos não-admin levam a outras rotas, e os dinâmicos são
 * um por fluxo (`/workflow/{id}`) e um por credencial (`/credentials`) — estes
 * nem passam pela `itensVisiveis`. Filtrar deixaria uma caixa vazia, que é pior
 * do que não abrir. De brinde, o `loadItems` não roda: some o `getWorkflows()`
 * que disparava a cada Ctrl+K na Home.
 *
 * Isto NÃO é controle de acesso: quem barra é o `proxy.ts`, que hoje devolve
 * `/` a quem não é admin em TODA página fora da Home. Então, por enquanto,
 * quem não é admin nunca vê a paleta — aqui ela não abre, e fora daqui ele não
 * chega. O que esta função decide é a OFERTA, e ela volta a importar quando
 * uma rota for reaberta a quem não é admin.
 *
 * Igualdade EXATA com `"/"`, nunca `startsWith` — o precedente é o
 * `shell-sidebar.tsx`, onde um prefixo casaria todas as rotas do app.
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

  // Detecta se estamos no editor de workflow (canvas)
  const isOnCanvas = pathname?.includes("/workflow/")
  const disponivel = paletaDisponivel(pathname, isAdmin)

  // Carrega itens dinâmicos ao abrir
  const loadItems = useCallback(async () => {
    const staticItems = itensVisiveis(STATIC_ITEMS(router), isAdmin)
    if (status !== "authenticated") { setItems(staticItems); return }

    // Credenciais e catálogo de nós vêm da workflowCatalogStore: são globais do
    // usuário e ficam em memória com TTL. Antes, cada Ctrl+K rebaixava o
    // catálogo inteiro (~100 KB) e a lista de credenciais que o canvas ao lado
    // acabara de buscar. Só a lista de workflows é volátil o bastante para
    // valer um GET por abertura.
    const catalogo = useWorkflowCatalogStore.getState()
    const [wfRes, credenciais, nosDoCatalogo] = await Promise.all([
      // Com os do assistente: a paleta é o atalho para abrir um fluxo pelo
      // nome, e não achar o que o assistente criou é o mesmo que não o ter.
      GisFlowService.getWorkflows(undefined, { incluirDoAssistente: true }),
      // A busca pode falhar (rede/sessão): a paleta segue útil com os itens
      // estáticos, então cada lista cai para vazia em vez de derrubar o resto.
      catalogo.ensureCredentials().catch(() => []),
      // Fora do canvas os nós não viram item da paleta — não vale baixá-los.
      isOnCanvas ? catalogo.ensureNodesAPI().catch(() => []) : Promise.resolve([]),
    ])

    const wfItems: CommandItem[] = (wfRes?.data ?? []).map(wf => ({
      id: `wf-${wf.id_hash}`,
      label: wf.name,
      description: wf.description ?? undefined,
      // A faísca no lugar da pasta distingue o que o assistente criou, do
      // mesmo jeito que o selo nas listas — aqui não há espaço para um selo.
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

    // Nós do workflow — só aparece no canvas
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

  // Atalho global Ctrl+K. `disponivel` é dependência de propósito: ele vira no
  // máximo uma vez por sessão (quando o `useSession` resolve), então re-registrar
  // o listener aí é irrelevante perto do que este arquivo evita a cada TECLA
  // (os refs de `filtered`/`selected`, abaixo).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        // O `preventDefault` fica: sem ele o Ctrl+K do navegador rouba o foco
        // para a barra de endereço, o que na Home seria um prêmio esquisito por
        // um atalho que não faz nada.
        e.preventDefault()
        if (!disponivel) return
        setOpen(v => !v)
      }
      // Fechar nunca depende de nada: um Esc preso é pior que qualquer regra.
      if (e.key === "Escape") setOpen(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [disponivel])

  // Aberta em outra rota e a pessoa navegou para a Home (o `router.push` de um
  // item, ou qualquer navegação client-side): fecha. Sem isto, a paleta podia
  // sobreviver à chegada na Home.
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

  // Memoizado: sem isso filtered seria um array novo a cada render e, como dep
  // do effect de teclado abaixo, forçaria remove/addEventListener a cada tecla.
  const filtered = useMemo(() => items.filter(item => {
    if (!query) return true
    const q = query.toLowerCase()
    return item.label.toLowerCase().includes(q) || item.description?.toLowerCase().includes(q) || item.group.toLowerCase().includes(q)
  }), [items, query])

  // Refs para o handler de teclado ler filtered/selected sem virar dependência
  // do effect — o listener registra uma vez por abertura, não a cada render.
  const filteredRef = useRef(filtered)
  const selectedRef = useRef(selected)
  filteredRef.current = filtered
  selectedRef.current = selected

  // Navegação com teclado
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

  // groups e o índice global de cada item derivam de filtered num único passe:
  // push (não spread) evita o O(n²) do reduce, e o Map troca o filtered.indexOf
  // (O(n²) no render) por consulta O(1) por item.
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
        {/* Campo de busca */}
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

        {/* Resultados — semântica de listbox: o contêiner é a lista, cada item é
            uma opção com `aria-selected`, e os grupos viram `role="group"` para
            o leitor de tela anunciar a faixa ("Navegar", "Workflows"…). */}
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
                    // Índice global via Map O(1) (antes era filtered.indexOf, O(n²))
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
                          // Movimento sob motion-safe: e alvo ≥40px no telefone; foco
                          // visível com o ring padrão do contrato.
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

        {/* Rodapé com dica */}
        <div className="border-t border-border px-3 py-1.5 flex gap-3 text-[10px] text-muted-foreground">
          <span>↑↓ navegar</span>
          <span>↵ selecionar</span>
          <span>Esc fechar</span>
        </div>
      </div>
    </div>
  )
}
