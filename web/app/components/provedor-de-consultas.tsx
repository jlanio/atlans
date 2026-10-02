"use client"

import type { ReactNode } from "react"
import { QueryClientProvider, environmentManager, type QueryClient } from "@tanstack/react-query"
import { criarClienteDeConsultas } from "@/lib/consultas"

let doNavegador: QueryClient | undefined

/**
 * No servidor, um cliente por requisição: o processo do Node atende usuários
 * diferentes ao mesmo tempo, e um cache de módulo passaria o dado de um para o
 * outro — o mesmo cuidado do `setAuthToken` no SessionSync. No navegador, um só
 * para a aba. Num `useState` ele se perderia se o primeiro render suspendesse
 * sem um Suspense entre este provedor e quem suspende (a recomendação da
 * biblioteca para o App Router).
 *
 * O cache não passa de uma sessão para outra: o logout (`signOut` com
 * redirecionamento) recarrega a página, e com ela este módulo.
 */
function clienteDeConsultas(): QueryClient {
  if (environmentManager.isServer()) return criarClienteDeConsultas()
  return (doNavegador ??= criarClienteDeConsultas())
}

/** O `QueryClientProvider` das telas do grupo (dashboard) — ver lib/consultas.ts. */
export function ProvedorDeConsultas({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={clienteDeConsultas()}>{children}</QueryClientProvider>
}
