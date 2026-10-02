import { headers } from "next/headers"
import HomeView from "../components/home"
import { caminhoInterno, type ModoDeEntrada } from "@/lib/entrada"

// A Home (`/`). Vive no grupo (dashboard) — o grupo não contribui segmento,
// então a rota é `/`. O `app/page.tsx` da raiz foi APAGADO (dois arquivos para
// a mesma rota quebram o build). Nada é lido do ambiente aqui: o fundo do
// globo é o MAPA_HIBRIDO_URL (ou o satélite, ou as ruas), que o layout raiz lê
// a cada pedido e entrega pelo FundosDoMapaProvider.
//
// A query decide se o modal de entrada nasce aberto, e em qual painel:
// `/?entrar=1` e `/?cadastro=1` são os destinos de /login, /register e do
// middleware (quem pede uma página sem sessão cai aqui, com o `callbackUrl`
// para voltar depois); `/?recuperar=1`, `/?redefinir=1&token=…` e
// `/?verificar=1&token=…` são os de /forgot-password, /reset-password e
// /verify-email — os links que chegam por e-mail.
//
// Lida AQUI, no servidor, e entregue como prop: a HomeView não precisa de
// `useSearchParams` (nem de Suspense, nem de mais um mock nos testes). Só um
// `callbackUrl` interno passa (open redirect).
//
// O `token` é repassado CRU: quem julga é o backend, no POST. Ele não é
// guardado, não vai para o histórico de navegação além da própria URL, e some
// da tela assim que o painel troca.
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
  // O país da conexão, quando a Cloudflare o manda: o globo começa na região
  // pelo fuso do navegador e só cai no país quando o fuso não diz nada.
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
