// web/lib/nome-na-tela.ts
//
// The name the screen shows: the sidebar wordmark, the entry screen's header
// and the tab title.
//
// The code shows "Atlans", the project's name. The form with the domain is the
// holder's installation, and it is their trademark (TRADEMARKS.md):
// whoever distributes a modified version or offers it as a service changes the
// name. That is why it belongs to the INSTALLATION, not to the code: it comes
// from NOME_NA_TELA in the web server's environment, read by the root layout on
// every request and passed to the client via context
// (`app/components/share/nome-na-tela.tsx`), like the source code link and the
// map basemaps. NEXT_PUBLIC_* would not work: it would bake the value in at
// build time, and the web image is the same for every installation.

export const NOME_PADRAO = "Atlans"

/** NOME_NA_TELA cleaned up, or "Atlans" when empty, too long or with an odd character. */
export function lerNomeNaTelaDoAmbiente(env: Record<string, string | undefined>): string {
  const nome = (env.NOME_NA_TELA ?? "").replace(/\s+/g, " ").trim()
  if (!nome || nome.length > 40 || /[\p{C}<>]/u.test(nome)) return NOME_PADRAO
  return nome
}
