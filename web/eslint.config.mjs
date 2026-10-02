import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Desde o Next 16 o lint é o ESLint direto (o `next lint` saiu), e o
// eslint-config-next já vem em config flat: sem o FlatCompat do
// @eslint/eslintrc. O `npm run lint` cobre as mesmas pastas que o `next lint`
// cobria (app/ e lib/), mais as extensões (extensoes/).
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // O eslint-config-next 16 traz o eslint-plugin-react-hooks 7, cujo
    // `recommended` soma às duas regras de antes (rules-of-hooks e
    // exhaustive-deps) as do React Compiler. As que o código já cumpre ficam
    // ligadas. Estas sete acusaram 169 pontos em app/ e lib/ na migração, todos
    // anteriores a ela (o app não usa o React Compiler), e ficam desligadas até
    // um PR próprio: refs 72, set-state-in-effect 70,
    // preserve-manual-memoization 10, immutability 7, incompatible-library 6,
    // use-memo 2, purity 2.
    rules: {
      "react-hooks/refs": "off",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/preserve-manual-memoization": "off",
      "react-hooks/immutability": "off",
      "react-hooks/incompatible-library": "off",
      "react-hooks/use-memo": "off",
      "react-hooks/purity": "off",
    },
  },
  // O `next lint` ignorava sozinho o que o build gera; o ESLint precisa da
  // lista. `public/monaco/` e `public/maplibre/` são copiados dos pacotes
  // (copiar-monaco.mjs e copiar-maplibre.mjs).
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "public/monaco/**", "public/maplibre/**"]),
]);

export default eslintConfig;
