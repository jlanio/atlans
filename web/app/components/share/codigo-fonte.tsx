"use client"
// The link to this installation's source code (CODIGO_FONTE_URL), read by the
// root layout and consulted by the sign-in screen and the account menu. See
// lib/codigo-fonte.ts.

import { createContext, useContext, type ReactNode } from "react"

const SourceCodeContext = createContext<string | null>(null)

export function SourceCodeProvider({ url, children }: { url: string | null; children: ReactNode }) {
  return <SourceCodeContext.Provider value={url}>{children}</SourceCodeContext.Provider>
}

/** The URL of this installation's source code, or null when it doesn't declare one. */
export function useSourceCode(): string | null {
  return useContext(SourceCodeContext)
}
