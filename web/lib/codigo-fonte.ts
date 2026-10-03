// web/lib/codigo-fonte.ts
//
// The link to the source code of the version running on this installation.
//
// The AGPL (section 13 of the LICENSE) requires that whoever uses the
// installation over the network can obtain its source code — the official one,
// or the fork of whoever modified it. The address belongs to the INSTALLATION,
// not to the code: it comes from CODIGO_FONTE_URL in the web server's
// environment, read by the root layout on every request and passed to the
// client via context (`app/components/share/codigo-fonte.tsx`), like the map
// basemaps. NEXT_PUBLIC_* would not work: it would bake the value in at build
// time, and the web image is the same for every installation.
//
// Without the variable, no link appears: the code ships no address at all.

/** The URL from CODIGO_FONTE_URL, or null when empty or without an http(s) scheme. */
export function lerCodigoFonteDoAmbiente(env: Record<string, string | undefined>): string | null {
  const url = (env.CODIGO_FONTE_URL ?? "").trim()
  return /^https?:\/\/\S+$/i.test(url) ? url : null
}
