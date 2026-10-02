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
import { formatarInteiro, plural } from "@/lib/formatos"
import { useFetchData } from "@/app/hooks/useFetchData"
import { ErroDeCarga, SemResultado, SkeletonDeCredenciais, VazioPrimeiroUso } from "./estados"
import type { ICredentials, ICredentialTypeSchema } from "@/service/types"

type SortKey = "name" | "recent" | "used"

// Semente de duplicação: valores para pré-preencher o modal de criar. `_key`
// só existe para forçar remontagem do CreateCredential (defaultValues são lidos
// uma vez).
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
  // A carga da lista é o `useFetchData`: `loading` (o `firstLoad` dele) cobre
  // só a PRIMEIRA carga (skeleton); `refreshing` é o recarregar, com a lista na
  // tela — antes o recarregar também virava skeleton e o layout saltava. O gate
  // de sessão e a guarda contra resposta velha também são dele.
  //
  // Sem o ramo de erro, falha de rede caía no estado vazio "Nenhuma credencial
  // cadastrada" — a tela mentia. O cartão de erro só vale sem carga aceita
  // (`atualizadoEm == null`); recarga que falha sobre lista pronta mantém o
  // que havia e avisa por toast (contrato §3.2).
  //
  // A lista mora no contexto, que os diálogos de criar/editar/excluir também
  // escrevem: cada resposta aceita vai para lá no mesmo tique (`onDados`).
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

  // ── controles de listagem (U1/U7) ──────────────────────────────────────────
  const [search, setSearch] = useState("")
  const [typeFilter, setTypeFilter] = useState<string>("__all__")
  const [sortBy, setSortBy] = useState<SortKey>("name")
  const [grouped, setGrouped] = useState(true)

  // Criar é uma ação pessoal (owner-only por natureza); qualquer sessão
  // autenticada pode. O fallback "peça a um editor" existe por contrato.
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
    // A listagem precisa do catálogo só para traduzir o slug do tipo
    // ("http_bearer") no label humano ("HTTP Bearer Token"). Falhar aqui não é
    // motivo para quebrar a tela: sem catálogo, o slug volta como fallback.
    const res = await GisFlowService.getCredentialTypes()
    setCredentialTypes(res.data ?? [])
  }

  function handleRefresh() {
    refetch()
    getTypes()
    if (currentWorkspace?.id_hash) computeUsage()
  }

  // Índice tipo→label montado uma vez: getTypeLabel roda no caminho quente do
  // filtro/ordenação (por credencial, por tecla). Sem o Map cada chamada fazia
  // um find O(N) sobre o catálogo — O(N×M) por render. `?? []` cobre catálogo
  // ainda não carregado.
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

  // ── duplicar (U6) ───────────────────────────────────────────────────────────
  // Só o dono duplica: precisa dos segredos descriptografados (GET /{id}/data é
  // owner-only). Abre o modal de criar pré-preenchido, sem herdar compartilhamento.
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
    // shrink-0 + whitespace-nowrap: sem isso "Expira em 12d" quebrava em duas
    // linhas em tela estreita e esticava o card. Pares canônicos de status
    // (contrato §6): vencida = vermelho (falha), a vencer = âmbar (aviso).
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
    // Só rende quando há uso: antes toda linha carregava um "0 nós" cinza, que
    // numa lista recém-criada era ruído em todas as linhas de uma vez.
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
    // Azul (compartilhamento/em circulação) no lugar do indigo antigo, que não
    // é um dos tons canônicos de status do contrato §6.
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

  // Tipos presentes na lista, para o filtro (só os que existem — não o catálogo inteiro).
  const typesPresent = useMemo(() => {
    const set = new Set((credentials ?? []).map(c => c.type))
    return Array.from(set).sort((a, b) => getTypeLabel(a).localeCompare(getTypeLabel(b)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [credentials, credentialTypes])

  // Filtro + ordenação. `visible` é a lista já peneirada; a separação por
  // propriedade (minhas × compartilhadas) e o agrupamento por tipo acontecem no
  // render — ver `renderCredList`.
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
      // "used": mais recentemente usadas primeiro; nunca-usadas ao fim.
      const av = a.last_used_at ?? "", bv = b.last_used_at ?? ""
      if (av && bv) return bv.localeCompare(av)
      if (av) return -1
      if (bv) return 1
      return a.name.localeCompare(b.name)
    })
    return list
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [credentials, search, typeFilter, sortBy, credentialTypes])

  // Agrupa uma lista por tipo (usado dentro de cada seção quando "Agrupar por
  // tipo" está ligado). Deixou de ser um useMemo sobre `visible` inteiro: agora
  // o agrupamento roda POR seção de propriedade — ver renderCredList.
  function agruparPorTipo(list: ICredentials[]) {
    const map = new Map<string, ICredentials[]>()
    for (const c of list) {
      const arr = map.get(c.type) ?? []
      arr.push(c)
      map.set(c.type, arr)
    }
    return Array.from(map.entries()).sort((a, b) => getTypeLabel(a[0]).localeCompare(getTypeLabel(b[0])))
  }

  // Separação primária por PROPRIEDADE: as minhas credenciais e as
  // compartilhadas comigo param de se misturar visualmente (o badge sozinho não
  // bastava). Só vira duas seções quando há de fato mistura; senão, lista única.
  // Memoizado: as duas varreduras de `visible` rodavam a cada render; só mudam
  // quando a lista visível ou a identidade (myId, via ownership) mudam.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const minhas = useMemo(() => visible.filter(c => ownership(c).isMine), [visible, myId])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const compartilhadas = useMemo(() => visible.filter(c => !ownership(c).isMine), [visible, myId])
  const temMistura = useMemo(() => minhas.length > 0 && compartilhadas.length > 0, [minhas, compartilhadas])

  // Pré-agrupa por tipo cada seção uma vez (chaveado por escopo), em vez de
  // reagrupar dentro de renderCredList a cada render. Só muda quando as listas
  // ou os labels (typeLabel) mudam; com "Agrupar por tipo" desligado ninguém lê.
  // `agruparPorTipo` é recriada a cada render (fecha sobre typeLabel, que já
  // está nas deps); incluí-la anularia o memo.
  const gruposPorEscopo = useMemo<Record<string, [string, ICredentials[]][]>>(() => ({
    mine: agruparPorTipo(minhas),
    shared: agruparPorTipo(compartilhadas),
    all: agruparPorTipo(visible),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [minhas, compartilhadas, visible, typeLabel])

  const hasCreds = !!credentials && credentials.length > 0
  const comFiltro = typeFilter !== "__all__"

  function clearFilters() {
    setSearch("")
    setTypeFilter("__all__")
  }

  // Subtítulo do cabeçalho: conta o escopo ("N credenciais · N em uso"). O zero
  // some (contrato §7) — "0 em uso" numa lista recém-criada não ajuda ninguém.
  function textoDoSubtitulo(): string {
    const partes = [plural(credentials!.length, "credencial", "credenciais")]
    if (usedCount > 0) partes.push(`${formatarInteiro(usedCount)} em uso`)
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
              {/* Ações destrutivas/de edição são owner-only: quem só recebeu a
                  credencial compartilhada não consegue carregar os segredos nem
                  o backend deixaria editar/excluir. Escondemos em vez de deixar
                  o clique falhar com 403. */}
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

  // Renderiza um conjunto de credenciais: plano, ou sub-agrupado por tipo quando
  // "Agrupar por tipo" está ligado. `scope` prefixa as keys para não colidirem
  // entre as seções "minhas" e "compartilhadas".
  function renderCredList(creds: ICredentials[], scope: string, aninhado: boolean) {
    if (grouped) {
      return (
        <div className="flex flex-col gap-4">
          {/* Grupos já pré-computados por escopo (ver gruposPorEscopo). */}
          {gruposPorEscopo[scope].map(([type, cs]) => {
            const style = getCredentialTypeStyle(type)
            const TypeIcon = style.icon
            // Nível do heading do tipo: h3 quando aninhado sob uma seção de
            // propriedade (o h2 "Minhas"/"Compartilhadas"); h2 quando a lista é
            // plana, para a cadeia de headings não pular de h1 direto para h3
            // (regressão para leitores de tela).
            const TituloTipo = aninhado ? "h3" : "h2"
            return (
              <div key={`${scope}-${type}`} className="flex flex-col gap-2">
                <div className="flex items-center gap-2 px-1">
                  <TypeIcon className={`size-3.5 ${style.fg}`} aria-hidden="true" />
                  <TituloTipo className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {getTypeLabel(type)}
                  </TituloTipo>
                  <span className="text-[11px] tabular-nums text-muted-foreground/60">{formatarInteiro(cs.length)}</span>
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
      {/* Cabeçalho fixo do contrato §1: título + subtítulo de escopo à esquerda,
          ações à direita (Atualizar em ghost e Criar como única primária). No
          telefone o secundário vai ao menu ⋯ e o primário ocupa a linha. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-foreground">Credenciais</h1>
          {/* Região viva estável: o `aria-live` fica no contêiner (não no <p>),
              que sobrevive à troca Skeleton↔texto, para o leitor de tela anunciar
              a contagem quando ela muda (ex.: após Atualizar). */}
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

            {/* Telefone: menu ⋯ com o secundário que saiu da linha. */}
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

      {/* Barra de busca/filtro/ordenação — só quando há o que filtrar (U1/U7). */}
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
          {/* Toggle canônico do contrato §1: grupo com aria-pressed, ativo em
              bg-accent, inativo em muted. */}
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

      {/* Precedência do contrato §3: carregando → erro (só na 1ª carga) →
          primeiro uso → conteúdo (com sem-resultado dentro). */}
      {loading ? (
        <SkeletonDeCredenciais />
      ) : loadError && atualizadoEm == null ? (
        <ErroDeCarga onTentar={handleRefresh} />
      ) : !hasCreds ? (
        <VazioPrimeiroUso canEdit={canEdit} onCriar={() => { setDuplicateSeed(undefined); setCreateModalState(true) }} />
      ) : visible.length === 0 ? (
        <SemResultado q={search} comFiltro={comFiltro} onLimpar={clearFilters} />
      ) : (
        // Lista — separada por PROPRIEDADE (minhas × compartilhadas comigo)
        // quando há mistura; cada seção respeita o "Agrupar por tipo". Sem
        // mistura, cai numa lista única (sem cabeçalho redundante).
        <div className={cn("flex flex-col gap-6 transition-opacity", refreshing && "opacity-60")}>
          {temMistura ? (
            <>
              <section aria-labelledby="cred-minhas-titulo" className="flex flex-col gap-2.5">
                <div className="flex items-center gap-2 border-b border-border/60 pb-1.5">
                  <TbUser className="size-4 text-muted-foreground" aria-hidden="true" />
                  <h2 id="cred-minhas-titulo" className="text-sm font-semibold text-foreground">Minhas credenciais</h2>
                  <span className="text-xs tabular-nums text-muted-foreground/70">{formatarInteiro(minhas.length)}</span>
                </div>
                {renderCredList(minhas, "mine", true)}
              </section>
              <section aria-labelledby="cred-compartilhadas-titulo" className="flex flex-col gap-2.5">
                <div className="flex items-center gap-2 border-b border-border/60 pb-1.5">
                  <TbUsers className="size-4 text-muted-foreground" aria-hidden="true" />
                  <h2 id="cred-compartilhadas-titulo" className="text-sm font-semibold text-foreground">Compartilhadas comigo</h2>
                  <span className="text-xs tabular-nums text-muted-foreground/70">{formatarInteiro(compartilhadas.length)}</span>
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
