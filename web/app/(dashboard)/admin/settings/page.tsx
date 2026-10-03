"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useFetchData } from "@/app/hooks/useFetchData"
import PageRoot from "@/app/components/page-root"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { TbRefresh } from "react-icons/tb"
import { IsolationFloorSection } from "@/app/components/admin/isolation-floor-section"
import { AssistantModel } from "@/app/components/admin/settings/modelo-do-assistente"
import { EXTENSOES } from "@/extensoes"
import { createToast } from "@/utils/createToast"
import { useSession } from "next-auth/react"
import { plural } from "@/lib/formatos"
import { CartaoDeErro, FormSkeleton, SkeletonDeNodes, TableSkeleton } from "@/app/components/admin/settings/estados"
import { SettingsSection } from "@/app/components/admin/settings/secao"
import { Frescor, SECTIONS, SettingsNav, type SectionId } from "@/app/components/admin/settings/nav"
import { buildAlerts, OverviewSection } from "@/app/components/admin/settings/visao-geral"
import { WhitelistSection } from "@/app/components/admin/settings/whitelist"
import { ArtifactRetentionSection } from "@/app/components/admin/settings/retencao-de-artefatos"
import { DriveSettingsSection } from "@/app/components/admin/settings/drive"
import { StorageUsageSection } from "@/app/components/admin/settings/armazenamento"
import { NodesAdminSection } from "@/app/components/admin/settings/nodes"
import { WorkspaceTrashSection } from "@/app/components/admin/settings/lixeira-de-workspaces"

// The presentation of the model section: what always applies, and what each
// extension adds (switching the model may change one of its accounts).
const MODEL_HELP_TEXT = [
  "Vale para o assistente da Home e o do editor.",
  ...EXTENSOES.flatMap(e => e.painelDoModelo?.apoio ?? []),
  "A troca entra na próxima conversa; as que estão em curso terminam no modelo em que começaram.",
].join(" ")

// ── Main page ──────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { data: session } = useSession()
  const token = (session?.user as { access_token?: string })?.access_token ?? ""

  const { data, loading, firstLoad: healthFirst, error: healthError, refetch: refetchHealth } = useFetchData(
    () => GisFlowService.getSystemHealth(),
    "Erro ao carregar configurações."
  )

  const { data: artifactSettings, loading: artifactLoading, firstLoad: artifactFirst, error: artifactError, refetch: refetchArtifacts } = useFetchData(
    () => GisFlowService.getArtifactSettings(),
    "Erro ao carregar configurações de artefatos."
  )

  const { data: modelo, loading: modelLoading, firstLoad: modelFirst, error: modelError, refetch: refetchModel } = useFetchData(
    () => GisFlowService.painelDoModelo(),
    "Erro ao carregar o modelo do assistente."
  )

  const { data: storageData, loading: storageLoading, firstLoad: storageFirst, error: storageError, refetch: refetchStorage } = useFetchData(
    () => GisFlowService.getStorageUsage(),
    "Erro ao carregar uso de armazenamento."
  )

  const { data: adminNodes, loading: nodesLoading, firstLoad: nodesFirst, error: nodesError, refetch: refetchNodes } = useFetchData(
    () => GisFlowService.listAdminNodes(),
    "Erro ao carregar lista de nodes."
  )

  const { data: trash, loading: trashLoading, firstLoad: trashFirst, error: trashError, refetch: refetchTrash } = useFetchData(
    () => GisFlowService.getWorkspaceTrash(),
    "Erro ao carregar a lixeira de workspaces."
  )

  const { data: policies, loading: policiesLoading, firstLoad: policiesFirst, error: policiesError, refetch: refetchPolicies } = useFetchData(
    () => GisFlowService.listWorkspacePolicies(),
    "Erro ao carregar as políticas de execução."
  )

  const anyLoading = loading || artifactLoading || storageLoading || nodesLoading || trashLoading || policiesLoading

  function refetchAll() {
    refetchHealth()
    refetchArtifacts()
    refetchStorage()
    refetchNodes()
    refetchTrash()
    refetchPolicies()
  }

  // Restore/purge touches what the Storage section shows (the workspace changes
  // state, or disappears), so the two reads have to move together.
  function refetchTrashAndStorage() {
    refetchTrash()
    refetchStorage()
  }

  async function handleSaveWhitelist(domains: string[]) {
    const res = await GisFlowService.updateWebhookWhitelist(domains)
    if (res.error) createToast.error(res.error.message ?? "Erro")
    else createToast.success("Whitelist atualizada.")
  }

  // Active section mirrored in the URL hash: allows going back through the
  // browser, reloading without losing your place and linking directly to a section.
  const [section, setSection] = useState<SectionId>("overview")

  useEffect(() => {
    const fromHash = window.location.hash.replace("#", "") as SectionId
    if (SECTIONS.some(s => s.id === fromHash)) setSection(fromHash)
  }, [])

  function goTo(id: SectionId) {
    setSection(id)
    window.history.replaceState(null, "", `#${id}`)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  const alerts = useMemo(
    () => buildAlerts(
      data ?? null, artifactSettings?.artifact_retention_days,
      storageData ?? null, adminNodes ?? null, trash ?? null, policies ?? null,
    ),
    [data, artifactSettings, storageData, adminNodes, trash, policies],
  )

  const alertsBySection = useMemo(() => {
    const acc: Partial<Record<SectionId, number>> = {}
    for (const a of alerts) acc[a.section] = (acc[a.section] ?? 0) + 1
    return acc
  }, [alerts])

  // Stamp of the end of each load cycle, for the "updated N ago". It stays null
  // until the first read completes — that is what holds the subtitle Skeleton.
  const [atualizadoEm, setUpdatedAt] = useState<number | null>(null)
  const wasLoading = useRef(anyLoading)
  useEffect(() => {
    if (wasLoading.current && !anyLoading) setUpdatedAt(Date.now())
    wasLoading.current = anyLoading
  }, [anyLoading])

  // Subtitle that tells the system's real state: how many pending items and how
  // many workspaces hold data. While the 1st load has not finished, it becomes a
  // Skeleton — it never writes "0 pendências" before knowing.
  const workspacesWithData = storageData?.by_workspace.length ?? 0
  const subtitleParts: string[] = [
    alerts.length > 0 ? plural(alerts.length, "pendência", "pendências") : "Nada requer atenção",
  ]
  if (workspacesWithData > 0) subtitleParts.push(`${plural(workspacesWithData, "workspace")} com dados`)
  const subtitulo = subtitleParts.join(" · ")

  return (
    <PageRoot>
      {/* `flex-wrap`: without it the title and the action row fight for the same line
          on a phone, and the one that gives way is always the title. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-foreground">Configurações</h1>
          {atualizadoEm != null ? (
            <p className="text-sm font-medium text-muted-foreground">{subtitulo}</p>
          ) : (
            <Skeleton className="mt-1 h-4 w-64" />
          )}
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={refetchAll}
            disabled={anyLoading}
            aria-label="Atualizar as configurações"
            className="gap-1.5 max-md:h-10"
          >
            <TbRefresh size={14} className={anyLoading ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
            Atualizar
          </Button>
          {atualizadoEm != null && <Frescor carimbo={atualizadoEm} />}
        </div>
      </div>

      <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
        <SettingsNav active={section} onSelect={goTo} alertsBySection={alertsBySection} />

        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {section === "overview" && (
            <SettingsSection
              id="overview"
              titulo="Visão geral"
              apoio="Resumo do sistema. Cada pendência leva direto à seção onde se resolve."
              carregando={anyLoading}
            >
              <OverviewSection
                storage={storageData ?? null}
                nodes={adminNodes ?? null}
                retentionDays={artifactSettings?.artifact_retention_days}
                whitelistCount={data?.webhook_whitelist.length ?? 0}
                alerts={alerts}
                loading={anyLoading && atualizadoEm == null}
                onNavigate={goTo}
              />
            </SettingsSection>
          )}

          {section === "seguranca" && (
            <>
              <SettingsSection
                id="whitelist"
                titulo="Webhook Whitelist"
                apoio="Restrinja para quais domínios o webhook de fim de execução pode ser enviado. Vale junto com a allowlist de cada workspace; lista vazia não restringe."
                carregando={loading}
              >
                {healthFirst ? (
                  <FormSkeleton rotulo="Carregando a whitelist" />
                ) : healthError && !data ? (
                  <CartaoDeErro mensagem={healthError} onTentar={refetchHealth} />
                ) : data ? (
                  // `key` derived from the server value: when the fetched
                  // whitelist changes (e.g. after Refresh), the section remounts
                  // with fresh state — the body stopped swapping to a Skeleton
                  // on refetch, so this remount replaces the re-sync the old
                  // unmount/remount guaranteed. Stable across ordinary
                  // re-renders, it does not discard edits in progress.
                  <WhitelistSection
                    key={data.webhook_whitelist.join(" ")}
                    domains={data.webhook_whitelist}
                    onSave={handleSaveWhitelist}
                  />
                ) : null}
              </SettingsSection>

              <SettingsSection
                id="retencao"
                titulo="Retenção de Artefatos"
                apoio="Por quantos dias os artefatos gerados pelos workflows ficam disponíveis para download. Após o prazo, são removidos automaticamente."
                carregando={artifactLoading}
              >
                {artifactFirst ? (
                  <FormSkeleton rotulo="Carregando a retenção" />
                ) : artifactError && !artifactSettings ? (
                  <CartaoDeErro mensagem={artifactError} onTentar={refetchArtifacts} />
                ) : (
                  // `key` from the server value: remounts and re-syncs the input when
                  // the fetched retention changes (e.g. after Refresh), as the
                  // old card's remount did — without erasing edits in progress.
                  <ArtifactRetentionSection
                    key={String(artifactSettings?.artifact_retention_days ?? "sem")}
                    initialDays={artifactSettings?.artifact_retention_days ?? null}
                  />
                )}
              </SettingsSection>
            </>
          )}

          {section === "armazenamento" && (
            <SettingsSection
              id="armazenamento"
              titulo="Armazenamento"
              apoio="Uso de disco do MinIO por workspace (Drive + Artefatos)."
              carregando={storageLoading}
            >
              {storageFirst ? (
                <TableSkeleton rotulo="Carregando o armazenamento" linhas={5} />
              ) : storageError && !storageData ? (
                <CartaoDeErro mensagem={storageError} onTentar={refetchStorage} />
              ) : storageData ? (
                <StorageUsageSection data={storageData} onRefresh={refetchStorage} />
              ) : null}
            </SettingsSection>
          )}

          {section === "drive" && (
            <SettingsSection
              id="drive"
              titulo="Drive — Upload de Arquivos"
              apoio="Tamanho máximo permitido por arquivo e as extensões aceitas na plataforma."
            >
              {token
                ? <DriveSettingsSection />
                : <FormSkeleton rotulo="Carregando as configurações do Drive" />}
            </SettingsSection>
          )}

          {section === "nodes" && (
            <SettingsSection
              id="nodes"
              titulo="Nodes da plataforma"
              apoio="Habilite ou desabilite nodes. Nodes desabilitados somem do drawer do canvas; workflows que os utilizam falham ao executar."
              carregando={nodesLoading}
            >
              {nodesFirst ? (
                <SkeletonDeNodes />
              ) : nodesError && !adminNodes ? (
                <CartaoDeErro mensagem={nodesError} onTentar={refetchNodes} />
              ) : adminNodes ? (
                <NodesAdminSection nodes={adminNodes} onChanged={refetchNodes} />
              ) : null}
            </SettingsSection>
          )}

          {section === "assistente" && (
            <SettingsSection
              id="assistente"
              titulo="Modelo do assistente"
              apoio={MODEL_HELP_TEXT}
              carregando={modelLoading}
            >
              {modelFirst ? (
                <FormSkeleton rotulo="Carregando o modelo do assistente" />
              ) : modelError && !modelo ? (
                <CartaoDeErro mensagem={modelError} onTentar={refetchModel} />
              ) : modelo ? (
                <AssistantModel painel={modelo} onTrocado={refetchModel} />
              ) : null}
            </SettingsSection>
          )}

          {section === "execucao" && (
            <SettingsSection
              id="execucao"
              titulo="Piso de isolamento"
              apoio="Por workspace: exigir isolamento proíbe o pool compartilhado como último recurso — o dono não consegue afrouxar. Use onde há exigência externa de que os dados nunca saiam dos executores dedicados."
              carregando={policiesLoading}
            >
              {policiesFirst ? (
                <TableSkeleton rotulo="Carregando as políticas de execução" linhas={4} />
              ) : policiesError && !policies ? (
                <CartaoDeErro mensagem={policiesError} onTentar={refetchPolicies} />
              ) : policies ? (
                <IsolationFloorSection items={policies} onChanged={refetchPolicies} />
              ) : null}
            </SettingsSection>
          )}

          {section === "lixeira" && (
            <SettingsSection
              id="lixeira"
              titulo="Lixeira de workspaces"
              apoio="Workspaces removidos pelos donos. Restaurar devolve o workspace e os workflows que caíram junto; excluir permanentemente descarta o registro. Só administradores enxergam esta lista."
              carregando={trashLoading}
            >
              {trashFirst ? (
                <TableSkeleton rotulo="Carregando a lixeira" linhas={3} />
              ) : trashError && !trash ? (
                <CartaoDeErro mensagem={trashError} onTentar={refetchTrash} />
              ) : trash ? (
                <WorkspaceTrashSection items={trash} onChanged={refetchTrashAndStorage} />
              ) : null}
            </SettingsSection>
          )}
        </div>
      </div>
    </PageRoot>
  )
}
