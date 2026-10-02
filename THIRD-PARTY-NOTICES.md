# Avisos de terceiros

O Atlans é software livre, sob a GNU Affero General Public License, versão 3
(AGPL-3.0-only); o texto está em [LICENSE](LICENSE). Ele usa obras de
terceiros, cada uma sob a licença que os autores dela escolheram. Esta página
diz quais são e sob que licença; o texto completo de cada licença vai junto com
a obra.

<!-- Gerado por scripts/avisos_de_terceiros.py a partir dos locks; não edite à
     mão, rode o script. -->

## Neste repositório

| Obra | Onde | Licença | Texto da licença |
|---|---|---|---|
| Inter, a fonte do web (The Inter Project Authors), servida como arquivo à parte | `web/app/fonts/inter/` | OFL-1.1 | `web/app/fonts/inter/OFL.txt` |
| shadcn/ui, os componentes de base da interface (shadcn), adaptados | `web/app/components/ui/`, `web/hooks/use-mobile.ts`, `desktop/src/renderer/components/ui/` | MIT | `web/app/components/ui/LICENSE.shadcn-ui.txt`, `desktop/src/renderer/components/ui/LICENSE.shadcn-ui.txt` |
| Monokai, o tema do editor de código, portado do monaco-themes (Brijesh Bittu) | `web/app/components/workflow/nodes-configuration/fields/monaco-code-editor.tsx` | MIT | `web/app/components/workflow/nodes-configuration/fields/LICENSE.monaco-themes.txt` |

## Dados de terceiros no repositório

`catalogo/geoservicos/` reúne metadados de serviços WFS públicos de muitas
instituições (nomes, títulos e esquemas de camadas, colhidos do GetCapabilities
e do DescribeFeatureType de cada um). Esse conteúdo é de cada instituição e
segue os termos do serviço de origem; a organização em notas, as finalidades e
as dicas são do Atlans. Ver `catalogo/README.md`.

## Nos artefatos montados

Quem monta e distribui um artefato distribui, junto com o Atlans, o que vai
dentro dele, e com isso as licenças dessas obras. O que cada um leva:

- **As imagens da API e do executor** (`Dockerfile.api`, `Dockerfile.executor`)
  levam a imagem base (o Debian do `python:3.12-slim`, com a licença de cada
  pacote do sistema em `/usr/share/doc/`), o Python, a [LICENSE](LICENSE) e
  este arquivo, e os pacotes do PyPI das listas abaixo, inteiros: a licença de
  cada um fica em `site-packages/<pacote>.dist-info/`.
- **A imagem do web** (`web/Dockerfile.ui`) leva o Alpine do `node:24-alpine`,
  o Node.js, a [LICENSE](LICENSE) e este arquivo (em `/app/`), e o que o build
  do Next junta (a pasta `standalone`): o código dos pacotes do npm, mas não os
  arquivos de licença deles. Quem distribui essa imagem entrega junto os textos
  das licenças dos pacotes do npm. O editor de código serve o Monaco da própria
  origem, com a `LICENSE` e o `ThirdPartyNotices.txt` dele em `/monaco/`; o
  worker do MapLibre vai com a `LICENSE.txt` dele em `/maplibre/`.
- **O app desktop** (`desktop/`) leva o Electron, que o instalador acompanha de
  `LICENSE.electron.txt` e `LICENSES.chromium.html`; o Python do
  python-build-standalone (PSF-2.0, com as bibliotecas que ele embute e o
  `LICENSE.txt` dele); os pacotes do executor, com as licenças; e, em
  `resources/`, a LICENSE e este arquivo. O que o build junta do npm vai sem os
  arquivos de licença, como no web.
- **Os serviços que o `docker-compose.yml` sobe** (Valkey, MinIO, step-ca e
  Traefik) vêm das imagens oficiais de cada projeto, baixadas na instalação,
  com as licenças delas. O PostgreSQL fica fora do compose.

## Pacotes

Os pacotes abaixo não moram neste repositório: a instalação os baixa do npm e
do PyPI, nas versões travadas nos locks. A licença é a que o pacote declara, e
o texto completo vem com ele, em `node_modules/<pacote>/` ou em
`site-packages/<pacote>.dist-info/`. Do npm, entra o que vai para a produção,
e também o que o build junta mesmo sendo de desenvolvimento (`tailwindcss` e
`tw-animate-css`, no CSS).

### Resumo

| Licença | npm | PyPI |
|---|--:|--:|
| MIT | 187 | 52 |
| ISC | 31 | 1 |
| Apache-2.0 | 17 | 12 |
| BSD-3-Clause | 5 | 23 |
| LGPL-3.0-or-later | 10 | 1 |
| BSD-2-Clause | 2 | 2 |
| Apache-2.0 AND LGPL-3.0-or-later | 3 | — |
| MPL-2.0 | — | 2 |
| PSF-2.0 | — | 2 |
| (MIT OR Apache-2.0) | 1 | — |
| (MPL-2.0 OR Apache-2.0) | 1 | — |
| 0BSD | 1 | — |
| Apache-2.0 AND BSD-3-Clause | — | 1 |
| Apache-2.0 AND LGPL-3.0-or-later AND MIT | 1 | — |
| Apache-2.0 OR BSD-2-Clause | — | 1 |
| Apache-2.0 OR BSD-3-Clause | — | 1 |
| Apache-2.0 OR MIT | — | 1 |
| BlueOak-1.0.0 | 1 | — |
| BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | — | 1 |
| CC-BY-4.0 | 1 | — |
| MIT AND ISC | 1 | — |
| MIT AND PSF-2.0 | — | 1 |
| MIT-0 | — | 1 |
| MIT-CMU | — | 1 |
| Python-2.0 | 1 | — |
| Unlicense | — | 1 |
| **Total** | **263** | **104** |

### Para revisar

Nada: cada licença acima está entre as compatíveis com a AGPL-3.0 (`COMPATIVEIS`, em `scripts/avisos_de_terceiros.py`).

### npm

Dos locks `web/package-lock.json` (web), `desktop/package-lock.json` (desktop).

| Pacote | Versão | Licença | Usado por |
|---|---|---|---|
| `@auth/core` | 0.41.3 | ISC | web |
| `@dagrejs/dagre` | 3.1.1 | MIT | web |
| `@dagrejs/graphlib` | 4.0.5 | MIT | web |
| `@emnapi/runtime` | 1.11.3 | MIT | web |
| `@floating-ui/core` | 1.7.1 | MIT | web |
| `@floating-ui/dom` | 1.7.1 | MIT | web |
| `@floating-ui/react-dom` | 2.1.3 | MIT | web |
| `@floating-ui/utils` | 0.2.9 | MIT | web |
| `@hookform/resolvers` | 5.9.1 | MIT | web |
| `@img/colour` | 1.1.0 | MIT | web |
| `@img/sharp-darwin-arm64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-darwin-x64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-freebsd-wasm32` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-libvips-darwin-arm64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-darwin-x64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linux-arm` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linux-arm64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linux-ppc64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linux-riscv64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linux-s390x` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linux-x64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linuxmusl-arm64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-libvips-linuxmusl-x64` | 1.3.3 | LGPL-3.0-or-later | web |
| `@img/sharp-linux-arm` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-linux-arm64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-linux-ppc64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-linux-riscv64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-linux-s390x` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-linux-x64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-linuxmusl-arm64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-linuxmusl-x64` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-wasm32` | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | web |
| `@img/sharp-webcontainers-wasm32` | 0.35.4 | Apache-2.0 | web |
| `@img/sharp-win32-arm64` | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later | web |
| `@img/sharp-win32-ia32` | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later | web |
| `@img/sharp-win32-x64` | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later | web |
| `@mapbox/jsonlint-lines-primitives` | 2.0.3 | MIT | web |
| `@mapbox/point-geometry` | 1.1.0 | ISC | web |
| `@mapbox/tiny-sdf` | 2.2.0 | BSD-2-Clause | web |
| `@mapbox/unitbezier` | 1.0.0 | BSD-2-Clause | web |
| `@mapbox/vector-tile` | 3.0.0 | BSD-3-Clause | web |
| `@maplibre/geojson-vt` | 6.1.1 | ISC | web |
| `@maplibre/maplibre-gl-style-spec` | 26.4.4 | ISC | web |
| `@maplibre/mlt` | 1.3.0 | (MIT OR Apache-2.0) | web |
| `@maplibre/vt-pbf` | 4.3.2 | MIT | web |
| `@monaco-editor/loader` | 1.7.0 | MIT | web |
| `@monaco-editor/react` | 4.7.0 | MIT | web |
| `@next/env` | 16.3.5 | MIT | web |
| `@next/swc-darwin-arm64` | 16.3.5 | MIT | web |
| `@next/swc-darwin-x64` | 16.3.5 | MIT | web |
| `@next/swc-linux-arm64-gnu` | 16.3.5 | MIT | web |
| `@next/swc-linux-arm64-musl` | 16.3.5 | MIT | web |
| `@next/swc-linux-x64-gnu` | 16.3.5 | MIT | web |
| `@next/swc-linux-x64-musl` | 16.3.5 | MIT | web |
| `@next/swc-win32-arm64-msvc` | 16.3.5 | MIT | web |
| `@next/swc-win32-x64-msvc` | 16.3.5 | MIT | web |
| `@panva/hkdf` | 1.2.1 | MIT | web |
| `@radix-ui/number` | 1.1.3 | MIT | web |
| `@radix-ui/primitive` | 1.1.7 | MIT | web |
| `@radix-ui/react-arrow` | 1.1.15 | MIT | web |
| `@radix-ui/react-avatar` | 1.2.6 | MIT | web |
| `@radix-ui/react-checkbox` | 1.3.11 | MIT | web |
| `@radix-ui/react-collection` | 1.1.15 | MIT | web |
| `@radix-ui/react-compose-refs` | 1.1.5 | MIT | web, desktop |
| `@radix-ui/react-context` | 1.2.2 | MIT | web |
| `@radix-ui/react-dialog` | 1.1.23 | MIT | web |
| `@radix-ui/react-direction` | 1.1.4 | MIT | web |
| `@radix-ui/react-dismissable-layer` | 1.1.19 | MIT | web |
| `@radix-ui/react-dropdown-menu` | 2.1.24 | MIT | web |
| `@radix-ui/react-focus-guards` | 1.1.6 | MIT | web |
| `@radix-ui/react-focus-scope` | 1.1.16 | MIT | web |
| `@radix-ui/react-id` | 1.1.4 | MIT | web |
| `@radix-ui/react-label` | 2.1.15 | MIT | web |
| `@radix-ui/react-menu` | 2.1.24 | MIT | web |
| `@radix-ui/react-popper` | 1.3.7 | MIT | web |
| `@radix-ui/react-portal` | 1.1.17 | MIT | web |
| `@radix-ui/react-presence` | 1.1.10 | MIT | web |
| `@radix-ui/react-primitive` | 2.1.10 | MIT | web |
| `@radix-ui/react-roving-focus` | 1.1.19 | MIT | web |
| `@radix-ui/react-select` | 2.3.7 | MIT | web |
| `@radix-ui/react-separator` | 1.1.15 | MIT | web |
| `@radix-ui/react-slot` | 1.3.3 | MIT | web, desktop |
| `@radix-ui/react-switch` | 1.3.7 | MIT | web |
| `@radix-ui/react-tooltip` | 1.2.16 | MIT | web |
| `@radix-ui/react-use-callback-ref` | 1.1.4 | MIT | web |
| `@radix-ui/react-use-controllable-state` | 1.2.6 | MIT | web |
| `@radix-ui/react-use-effect-event` | 0.0.5 | MIT | web |
| `@radix-ui/react-use-is-hydrated` | 0.1.3 | MIT | web |
| `@radix-ui/react-use-layout-effect` | 1.1.4 | MIT | web |
| `@radix-ui/react-use-previous` | 1.1.4 | MIT | web |
| `@radix-ui/react-use-rect` | 1.1.4 | MIT | web |
| `@radix-ui/react-use-size` | 1.1.4 | MIT | web |
| `@radix-ui/react-visually-hidden` | 1.2.11 | MIT | web |
| `@radix-ui/rect` | 1.1.3 | MIT | web |
| `@reduxjs/toolkit` | 2.11.2 | MIT | web |
| `@standard-schema/spec` | 1.1.0 | MIT | web |
| `@standard-schema/utils` | 0.3.0 | MIT | web |
| `@swc/helpers` | 0.5.23 | Apache-2.0 | web |
| `@tanstack/query-core` | 5.104.0 | MIT | web |
| `@tanstack/react-query` | 5.104.0 | MIT | web |
| `@tanstack/react-virtual` | 3.14.13 | MIT | web |
| `@tanstack/virtual-core` | 3.17.11 | MIT | web |
| `@types/d3-array` | 3.2.2 | MIT | web |
| `@types/d3-color` | 3.1.3 | MIT | web |
| `@types/d3-drag` | 3.0.7 | MIT | web |
| `@types/d3-ease` | 3.0.2 | MIT | web |
| `@types/d3-interpolate` | 3.0.4 | MIT | web |
| `@types/d3-path` | 3.1.1 | MIT | web |
| `@types/d3-scale` | 4.0.9 | MIT | web |
| `@types/d3-selection` | 3.0.11 | MIT | web |
| `@types/d3-shape` | 3.1.8 | MIT | web |
| `@types/d3-time` | 3.0.4 | MIT | web |
| `@types/d3-timer` | 3.0.2 | MIT | web |
| `@types/d3-transition` | 3.0.9 | MIT | web |
| `@types/d3-zoom` | 3.0.8 | MIT | web |
| `@types/geojson` | 7946.0.16 | MIT | web |
| `@types/react` | 19.3.0 | MIT | web, desktop |
| `@types/react-dom` | 19.3.0 | MIT | web |
| `@types/trusted-types` | 2.0.7 | MIT | web |
| `@types/use-sync-external-store` | 0.0.6 | MIT | web |
| `@xyflow/react` | 12.11.6 | MIT | web |
| `@xyflow/system` | 0.0.82 | MIT | web |
| `agent-base` | 6.0.2 | MIT | web |
| `argparse` | 2.0.1 | Python-2.0 | desktop |
| `aria-hidden` | 1.2.6 | MIT | web |
| `asynckit` | 0.4.0 | MIT | web |
| `axios` | 1.20.0 | MIT | web |
| `baseline-browser-mapping` | 2.11.23 | Apache-2.0 | web |
| `bidi-js` | 1.1.0 | MIT | web |
| `builder-util-runtime` | 9.7.0 | MIT | desktop |
| `call-bind-apply-helpers` | 1.0.2 | MIT | web |
| `caniuse-lite` | 1.0.30001810 | CC-BY-4.0 | web |
| `class-variance-authority` | 0.7.1 | Apache-2.0 | web, desktop |
| `classcat` | 5.0.5 | MIT | web |
| `client-only` | 0.0.1 | MIT | web |
| `clsx` | 2.1.1 | MIT | web, desktop |
| `combined-stream` | 1.0.8 | MIT | web |
| `csstype` | 3.2.3 | MIT | web, desktop |
| `d3-array` | 3.2.4 | ISC | web |
| `d3-color` | 3.1.0 | ISC | web |
| `d3-dispatch` | 3.0.1 | ISC | web |
| `d3-drag` | 3.0.0 | ISC | web |
| `d3-ease` | 3.0.1 | BSD-3-Clause | web |
| `d3-format` | 3.1.2 | ISC | web |
| `d3-interpolate` | 3.0.1 | ISC | web |
| `d3-path` | 3.1.0 | ISC | web |
| `d3-scale` | 4.0.2 | ISC | web |
| `d3-selection` | 3.0.0 | ISC | web |
| `d3-shape` | 3.2.0 | ISC | web |
| `d3-time` | 3.1.0 | ISC | web |
| `d3-time-format` | 4.1.0 | ISC | web |
| `d3-timer` | 3.0.1 | ISC | web |
| `d3-transition` | 3.0.1 | ISC | web |
| `d3-zoom` | 3.0.0 | ISC | web |
| `dayjs` | 1.11.23 | MIT | web |
| `debug` | 4.4.3 | MIT | web, desktop |
| `decimal.js-light` | 2.5.1 | MIT | web |
| `delayed-stream` | 1.0.0 | MIT | web |
| `detect-libc` | 2.1.2 | Apache-2.0 | web |
| `detect-node-es` | 1.1.0 | MIT | web |
| `dompurify` | 3.4.8 | (MPL-2.0 OR Apache-2.0) | web |
| `dunder-proto` | 1.0.1 | MIT | web |
| `earcut` | 3.2.3 | ISC | web |
| `electron-updater` | 6.8.9 | MIT | desktop |
| `es-define-property` | 1.0.1 | MIT | web |
| `es-errors` | 1.3.0 | MIT | web |
| `es-object-atoms` | 1.1.1 | MIT | web |
| `es-set-tostringtag` | 2.1.0 | MIT | web |
| `es-toolkit` | 1.45.1 | MIT | web |
| `eventemitter3` | 5.0.4 | MIT | web |
| `follow-redirects` | 1.16.0 | MIT | web |
| `form-data` | 4.0.6 | MIT | web |
| `framer-motion` | 13.4.0 | MIT | web |
| `fs-extra` | 10.1.0 | MIT | desktop |
| `function-bind` | 1.1.2 | MIT | web |
| `get-intrinsic` | 1.3.0 | MIT | web |
| `get-nonce` | 1.0.1 | MIT | web |
| `get-proto` | 1.0.1 | MIT | web |
| `gl-matrix` | 3.4.4 | MIT | web |
| `gopd` | 1.2.0 | MIT | web |
| `graceful-fs` | 4.2.11 | ISC | desktop |
| `has-symbols` | 1.1.0 | MIT | web |
| `has-tostringtag` | 1.0.2 | MIT | web |
| `hasown` | 2.0.4 | MIT | web |
| `https-proxy-agent` | 5.0.1 | MIT | web |
| `immer` | 11.1.18 | MIT | web |
| `internmap` | 2.0.3 | ISC | web |
| `jose` | 6.2.12 | MIT | web |
| `js-cookie` | 3.0.8 | MIT | web |
| `js-yaml` | 4.3.1 | MIT | desktop |
| `json-edit-react` | 1.30.2 | MIT | web |
| `json-stringify-pretty-compact` | 4.0.0 | MIT | web |
| `jsonfile` | 6.2.1 | MIT | desktop |
| `kdbush` | 4.1.0 | ISC | web |
| `lazy-val` | 1.0.5 | MIT | desktop |
| `lodash.escaperegexp` | 4.1.2 | MIT | desktop |
| `lodash.isequal` | 4.5.0 | MIT | desktop |
| `lucide-react` | 1.47.0 | ISC | web |
| `maplibre-gl` | 6.10.0 | BSD-3-Clause | web |
| `marked` | 14.0.0 | MIT | web |
| `math-intrinsics` | 1.1.0 | MIT | web |
| `mime-db` | 1.52.0 | MIT | web |
| `mime-types` | 2.1.35 | MIT | web |
| `minimist` | 1.2.8 | MIT | web |
| `monaco-editor` | 0.56.0 | MIT | web |
| `motion-dom` | 13.3.0 | MIT | web |
| `motion-utils` | 13.3.0 | MIT | web |
| `ms` | 2.1.3 | MIT | web, desktop |
| `murmurhash-js` | 1.0.0 | MIT | web |
| `nanoid` | 3.3.19 | MIT | web |
| `next` | 16.3.5 | MIT | web |
| `next-auth` | 5.0.0-beta.32 | ISC | web |
| `next-themes` | 0.4.6 | MIT | web |
| `oauth4webapi` | 3.8.8 | MIT | web |
| `pbf` | 5.1.2 | BSD-3-Clause | web |
| `picocolors` | 1.1.1 | ISC | web |
| `postcss` | 8.5.23 | MIT | web |
| `potpack` | 2.1.0 | ISC | web |
| `preact` | 10.24.3 | MIT | web |
| `preact-render-to-string` | 6.5.11 | MIT | web |
| `protocol-buffers-schema` | 3.6.1 | MIT | web |
| `proxy-from-env` | 2.1.0 | MIT | web |
| `quickselect` | 3.0.0 | ISC | web |
| `react` | 19.3.0 | MIT | web, desktop |
| `react-dom` | 19.3.0 | MIT | web, desktop |
| `react-hook-form` | 7.88.0 | MIT | web |
| `react-icons` | 5.7.0 | MIT | web, desktop |
| `react-is` | 19.1.0 | MIT | web |
| `react-redux` | 9.2.0 | MIT | web |
| `react-remove-scroll` | 2.7.2 | MIT | web |
| `react-remove-scroll-bar` | 2.3.8 | MIT | web |
| `react-style-singleton` | 2.2.3 | MIT | web |
| `recharts` | 3.10.1 | MIT | web |
| `redux` | 5.0.1 | MIT | web |
| `redux-thunk` | 3.1.0 | MIT | web |
| `require-from-string` | 2.0.2 | MIT | web |
| `reselect` | 5.2.0 | MIT | web |
| `resolve-protobuf-schema` | 2.1.0 | MIT | web |
| `sax` | 1.6.1 | BlueOak-1.0.0 | desktop |
| `scheduler` | 0.28.0 | MIT | web, desktop |
| `semver` | 7.7.4 | ISC | desktop |
| `semver` | 7.8.5 | ISC | web |
| `sharp` | 0.35.4 | Apache-2.0 | web |
| `sonner` | 2.0.8 | MIT | web |
| `source-map-js` | 1.2.1 | BSD-3-Clause | web |
| `state-local` | 1.0.7 | MIT | web |
| `styled-jsx` | 5.1.6 | MIT | web |
| `tailwind-merge` | 3.7.0 | MIT | web, desktop |
| `tailwindcss` | 4.3.3 | MIT | web, desktop |
| `tiny-invariant` | 1.3.3 | MIT | web |
| `tiny-typed-emitter` | 2.1.0 | MIT | desktop |
| `tinyqueue` | 3.0.0 | ISC | web |
| `tslib` | 2.8.1 | 0BSD | web |
| `tw-animate-css` | 1.4.0 | MIT | web, desktop |
| `universalify` | 2.0.1 | MIT | desktop |
| `use-callback-ref` | 1.3.3 | MIT | web |
| `use-sidecar` | 1.1.3 | MIT | web |
| `use-sync-external-store` | 1.5.0 | MIT | web |
| `uuid` | 14.0.2 | MIT | web |
| `victory-vendor` | 37.3.6 | MIT AND ISC | web |
| `zod` | 4.6.5 | MIT | web |
| `zustand` | 4.5.7 | MIT | web |
| `zustand` | 5.0.15 | MIT | web |

### Os ícones do react-icons

O `react-icons` é MIT, mas cada conjunto de ícones mantém a licença do projeto de onde veio. Os conjuntos que o web e o app desktop usam:

| Conjunto | Projeto | Licença |
|---|---|---|
| `react-icons/bs` | Bootstrap Icons | MIT |
| `react-icons/fa` | Font Awesome 5 Free (Fonticons, Inc., https://fontawesome.com) | CC-BY-4.0 |
| `react-icons/fi` | Feather | MIT |
| `react-icons/gr` | Grommet Icons | Apache-2.0 |
| `react-icons/io5` | Ionicons 5 | MIT |
| `react-icons/lu` | Lucide | ISC |
| `react-icons/md` | Material Design icons (Google) | Apache-2.0 |
| `react-icons/pi` | Phosphor Icons | MIT |
| `react-icons/si` | Simple Icons | CC0-1.0 |
| `react-icons/tb` | Tabler Icons | MIT |

Os ícones do Font Awesome Free são de Fonticons, Inc. (https://fontawesome.com), sob a Creative Commons Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/). Os logos de outros produtos (do Simple Icons, como o do PostgreSQL e o do MySQL) só identificam esses produtos: as marcas são dos donos delas.

### PyPI

Dos locks `requirements.txt` (API), `executor/requirements-full.txt` (executor), `executor/requirements.txt` (executor mínimo).

| Pacote | Versão | Licença | Usado por |
|---|---|---|---|
| `aiosqlite` | 0.22.1 | MIT | API |
| `alembic` | 1.20.0 | MIT | API |
| `annotated-doc` | 0.0.5 | MIT | API |
| `annotated-types` | 0.8.0 | MIT | API |
| `anyio` | 4.15.1 | MIT | API, executor, executor mínimo |
| `apscheduler` | 3.11.3 | MIT | API |
| `asyncpg` | 0.31.0 | Apache-2.0 | API, executor |
| `attrs` | 26.1.0 | MIT | API, executor |
| `bcrypt` | 5.0.0 | Apache-2.0 | API |
| `boto3` | 1.43.98 | Apache-2.0 | API, executor |
| `botocore` | 1.43.103 | Apache-2.0 | API, executor |
| `cachetools` | 7.2.0 | MIT | API, executor |
| `certifi` | 2026.7.22 | MPL-2.0 | API, executor, executor mínimo |
| `cffi` | 2.1.1 | MIT-0 | API, executor, executor mínimo |
| `charset-normalizer` | 3.5.1 | MIT | API, executor, executor mínimo |
| `click` | 8.5.0 | BSD-3-Clause | API |
| `contourpy` | 1.4.0 | BSD-3-Clause | API, executor |
| `croniter` | 6.2.4 | MIT | API, executor |
| `cryptography` | 50.0.1 | Apache-2.0 OR BSD-3-Clause | API, executor, executor mínimo |
| `cycler` | 0.12.1 | BSD-3-Clause | API, executor |
| `deprecated` | 1.3.1 | MIT | API |
| `dnspython` | 2.8.0 | ISC | API |
| `email-validator` | 2.3.0 | Unlicense | API |
| `fastapi` | 0.141.1 | MIT | API |
| `fonttools` | 4.65.0 | MIT | API, executor |
| `geoalchemy2` | 0.20.0 | MIT | API, executor |
| `geographiclib` | 2.1 | MIT | API, executor |
| `geopandas` | 1.1.4 | BSD-3-Clause | API, executor |
| `geopy` | 2.5.0 | MIT | API, executor |
| `greenlet` | 3.5.5 | MIT AND PSF-2.0 | API, executor |
| `h11` | 0.16.0 | MIT | API, executor, executor mínimo |
| `httpcore` | 1.0.9 | BSD-3-Clause | API, executor, executor mínimo |
| `httpcore2` | 2.12.0 | BSD-3-Clause | API |
| `httptools` | 0.8.0 | MIT | API |
| `httpx` | 0.28.1 | BSD-3-Clause | API, executor, executor mínimo |
| `httpx2` | 2.12.0 | BSD-3-Clause | API |
| `idna` | 3.19 | BSD-3-Clause | API, executor, executor mínimo |
| `iniconfig` | 2.3.0 | MIT | API |
| `jinja2` | 3.1.6 | BSD-3-Clause | API, executor |
| `jmespath` | 1.1.0 | MIT | API, executor |
| `jsonschema` | 4.26.0 | MIT | API, executor |
| `jsonschema-specifications` | 2025.9.1 | MIT | API, executor |
| `kiwisolver` | 1.5.1 | BSD-3-Clause | API, executor |
| `limits` | 5.8.0 | MIT | API |
| `lxml` | 6.1.3 | BSD-3-Clause | API, executor, executor mínimo |
| `mako` | 1.4.1 | MIT | API |
| `markdown-it-py` | 4.2.0 | MIT | API, executor, executor mínimo |
| `markupsafe` | 3.0.3 | BSD-3-Clause | API, executor |
| `matplotlib` | 3.11.2 | PSF-2.0 | API, executor |
| `mcp` | 2.2.0 | MIT | API |
| `mcp-types` | 2.2.0 | MIT | API |
| `mdurl` | 0.1.2 | MIT | API, executor, executor mínimo |
| `nh3` | 0.3.7 | MIT | API |
| `numpy` | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | API, executor |
| `opentelemetry-api` | 1.44.0 | Apache-2.0 | API |
| `owslib` | 0.36.0 | BSD-3-Clause | API, executor, executor mínimo |
| `packaging` | 26.3 | Apache-2.0 OR BSD-2-Clause | API, executor |
| `pandas` | 2.3.3 | BSD-3-Clause | API, executor |
| `pathspec` | 1.1.1 | MPL-2.0 | API, executor |
| `pillow` | 12.3.0 | MIT-CMU | API, executor |
| `pluggy` | 1.6.0 | MIT | API |
| `psutil` | 7.2.2 | BSD-3-Clause | API, executor, executor mínimo |
| `psycopg2-binary` | 2.9.13 | LGPL-3.0-or-later | API, executor |
| `pyarrow` | 25.0.1 | Apache-2.0 | API, executor |
| `pycparser` | 3.0 | BSD-3-Clause | API, executor, executor mínimo |
| `pydantic` | 2.13.5 | MIT | API |
| `pydantic-core` | 2.46.5 | MIT | API |
| `pygments` | 2.21.0 | BSD-2-Clause | API, executor, executor mínimo |
| `pyjwt` | 2.14.0 | MIT | API |
| `pyogrio` | 0.13.0 | MIT | API, executor |
| `pyparsing` | 3.3.2 | MIT | API, executor |
| `pyproj` | 3.8.0 | MIT | API, executor |
| `pytest` | 9.1.1 | MIT | API |
| `pytest-asyncio` | 1.4.0 | Apache-2.0 | API |
| `python-dateutil` | 2.9.0.post0 | Apache-2.0 AND BSD-3-Clause | API, executor, executor mínimo |
| `python-dotenv` | 1.2.3 | BSD-3-Clause | API, executor, executor mínimo |
| `python-multipart` | 0.0.32 | Apache-2.0 | API |
| `pytz` | 2026.3.post1 | MIT | API, executor |
| `pyyaml` | 6.0.3 | MIT | API, executor, executor mínimo |
| `redis` | 8.1.0 | MIT | API, executor |
| `referencing` | 0.37.0 | MIT | API, executor |
| `requests` | 2.34.2 | Apache-2.0 | API, executor, executor mínimo |
| `resend` | 2.47.0 | MIT | API |
| `rich` | 15.0.0 | MIT | API, executor, executor mínimo |
| `rpds-py` | 2026.6.3 | MIT | API, executor |
| `s3transfer` | 0.19.2 | Apache-2.0 | API, executor |
| `shapely` | 2.1.2 | BSD-3-Clause | API, executor |
| `six` | 1.17.0 | MIT | API, executor, executor mínimo |
| `slowapi` | 0.1.10 | MIT | API |
| `sqlalchemy` | 2.0.54 | MIT | API, executor |
| `sse-starlette` | 3.4.11 | BSD-3-Clause | API |
| `starlette` | 1.6.0 | BSD-3-Clause | API |
| `truststore` | 0.10.4 | MIT | API |
| `typing-extensions` | 4.16.0 | PSF-2.0 | API, executor, executor mínimo |
| `typing-inspection` | 0.4.4 | MIT | API |
| `tzdata` | 2026.4 | Apache-2.0 | API, executor |
| `tzlocal` | 5.4.4 | MIT | API |
| `urllib3` | 2.7.0 | MIT | API, executor, executor mínimo |
| `uvicorn` | 0.53.0 | BSD-3-Clause | API |
| `uvloop` | 0.22.1 | Apache-2.0 OR MIT | API |
| `watchdog` | 6.0.0 | Apache-2.0 | API, executor |
| `watchfiles` | 1.2.0 | MIT | API |
| `websockets` | 17.1 | BSD-3-Clause | API, executor, executor mínimo |
| `wrapt` | 2.4.1 | BSD-2-Clause | API |

### Bibliotecas nativas dentro das wheels

Algumas wheels do PyPI trazem bibliotecas compiladas, com licença própria, junto do código do pacote. A coluna «Licença» acima é a do pacote Python; o que mais vai dentro:

| Pacote | Bibliotecas | Licença | Texto |
|---|---|---|---|
| `shapely` | GEOS | LGPL-2.1 | `shapely-*.dist-info/licenses/LICENSE_GEOS` |
| `pyogrio` | GDAL, com as bibliotecas que ele usa | MIT, com partes sob outras licenças livres | https://gdal.org/en/stable/license.html |
| `pyproj` | PROJ, com as bibliotecas que ele usa (SQLite, libcurl, libtiff) | MIT; as outras, as delas | `pyproj-*.dist-info/licenses/LICENSE_proj` (o PROJ) |
| `numpy` | OpenBLAS e LAPACK; o runtime do GCC (libgfortran) | BSD-3-Clause; GPL-3.0-or-later WITH GCC-exception-3.1 | `numpy-*.dist-info/licenses/LICENSE.txt` |
| `pillow` | as bibliotecas de imagem (libjpeg, libpng, libtiff, libwebp, FreeType, HarfBuzz e outras) | as de cada uma | `pillow-*.dist-info/licenses/LICENSE` |
| `psycopg2-binary` | libpq e OpenSSL, e o que o libpq usa: krb5, OpenLDAP, Cyrus SASL, PCRE, libselinux, libxcrypt | PostgreSQL; Apache-2.0; MIT (krb5), OpenLDAP Public License, BSD (SASL, PCRE), domínio público (libselinux), LGPL-2.1 (libxcrypt) | https://www.postgresql.org/about/licence/ e https://openssl-library.org/source/license/; as demais, nos projetos de cada uma |
| `cryptography` | OpenSSL, ligado estaticamente ao módulo Rust | Apache-2.0 | https://openssl-library.org/source/license/ |
| `uvloop` | libuv, ligado estaticamente | MIT | https://github.com/libuv/libuv/blob/v1.x/LICENSE |
| `pyarrow` | Arrow C++ e as bibliotecas que ele embute (zstd, lz4, snappy, brotli, re2, thrift e outras) | Apache-2.0; as outras, as delas | `pyarrow-*.dist-info/licenses/LICENSE.txt` e `NOTICE.txt` |
| `lxml` | libxml2 e libxslt | MIT | `lxml-*.dist-info/licenses/LICENSES.txt` |
