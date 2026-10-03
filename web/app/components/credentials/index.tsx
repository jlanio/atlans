"use client"
import { GisFlowService } from "@/service/GisFlowService"
import { useEffect, useMemo, useState } from "react"
import { useSession } from "next-auth/react"
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select"
import { EntityCard } from "@/app/components/shared/EntityCard"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "../ui/dropdown-menu"
import { Dialog, DialogTrigger } from "../ui/dialog"
import { TbDotsVertical, TbSettings, TbTrash, TbLink, TbAlertTriangle, TbClock, TbPlus, TbRefresh, TbSearch, TbCopy, TbUser, TbUsers, TbHistory, TbLayoutGrid } from "react-icons/tb"
import PageRoot from "../page-root"
import { fromBackend, fromNowLocal } from "@/lib/dayjs"
import { useCredentialsContext } from "@/context/useCredentialsContext"
import DeleteCredential from "./dialog-content/delete-credential"
import ConfigureCredential from "./dialog-content/configure-credential"
import CreateCredential from "./dialog-content/create-credential"
import { useWorkspace } from "@/context/WorkspaceContext"
import { Skeleton } from "../ui/skeleton"
import { getCredentialTypeStyle } from "@/consts/CredentialTypeStyles"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import { formatInteger, plural } from "@/lib/formatos"
import { useFetchData } from "@/app/hooks/useFetchData"
import { ErroDeCarga, SemResultado, CredentialsSkeleton, VazioPrimeiroUso } from "./estados"
import type { ICredentials, ICredentialTypeSchema } from "@/service/types"

type SortKey = "name" | "recent" | "used"

// Duplication seed: values to prefill the create modal. `_key` only
// exists to force CreateCredential to remount (defaultValues are read
// once).
interface DuplicateSeed {
  _key: string
  name: string
  type: string
  data: Record<string, string>
  description?: string
  tags?: string[]
}

const CredentialsActions = () => {

  const { data: session, status } = useSession()
  const myId = session?.user?.id_hash ?? null
  const { current: currentWorkspace } = useWorkspace()
  const { credentials, setCredentialsContext } = useCredentialsContext()
  const [deleteCredentialId, setDeleteCredentialId] = useState<string>();
  const [configureCredentialId, setConfigureCredentialId] = useState<string>();
  const [createModalState, setCreateModalState] = useState(false);
  const [duplicateSeed, setDuplicateSeed] = useState<DuplicateSeed>();
  // Loading the list is `useFetchData`'s job: `loading` (its `firstLoad`) covers
  // only the FIRST load (skeleton); `refreshing` is the reload, with the list on
  // screen — before, reloading also turned into a skeleton and the layout
  // jumped. The session gate and the guard against stale responses are its too.
  //
  // Without the error branch, a network failure fell into the "Nenhuma
  // credencial cadastrada" (no credentials registered) empty state — the screen
  // lied. The error card only applies with no accepted load
  // (`atualizadoEm == null`); a reload that fails over a ready list keeps what
  // was there and warns via toast (contract §3.2).
  //
  // The list lives in the context, which the create/edit/delete dialogs also
  // write: each accepted response goes there in the same tick (`onDados`).
  const { firstLoad: loading, refreshing, error, atualizadoEm, refetch } = useFetchData(
    () => GisFlowService.getCredentials(),
    "Não foi possível carregar as credenciais.",
    [], 0,
    {
      onDados: lista => setCredentialsContext(prev => ({ ...prev, credentials: lista })),
      onErroComDados: () => createToast.error("Não foi possível atualizar as credenciais"),
    },
  )
  const loadError = error != null && atualizadoEm == null
  const [usageMap, setUsageMap] = useState<Record<string, number>>({})
  const [credentialTypes, setCredentialTypes] = useState<ICredentialTypeSchema[]>([])

  // ── listing controls (U1/U7) ───────────────────────────────────────────────
  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState<string>("__all__")
  const [sortBy, setSortBy] = useState<SortKey>("name")
  const [grouped, setGrouped] = useState(true)

  // Creating is a personal action (owner-only by nature); any authenticated
  // session can. The "peça a um editor" (ask an editor) fallback exists by contract.
  const canEdit = status !== "unauthenticated"

  const handleCloseModal = () => {
    setDeleteCredentialId(undefined);
    setConfigureCredentialId(undefined);
    if (currentWorkspace?.id_hash) computeUsage();
  };

  useEffect(() => {
    if (status === "authenticated") getTypes()
  }, [status])

  useEffect(() => {
    if (status === "authenticated" && currentWorkspace?.id_hash) {
      computeUsage()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, currentWorkspace?.id_hash])

  async function getTypes() {
    // The listing needs the catalog only to translate the type slug
    // ("http_bearer") into the human label ("HTTP Bearer Token"). Failing here is
    // no reason to break the screen: without the catalog, the slug comes back as fallback.
    const res = await GisFlowService.getCredentialTypes()
    setCredentialTypes(res.data ?? [])
  }

  function handleRefresh() {
    refetch()
    getTypes()
    if (currentWorkspace?.id_hash) computeUsage()
  }

  // type→label index built once: getTypeLabel runs on the hot path of
  // filtering/sorting (per credential, per keystroke). Without the Map each call
  // did an O(N) find over the catalog — O(N×M) per render. `?? []` covers a
  // catalog not loaded yet.
  const typeLabel = useMemo(
    () => new Map((credentialTypes ?? []).map(t => [t.type, t.label])),
    [credentialTypes],
  )

  function getTypeLabel(credType: string) {
    return typeLabel.get(credType) ?? credType
  }

  async function computeUsage() {
    const res = await GisFlowService.getCredentialsUsage(currentWorkspace?.id_hash)
    if (!res.data) return
    const map: Record<string, number> = {}
    for (const [credId, info] of Object.entries(res.data)) {
      map[credId] = info.node_count
    }
    setUsageMap(map)
  }

  // ── duplicate (U6) ──────────────────────────────────────────────────────────
  // Only the owner duplicates: it needs the decrypted secrets (GET /{id}/data is
  // owner-only). Opens the create modal prefilled, without inheriting sharing.
  async function handleDuplicate(cred: ICredentials) {
    const res = await GisFlowService.getCredentialData(cred.id)
    if (res?.error || !res.data) {
      return createToast.error("Não foi possível duplicar", res?.error?.message)
    }
    setDuplicateSeed({
      _key: `${cred.id}-${Date.now()}`,
      name: `Cópia de ${cred.name}`,
      type: res.data.type,
      data: res.data.data ?? {},
      description: res.data.description ?? undefined,
      tags: res.data.tags ?? undefined,
    })
    setCreateModalState(true)
  }

  function ownership(cred: ICredentials) {
    const isMine = !!cred.owner_id && cred.owner_id === myId
    const isShared = !!cred.workspace_id
    return { isMine, isShared, sharedWithMe: isShared && !isMine }
  }

  function getExpiryBadge(expiresAt?: string | null) {
    if (!expiresAt) return null
    const exp = fromBackend(expiresAt)
    if (!exp) return null
    const diffDays = Math.ceil((exp.valueOf() - Date.now()) / 86_400_000)
    // shrink-0 + whitespace-nowrap: without it "Expira em 12d" (expires in 12d)
    // broke into two lines on a narrow screen and stretched the card. Canonical
    // status pairs (contract §6): expired = red (failure), expiring = amber (warning).
    if (diffDays <= 0) return (
      <span className="flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium tabular-nums bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400">
        <TbAlertTriangle className="size-3" aria-hidden="true" />
        Expirada
      </span>
    )
    if (diffDays <= 7) return (
      <span className="flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium tabular-nums bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400">
        <TbClock className="size-3" aria-hidden="true" />
        Expira em {diffDays}d
      </span>
    )
    return null
  }

  function getUsageBadge(credId: string) {
    // Only renders when there is usage: before, every row carried a gray "0 nós",
    // which in a freshly created list was noise on every row at once.
    const count = usageMap[credId] ?? 0
    if (count === 0) return null
    return (
      <span
        className="flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-xs font-medium tabular-nums text-primary"
        title={`Usada em ${plural(count, "nó", "nós")} de workflow`}
      >
        <TbLink className="size-3" aria-hidden="true" />
        {plural(count, "nó", "nós")}
      </span>
    )
  }

  function getLastUsedBadge(lastUsed?: string | null) {
    if (!lastUsed) return null
    return (
      <span
        className="hidden shrink-0 items-center gap-1 whitespace-nowrap rounded-full border border-transparent bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground sm:flex"
        title={`Última utilização: ${fromNowLocal(lastUsed)}`}
      >
        <TbHistory className="size-3" aria-hidden="true" />
        {fromNowLocal(lastUsed)}
      </span>
    )
  }

  function getSharedBadge(cred: ICredentials) {
    const { isMine, isShared, sharedWithMe } = ownership(cred)
    if (!isShared) return null
    // Blue (sharing/in circulation) instead of the old indigo, which is not
    // one of the canonical status tones of contract §6.
    return (
      <span
        className="flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400"
        title={sharedWithMe ? "Compartilhada com você por outro membro" : "Compartilhada com o workspace"}
      >
        <TbUsers className="size-3" aria-hidden="true" />
        {isMine ? "Compartilhada" : "Compartilhada comigo"}
      </span>
    )
  }

  // Memoizado: derivava a cada render varrendo credentials × usageMap.
  const usedCount = useMemo(
    () => credentials?.filter(c => (usageMap[c.id] ?? 0) > 0).length ?? 0,
    [credentials, usageMap],
  )

  // Types present in the list, for the filter (only the ones that exist — not the whole catalog).
  const typesPresent = useMemo(() => {
    const set = new Set((credentials ?? []).map(c => c.type))
    return Array.from(set).sort((a, b) => getTypeLabel(a).localeCompare(getTypeLabel(b)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [credentials, credentialTypes])

  // Filter + sort. `visible` is the already-sifted list; the split by
  // ownership (mine × shared) and the grouping by type happen at
  // render — see `renderCredList`.
  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    let list = (credentials ?? []).filter(c => {
      if (typeFilter !== "__all__" && c.type !== typeFilter) return false
      if (!q) return true
      const haystack = [
        c.name,
        getTypeLabel(c.type),
        c.description ?? "",
        ...(c.tags ?? []),
      ].join(" ").toLowerCase()
      return haystack.includes(q)
    })
    list = [...list].sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name)
      if (sortBy === "recent") return (b.created_at ?? "").localeCompare(a.created_at ?? "")
      // "used": most recently used first; never-used at the end.
      const av = a.last_used_at ?? "", bv = b.last_used_at ?? ""
      if (av && bv) return bv.localeCompare(av)
      if (av) return -1
      if (bv) return 1
      return a.name.localeCompare(b.name)
    })
    return list
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [credentials, search, typeFilter, sortBy, credentialTypes])

  // Groups a list by type (used inside each section when "Agrupar por
  // tipo" (group by type) is on). It is no longer a useMemo over the whole
  // `visible`: grouping now runs PER ownership section — see renderCredList.
  function groupByType(list: ICredentials[]) {
    const map = new Map<string, ICredentials[]>()
    for (const c of list) {
      const arr = map.get(c.type) ?? []
      arr.push(c)
      map.set(c.type, arr)
    }
    return Array.from(map.entries()).sort((a, b) => getTypeLabel(a[0]).localeCompare(getTypeLabel(b[0])))
  }

  // Primary split by OWNERSHIP: my credentials and those shared with me
  // stop mixing visually (the badge alone was not enough). It only becomes
  // two sections when there is actually a mix; otherwise, a single list.
  // Memoized: the two sweeps of `visible` ran on every render; they only change
  // when the visible list or the identity (myId, via ownership) changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const minhas = useMemo(() => visible.filter(c => ownership(c).isMine), [visible, myId])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const compartilhadas = useMemo(() => visible.filter(c => !ownership(c).isMine), [visible, myId])
  const isMixed = useMemo(() => minhas.length > 0 && compartilhadas.length > 0, [minhas, compartilhadas])

  // Pre-groups each section by type once (keyed by scope), instead of
  // regrouping inside renderCredList on every render. Only changes when the lists
  // or the labels (typeLabel) change; with "Agrupar por tipo" off nobody reads it.
  // `agruparPorTipo` is recreated on every render (it closes over typeLabel,
  // which is already in the deps); including it would void the memo.
  const groupsByScope = useMemo<Record<string, [string, ICredentials[]][]>>(() => ({
    mine: groupByType(minhas),
    shared: groupByType(compartilhadas),
    all: groupByType(visible),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [minhas, compartilhadas, visible, typeLabel])

  const hasCreds = !!credentials && credentials.length > 0
  const comFiltro = typeFilter !== "__all__"

  function clearFilters() {
    setSearch("")
    setTypeFilter("__all__")
  }

  // Header subtitle: counts the scope ("N credenciais · N em uso"). Zero
  // disappears (contract §7) — "0 em uso" in a freshly created list helps no one.
  function textoDoSubtitulo(): string {
    const partes = [plural(credentials!.length, "credencial", "credenciais")]
    if (usedCount > 0) partes.push(`${formatInteger(usedCount)} em uso`)
    return partes.join(" · ")
  }

  function renderCard(credential: ICredentials) {
    const style = getCredentialTypeStyle(credential.type)
    const TypeIcon = style.icon
    const { isMine } = ownership(credential)
    return (
      <li key={credential.id}>
        <EntityCard
          title={credential.name}
          description={credential.description || getTypeLabel(credential.type)}
          badge={getSharedBadge(credential)}
          onClick={() => isMine && setConfigureCredentialId(credential.id)}
          leading={
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-md ${style.bg}`}
              title={getTypeLabel(credential.type)}
            >
              <TypeIcon className={`size-4 ${style.fg}`} aria-hidden="true" />
            </span>
          }
          actions={
            <>
              {getExpiryBadge(credential.expires_at)}
              {getUsageBadge(credential.id)}
              {getLastUsedBadge(credential.last_used_at)}
              {/* Destructive/edit actions are owner-only: someone who only received the
                  shared credential cannot load the secrets, nor would the
                  backend let them edit/delete. We hide them instead of letting
                  the click fail with 403. */}
              {isMine && (
                <DropdownMenu>
                  <DropdownMenuTrigger
                    aria-label={`Ações da credencial ${credential.name}`}
                    className="flex size-7 items-center justify-center rounded-full outline-none hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:size-10"
                  >
                    <TbDotsVertical aria-hidden="true" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => setConfigureCredentialId(credential.id)}>
                      <TbSettings className="text-muted-foreground" />
                      <p>Editar</p>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleDuplicate(credential)}>
                      <TbCopy className="text-muted-foreground" />
                      <p>Duplicar</p>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setDeleteCredentialId(credential.id)}>
                      <TbTrash className="text-muted-foreground" />
                      <p>Excluir</p>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </>
          }
        />
      </li>
    )
  }

  // Renders a set of credentials: flat, or sub-grouped by type when
  // "Agrupar por tipo" is on. `scope` prefixes the keys so they don't collide
  // between the "minhas" (mine) and "compartilhadas" (shared) sections.
  function renderCredList(creds: ICredentials[], scope: string, aninhado: boolean) {
    if (grouped) {
      return (
        <div className="flex flex-col gap-4">
          {/* Groups already precomputed per scope (see groupsByScope). */}
          {groupsByScope[scope].map(([type, cs]) => {
            const style = getCredentialTypeStyle(type)
            const TypeIcon = style.icon
            // Level of the type heading: h3 when nested under an ownership
            // section (the "Minhas"/"Compartilhadas" h2); h2 when the list is
            // flat, so the heading chain doesn't jump from h1 straight to h3
            // (a regression for screen readers).
            const TypeHeading = aninhado ? "h3" : "h2"
            return (
              <div key={`${scope}-${type}`} className="flex flex-col gap-2">
                <div className="flex items-center gap-2 px-1">
                  <TypeIcon className={`size-3.5 ${style.fg}`} aria-hidden="true" />
                  <TypeHeading className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {getTypeLabel(type)}
                  </TypeHeading>
                  <span className="text-[11px] tabular-nums text-muted-foreground/60">{formatInteger(cs.length)}</span>
                </div>
                <ul className="flex flex-col gap-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300">
                  {cs.map(renderCard)}
                </ul>
              </div>
            )
          })}
        </div>
      )
    }
    return (
      <ul className="flex flex-col gap-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300">
        {creds.map(renderCard)}
      </ul>
    )
  }

  return (
    <PageRoot>
      {/* Fixed header of contract §1: title + scope subtitle on the left,
          actions on the right (Atualizar as ghost and Criar as the only primary).
          On phones the secondary goes into the ⋯ menu and the primary fills the row. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-foreground">Credenciais</h1>
          {/* Stable live region: the `aria-live` sits on the container (not on the <p>),
              which survives the Skeleton↔text swap, so the screen reader announces
              the count when it changes (e.g. after Atualizar). */}
          <div aria-live="polite" aria-atomic="true">
            {loading ? (
              <Skeleton className="mt-1 h-4 w-64" />
            ) : (
              <p className="text-sm font-medium tabular-nums text-muted-foreground">
                {hasCreds
                  ? textoDoSubtitulo()
                  : "Conexões privadas — bancos, APIs e serviços — reutilizáveis nos seus workflows"}
              </p>
            )}
          </div>
        </div>

        <Dialog
          open={createModalState}
          onOpenChange={open => { setCreateModalState(open); if (!open) setDuplicateSeed(undefined) }}
        >
          <div className="flex w-full items-center gap-2 select-none sm:w-auto">
            {/* Desktop: Atualizar. */}
            <div className="hidden items-center gap-2 md:flex">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={loading || refreshing}
                aria-label="Atualizar a lista de credenciais"
                className="gap-1.5"
              >
                <TbRefresh size={14} className={refreshing ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
                Atualizar
              </Button>
            </div>

            {/* Phone: ⋯ menu with the secondary action that left the row. */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" aria-label="Mais ações" className="size-10 shrink-0 md:hidden">
                  <TbDotsVertical size={16} aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled={loading || refreshing} onClick={handleRefresh}>
                  <TbRefresh className={refreshing ? "motion-safe:animate-spin" : undefined} /> Atualizar
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <DialogTrigger asChild>
              <Button onClick={() => setDuplicateSeed(undefined)} size="sm" className="flex-1 max-md:h-10 md:flex-none">
                <TbPlus size={15} aria-hidden="true" />
                Criar credencial
              </Button>
            </DialogTrigger>
          </div>
          <CreateCredential
            key={duplicateSeed?._key ?? "new"}
            initialValues={duplicateSeed}
            setCreateModalState={setCreateModalState}
          />
        </Dialog>
      </div>

      {/* Search/filter/sort bar — only when there is something to filter (U1/U7). */}
      {!loading && !loadError && hasCreds && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[12rem] flex-1">
            <TbSearch className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por nome, tipo, descrição ou tag"
              aria-label="Buscar credenciais"
              className="pl-8 max-md:h-10"
            />
          </div>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-auto min-w-[9rem] max-md:h-10" aria-label="Filtrar por tipo">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Todos os tipos</SelectItem>
              {typesPresent.map(t => (
                <SelectItem key={t} value={t}>{getTypeLabel(t)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={v => setSortBy(v as SortKey)}>
            <SelectTrigger className="w-auto min-w-[9rem] max-md:h-10" aria-label="Ordenar credenciais">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Nome (A–Z)</SelectItem>
              <SelectItem value="recent">Mais recentes</SelectItem>
              <SelectItem value="used">Uso recente</SelectItem>
            </SelectContent>
          </Select>
          {/* Canonical toggle of contract §1: group with aria-pressed, active in
              bg-accent, inactive in muted. */}
          <div
            role="group"
            aria-label="Agrupamento"
            className="inline-flex h-9 overflow-hidden rounded-md border bg-card max-md:h-10"
          >
            <button
              type="button"
              aria-pressed={grouped}
              onClick={() => setGrouped(g => !g)}
              className={cn(
                "flex items-center gap-1.5 px-3 text-xs font-medium outline-none transition-colors",
                "focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                grouped ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
              )}
            >
              <TbLayoutGrid size={14} aria-hidden="true" />
              Agrupar por tipo
            </button>
          </div>
        </div>
      )}

      {/* Precedence of contract §3: loading → error (only on the 1st load) →
          first use → content (with no-results inside). */}
      {loading ? (
        <CredentialsSkeleton />
      ) : loadError && atualizadoEm == null ? (
        <ErroDeCarga onTentar={handleRefresh} />
      ) : !hasCreds ? (
        <VazioPrimeiroUso canEdit={canEdit} onCriar={() => { setDuplicateSeed(undefined); setCreateModalState(true) }} />
      ) : visible.length === 0 ? (
        <SemResultado q={search} comFiltro={comFiltro} onLimpar={clearFilters} />
      ) : (
        // List — split by OWNERSHIP (mine × shared with me) when there is a
        // mix; each section honors "Agrupar por tipo". With no mix, it
        // falls back to a single list (no redundant header).
        <div className={cn("flex flex-col gap-6 transition-opacity", refreshing && "opacity-60")}>
          {isMixed ? (
            <>
              <section aria-labelledby="cred-minhas-titulo" className="flex flex-col gap-2.5">
                <div className="flex items-center gap-2 border-b border-border/60 pb-1.5">
                  <TbUser className="size-4 text-muted-foreground" aria-hidden="true" />
                  <h2 id="cred-minhas-titulo" className="text-sm font-semibold text-foreground">Minhas credenciais</h2>
                  <span className="text-xs tabular-nums text-muted-foreground/70">{formatInteger(minhas.length)}</span>
                </div>
                {renderCredList(minhas, "mine", true)}
              </section>
              <section aria-labelledby="cred-compartilhadas-titulo" className="flex flex-col gap-2.5">
                <div className="flex items-center gap-2 border-b border-border/60 pb-1.5">
                  <TbUsers className="size-4 text-muted-foreground" aria-hidden="true" />
                  <h2 id="cred-compartilhadas-titulo" className="text-sm font-semibold text-foreground">Compartilhadas comigo</h2>
                  <span className="text-xs tabular-nums text-muted-foreground/70">{formatInteger(compartilhadas.length)}</span>
                </div>
                {renderCredList(compartilhadas, "shared", true)}
              </section>
            </>
          ) : (
            renderCredList(visible, "all", false)
          )}
        </div>
      )}

      <Dialog
        open={!!deleteCredentialId || !!configureCredentialId}
        onOpenChange={handleCloseModal}
      >
        {deleteCredentialId &&
          <DeleteCredential
            deleteCredentialId={deleteCredentialId}
            setDeleteCredentialId={setDeleteCredentialId}
            usageCount={usageMap[deleteCredentialId] ?? 0} />
        }
        {configureCredentialId &&
          <ConfigureCredential
            configureCredentialId={configureCredentialId}
            setConfigureCredentialId={setConfigureCredentialId} />
        }
      </Dialog>

    </PageRoot>
  )

}

export default CredentialsActions
