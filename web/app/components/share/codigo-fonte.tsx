"use client"
// O link para o código-fonte desta instalação (CODIGO_FONTE_URL), lido pelo
// layout raiz e consultado pela tela de entrada e pelo menu da conta. Ver
// lib/codigo-fonte.ts.

import { createContext, useContext, type ReactNode } from "react"

const CodigoFonteContexto = createContext<string | null>(null)

export function CodigoFonteProvider({ url, children }: { url: string | null; children: ReactNode }) {
  return <CodigoFonteContexto.Provider value={url}>{children}</CodigoFonteContexto.Provider>
}

/** A URL do código-fonte desta instalação, ou null quando ela não a declara. */
export function useCodigoFonte(): string | null {
  return useContext(CodigoFonteContexto)
}
