import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Since Next 16 linting is ESLint directly (`next lint` is gone), and
// eslint-config-next already ships as a flat config: no FlatCompat from
// @eslint/eslintrc. `npm run lint` covers the same folders `next lint`
// covered (app/ and lib/), plus the extensions (extensoes/).
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // eslint-config-next 16 brings eslint-plugin-react-hooks 7, whose
    // `recommended` adds the React Compiler rules to the two earlier ones
    // (rules-of-hooks and exhaustive-deps). The ones the code already satisfies
    // stay on. These seven flagged 169 spots in app/ and lib/ during the
    // migration, all predating it (the app does not use the React Compiler),
    // and stay off until a dedicated PR: refs 72, set-state-in-effect 70,
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
  // `next lint` ignored what the build generates on its own; ESLint needs the
  // list. `public/monaco/` and `public/maplibre/` are copied from the packages
  // (copiar-monaco.mjs and copiar-maplibre.mjs).
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "public/monaco/**", "public/maplibre/**"]),
]);

export default eslintConfig;
