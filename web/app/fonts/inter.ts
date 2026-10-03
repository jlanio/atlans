// The web app's Inter, served from files in this repository (app/fonts/inter/).
//
// Until now it came from `next/font/google`, which downloads the CSS and the
// Google Fonts files on every `next build`. Sometimes Google returns the URL of a
// file with no extension, and the Next 15 loader (`/\.(woff|woff2|…)$/.exec(url)[1]`
// in loader.js) breaks with "Cannot read properties of null (reading '1')":
// the CI Frontend job failed and, through the same `next build`, so did the CD
// image. With the files in the repository, the build needs no network for the font.
//
// The seven files are the same, byte for byte, as the ones the build downloaded
// (Inter v20 from Google Fonts, variable, one per character range; origin and
// SHA-256 in inter/README.md), and the CSS reproduces what Google served: one
// @font-face per range, all with the "Inter" family and each one's
// `unicode-range`. The browser downloads only the ranges the page uses, and only
// the Latin one is preloaded. Weight 400–700, as before: a weight outside that
// falls back to the nearest one, not to a new weight of the variable font.
//
// Each call needs literals written out in full (next/font reads the arguments
// at compile time), hence the repeated family.
import localFont from "next/font/local"

// The Latin range defines the `--font-inter` variable (see globals.css) and
// "Inter Fallback", Arial with its metrics adjusted to Inter's.
export const inter = localFont({
  src: "./inter/inter-latin.woff2",
  weight: "400 700",
  variable: "--font-inter",
  declarations: [
    { prop: "font-family", value: "Inter" },
    { prop: "unicode-range", value: "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD" },
  ],
})

// The other ranges only add @font-face rules to the same family.
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
