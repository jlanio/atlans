"use client"

import type { ReactNode } from "react"
import { QueryClientProvider, environmentManager, type QueryClient } from "@tanstack/react-query"
import { criarClienteDeConsultas } from "@/lib/consultas"

let doNavegador: QueryClient | undefined

/**
 * On the server, one client per request: the Node process serves different
 * users at the same time, and a module cache would pass one user's data to
 * another — the same care as `setAuthToken` in SessionSync. In the browser, a
 * single one for the tab. In a `useState` it would be lost if the first render
 * suspended without a Suspense between this provider and whoever suspends (the
 * library's recommendation for the App Router).
 *
 * The cache does not carry over from one session to another: logout (`signOut`
 * with redirect) reloads the page, and this module with it.
 */
function clienteDeConsultas(): QueryClient {
  if (environmentManager.isServer()) return criarClienteDeConsultas()
  return (doNavegador ??= criarClienteDeConsultas())
}

/** The `QueryClientProvider` for the (dashboard) group's screens — see lib/consultas.ts. */
export function ProvedorDeConsultas({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={clienteDeConsultas()}>{children}</QueryClientProvider>
}
