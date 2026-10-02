import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, statSync } from "fs"
import { join, relative } from "path"

// A camada HTTP central não pode ser contornada.
//
// `/drive`, `/admin/settings` e `/artifacts` montavam `axios`/`fetch` na mão,
// com `Authorization: Bearer` explícito — 10 sítios. O interceptor do
// GisFlowService já anexa o token, então a duplicação não era só verbosidade:
//
//   - as MUTAÇÕES fora do service não passam por `mutar()`, e portanto não
//     incrementam `epocaEscrita`. Um GET já em voo continuava elegível para
//     coalescência, e o refetch do sucesso podia receber uma lista calculada
//     ANTES da escrita — exatamente o bug que a época existe para fechar;
//   - cada sítio reimplementava o tratamento de erro à sua maneira.
//
// Este teste varre o código do dashboard em busca de chamadas cruas. As
// exceções são poucas e cada uma tem um motivo registrado.

const RAIZ = join(__dirname, "..", "..")

/** Arquivos onde uma chamada HTTP crua é correta. */
const EXCECOES: { arquivo: string; motivo: string }[] = [
  {
    // Fluxos PRÉ-autenticação: não há token para o interceptor anexar, e não há
    // lista em cache para invalidar.
    arquivo: "app/(auth)/",
    motivo: "roda antes da sessão existir",
  },
  {
    // O modal de entrada da Home: os formulários de login e cadastro (e o
    // reenvio da verificação) que moraram em app/(auth)/ — o mesmo fluxo
    // pré-autenticação, agora sobre o globo.
    arquivo: "app/components/home/entrada/",
    motivo: "roda antes da sessão existir",
  },
  {
    // Route handler do Next: roda no servidor, é o próprio proxy da API.
    arquivo: "app/terra/",
    motivo: "proxy server-side, não é cliente de browser",
  },
  {
    // Server component que busca um portal público, sem sessão.
    arquivo: "app/(portal)/",
    motivo: "server component público, sem token",
  },
  {
    // Monta SNIPPETS (Python e JS) para o usuário copiar e rodar na máquina
    // dele. O `fetch`/`Authorization` está dentro de template literal: é texto
    // exibido, não código executado pela página.
    arquivo: "app/components/workflow/nodes-configuration/webhook-helper.tsx",
    motivo: "gera snippet de exemplo para o usuário, não executa a chamada",
  },
  {
    // Snippets de conexão MCP (Claude Code, mcp.json, mcp-remote) que o usuário
    // copia para a máquina dele. O `Authorization: Bearer ${ATLANS_TOKEN}` é
    // texto exibido — sempre com placeholder, nunca o segredo real — e não
    // código que a página executa. As chamadas de verdade passam pelo service.
    arquivo: "app/components/tokens/dialog-content/create-token.tsx",
    motivo: "gera snippet de conexão MCP para o usuário, não executa a chamada",
  },
  {
    // A conversa do assistente é `text/event-stream`, e o axios NÃO entrega
    // stream no navegador: `onDownloadProgress` devolve a resposta acumulada,
    // que é a mesma coisa que esperar o fim. `fetch` + `response.body.getReader()`
    // é o único caminho.
    //
    // Nenhum dos dois motivos da época de escrita se aplica: a rota não muta
    // nada que uma leitura em cache pudesse desencontrar (o transcrito vive no
    // Redis do servidor, e o painel não o relê por GET), e o tratamento de erro
    // é próprio de um stream — a resposta já começou quando a falha aparece.
    // O `GET /assistente/editor/estado` e o `DELETE /assistente/editor/conversa`, que são
    // requisições normais, passam pelo service.
    arquivo: "app/hooks/workflow/useAssistenteEditor.ts",
    motivo: "SSE: axios não entrega stream no navegador",
  },
  {
    // O assistente da Home é o mesmo caso do assistente: `POST /assistente/conversa` e
    // `POST /conversas/{id}/confirmacoes/{tuid}` são `text/event-stream`. As
    // requisições normais (`GET /assistente/estado`, lista, replay, camadas) passam
    // pelo service.
    arquivo: "app/hooks/home/useAssistente.ts",
    motivo: "SSE: axios não entrega stream no navegador",
  },
  {
    // A URL pré-assinada da camada aponta para o MinIO (outra origem). Mandar o
    // JWT da plataforma para lá seria vazá-lo — o fetch cru, sem Authorization, é
    // a escolha certa, como em artifacts/tabela.tsx. A camada em si vem por
    // `GET /assistente/camadas/{id}` pelo service.
    arquivo: "app/hooks/home/useCamadas.ts",
    motivo: "fetch cross-origin da URL pré-assinada, sem Authorization",
  },
]

function arquivosTs(dir: string, acc: string[] = []): string[] {
  for (const nome of readdirSync(dir)) {
    if (nome === "node_modules" || nome === ".next") continue
    const caminho = join(dir, nome)
    if (statSync(caminho).isDirectory()) arquivosTs(caminho, acc)
    else if (/\.tsx?$/.test(nome)) acc.push(caminho)
  }
  return acc
}

describe("camada HTTP central", () => {
  it("nenhuma página do dashboard chama axios/fetch direto", () => {
    const violacoes: string[] = []

    for (const caminho of arquivosTs(join(RAIZ, "app"))) {
      const rel = relative(RAIZ, caminho).replace(/\\/g, "/")
      if (EXCECOES.some(e => rel.startsWith(e.arquivo))) continue

      const fonte = readFileSync(caminho, "utf8")
      fonte.split("\n").forEach((linha, i) => {
        // Ignora comentários e strings de exemplo mostradas ao usuário
        // (webhook-helper monta um snippet com `fetch(` dentro de template).
        const semComentario = linha.replace(/\/\/.*$/, "")
        if (/\baxios\.(get|post|put|patch|delete)\s*\(/.test(semComentario)
            || /\bawait\s+fetch\s*\(/.test(semComentario)) {
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
    // Uma exceção obsoleta afrouxa o teste em silêncio: o caminho volta a ser
    // permitido para código novo.
    for (const { arquivo } of EXCECOES) {
      expect(() => statSync(join(RAIZ, arquivo)), `${arquivo} sumiu — remova a exceção`)
        .not.toThrow()
    }
  })

  it("o Authorization não é montado à mão em nenhuma página", () => {
    const violacoes: string[] = []
    for (const caminho of arquivosTs(join(RAIZ, "app"))) {
      const rel = relative(RAIZ, caminho).replace(/\\/g, "/")
      if (EXCECOES.some(e => rel.startsWith(e.arquivo))) continue
      const fonte = readFileSync(caminho, "utf8")
      fonte.split("\n").forEach((linha, i) => {
        const semComentario = linha.replace(/\/\/.*$/, "")
        if (/Authorization["']?\s*[:=]\s*[`"']Bearer/.test(semComentario)) {
          violacoes.push(`${rel}:${i + 1} — ${linha.trim()}`)
        }
      })
    }
    expect(violacoes, "o interceptor do GisFlowService já anexa o token").toEqual([])
  })
})
