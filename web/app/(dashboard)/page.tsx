import { headers } from "next/headers"
import HomeView from "../components/home"
import { caminhoInterno, type ModoDeEntrada } from "@/lib/entrada"

// The Home (`/`). It lives in the (dashboard) group — the group contributes no
// segment, so the route is `/`. The root `app/page.tsx` was DELETED (two files for
// the same route break the build). Nothing is read from the environment here: the
// globe's background is MAPA_HIBRIDO_URL (or the satellite, or the streets), which
// the root layout reads on every request and delivers via FundosDoMapaProvider.
//
// The query decides whether the sign-in modal is born open, and on which panel:
// `/?entrar=1` and `/?cadastro=1` are the destinations of /login, /register and
// the middleware (whoever asks for a page without a session lands here, with the
// `callbackUrl` to return later); `/?recuperar=1`, `/?redefinir=1&token=…` and
// `/?verificar=1&token=…` are those of /forgot-password, /reset-password and
// /verify-email — the links that arrive by email.
//
// Read HERE, on the server, and delivered as a prop: HomeView does not need
// `useSearchParams` (nor Suspense, nor one more mock in the tests). Only an
// internal `callbackUrl` passes (open redirect).
//
// The `token` is passed through RAW: the backend is the judge, in the POST. It
// is not stored, does not go into the browsing history beyond the URL itself,
// and leaves the screen as soon as the panel changes.
export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const sp = await searchParams
  const entrada: ModoDeEntrada | undefined =
    "redefinir" in sp ? "redefinir"
      : "recuperar" in sp ? "recuperar"
        : "verificar" in sp ? "verificar"
          : "cadastro" in sp ? "cadastro"
            : "entrar" in sp ? "entrar"
              : undefined
  // The connection's country, when Cloudflare sends it: the globe starts on the
  // region from the browser's time zone and only falls back to the country when
  // the time zone says nothing.
  const paisDaConexao = (await headers()).get("cf-ipcountry")
  return (
    <HomeView
      entrada={entrada}
      tokenDoLink={typeof sp.token === "string" ? sp.token : undefined}
      callbackUrl={caminhoInterno(sp.callbackUrl)}
      paisDaConexao={paisDaConexao}
    />
  )
}
