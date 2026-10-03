"use client";

import { SessionProvider, useSession, signOut } from "next-auth/react";
import type { Session } from "next-auth";
import { useEffect } from "react";
import { setAuthToken } from "@/service/GisFlowService";
import { clearCachedHasAgents } from "@/lib/sidebar-cache";
import { destinoDaEntrada } from "@/lib/entrada";
import { NotificationsProvider } from "@/context/NotificationsContext";
import CommandPalette from "@/app/components/command-palette";

/**
 * Syncs the Auth.js session's access_token with the Axios interceptor.
 * - Calls setAuthToken in the render body (synchronous) to avoid a race
 *   condition with child component effects that already make API calls.
 * - Uses useEffect only to detect RefreshTokenExpired and force logout.
 *
 * Exported for tests: the "does not write on the server" guarantee is the kind
 * of invariant that only ever disappears silently.
 */
export function SessionSync() {
  const { data: session } = useSession();

  // SEC: the write is client-ONLY.
  //
  // `setAuthToken` writes to a MODULE variable (`let _token` in
  // GisFlowService), which in the browser is per tab but in Node is per
  // PROCESS, shared by all in-flight requests. Since the SessionProvider started
  // receiving the session resolved on the server, this render body runs during
  // SSR already WITH the real access_token: user A's render wrote A's token and
  // B's, concurrent, overwrote it with B's — any read by the axios interceptor
  // running on the server would pick up the other user's credential.
  //
  // The guard does not cost the latency gain: on the server axios has a relative
  // baseURL ("/terra") and makes no request at all, and on hydration this line
  // runs in the client's first render — therefore before the children's effects
  // that fire the API calls.
  if (typeof window !== "undefined") {
    setAuthToken(session?.user?.access_token ?? null);
  }

  useEffect(() => {
    if (session?.error === "RefreshTokenExpired") {
      // Clears local caches before signOut — keeps the next login (same tab)
      // from starting with state inherited from this user.
      clearCachedHasAgents();
      // Whoever was logged in wants to sign back in: the Home with the modal open.
      signOut({ callbackUrl: destinoDaEntrada("entrar") });
    }
  }, [session?.error]);

  return null;
}

/**
 * `session` comes resolved from the server — in practice, from the MIDDLEWARE,
 * passed to the dashboard layout via header (see SESSION_HEADER in auth.ts).
 * Without it next-auth fires a GET /api/auth/session on mount and `status`
 * stays "loading" until the response — and since every fetch in the app uses
 * `status === "authenticated"` as its trigger, the whole screen waited for that
 * round-trip before requesting the first piece of data. With the initial session
 * the status is born "authenticated" and the fetches go out in the same tick as
 * hydration.
 */
export default function Providers({
  session,
  children,
}: {
  session: Session | null;
  children: React.ReactNode;
}) {
  return (
    <SessionProvider session={session}>
      <SessionSync />
      <NotificationsProvider>
        <CommandPalette />
        {children}
      </NotificationsProvider>
    </SessionProvider>
  );
}
