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

/** Janela mínima entre reloads automáticos — ver o listener de foco abaixo. */
const RELOAD_THROTTLE_MS = 10_000;

export default function WorkspacesPage() {
  const { workspaces, current, setCurrent, reload, loading, error } = useWorkspace();
  const { data: session } = useSession();
  const currentUserId = session?.user?.id_hash ?? null;

  const router = useRouter();
  const searchParams = useSearchParams();

  const [createOpen, setCreateOpen] = useState(false);
  // Alvo do painel de configuração e a seção em que ele abre: os atalhos do
  // painel do ativo ("Membros") pulam direto para a seção certa.
  const [painel, setPainel] = useState<{ id: string; secao: SectionId } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Executor de cada workspace: troca em um passo no painel do ativo, status
  // por texto na fileira dos outros.
  const executor = useWorkspaceExecutors(workspaces);

  // Derivado da lista, e não guardado: assim o painel acompanha uma renomeação
  // feita lá dentro e se fecha sozinho se o workspace sair da lista (saída,
  // exclusão, ou remoção feita por outra pessoa).
  const settingsTarget = workspaces.find(w => w.id_hash === painel?.id) ?? null;

  // Fechar por `open={false}` não dispara `onOpenChange`, então o id do alvo
  // sobreviveria ao desaparecimento do workspace — e reabriria o painel sozinho
  // se ele voltasse à lista. O reset tem de ser explícito.
  useEffect(() => {
    if (painel && !settingsTarget) setPainel(null);
  }, [painel, settingsTarget]);

  // Re-fetch ao montar — sem isso, workspaces deletadas por OUTROS donos ou
  // remoções de membership feitas em outra sessão ficam visíveis até relogar.
  useEffect(() => { reload(); }, [reload]);

  const lastReloadRef = useRef(0);
  useEffect(() => {
    // O intervalo cobre "usuário fica parado na tela enquanto o dono apaga"; o
    // listener de foco cobre "usuário volta de outra aba". O throttle existe
    // porque alt-tab repetido chamaria reload a cada volta.
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
    // Limpa o parâmetro: sem isso, cancelar o diálogo e dar F5 o reabria.
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

  // O ativo sai da LISTA, não do context: `current` pode ficar defasado por um
  // instante após uma exclusão, e o painel não pode mostrar um workspace que a
  // fileira já não tem.
  const ativo = current ? workspaces.find(w => w.id_hash === current.id_hash) ?? null : null;
  const outros = workspaces.filter(w => w.id_hash !== ativo?.id_hash);

  return (
    <PageRoot>
      {/* Cabeçalho — mesmo padrão de Artefatos/Executores/Histórico. */}
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

      {/* Erro precede o estado vazio: sem esta distinção, um 401/500 renderizava
          "Nenhum workspace encontrado" para quem tem dez — a tela afirmava um
          fato sobre os dados quando não tinha dado nenhum. */}
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
          {/* `key` pelo id: trocar de workspace remonta o painel, e a entrada
              animada é o que mostra que o escolhido subiu — sem ela a tela só
              "piscava" com outro conteúdo no mesmo lugar. */}
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

      {/* `key` remonta o painel a cada abertura — sem isso o estado das seções
          (rascunho da allowlist, seção ativa) e os dados já buscados vazariam de
          uma abertura para a outra, e reabrir mostraria membros obsoletos. */}
      <WorkspaceSettingsSheet
        key={painel?.id ?? "none"}
        workspace={settingsTarget}
        initialSection={painel?.secao}
        currentUserId={currentUserId}
        onClose={() => {
          setPainel(null);
          // O executor pode ter mudado lá dentro; o painel do ativo e a fileira
          // precisam refletir.
          executor.recarregar();
        }}
      />
    </PageRoot>
  );
}
