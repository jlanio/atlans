import { execSync } from "node:child_process"
import path from "node:path"
import { describe, it, expect } from "vitest"

describe("package-lock.json", () => {
  it("está sincronizado com package.json (npm ci deve funcionar)", () => {
    const webDir = path.resolve(__dirname, "..")
    try {
      execSync("npm ci --dry-run --ignore-scripts", {
        cwd: webDir,
        stdio: "pipe",
        timeout: 30_000,
      })
    } catch (err: unknown) {
      const stderr =
        err instanceof Error && "stderr" in err
          ? (err as { stderr: Buffer }).stderr?.toString()
          : String(err)
      expect.fail(
        `package-lock.json desatualizado — rode "npm install" e commite o lockfile.\n\n${stderr}`
      )
    }
  })
})
