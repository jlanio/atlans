"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
  ReactNode,
} from "react";
import { useSession } from "next-auth/react";
import { createToast } from "@/utils/createToast";
import { GisFlowService, setAuthToken } from "@/service/GisFlowService";
import type { IWorkspace } from "@/service/types";

// ----- tipos -----
// A forma canonica vive em service/types.ts — e o que o GisFlowService devolve.
// Re-exportada aqui porque este context e o dono do estado do workspace ativo,
// e e daqui que os componentes importam o tipo.
export type Workspace = IWorkspace;

// ----- helpers de role -----
export const ROLE_ORDER = ["viewer", "editor", "operator", "admin", "owner"] as const;

export function hasMinRole(actual: string | null | undefined, minimum: string): boolean {
  if (!actual) return false;
  const ai = ROLE_ORDER.indexOf(actual as typeof ROLE_ORDER[number]);
  const mi = ROLE_ORDER.indexOf(minimum as typeof ROLE_ORDER[number]);
  if (ai === -1 || mi === -1) return false;
  return ai >= mi;
}

/**
 * Workspaces para onde o workflow atual pode ser movido.
 *
 * Espelha `_assert_can_move` do backend: mover exige admin/owner na origem E no
 * destino. Fica aqui, ao lado de `hasMinRole`, porque duas telas precisam da
 * mesma resposta — o menu (para decidir se oferece "Mover") e o diálogo (para
 * listar os destinos). Escrita duas vezes, elas divergiriam em silêncio: o menu
 * apareceria e o select viria vazio.
 */
export function moveTargets(workspaces: Workspace[], currentId?: string | null): Workspace[] {
  return workspaces.filter(
    (w) => w.id_hash !== currentId && hasMinRole(w.my_role, "admin"),
  );
}

interface WorkspaceContextValue {
  workspaces: Workspace[];
  /** Workspace ativo no momento */
  current: Workspace | null;
  loading: boolean;
  /**
   * Falha do último carregamento da lista. Sem isto, um 401/500 chegava na tela
   * indistinguível de "você não tem workspace nenhum" — quem tinha dez via o
   * convite para criar o primeiro.
   */
  error: string | null;
  /** Pode criar/editar/deletar workflows, fazer upload e delete no Drive e artifacts */
  canEdit: boolean;
  /** Pode executar workflows e retry */
  canExecute: boolean;
  /** Pode convidar/remover membros, alterar roles, definir executor */
  canManage: boolean;
  setCurrent: (ws: Workspace | null) => void;
  reload: () => Promise<void>;
  createWorkspace: (name: string, description?: string) => Promise<Workspace>;
  updateWorkspace: (id_hash: string, name: string, description?: string | null) => Promise<Workspace>;
  deleteWorkspace: (id_hash: string) => Promise<void>;
  /** Sai de um workspace do qual se é membro (não funciona para o dono). */
  leaveWorkspace: (id_hash: string) => Promise<void>;
}

// ----- chave localStorage -----
const WS_KEY = "atlas_workspace_id";

const WorkspaceContext = createContext<WorkspaceContextValue>({
  workspaces: [],
  current: null,
  loading: true,
  error: null,
  canEdit: false,
  canExecute: false,
  canManage: false,
  setCurrent: () => {},
  reload: async () => {},
  createWorkspace: async () => { throw new Error("not ready") },
  updateWorkspace: async () => { throw new Error("not ready") },
  deleteWorkspace: async () => {},
  leaveWorkspace: async () => {},
});

export function useWorkspace() {
  return useContext(WorkspaceContext);
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();
  const workspaceIdFromSession = session?.user?.workspace_id ?? null;
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [current, setCurrentState] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const accessToken = session?.user?.access_token ?? null;
  const myRole = current?.my_role ?? null;
  const canEdit = hasMinRole(myRole, "editor");
  const canExecute = hasMinRole(myRole, "operator");
  const canManage = hasMinRole(myRole, "admin");

  const reload = useCallback(async () => {
    try {
      // Garante o token no interceptor antes da 1a chamada. O SessionSync já
      // faz isso no corpo do render (providers.tsx), mas repetir aqui é
      // idempotente e não deixa o carregamento inicial depender da ordem de
      // montagem — que é o que o header explícito antigo protegia.
      if (accessToken) setAuthToken(accessToken);

      const res = await GisFlowService.listWorkspaces();
      // Os helpers do service NÃO lançam: erro vem como res.error. Sem esta
      // checagem um 401/500 cairia no caminho feliz com data undefined.
      //
      // A lista anterior NÃO é limpa: um refresh periódico que falha não deve
      // apagar da tela o que o usuário já estava vendo. O banner de erro conta
      // o que houve; os dados velhos continuam melhor que nenhum dado.
      if (res.error) {
        setError(res.error.message ?? "Não foi possível carregar os workspaces.");
        return;
      }
      setError(null);

      const data = res.data ?? [];
      setWorkspaces(data);

      // Restaura workspace salvo ou usa o workspace padrão do usuário
      const savedId = localStorage.getItem(WS_KEY);
      const preferred =
        data.find((w) => w.id_hash === savedId) ??
        data.find((w) => w.id_hash === workspaceIdFromSession) ??
        data.find((w) => w.is_default) ??
        data[0] ??
        null;
      setCurrentState(preferred);
    } finally {
      setLoading(false);
    }
  }, [workspaceIdFromSession, accessToken]);

  // Carrega quando a sessão Auth.js é estabelecida
  useEffect(() => {
    if (status === "authenticated") {
      reload();
    } else if (status === "unauthenticated") {
      setWorkspaces([]);
      setCurrentState(null);
      setLoading(false);
    }
  }, [status, reload]);

  // Rastreia o workspace anterior via ref para decidir se emite toast na
  // troca. Evita re-criacao do useCallback a cada mudanca (usar `current`
  // como dep forcaria isso). Tambem evita spurious toast na hidratacao
  // inicial: prevId comeca null e so vira setado apos a 1a troca.
  const prevIdRef = useRef<string | null>(null);

  const setCurrent = useCallback((ws: Workspace | null) => {
    const prevId = prevIdRef.current;
    prevIdRef.current = ws?.id_hash ?? null;

    setCurrentState(ws);
    if (ws) {
      localStorage.setItem(WS_KEY, ws.id_hash);
      // Toast so quando ha troca real entre dois workspaces (nao no
      // primeiro set apos boot). Sinaliza mudanca de escopo — util
      // antes de acoes destrutivas ou de criacao no workspace novo.
      if (prevId && prevId !== ws.id_hash) {
        createToast.info(`Agora trabalhando em ${ws.name}`);
      }
    } else {
      localStorage.removeItem(WS_KEY);
    }
  }, []);

  // As três mutações lançam em caso de erro: as telas que as chamam já tratam
  // com try/catch e toast próprio, e propagar o erro é o que impede um "criado
  // com sucesso" após uma falha.
  const createWorkspace = useCallback(
    async (name: string, description?: string) => {
      const res = await GisFlowService.createWorkspace(
        name, description ?? null, session?.user?.id_hash ?? null,
      );
      if (res.error || !res.data) throw new Error(res.error?.message ?? "Falha ao criar workspace.");
      await reload();
      return res.data;
    },
    [session?.user?.id_hash, reload]
  );

  const updateWorkspace = useCallback(
    async (id_hash: string, name: string, description?: string | null) => {
      const res = await GisFlowService.updateWorkspace(id_hash, name, description ?? null);
      if (res.error || !res.data) throw new Error(res.error?.message ?? "Falha ao atualizar workspace.");
      await reload();
      return res.data;
    },
    [reload]
  );

  const deleteWorkspace = useCallback(
    async (id_hash: string) => {
      const res = await GisFlowService.deleteWorkspace(id_hash);
      if (res.error) throw new Error(res.error.message ?? "Falha ao remover workspace.");
      if (current?.id_hash === id_hash) {
        setCurrentState(null);
        localStorage.removeItem(WS_KEY);
      }
      await reload();
    },
    [current, reload]
  );

  // Sair é o mesmo DELETE de remover membro, com o próprio id. Mora aqui, e não
  // na tela, porque só o context sabe reconciliar o workspace ativo: sair do
  // que estava selecionado deixaria a aplicação inteira apontando para um
  // workspace ao qual o usuário não tem mais acesso.
  const leaveWorkspace = useCallback(
    async (id_hash: string) => {
      const myId = session?.user?.id_hash;
      if (!myId) throw new Error("Sessão inválida.");
      const res = await GisFlowService.removeWorkspaceMember(id_hash, myId);
      if (res.error) throw new Error(res.error.message ?? "Falha ao sair do workspace.");
      if (current?.id_hash === id_hash) {
        setCurrentState(null);
        localStorage.removeItem(WS_KEY);
      }
      await reload();
    },
    [session?.user?.id_hash, current, reload]
  );

  // Sem o memo, cada render deste provider entregava um objeto novo e todo
  // consumidor de useWorkspace() re-renderizava junto — inclusive a sidebar e o
  // canvas, que não dependiam de nada que tivesse mudado.
  const value = useMemo<WorkspaceContextValue>(
    () => ({ workspaces, current, loading, error, canEdit, canExecute, canManage, setCurrent, reload, createWorkspace, updateWorkspace, deleteWorkspace, leaveWorkspace }),
    [workspaces, current, loading, error, canEdit, canExecute, canManage, setCurrent, reload, createWorkspace, updateWorkspace, deleteWorkspace, leaveWorkspace],
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}
