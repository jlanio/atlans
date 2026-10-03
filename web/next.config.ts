import type { NextConfig } from "next";

// Frontend CSP, BLOCKING (`Content-Security-Policy`). It ran earlier in
// Report-Only, reporting each violation to POST /api/csp-report (the web
// container's log); the only legitimate thing it would block was Monaco coming
// from jsdelivr — the code editor now loads from `public/monaco/vs`, copied from
// the package at build time (scripts/copiar-monaco.mjs). It keeps reporting:
// each block reaches the same collector, with `disposicao: "enforce"`.
//
// 'unsafe-inline' in script/style is what Next.js requires without a nonce
// (styled-jsx and the App Router chunks). `https:` and `wss:` in
// connect-src/img-src because the tiles (OSM and the installation's satellite
// provider) and the S3 presigned URLs (MINIO_EXTERNAL_ENDPOINT) are deploy
// configuration, and this file is evaluated at image BUILD time, without that
// env — which is also why going back to Report-Only is a new build, not a
// variable.
//
// Only in `next dev`: 'unsafe-eval' (HMR) and `http:`/`ws:` outside the origin —
// there the WebSocket goes straight to the API on another port
// (NEXT_PUBLIC_API_PORT, see utils/env.ts) and MinIO is http://localhost:9000.
// In production all of that goes through the same origin or over HTTPS, and on
// an HTTPS page the browser would block `http:` as mixed content anyway.
//
// Third-party scripts that the EDGE injects into the HTML, outside our build:
// the Cloudflare Web Analytics beacon (`static.cloudflareinsights.com/
// beacon.min.js/<versão>`), inserted into every text/html response of the zone
// while automatic injection is enabled in the Cloudflare dashboard. Only the
// host, no path: the real URL carries the version after `beacon.min.js`, and a
// path without a trailing slash in the CSP matches exactly. Its POST
// (`cloudflareinsights.com/cdn-cgi/rum`) already fits connect-src's `https:`.
// Without Cloudflare in front (closed installation) the entry is harmless.
const edgeScripts = "https://static.cloudflareinsights.com";

const emDev = process.env.NODE_ENV === "development";

const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' ${edgeScripts}${emDev ? " 'unsafe-eval'" : ""}`,
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
  // With `report-to` present Chrome ignores `report-uri` — and it only delivers
  // through the Reporting API over HTTPS. In `next dev` (HTTP) nothing would
  // reach the log; without the directive, `report-uri` sends each report at once.
  ...(emDev ? [] : ["report-to csp"]),
].join("; ");

// Here, and not in the middleware: the middleware's matcher excludes the
// public surface (/login, /register, /share, /api/auth) and, on the routes it
// covers, returns the redirect for users without a session before any header —
// an external scan saw "no header configured". `headers()` applies to every
// server response. No X-XSS-Protection on purpose: the auditor is gone from
// browsers and the `block` mode created cross-origin leaks (XS-Leaks).
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // `geolocation=(self)`: the Home locates the person on the globe (MapLibre's
  // GeolocateControl). Only the origin itself — no embedded third party gets
  // access. Camera and microphone remain denied for everyone.
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(self)" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "Content-Security-Policy", value: csp },
  { key: "Reporting-Endpoints", value: 'csp="/api/csp-report"' },
];

const nextConfig: NextConfig = {
  // `standalone` makes `next build` generate `.next/standalone` with the server
  // and only the modules it actually imports (file tracing). That is what the
  // production image copies — instead of the whole `.next`, which carries
  // 1.4 GB of build cache, and the full `node_modules` installed a second time
  // in the runner.
  output: "standalone",
  transpilePackages: ["@monaco-editor/react"],
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;
