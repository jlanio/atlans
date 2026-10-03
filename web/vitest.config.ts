import { configDefaults, defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import path from "path"

// A FIXED time zone, and not UTC, for the whole suite. CI runs in UTC, and there
// a time zone bug — the cron hour in the wrong zone, the "tomorrow" of the
// wrong day — slips by unseen: in UTC the local zone and UTC coincide. La Paz
// is UTC−4 all year round (no daylight saving time): the result does not change
// with the date the suite runs on. Here, and not in a `TZ=` in the npm script,
// so it also applies on Windows.
process.env.TZ = "America/La_Paz"

// `--mode nucleo` (`npm run test:nucleo`): the core suite with no extension at
// all, which is what the free distribution runs. `@/extensoes/instaladas`
// becomes the empty list (`extensoes/nenhuma.ts`) and the extensions' tests are
// left out. A mode, and not an environment variable, for the same reason as the
// time zone: so it also applies on Windows.
export default defineConfig(({ mode }) => {
  const nucleo = mode === "nucleo"
  return {
    plugins: [react()],
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./vitest.setup.ts"],
      exclude: nucleo ? [...configDefaults.exclude, "__tests__/extensoes/**"] : configDefaults.exclude,
    },
    resolve: {
      // A ordem importa: o primeiro apelido que casa ganha.
      alias: [
        ...(nucleo
          ? [{ find: "@/extensoes/instaladas", replacement: path.resolve(__dirname, "extensoes/nenhuma.ts") }]
          : []),
        { find: "@", replacement: path.resolve(__dirname, ".") },
      ],
    },
  }
})
