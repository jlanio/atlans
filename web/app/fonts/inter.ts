// A Inter do web, servida dos arquivos deste repositório (app/fonts/inter/).
//
// Até aqui ela vinha do `next/font/google`, que baixa o CSS e os arquivos do
// Google Fonts a cada `next build`. Às vezes o Google devolve o endereço de um
// arquivo sem extensão, e o carregador do Next 15 (`/\.(woff|woff2|…)$/.exec(url)[1]`
// no loader.js) quebra com "Cannot read properties of null (reading '1')":
// caía o job Frontend do CI e, pelo mesmo `next build`, a imagem do CD. Com os
// arquivos no repositório, o build não depende de rede nenhuma para a fonte.
//
// Os sete arquivos são os mesmos, byte a byte, que o build baixava (Inter v20
// do Google Fonts, variável, um por faixa de caracteres; origem e SHA-256 em
// inter/LEIA-ME.md), e o CSS reproduz o que o Google servia: uma @font-face por
// faixa, todas com a família "Inter" e o `unicode-range` de cada uma. O
// navegador baixa só as faixas que a página usa, e só a latina é pré-carregada.
// Peso 400–700, como antes: um peso fora disso cai no mais próximo, e não num
// peso novo da fonte variável.
//
// Cada chamada precisa de literais escritos por extenso (o next/font lê os
// argumentos em tempo de compilação), daí a repetição da família.
import localFont from "next/font/local"

// A faixa latina define a variável `--font-inter` (ver globals.css) e a
// "Inter Fallback", a Arial com as métricas ajustadas às da Inter.
export const inter = localFont({
  src: "./inter/inter-latin.woff2",
  weight: "400 700",
  variable: "--font-inter",
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD" },
  ],
})

// As outras faixas só acrescentam @font-face à mesma família.
export const interLatinExt = localFont({
  src: "./inter/inter-latin-ext.woff2",
  weight: "400 700",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF" },
  ],
})

export const interCyrillic = localFont({
  src: "./inter/inter-cyrillic.woff2",
  weight: "400 700",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116" },
  ],
})

export const interCyrillicExt = localFont({
  src: "./inter/inter-cyrillic-ext.woff2",
  weight: "400 700",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F" },
  ],
})

export const interGreek = localFont({
  src: "./inter/inter-greek.woff2",
  weight: "400 700",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+0370-0377, U+037A-037F, U+0384-038A, U+038C, U+038E-03A1, U+03A3-03FF" },
  ],
})

export const interGreekExt = localFont({
  src: "./inter/inter-greek-ext.woff2",
  weight: "400 700",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+1F00-1FFF" },
  ],
})

export const interVietnamese = localFont({
  src: "./inter/inter-vietnamese.woff2",
  weight: "400 700",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB" },
  ],
})
