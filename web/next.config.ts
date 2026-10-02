import type { NextConfig } from "next";

// CSP do frontend, BLOQUEANTE (`Content-Security-Policy`). Rodou antes em
// Report-Only, relatando cada violação em POST /api/csp-report (o log do
// container web); o que ela barraria de legítimo era o Monaco vindo do
// jsdelivr — o editor de código agora carrega de `public/monaco/vs`, copiado do
// pacote no build (scripts/copiar-monaco.mjs). Continua relatando: cada bloqueio
// chega ao mesmo coletor, com `disposicao: "enforce"`.
//
// 'unsafe-inline' em script/style é o que o Next.js exige sem nonce (styled-jsx
// e os chunks do App Router). `https:` e `wss:` em connect-src/img-src porque os
// tiles (o OSM e o provedor de satélite da instalação) e as URLs pré-assinadas do S3 (MINIO_EXTERNAL_ENDPOINT)
// são configuração de deploy, e este arquivo é avaliado no BUILD da imagem, sem
// esse env — por isso também voltar para Report-Only é um build novo, não uma
// variável.
//
// Só no `next dev`: 'unsafe-eval' (HMR) e `http:`/`ws:` fora da origem — lá o
// WebSocket vai direto à API em outra porta (NEXT_PUBLIC_API_PORT, ver
// utils/env.ts) e o MinIO é http://localhost:9000. Em produção tudo isso passa
// pela mesma origem ou por HTTPS, e numa página HTTPS o navegador barraria
// `http:` como conteúdo misto de qualquer forma.
//
// Scripts de terceiros que a BORDA injeta no HTML, fora do nosso build: o
// beacon do Cloudflare Web Analytics (`static.cloudflareinsights.com/
// beacon.min.js/<versão>`), inserido em toda resposta text/html da zona
// enquanto a injeção automática estiver ligada no painel da Cloudflare. Só o
// host, sem caminho: a URL real leva a versão depois de `beacon.min.js`, e um
// caminho sem barra final na CSP casa exato. O POST dele
// (`cloudflareinsights.com/cdn-cgi/rum`) já cabe no `https:` do connect-src.
// Sem Cloudflare na frente (instalação fechada) a entrada é inócua.
const scriptsDaBorda = "https://static.cloudflareinsights.com";

const emDev = process.env.NODE_ENV === "development";

const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' ${scriptsDaBorda}${emDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: https:${emDev ? " http:" : ""}`,
  "font-src 'self' data:",
  `connect-src 'self' https: wss:${emDev ? " http: ws:" : ""}`,
  "worker-src 'self' blob:",
  "media-src 'self' blob:",
  "object-src 'none'",
  "frame-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "report-uri /api/csp-report",
  // Com `report-to` presente o Chrome ignora o `report-uri` — e ele só entrega
  // pelo Reporting API em HTTPS. No `next dev` (HTTP) nada chegaria ao log;
  // sem a diretiva, o `report-uri` manda cada relato na hora.
  ...(emDev ? [] : ["report-to csp"]),
].join("; ");

// Aqui, e não no middleware: o matcher do middleware exclui a superfície
// pública (/login, /register, /share, /api/auth) e, nas rotas que cobre,
// devolve o redirect de quem não tem sessão antes de qualquer header — um
// scan externo via "nenhum header configurado". `headers()` vale para toda
// resposta do servidor. Sem X-XSS-Protection de propósito: o auditor saiu
// dos navegadores e o modo `block` criava vazamentos entre origens (XS-Leaks).
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // `geolocation=(self)`: a Home localiza a pessoa no globo (o GeolocateControl
  // do MapLibre). Só a própria origem — nenhum terceiro embutido ganha o acesso.
  // Câmera e microfone seguem negados para todos.
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(self)" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "Content-Security-Policy", value: csp },
  { key: "Reporting-Endpoints", value: 'csp="/api/csp-report"' },
];

const nextConfig: NextConfig = {
  // `standalone` faz o `next build` gerar `.next/standalone` com o servidor e
  // só os módulos que ele de fato importa (file tracing). É o que a imagem de
  // produção copia — em vez do `.next` inteiro, que carrega 1,4 GB de cache de
  // build, e do `node_modules` completo instalado uma segunda vez no runner.
  output: "standalone",
  transpilePackages: ["@monaco-editor/react"],
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;
