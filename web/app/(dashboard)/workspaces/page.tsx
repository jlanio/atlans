"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { TbAlertTriangle, TbBuildingFactory2, TbPlus, TbRefresh } from "react-icons/tb";
import { hasMinRole, useWorkspace, type Workspace } from "@/context/WorkspaceContext";
import PageRoot from "@/app/components/page-root";
import { Button } from "@/app/components/ui/button";
import { Dialog } from "@/app/components/ui/dialog";
import { Skeleton } from "@/app/components/ui/skeleton";
import { VazioPrimeiroUso } from "@/app/components/shared/estados";
import { WorkspaceHero } from "@/app/components/workspace/workspace-hero";
import { WorkspaceRow } from "@/app/components/workspace/workspace-row";
import { useWorkspaceExecutors } from "@/app/components/workspace/use-workspace-executors";
import { CreateWorkspaceDialog } from "@/app/components/workspace/dialog-content/create-workspace";
import { WorkspaceSettingsSheet, type SectionId } from "@/app/components/workspace/settings-sheet";

/** Minimum window between automatic reloads — see the focus listener below. */
const RELOAD_THROTTLE_MS = 10_000;

export default function WorkspacesPage() {
  const { workspaces, current, setCurrent, reload, loading, error } = useWorkspace();
  const { data: session } = useSession();
  const currentUserId = session?.user?.id_hash ?? null;

  const router = useRouter();
  const searchParams = useSearchParams();

  const [createOpen, setCreateOpen] = useState(false);
  // Target of the settings panel and the section it opens on: the shortcuts on
  // the active one's panel ("Membros") jump straight to the right section.
  const [painel, setPainel] = useState<{ id: string; secao: SectionId } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Each workspace's executor: changed in one step on the active one's panel,
  // status as text on the others' row.
  const executor = useWorkspaceExecutors(workspaces);

  // Derived from the list, and not stored: that way the panel follows a rename
  // made inside it and closes on its own if the workspace leaves the list
  // (leaving, deletion, or removal done by someone else).
  const settingsTarget = workspaces.find(w => w.id_hash === painel?.id) ?? null;

  // Closing via `open={false}` does not fire `onOpenChange`, so the target id
  // would survive the workspace's disappearance — and would reopen the panel on
  // its own if it came back to the list. The reset has to be explicit.
  useEffect(() => {
    if (painel && !settingsTarget) setPainel(null);
  }, [painel, settingsTarget]);

  // Re-fetch on mount — without it, workspaces deleted by OTHER owners or
  // membership removals made in another session stay visible until re-login.
  useEffect(() => { reload(); }, [reload]);

  const lastReloadRef = useRef(0);
  useEffect(() => {
    // The interval covers "user sits on the screen while the owner deletes"; the
    // focus listener covers "user comes back from another tab". The throttle
    // exists because repeated alt-tab would call reload on every return.
    function maybeReload() {
      const agora = Date.now();
      if (agora - lastReloadRef.current < RELOAD_THROTTLE_MS) return;
      lastReloadRef.current = agora;
      reload();
    }
    const id = setInterval(() => {
      if (document.visibilityState === "visible") maybeReload();
    }, 90_000);
    function onVisibility() {
      if (document.visibilityState === "visible") maybeReload();
    }
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [reload]);

  useEffect(() => {
    if (searchParams.get("new") !== "1") return;
    setCreateOpen(true);
    // Clears the parameter: without this, canceling the dialog and pressing F5 reopened it.
    router.replace("/workspaces");
  }, [searchParams, router]);

  async function handleRefresh() {
    setRefreshing(true);
    lastReloadRef.current = Date.now();
    await Promise.all([reload(), executor.recarregar()]);
    setRefreshing(false);
  }

  function abrirPainel(id: string, secao: SectionId = "geral") {
    setPainel({ id, secao });
  }

  function leituraDoExecutor(ws: Workspace) {
    return {
      executores: executor.executores,
      alvo: executor.alvos[ws.id_hash],
      alvoDesconhecido: executor.desconhecidos.has(ws.id_hash),
      erroExecutores: executor.erro,
      politica: executor.politicas[ws.id_hash] ?? null,
    };
  }

  const carregandoInicial = loading && workspaces.length === 0;

  // The active one comes from the LIST, not from the context: `current` may lag
  // for an instant after a deletion, and the panel must not show a workspace the
  // row no longer has.
  const ativo = current ? workspaces.find(w => w.id_hash === current.id_hash) ?? null : null;
  const outros = workspaces.filter(w => w.id_hash !== ativo?.id_hash);

  return (
    <PageRoot>
      {/* Header — same pattern as Artifacts/Executors/History. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Workspaces</h1>
          <p className="text-sm text-muted-foreground font-medium">
            Gerencie seus workspaces: membros, notificações e onde os workflows de cada um rodam.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing || executor.salvando.size > 0} className="gap-1.5">
            <TbRefresh size={14} className={refreshing ? "animate-spin" : ""} />
            Atualizar
          </Button>
          <Button size="sm" className="gap-1.5" onClick={() => setCreateOpen(true)}>
            <TbPlus size={14} />
            Novo workspace
          </Button>
        </div>
      </div>

      {/* Error precedes the empty state: without this distinction, a 401/500 rendered
          "Nenhum workspace encontrado" for someone who has ten — the screen asserted
          a fact about the data when it had no data at all. */}
      {error && (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-3 rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          <TbAlertTriangle size={16} className="shrink-0" />
          <p className="min-w-0 flex-1 basis-64">{error}</p>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
            Tentar novamente
          </Button>
        </div>
      )}

      {!error && !carregandoInicial && workspaces.length === 0 && (
        <VazioPrimeiroUso
          icone={TbBuildingFactory2}
          titulo="Nenhum workspace encontrado"
          descricao="Crie seu primeiro workspace para organizar workflows e colaborar com sua equipe."
          cta={{ rotulo: "Criar workspace", icone: TbPlus, onClick: () => setCreateOpen(true) }}
        />
      )}

      {carregandoInicial ? (
        <>
          <Skeleton className="h-48 w-full rounded-xl" />
          <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}
          </div>
        </>
      ) : workspaces.length > 0 && (
        <>
          {/* `key` by id: switching workspace remounts the panel, and the animated
              entrance is what shows the chosen one moved up — without it the
              screen just "flashed" with other content in the same place. */}
          {ativo && (
            <WorkspaceHero
              key={ativo.id_hash}
              workspace={ativo}
              {...leituraDoExecutor(ativo)}
              salvandoExecutor={executor.salvando.has(ativo.id_hash)}
              podeGerenciar={hasMinRole(ativo.my_role, "admin")}
              onTrocarExecutor={valor => executor.trocar(ativo.id_hash, valor, ativo.name)}
              onConfigurar={secao => abrirPainel(ativo.id_hash, secao)}
            />
          )}

          {outros.length > 0 && (
            <section aria-labelledby="outros-workspaces" className="flex flex-col gap-2.5">
              <div className="flex items-baseline justify-between px-0.5">
                <h2
                  id="outros-workspaces"
                  className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground"
                >
                  {ativo ? "Outros workspaces" : "Workspaces"}
                </h2>
                <span className="text-xs tabular-nums text-muted-foreground">{outros.length}</span>
              </div>
              <ul className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                {outros.map(ws => (
                  <WorkspaceRow
                    key={ws.id_hash}
                    workspace={ws}
                    {...leituraDoExecutor(ws)}
                    onUsar={() => setCurrent(ws)}
                    onConfigurar={() => abrirPainel(ws.id_hash)}
                  />
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        {createOpen && <CreateWorkspaceDialog onClose={() => setCreateOpen(false)} />}
      </Dialog>

      {/* `key` remounts the panel on every open — without it the sections' state
          (allowlist draft, active section) and the already-fetched data would leak
          from one open to the next, and reopening would show stale members. */}
      <WorkspaceSettingsSheet
        key={painel?.id ?? "none"}
        workspace={settingsTarget}
        initialSection={painel?.secao}
        currentUserId={currentUserId}
        onClose={() => {
          setPainel(null);
          // The executor may have changed in there; the active one's panel and the
          // row need to reflect it.
          executor.recarregar();
        }}
      />
    </PageRoot>
  );
}
