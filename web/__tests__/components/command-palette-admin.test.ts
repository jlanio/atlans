/**
 * Itens de admin da paleta de comandos. Dashboard, Usuários e Configurações são
 * rotas de administrador do sistema — antes a paleta os oferecia a todos e só o
 * middleware barrava, terminando em redirect. Agora carregam a marca `admin` e
 * `itensVisiveis` os esconde de quem não é admin.
 *
 * Hoje a marca não muda o que ninguém vê: quem não é admin só alcança a Home
 * (`proxy.ts`), onde a paleta não abre para ele. Ela protege o dia em que uma
 * rota for reaberta a quem não é admin — e por isso continua testada.
 *
 * Testado no nível puro (a função e a lista, sem render): a regra de visibilidade
 * não depende de sessão nem de DOM.
 */
import { describe, it, expect, vi } from "vitest"
import { STATIC_ITEMS, itensVisiveis, paletaDisponivel } from "@/app/components/command-palette"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const router = { push: vi.fn() } as any
const ids = (itens: { id: string }[]) => itens.map(i => i.id)

const SO_ADMIN = ["dashboard", "users", "settings"]

describe("itensVisiveis", () => {
  it("esconde os itens de admin de quem não é admin", () => {
    const visiveis = ids(itensVisiveis(STATIC_ITEMS(router), false))
    for (const id of SO_ADMIN) expect(visiveis).not.toContain(id)
    // O resto continua visível.
    expect(visiveis).toContain("projects")
    expect(visiveis).toContain("drive")
    expect(visiveis).toContain("new-workflow")
    // «planos» NÃO está aqui: a rota não existe mais (numa instalação com os
    // planos, eles são um modal aberto pelo menu da conta). Um item de paleta
    // faria `router.push` para o nada — e a paleta nem abre na Home para quem
    // não é admin.
    expect(visiveis).not.toContain("planos")
  })

  it("mostra tudo para o admin", () => {
    const visiveis = ids(itensVisiveis(STATIC_ITEMS(router), true))
    for (const id of SO_ADMIN) expect(visiveis).toContain(id)
  })

  it("exatamente Dashboard, Usuários e Configurações são marcados admin", () => {
    // Guarda a marca: se alguém marcar (ou desmarcar) um item por engano, cai.
    const marcados = STATIC_ITEMS(router).filter(i => i.admin).map(i => i.id).sort()
    expect(marcados).toEqual([...SO_ADMIN].sort())
  })
})

describe("paletaDisponivel", () => {
  // A Home não OFERECE saída a quem não administra o sistema. Não é controle de
  // acesso: quem barra é o `proxy.ts`, que hoje devolve `/` a quem não é admin
  // em toda página fora da Home.
  it("na Home, só o admin tem paleta", () => {
    expect(paletaDisponivel("/", false)).toBe(false)
    expect(paletaDisponivel("/", true)).toBe(true)
  })

  it("fora da Home, todo mundo tem", () => {
    for (const rota of ["/projects", "/drive", "/workflow/abc", "/dashboard"]) {
      expect(paletaDisponivel(rota, false)).toBe(true)
    }
  })

  it("a Home é casamento EXATO, não prefixo", () => {
    // Um `startsWith("/")` casaria o app inteiro; e uma rota que só COMEÇA com
    // "/" seguido de mais coisa nunca é a Home.
    expect(paletaDisponivel("/projetos", false)).toBe(true)
    expect(paletaDisponivel("/*", false)).toBe(true)
  })

  it("pathname ausente não fecha a paleta", () => {
    // `usePathname()` pode devolver nulo fora de uma rota resolvida; fechar aí
    // seria esconder a paleta do app inteiro por um estado transitório.
    expect(paletaDisponivel(null, false)).toBe(true)
    expect(paletaDisponivel(undefined, false)).toBe(true)
  })
})
