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
 * Sincroniza o access_token da sessão Auth.js com o interceptor Axios.
 * - Chama setAuthToken no corpo do render (síncrono) para evitar race condition
 *   com effects de componentes filhos que já fazem chamadas à API.
 * - Usa useEffect apenas para detectar RefreshTokenExpired e forçar logout.
 *
 * Exportado para teste: a garantia de "no servidor não escreve" é o tipo de
 * invariante que só some silenciosamente.
 */
export function SessionSync() {
  const { data: session } = useSession();

  // SEG: a escrita é EXCLUSIVA do cliente.
  //
  // `setAuthToken` grava numa variável de MÓDULO (`let _token` em
  // GisFlowService), que no browser é por-aba mas no Node é por-PROCESSO,
  // compartilhada por todas as requisições em voo. Desde que o SessionProvider
  // passou a receber a sessão resolvida no servidor, este corpo de render passa
  // a rodar no SSR já COM o access_token real: o render do usuário A gravava o
  // token de A e o de B, concorrente, sobrescrevia com o de B — qualquer leitura
  // pelo interceptor do axios rodando no servidor pegaria a credencial do outro
  // usuário.
  //
  // O guard não custa o ganho de latência: no servidor o axios tem baseURL
  // relativo ("/terra") e não faz requisição nenhuma, e na hidratação esta linha
  // roda no primeiro render do cliente — antes, portanto, dos effects dos filhos
  // que disparam as chamadas à API.
  if (typeof window !== "undefined") {
    setAuthToken(session?.user?.access_token ?? null);
  }

  useEffect(() => {
    if (session?.error === "RefreshTokenExpired") {
      // Limpa caches locais antes do signOut — evita que o próximo login
      // (mesma aba) parta com estado herdado deste usuário.
      clearCachedHasAgents();
      // Quem estava logado quer voltar a entrar: a Home com o modal aberto.
      signOut({ callbackUrl: destinoDaEntrada("entrar") });
    }
  }, [session?.error]);

  return null;
}

/**
 * `session` vem resolvida do servidor — na prática, do MIDDLEWARE, repassada ao
 * layout do dashboard por cabeçalho (ver SESSION_HEADER em auth.ts).
 * Sem ela o next-auth dispara um GET /api/auth/session na montagem e `status`
 * fica "loading" até a resposta — e como todo fetch da aplicação usa
 * `status === "authenticated"` como gatilho, a tela inteira esperava esse
 * round-trip antes de pedir o primeiro dado. Com a sessão inicial o status já
 * nasce "authenticated" e os fetches saem no mesmo tick da hidratação.
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
