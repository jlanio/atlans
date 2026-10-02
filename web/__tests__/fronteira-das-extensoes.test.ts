/**
 * O núcleo do web anda sem as extensões (`web/extensoes/<nome>`), e a
 * distribuição livre não as traz. É o par do teste do servidor
 * (`tests/unit/test_fronteira_das_extensoes.py`), com dois jeitos de quebrar:
 *
 *   IMPORT     um arquivo do núcleo (ou um teste dele) importa uma extensão
 *              pelo nome, ou a cita num `vi.mock`;
 *   REGISTRO   no modo núcleo (`npm run test:nucleo`), o registro não está
 *              vazio — e a suíte inteira estaria testando outra coisa.
 *
 * O núcleo fala com as extensões só pelo registro (`@/extensoes`). Quem lista
 * as presentes é `extensoes/instaladas.ts`, o único arquivo autorizado a
 * citá-las pelo nome; a distribuição livre o troca pela lista vazia. A prova
 * definitiva é o job «Frontend sem extensões» do CI, que APAGA as extensões
 * (`scripts/sem_extensoes.sh`) e roda tipos, testes e build; este teste é o
 * aviso rápido, na suíte de todo dia.
 *
 * Os especificadores saem da árvore sintática do TypeScript, e não de uma
 * expressão regular: um comentário entre o `from` e o caminho, ou o comentário
 * mágico de um `import()`, passava pela regex.
 */
import fs from "node:fs"
import path from "node:path"
import ts from "typescript"
import { describe, expect, it } from "vitest"

const WEB = path.resolve(__dirname, "..")
const PASTAS_FORA = new Set(["node_modules", ".next", "public", "out", "build", "coverage"])
const CODIGO = /\.(ts|tsx|js|jsx|mjs|cjs)$/
const METODOS_DO_VI = new Set(["mock", "doMock", "unmock", "importActual", "importMock"])

/** `extensoes/<nome>/…` e `__tests__/extensoes/…` são das extensões. */
function daExtensao(relativo: string): boolean {
  const partes = relativo.split("/")
  return (partes[0] === "extensoes" && partes.length > 2) || (partes[0] === "__tests__" && partes[1] === "extensoes")
}

// Este arquivo cita extensões de mentira de propósito, nos exemplos do detector.
const ESTE = path.relative(WEB, __filename).split(path.sep).join("/")

function arquivosDoNucleo(pasta = WEB): string[] {
  const achados: string[] = []
  for (const entrada of fs.readdirSync(pasta, { withFileTypes: true })) {
    if (PASTAS_FORA.has(entrada.name)) continue
    const caminho = path.join(pasta, entrada.name)
    const relativo = path.relative(WEB, caminho).split(path.sep).join("/")
    if (daExtensao(relativo) || relativo === "extensoes/instaladas.ts" || relativo === ESTE) continue
    if (entrada.isDirectory()) achados.push(...arquivosDoNucleo(caminho))
    else if (CODIGO.test(entrada.name)) achados.push(relativo)
  }
  return achados
}

/** Os módulos que um arquivo cita: imports e exports (de tipo também), `import()`,
 *  `import("…")` em tipo, `require` e os `vi.mock` e parentes. */
export function especificadores(texto: string, arquivo: string): string[] {
  const tipo = /\.[jt]sx$/.test(arquivo) ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  const fonte = ts.createSourceFile(arquivo, texto, ts.ScriptTarget.Latest, false, tipo)
  const achados: string[] = []
  const literal = (no: ts.Node | undefined) =>
    no && (ts.isStringLiteral(no) || ts.isNoSubstitutionTemplateLiteral(no)) ? no.text : undefined
  const anotar = (no: ts.Node | undefined) => {
    const texto = literal(no)
    if (texto !== undefined) achados.push(texto)
  }
  const visitar = (no: ts.Node): void => {
    if (ts.isImportDeclaration(no) || ts.isExportDeclaration(no)) {
      anotar(no.moduleSpecifier)
    } else if (ts.isImportEqualsDeclaration(no) && ts.isExternalModuleReference(no.moduleReference)) {
      anotar(no.moduleReference.expression)
    } else if (ts.isImportTypeNode(no) && ts.isLiteralTypeNode(no.argument)) {
      anotar(no.argument.literal)
    } else if (ts.isCallExpression(no)) {
      const alvo = no.expression
      const doVi = ts.isPropertyAccessExpression(alvo) && ts.isIdentifier(alvo.expression)
        && alvo.expression.text === "vi" && METODOS_DO_VI.has(alvo.name.text)
      const require = ts.isIdentifier(alvo) && alvo.text === "require"
      if (alvo.kind === ts.SyntaxKind.ImportKeyword || doVi || require) anotar(no.arguments[0])
    }
    ts.forEachChild(no, visitar)
  }
  visitar(fonte)
  return achados
}

/** O que o núcleo pode alcançar dentro de `extensoes/`: o registro, que são os
 *  arquivos soltos na raiz da pasta (as subpastas são as extensões, e o corte
 *  da distribuição livre apaga só elas). A lista das instaladas fica de fora:
 *  só o próprio registro a lê. */
const DO_REGISTRO = new Set([
  "extensoes",
  ...fs.readdirSync(path.join(WEB, "extensoes"), { withFileTypes: true })
    .filter(e => e.isFile() && CODIGO.test(e.name))
    .map(e => `extensoes/${e.name.replace(CODIGO, "")}`)
    .filter(alvo => alvo !== "extensoes/instaladas"),
])

/** Os alvos de `extensoes/` que um arquivo do núcleo cita sem poder. */
export function citacoesProibidas(texto: string, arquivo: string): string[] {
  const proibidas: string[] = []
  for (const especificador of especificadores(texto, arquivo)) {
    let alvo: string
    if (especificador.startsWith("@/")) alvo = especificador.slice(2)
    else if (especificador.startsWith(".")) alvo = path.posix.join(path.posix.dirname(arquivo), especificador)
    else continue
    alvo = alvo.replace(/\.(tsx?|jsx?|mjs)$/, "").replace(/\/index$/, "")
    if (alvo !== "extensoes" && !alvo.startsWith("extensoes/")) continue
    if (DO_REGISTRO.has(alvo)) continue
    // O registro, e só ele, lê a lista das instaladas.
    if (arquivo === "extensoes/index.ts" && alvo === "extensoes/instaladas") continue
    proibidas.push(especificador)
  }
  return proibidas
}

describe("a fronteira entre o núcleo e as extensões", () => {
  it("o detector enxerga os jeitos de citar uma extensão", () => {
    const ouro = "ouro" // uma extensão de mentira
    const ve = (codigo: string, arquivo = "app/a.tsx") => citacoesProibidas(codigo, arquivo)

    expect(ve(`import x from "@/extensoes/${ouro}/store"`)).toHaveLength(1)
    expect(ve(`vi.mock("@/extensoes/${ouro}/servico", () => ({}))`, "__tests__/a.test.ts")).toHaveLength(1)
    expect(ve(`await vi.importMock("@/extensoes/${ouro}/store")`, "__tests__/a.test.ts")).toHaveLength(1)
    expect(ve(`import x from "../../extensoes/${ouro}"`, "app/components/a.tsx")).toHaveLength(1)
    expect(ve(`import { y } from /* comentário */ "../../extensoes/${ouro}/formatos"`, "app/components/a.tsx")).toHaveLength(1)
    expect(ve(`const m = import(/* webpackChunkName: "x" */ "../../extensoes/${ouro}/admin")`, "app/components/a.tsx")).toHaveLength(1)
    expect(ve(`import type { T } from "@/extensoes/${ouro}/tipos"`)).toHaveLength(1)
    expect(ve(`type T = typeof import("@/extensoes/${ouro}")`)).toHaveLength(1)
    expect(ve(`export { a } from "@/extensoes/${ouro}"`)).toHaveLength(1)
    expect(ve(`import { INSTALADAS } from "@/extensoes/instaladas"`)).toHaveLength(1)

    expect(ve(`import { EXTENSOES } from "@/extensoes"`)).toEqual([])
    expect(ve(`export { LimiteDaExtensao } from "./limite"`, "extensoes/index.ts")).toEqual([])
    expect(ve(`import type { ExtensaoDoWeb } from "@/extensoes/tipos"`)).toEqual([])
    expect(ve(`// import x from "@/extensoes/${ouro}"\nconst a = 1`)).toEqual([])
    expect(ve(`import { INSTALADAS } from "@/extensoes/instaladas"`, "extensoes/index.ts")).toEqual([])
  })

  it("nenhum arquivo do núcleo cita uma extensão pelo nome", () => {
    const arquivos = arquivosDoNucleo()
    // O teste enxerga o núcleo: a casca e o registro estão na lista.
    expect(arquivos).toContain("app/components/sidebar/user-sidebar.tsx")
    expect(arquivos).toContain("extensoes/index.ts")
    expect(arquivos).not.toContain(ESTE)

    const erros = Object.fromEntries(
      arquivos
        .map(a => [a, citacoesProibidas(fs.readFileSync(path.join(WEB, a), "utf8"), a)] as const)
        .filter(([, citadas]) => citadas.length > 0),
    )
    expect(erros, "o núcleo fala com as extensões só por `@/extensoes`; os testes delas vão em __tests__/extensoes/").toEqual({})
  })

  it.runIf(import.meta.env.MODE === "nucleo")("no modo núcleo, o registro está vazio", async () => {
    const { EXTENSOES } = await import("@/extensoes")
    expect(EXTENSOES).toEqual([])
  })
})
