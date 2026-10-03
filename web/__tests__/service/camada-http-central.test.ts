import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, statSync } from "fs"
import { join, relative } from "path"

// The central HTTP layer must not be bypassed.
//
// `/drive`, `/admin/settings` and `/artifacts` built `axios`/`fetch` by hand,
// with an explicit `Authorization: Bearer` — 10 sites. The GisFlowService
// interceptor already attaches the token, so the duplication wasn't just verbosity:
//
//   - MUTATIONS outside the service don't go through `mutar()`, and therefore
//     don't increment `epocaEscrita`. A GET already in flight stayed eligible
//     for coalescing, and the success refetch could receive a list computed
//     BEFORE the write — exactly the bug the epoch exists to close;
//   - each site reimplemented error handling its own way.
//
// This test scans the dashboard code for raw calls. The exceptions are few and
// each one has a recorded reason.

const RAIZ = join(__dirname, "..", "..")

/** Files where a raw HTTP call is correct. */
const EXCECOES: { arquivo: string; motivo: string }[] = [
  {
    // PRE-authentication flows: there's no token for the interceptor to attach,
    // and no cached list to invalidate.
    arquivo: "app/(auth)/",
    motivo: "roda antes da sessão existir",
  },
  {
    // Home's sign-in modal: the login and sign-up forms (and the verification
    // resend) that used to live in app/(auth)/ — the same pre-authentication
    // flow, now over the globe.
    arquivo: "app/components/home/entrada/",
    motivo: "roda antes da sessão existir",
  },
  {
    // Next route handler: runs on the server, it's the API proxy itself.
    arquivo: "app/terra/",
    motivo: "proxy server-side, não é cliente de browser",
  },
  {
    // Server component that fetches a public portal, with no session.
    arquivo: "app/(portal)/",
    motivo: "server component público, sem token",
  },
  {
    // Builds SNIPPETS (Python and JS) for the user to copy and run on their
    // machine. The `fetch`/`Authorization` is inside a template literal: it's
    // displayed text, not code executed by the page.
    arquivo: "app/components/workflow/nodes-configuration/webhook-helper.tsx",
    motivo: "gera snippet de exemplo para o usuário, não executa a chamada",
  },
  {
    // MCP connection snippets (Claude Code, mcp.json, mcp-remote) that the user
    // copies to their machine. The `Authorization: Bearer ${ATLANS_TOKEN}` is
    // displayed text — always with a placeholder, never the real secret — and
    // not code the page executes. The real calls go through the service.
    arquivo: "app/components/tokens/dialog-content/create-token.tsx",
    motivo: "gera snippet de conexão MCP para o usuário, não executa a chamada",
  },
  {
    // The assistant conversation is `text/event-stream`, and axios does NOT
    // deliver a stream in the browser: `onDownloadProgress` returns the
    // accumulated response, which is the same as waiting for the end.
    // `fetch` + `response.body.getReader()` is the only way.
    //
    // Neither of the write-epoch reasons applies: the route mutates nothing
    // that a cached read could get out of sync with (the transcript lives in
    // the server's Redis, and the panel doesn't re-read it via GET), and error
    // handling is specific to a stream — the response has already started when
    // the failure shows up. `GET /assistente/editor/estado` and
    // `DELETE /assistente/editor/conversa`, which are regular requests, go
    // through the service.
    arquivo: "app/hooks/workflow/useAssistenteEditor.ts",
    motivo: "SSE: axios não entrega stream no navegador",
  },
  {
    // The Home assistant is the same case as the assistant: `POST /assistente/conversa`
    // and `POST /conversas/{id}/confirmacoes/{tuid}` are `text/event-stream`. The
    // regular requests (`GET /assistente/estado`, list, replay, layers) go
    // through the service.
    arquivo: "app/hooks/home/useAssistente.ts",
    motivo: "SSE: axios não entrega stream no navegador",
  },
  {
    // The layer's presigned URL points to MinIO (another origin). Sending the
    // platform JWT there would leak it — the raw fetch, without Authorization,
    // is the right choice, as in artifacts/tabela.tsx. The layer itself comes
    // through `GET /assistente/camadas/{id}` via the service.
    arquivo: "app/hooks/home/useCamadas.ts",
    motivo: "fetch cross-origin da URL pré-assinada, sem Authorization",
  },
]

function tsFiles(dir: string, acc: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    if (nome === "node_modules" || nome === ".next") continue
    const caminho = join(dir, nome)
    if (statSync(caminho).isDirectory()) tsFiles(caminho, acc)
    else if (/\.tsx?$/.test(nome)) acc.push(caminho)
  }
  return acc
}

describe("camada HTTP central", () => {
  it("nenhuma página do dashboard chama axios/fetch direto", () => {
    const violacoes: string[] = []

    for (const caminho of tsFiles(join(RAIZ, "app"))) {
      const rel = relative(RAIZ, caminho).replace(/\\/g, "/")
      if (EXCECOES.some(e => rel.startsWith(e.arquivo))) continue

      const fonte = readFileSync(caminho, "utf8")
      fonte.split("\n").forEach((linha, i) => {
        // Ignores comments and example strings shown to the user
        // (webhook-helper builds a snippet with `fetch(` inside a template).
        const withoutComment = linha.replace(/\/\/.*$/, "")
        if (/\baxios\.(get|post|put|patch|delete)\s*\(/.test(withoutComment)
            || /\bawait\s+fetch\s*\(/.test(withoutComment)) {
          violacoes.push(`${rel}:${i + 1} — ${linha.trim()}`)
        }
      })
    }

    expect(violacoes, [
      "chamada HTTP fora do GisFlowService.",
      "Mutações assim não incrementam `epocaEscrita` e reabrem a leitura",
      "pré-mutação. Use o service, ou registre a exceção com o motivo:",
      ...violacoes,
    ].join("\n")).toEqual([])
  })

  it("as exceções registradas ainda existem", () => {
    // An obsolete exception silently loosens the test: the path becomes
    // allowed again for new code.
    for (const { arquivo } of EXCECOES) {
      expect(() => statSync(join(RAIZ, arquivo)), `${arquivo} sumiu — remova a exceção`)
        .not.toThrow()
    }
  })

  it("o Authorization não é montado à mão em nenhuma página", () => {
    const violacoes: string[] = []
    for (const caminho of tsFiles(join(RAIZ, "app"))) {
      const rel = relative(RAIZ, caminho).replace(/\\/g, "/")
      if (EXCECOES.some(e => rel.startsWith(e.arquivo))) continue
      const fonte = readFileSync(caminho, "utf8")
      fonte.split("\n").forEach((linha, i) => {
        const withoutComment = linha.replace(/\/\/.*$/, "")
        if (/Authorization["']?\s*[:=]\s*[`"']Bearer/.test(withoutComment)) {
          violacoes.push(`${rel}:${i + 1} — ${linha.trim()}`)
        }
      })
    }
    expect(violacoes, "o interceptor do GisFlowService já anexa o token").toEqual([])
  })
})
