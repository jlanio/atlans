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

// ----- types -----
// The canonical shape lives in service/types.ts — it is what GisFlowService returns.
// Re-exported here because this context owns the active workspace's state,
// and this is where components import the type from.
export type Workspace = IWorkspace;

// ----- role helpers -----
export const ROLE_ORDER = ["viewer", "editor", "operator", "admin", "owner"] as const;

export function hasMinRole(actual: string | null | undefined, minimum: string): boolean {
  if (!actual) return false;
  const ai = ROLE_ORDER.indexOf(actual as typeof ROLE_ORDER[number]);
  const mi = ROLE_ORDER.indexOf(minimum as typeof ROLE_ORDER[number]);
  if (ai === -1 || mi === -1) return false;
  return ai >= mi;
}

/**
 * Workspaces the current workflow can be moved to.
 *
 * Mirrors the backend's `_assert_can_move`: moving requires admin/owner in the
 * source AND in the destination. It lives here, next to `hasMinRole`, because
 * two screens need the same answer — the menu (to decide whether to offer
 * "Mover") and the dialog (to list the destinations). Written twice, they would
 * silently diverge: the menu would show up and the select would come up empty.
 */
export function moveTargets(workspaces: Workspace[], currentId?: string | null): Workspace[] {
  return workspaces.filter(
    (w) => w.id_hash !== currentId && hasMinRole(w.my_role, "admin"),
  );
}

interface WorkspaceContextValue {
  workspaces: Workspace[];
  /** Currently active workspace */
  current: Workspace | null;
  loading: boolean;
  /**
   * Failure of the last load of the list. Without this, a 401/500 reached the
   * screen indistinguishable from "you have no workspace at all" — someone who
   * had ten saw the invitation to create the first one.
   */
  error: string | null;
  /** Can create/edit/delete workflows, upload and delete in the Drive and artifacts */
  canEdit: boolean;
  /** Can execute workflows and retry */
  canExecute: boolean;
  /** Pode convidar/remover membros, alterar roles, definir executor */
  canManage: boolean;
  setCurrent: (ws: Workspace | null) => void;
  reload: () => Promise<void>;
  createWorkspace: (name: string, description?: string) => Promise<Workspace>;
  updateWorkspace: (id_hash: string, name: string, description?: string | null) => Promise<Workspace>;
  deleteWorkspace: (id_hash: string) => Promise<void>;
  /** Leaves a workspace one is a member of (does not work for the owner). */
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
      // Ensures the token is in the interceptor before the 1st call. SessionSync
      // already does this in the render body (providers.tsx), but repeating it
      // here is idempotent and keeps the initial load from depending on mount
      // order — which is what the old explicit header protected.
      if (accessToken) setAuthToken(accessToken);

      const res = await GisFlowService.listWorkspaces();
      // The service helpers do NOT throw: an error comes as res.error. Without
      // this check a 401/500 would fall into the happy path with data undefined.
      //
      // The previous list is NOT cleared: a periodic refresh that fails should
      // not wipe from the screen what the user was already looking at. The
      // error banner tells what happened; stale data is still better than none.
      if (res.error) {
        setError(res.error.message ?? "Não foi possível carregar os workspaces.");
        return;
      }
      setError(null);

      const data = res.data ?? [];
      setWorkspaces(data);

      // Restores the saved workspace or uses the user's default workspace
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

  // Loads when the Auth.js session is established
  useEffect(() => {
    if (status === "authenticated") {
      reload();
    } else if (status === "unauthenticated") {
      setWorkspaces([]);
      setCurrentState(null);
      setLoading(false);
    }
  }, [status, reload]);

  // Tracks the previous workspace via a ref to decide whether to emit a toast
  // on switching. Avoids re-creating the useCallback on every change (using
  // `current` as a dep would force that). Also avoids a spurious toast on
  // initial hydration: prevId starts null and is only set after the 1st switch.
  const prevIdRef = useRef<string | null>(null);

  const setCurrent = useCallback((ws: Workspace | null) => {
    const prevId = prevIdRef.current;
    prevIdRef.current = ws?.id_hash ?? null;

    setCurrentState(ws);
    if (ws) {
      localStorage.setItem(WS_KEY, ws.id_hash);
      // Toast only when there is a real switch between two workspaces (not on
      // the first set after boot). Signals a change of scope — useful before
      // destructive or creation actions in the new workspace.
      if (prevId && prevId !== ws.id_hash) {
        createToast.info(`Agora trabalhando em ${ws.name}`);
      }
    } else {
      localStorage.removeItem(WS_KEY);
    }
  }, []);

  // The three mutations throw on error: the screens that call them already
  // handle it with try/catch and their own toast, and propagating the error is
  // what prevents a "created successfully" after a failure.
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

  // Leaving is the same DELETE as removing a member, with one's own id. It lives
  // here, and not in the screen, because only the context knows how to
  // reconcile the active workspace: leaving the selected one would leave the
  // whole application pointing at a workspace the user no longer has access to.
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

  // Without the memo, every render of this provider handed out a new object and
  // every useWorkspace() consumer re-rendered along with it — including the
  // sidebar and the canvas, which depended on nothing that had changed.
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
