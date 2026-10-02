import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { CATALOGO, ORGAOS_FEDERAIS } from "@/lib/catalogo"
import { formatarInteiro } from "@/lib/formatos"

/**
 * A casca da Home: Nova conversa + grupo Meus (Agendamentos, Artefatos, Chats),
 * Chats já aberto, rodapé UserSidebar. As folhas pesadas (UserSidebar, as
 * listas) viram marcadores — o foco é a ESTRUTURA e o comportamento do grupo
 * Meu: o clique no trilho, o aberto/fechado lembrado, a lista que fecha sem
 * desmontar, e a montagem só depois de hidratar.
 */

// jsdom não tem matchMedia; o SidebarProvider (useIsMobile) precisa dele. Quem
// decide telefone × desktop é `innerWidth` — o hook lê a largura, não `matches`.
beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (q: string) => ({
      matches: false, media: q, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    }),
  })
})
function largura(px: number) {
  Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: px })
}

// A sessao e MUTAVEL: o papel decide se a marca e link, e os dois casos precisam
// do mesmo render. `vi.hoisted` porque a fabrica do `vi.mock` e icada.
// `status` e `erro` sobrepõem a derivação do papel: é como o teste vira a
// casca anônima (sem sessão) e a da sessão vencida.
const sessao = vi.hoisted(() => ({
  papel: "admin" as string | undefined,
  status: undefined as string | undefined,
  erro: undefined as string | undefined,
}))
vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: sessao.papel === undefined ? null : { user: { role: sessao.papel }, ...(sessao.erro ? { error: sessao.erro } : {}) },
    status: sessao.status ?? (sessao.papel === undefined ? "loading" : "authenticated"),
  }),
}))

// O UserSidebar captura a prop da paleta dos portais; a lista de Chats conta as
// MONTAGENS (efeito de montagem), não os renders — é o que distingue "escondeu"
// de "desmontou e remontou".
const espiao = vi.hoisted(() => ({ chatsMontou: vi.fn() }))
vi.mock("@/app/components/sidebar/user-sidebar", () => ({
  default: (p: { portalClassName?: string }) => (
    <div data-testid="user-sidebar" data-portal={p.portalClassName ?? ""} />
  ),
}))
vi.mock("@/app/components/home/chats/lista", async () => {
  const React = await import("react")
  return {
    ChatsLista: () => {
      React.useEffect(() => { espiao.chatsMontou() }, [])
      return <div data-testid="chats-lista" />
    },
  }
})
vi.mock("@/app/components/home/agendamentos/lista", () => ({ AgendamentosLista: () => <div data-testid="agendamentos-lista" /> }))
vi.mock("@/app/components/home/artefatos/lista", () => ({ ArtefatosLista: () => <div data-testid="artefatos-lista" /> }))

import { SidebarProvider } from "@/app/components/ui/sidebar"
import HomeSidebar from "@/app/components/sidebar/home-sidebar"
import { useHomeStore, MEU_PADRAO } from "@/app/stores/homeStore"

const hidratarReal = useHomeStore.getState().hidratar

function montar(props: Omit<React.ComponentProps<typeof SidebarProvider>, "children"> = {}) {
  return render(
    <SidebarProvider {...props}>
      <HomeSidebar />
    </SidebarProvider>,
  )
}

beforeEach(() => {
  cleanup()
  window.localStorage.clear()
  largura(1280)
  useHomeStore.setState({ conversaId: null, hidratado: false, meu: { ...MEU_PADRAO }, hidratar: hidratarReal, entrada: null })
  sessao.papel = "admin"
  sessao.status = undefined
  sessao.erro = undefined
  espiao.chatsMontou.mockClear()
})

function semSessao() {
  sessao.papel = undefined
  sessao.status = "unauthenticated"
}

describe("HomeSidebar — sem sessão", () => {
  it("a casca anônima: vitrine do catálogo no corpo, sem Nova conversa, sem o grupo Meus, sem a conta; Entrar e Criar conta pedem o modal", () => {
    semSessao()
    montar()
    expect(screen.queryByText("Nova conversa")).toBeNull()
    for (const rotulo of ["Meus", "Chats", "Agendamentos", "Artefatos"]) expect(screen.queryByText(rotulo), rotulo).toBeNull()
    expect(screen.queryByTestId("chats-lista")).toBeNull()
    expect(espiao.chatsMontou).not.toHaveBeenCalled()
    expect(screen.queryByTestId("user-sidebar")).toBeNull()
    // A vitrine: números da constante (nunca de um GET — a casca anônima não
    // faz requisição) e as três fitas rotuladas.
    expect(screen.getByText("No catálogo")).toBeTruthy()
    expect(screen.getByText(formatarInteiro(CATALOGO.camadas))).toBeTruthy()
    expect(screen.getByText(new RegExp(`de ${CATALOGO.instituicoes} instituições em ${CATALOGO.paises} países`))).toBeTruthy()
    expect(screen.getByText(/Pare de procurar dados/i)).toBeTruthy()
    for (const rotulo of ["Brasil", "Fora do Brasil"]) expect(screen.getByText(rotulo), rotulo).toBeTruthy()
    // A marca continua, inerte; a landmark também.
    expect(screen.getByText("Atlans").closest("a")).toBeNull()
    expect(screen.getByRole("navigation", { name: "Barra lateral da Home" })).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: "Entrar" }))
    expect(useHomeStore.getState().entrada).toBe("entrar")
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }))
    expect(useHomeStore.getState().entrada).toBe("cadastro")
  })

  it("cada nome da fita sai duas vezes — a segunda é a emenda do laço, e some do leitor de tela", () => {
    // A animação anda até -50%: sem a cópia, a volta ao início pisca. Mas são
    // nomes, não enfeite, então quem lê por áudio ouve a lista uma vez só.
    semSessao()
    montar()
    const copias = screen.getAllByText(ORGAOS_FEDERAIS[0].rotulo)
    expect(copias).toHaveLength(2)
    expect(copias[0].getAttribute("aria-hidden")).toBeNull()
    expect(copias[1].getAttribute("aria-hidden")).toBe("true")
  })

  it("um grupo Meus lembrado aberto por outra pessoa no mesmo navegador não monta nada sem sessão", () => {
    // O ItemColapsavel monta a lista em `hidratado && aberto`: sem sessão o
    // grupo não pode nem existir, senão cada lista sairia com o seu GET.
    window.localStorage.setItem("atlans:home:meu", JSON.stringify({ agendamentos: true, artefatos: true, chats: true }))
    semSessao()
    montar()
    expect(screen.queryByTestId("agendamentos-lista")).toBeNull()
    expect(screen.queryByTestId("artefatos-lista")).toBeNull()
    expect(espiao.chatsMontou).not.toHaveBeenCalled()
  })

  it("a sessão vencida conta como anônima (o instante antes do signOut do SessionSync)", () => {
    sessao.papel = "user"
    sessao.erro = "RefreshTokenExpired"
    montar()
    expect(espiao.chatsMontou).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: "Entrar" })).toBeTruthy()
  })

  it("enquanto a sessão carrega, a casca é a de sempre (o gate é 'sem sessão', não 'sem authenticated')", () => {
    sessao.papel = undefined   // status: loading
    montar()
    expect(screen.getByText("Nova conversa")).toBeTruthy()
    expect(screen.getByText("Meus")).toBeTruthy()
    expect(screen.queryByRole("button", { name: "Entrar" })).toBeNull()
  })

  it("no trilho, Entrar e Criar conta têm ícone e o convite some", () => {
    semSessao()
    montar({ open: false })
    const entrar = screen.getByRole("button", { name: "Entrar" })
    expect(entrar.querySelector("svg")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Criar conta" }).querySelector("svg")).toBeTruthy()
    expect(screen.getByText("No catálogo").closest('[data-slot="sidebar-group"]')!.className).toContain("group-data-[collapsible=icon]:hidden")
    // No telefone o clique fecha a gaveta antes de abrir o modal — coberto
    // pelo `setOpenMobile` do provider; aqui só o desktop.
  })
})

describe("HomeSidebar", () => {
  it("mostra Nova conversa e o grupo Meus com os três itens", () => {
    montar()
    expect(screen.getByText("Nova conversa")).toBeTruthy()
    expect(screen.getByText("Meus")).toBeTruthy()
    expect(screen.getByText("Agendamentos")).toBeTruthy()
    expect(screen.getByText("Artefatos")).toBeTruthy()
    expect(screen.getByText("Chats")).toBeTruthy()
  })

  it("a marca leva a Projetos para o admin do sistema", () => {
    montar()
    const marca = screen.getByText("Atlans").closest("a")
    expect(marca).toBeTruthy()
    expect(marca?.getAttribute("href")).toBe("/projects")
  })

  it("quem NÃO é admin não tem como sair da Home pela marca", () => {
    // A Home passa a ser a única página de quem não administra o sistema. O
    // `Marca` sem `href` vira `<span>`: some o destino E a afordância (o realce
    // de hover que dizia "isto é clicável").
    sessao.papel = "user"
    montar()
    expect(screen.getByText("Atlans")).toBeTruthy()
    expect(screen.getByText("Atlans").closest("a")).toBeNull()
  })

  it("enquanto a sessão carrega a marca fica inerte (falha fechada)", () => {
    // O contrário piscaria um link para /projects que some no render seguinte.
    sessao.papel = undefined
    montar()
    expect(screen.getByText("Atlans").closest("a")).toBeNull()
  })

  it("Chats já vem aberto (a lista de conversas aparece)", () => {
    montar()
    expect(screen.getByTestId("chats-lista")).toBeTruthy()
  })

  it("o rodapé é o UserSidebar reusado", () => {
    montar()
    expect(screen.getByTestId("user-sidebar")).toBeTruthy()
  })

  it("Nova conversa limpa a seleção no store", () => {
    useHomeStore.setState({ conversaId: "abc" })
    montar()
    fireEvent.click(screen.getByText("Nova conversa"))
    expect(useHomeStore.getState().conversaId).toBeNull()
  })

  it("é uma landmark nomeada — a Home só teria o <main> anônimo", () => {
    montar()
    const nav = screen.getByRole("navigation", { name: "Barra lateral da Home" })
    expect(nav).toBeTruthy()
    // Também pinta o fundo: no telefone o painel é o SheetContent, e sem uma
    // classe de fundo DENTRO do `.home` o fundo vinha do tema do app.
    expect(nav.className).toContain("bg-sidebar")
    expect(nav.className).toContain("home")
  })

  it("os alvos do telefone têm 40px (§5 do padrão de telas)", () => {
    montar()
    const novaConversa = screen.getByText("Nova conversa").closest("button")
    expect(novaConversa!.className).toContain("max-md:h-10")
    const agendamentos = screen.getByText("Agendamentos").closest("button")
    expect(agendamentos!.className).toContain("max-md:h-10")
  })

  it("Agendamentos e Artefatos abrem as listas vivas (sem 'Em breve')", () => {
    montar()
    expect(screen.queryByText("Em breve.")).toBeNull()
    // Colapsados por padrão; o clique no rótulo abre a sublista.
    fireEvent.click(screen.getByText("Agendamentos"))
    expect(screen.getByTestId("agendamentos-lista")).toBeTruthy()
    fireEvent.click(screen.getByText("Artefatos"))
    expect(screen.getByTestId("artefatos-lista")).toBeTruthy()
  })
})

describe("HomeSidebar — o grupo Meus", () => {
  it("no trilho, clicar um item EXPANDE a barra e o abre — nunca alterna às cegas", () => {
    // O defeito: recolhida, a sublista está em display:none e o clique só
    // virava um estado invisível — ao expandir, o item estava no OPOSTO do que
    // a pessoa deixou.
    const aoAbrir = vi.fn()
    montar({ open: false, onOpenChange: aoAbrir })
    fireEvent.click(screen.getByText("Agendamentos"))
    expect(aoAbrir).toHaveBeenLastCalledWith(true)
    expect(useHomeStore.getState().meu.agendamentos).toBe(true)
    // Um item JÁ aberto continua aberto: no trilho não há o que fechar.
    fireEvent.click(screen.getByText("Chats"))
    expect(useHomeStore.getState().meu.chats).toBe(true)
    expect(aoAbrir).toHaveBeenCalledTimes(2)
  })

  it("no trilho o item não anuncia aria-expanded — não há nada que expanda", () => {
    montar({ open: false })
    expect(screen.getByText("Chats").closest("button")!.hasAttribute("aria-expanded")).toBe(false)
  })

  it("expandido, aria-expanded acompanha e aria-controls aponta para a lista", () => {
    montar()
    const botao = screen.getByText("Chats").closest("button")!
    expect(botao.getAttribute("aria-expanded")).toBe("true")
    const alvo = document.getElementById(botao.getAttribute("aria-controls")!)!
    expect(alvo.contains(screen.getByTestId("chats-lista"))).toBe(true)
    fireEvent.click(botao)
    expect(botao.getAttribute("aria-expanded")).toBe("false")
    expect(alvo.hasAttribute("hidden")).toBe(true)
  })

  it("fechar um item ESCONDE a lista sem desmontá-la", () => {
    // `{aberto && children}` refazia as requisições a cada reabertura e perdia
    // as páginas do "Ver mais", o erro e a rolagem.
    montar()
    expect(espiao.chatsMontou).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByText("Chats"))
    expect(screen.getByTestId("chats-lista")).toBeTruthy()
    fireEvent.click(screen.getByText("Chats"))
    expect(espiao.chatsMontou).toHaveBeenCalledTimes(1)
  })

  it("nada monta antes de hidratar; hidratar monta o que está aberto", () => {
    useHomeStore.setState({ hidratar: () => {} })
    montar()
    expect(screen.queryByTestId("chats-lista")).toBeNull()
    act(() => { useHomeStore.setState({ hidratado: true }) })
    expect(screen.getByTestId("chats-lista")).toBeTruthy()
  })

  it("o aberto/fechado lembrado no navegador vale na montagem", () => {
    window.localStorage.setItem("atlans:home:meu", JSON.stringify({ agendamentos: true, artefatos: false, chats: false }))
    montar()
    expect(screen.getByTestId("agendamentos-lista")).toBeTruthy()
    expect(screen.queryByTestId("chats-lista")).toBeNull()
  })

  it("o estado sobrevive a desmontar e remontar a barra (gaveta do telefone, troca de rota)", () => {
    const { unmount } = montar()
    fireEvent.click(screen.getByText("Artefatos"))
    unmount()
    // A memória da árvore some; a store volta ao default — só o navegador lembra.
    useHomeStore.setState({ meu: { ...MEU_PADRAO }, hidratado: false })
    montar()
    expect(screen.getByTestId("artefatos-lista")).toBeTruthy()
  })

  it("tem o trilho arrastável do shadcn no desktop", () => {
    montar()
    expect(document.querySelector('[data-sidebar="rail"]')).toBeTruthy()
  })

  it("no telefone a lista de Chats NÃO monta antes de a gaveta abrir", () => {
    // O primeiro render ainda é o ramo desktop (`useIsMobile` começa indefinido):
    // montar ali disparava um GET que ia para o lixo quando o Sheet assumia.
    largura(375)
    montar()
    expect(espiao.chatsMontou).not.toHaveBeenCalled()
    expect(screen.queryByTestId("chats-lista")).toBeNull()
    expect(document.querySelector('[data-sidebar="rail"]')).toBeNull()
  })

  it("o UserSidebar recebe a paleta dos portais", () => {
    montar()
    expect(screen.getByTestId("user-sidebar").getAttribute("data-portal")).toBe("home-portal")
  })

  it("no trilho o cabeçalho empilha marca e gatilho, e a marca fica — só o wordmark some", () => {
    montar()
    const wordmark = screen.getByText("Atlans")
    const marca = wordmark.closest("a")!
    expect(marca.parentElement!.className).toContain("group-data-[collapsible=icon]:flex-col")
    expect(marca.className).not.toContain("group-data-[collapsible=icon]:hidden")
    expect(wordmark.className).toContain("group-data-[collapsible=icon]:sr-only")
  })
})
