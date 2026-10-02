import { configDefaults, defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import path from "path"

// Fuso FIXO, e fora de UTC, para a suíte inteira. O CI roda em UTC, e ali um
// erro de fuso — a hora do cron no fuso errado, o "amanhã" do dia errado —
// passa sem ninguém ver: em UTC o fuso local e o UTC coincidem. La Paz é
// UTC−4 o ano todo (sem horário de verão): o resultado não muda com a data em
// que a suíte roda. Aqui, e não num `TZ=` no script do npm, para valer também
// no Windows.
process.env.TZ = "America/La_Paz"

// `--mode nucleo` (o `npm run test:nucleo`): a suíte do núcleo sem extensão
// nenhuma, o que a distribuição livre roda. `@/extensoes/instaladas` vira a
// lista vazia (`extensoes/nenhuma.ts`) e os testes das extensões ficam de fora.
// Um modo, e não uma variável de ambiente, pelo mesmo motivo do fuso: valer
// também no Windows.
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
