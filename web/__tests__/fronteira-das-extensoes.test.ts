/**
 * The web core runs without the extensions (`web/extensoes/<nome>`), and the
 * free distribution doesn't ship them. It's the counterpart of the server test
 * (`tests/unit/test_fronteira_das_extensoes.py`), with two ways to break:
 *
 *   IMPORT     a core file (or one of its tests) imports an extension by
 *              name, or mentions it in a `vi.mock`;
 *   REGISTRY   in core mode (`npm run test:nucleo`), the registry isn't
 *              empty — and the whole suite would be testing something else.
 *
 * The core talks to the extensions only through the registry (`@/extensoes`).
 * What lists the present ones is `extensoes/instaladas.ts`, the only file
 * allowed to name them; the free distribution swaps it for the empty list. The
 * definitive proof is the CI job «Frontend sem extensões» (frontend without
 * extensions), which DELETES the extensions (`scripts/sem_extensoes.sh`) and
 * runs types, tests and build; this test is the quick warning, in the everyday
 * suite.
 *
 * The specifiers come from the TypeScript syntax tree, not from a regular
 * expression: a comment between the `from` and the path, or the magic comment
 * of an `import()`, got past the regex.
 */
import fs from "node:fs"
import path from "node:path"
import ts from "typescript"
import { describe, expect, it } from "vitest"

const WEB = path.resolve(__dirname, "..")
const EXCLUDED_DIRS = new Set(["node_modules", ".next", "public", "out", "build", "coverage"])
const CODE_FILE = /\.(ts|tsx|js|jsx|mjs|cjs)$/
const VI_METHODS = new Set(["mock", "doMock", "unmock", "importActual", "importMock"])

/** `extensoes/<nome>/…` and `__tests__/extensoes/…` belong to the extensions. */
function isFromExtension(relativo: string): boolean {
  const partes = relativo.split("/")
  return (partes[0] === "extensoes" && partes.length > 2) || (partes[0] === "__tests__" && partes[1] === "extensoes")
}

// This file mentions fake extensions on purpose, in the detector's examples.
const THIS_FILE = path.relative(WEB, __filename).split(path.sep).join("/")

function coreFiles(pasta = WEB): string[] {
  const achados: string[] = []
  for (const entrada of fs.readdirSync(pasta, { withFileTypes: true })) {
    if (EXCLUDED_DIRS.has(entrada.name)) continue
    const caminho = path.join(pasta, entrada.name)
    const relativo = path.relative(WEB, caminho).split(path.sep).join("/")
    if (isFromExtension(relativo) || relativo === "extensoes/instaladas.ts" || relativo === THIS_FILE) continue
    if (entrada.isDirectory()) achados.push(...coreFiles(caminho))
    else if (CODE_FILE.test(entrada.name)) achados.push(relativo)
  }
  return achados
}

/** The modules a file references: imports and exports (type-only too), `import()`,
 *  `import("…")` in types, `require` and `vi.mock` and its relatives. */
export function specifiers(texto: string, arquivo: string): string[] {
  const tipo = /\.[jt]sx$/.test(arquivo) ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  const fonte = ts.createSourceFile(arquivo, texto, ts.ScriptTarget.Latest, false, tipo)
  const achados: string[] = []
  const literal = (no: ts.Node | undefined) =>
    no && (ts.isStringLiteral(no) || ts.isNoSubstitutionTemplateLiteral(no)) ? no.text : undefined
  const collect = (no: ts.Node | undefined) => {
    const texto = literal(no)
    if (texto !== undefined) achados.push(texto)
  }
  const visit = (no: ts.Node): void => {
    if (ts.isImportDeclaration(no) || ts.isExportDeclaration(no)) {
      collect(no.moduleSpecifier)
    } else if (ts.isImportEqualsDeclaration(no) && ts.isExternalModuleReference(no.moduleReference)) {
      collect(no.moduleReference.expression)
    } else if (ts.isImportTypeNode(no) && ts.isLiteralTypeNode(no.argument)) {
      collect(no.argument.literal)
    } else if (ts.isCallExpression(no)) {
      const alvo = no.expression
      const doVi = ts.isPropertyAccessExpression(alvo) && ts.isIdentifier(alvo.expression)
        && alvo.expression.text === "vi" && VI_METHODS.has(alvo.name.text)
      const require = ts.isIdentifier(alvo) && alvo.text === "require"
      if (alvo.kind === ts.SyntaxKind.ImportKeyword || doVi || require) collect(no.arguments[0])
    }
    ts.forEachChild(no, visit)
  }
  visit(fonte)
  return achados
}

/** What the core may reach inside `extensoes/`: the registry, which is the
 *  loose files at the folder's root (the subfolders are the extensions, and
 *  the free distribution's cut deletes only them). The list of installed ones
 *  is excluded: only the registry itself reads it. */
const DO_REGISTRO = new Set([
  "extensoes",
  ...fs.readdirSync(path.join(WEB, "extensoes"), { withFileTypes: true })
    .filter(e => e.isFile() && CODE_FILE.test(e.name))
    .map(e => `extensoes/${e.name.replace(CODE_FILE, "")}`)
    .filter(alvo => alvo !== "extensoes/instaladas"),
])

/** The `extensoes/` targets that a core file references without being allowed to. */
export function forbiddenImports(texto: string, arquivo: string): string[] {
  const forbidden: string[] = []
  for (const specifier of specifiers(texto, arquivo)) {
    let alvo: string
    if (specifier.startsWith("@/")) alvo = specifier.slice(2)
    else if (specifier.startsWith(".")) alvo = path.posix.join(path.posix.dirname(arquivo), specifier)
    else continue
    alvo = alvo.replace(/\.(tsx?|jsx?|mjs)$/, "").replace(/\/index$/, "")
    if (alvo !== "extensoes" && !alvo.startsWith("extensoes/")) continue
    if (DO_REGISTRO.has(alvo)) continue
    // The registry, and only it, reads the list of installed ones.
    if (arquivo === "extensoes/index.ts" && alvo === "extensoes/instaladas") continue
    forbidden.push(specifier)
  }
  return forbidden
}

describe("a fronteira entre o núcleo e as extensões", () => {
  it("o detector enxerga os jeitos de citar uma extensão", () => {
    const ouro = "ouro" // a fake extension
    const ve = (codigo: string, arquivo = "app/a.tsx") => forbiddenImports(codigo, arquivo)

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
    const arquivos = coreFiles()
    // The test sees the core: the shell and the registry are in the list.
    expect(arquivos).toContain("app/components/sidebar/user-sidebar.tsx")
    expect(arquivos).toContain("extensoes/index.ts")
    expect(arquivos).not.toContain(THIS_FILE)

    const erros = Object.fromEntries(
      arquivos
        .map(a => [a, forbiddenImports(fs.readFileSync(path.join(WEB, a), "utf8"), a)] as const)
        .filter(([, cited]) => cited.length > 0),
    )
    expect(erros, "o núcleo fala com as extensões só por `@/extensoes`; os testes delas vão em __tests__/extensoes/").toEqual({})
  })

  it.runIf(import.meta.env.MODE === "nucleo")("no modo núcleo, o registro está vazio", async () => {
    const { EXTENSOES } = await import("@/extensoes")
    expect(EXTENSOES).toEqual([])
  })
})
