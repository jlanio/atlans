import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { CATALOGO, ORGAOS_FEDERAIS } from "@/lib/catalogo"
import { formatInteger } from "@/lib/formatos"

/**
 * The Home shell: New conversation + the Mine group (Schedules, Artifacts,
 * Chats), Chats already open, UserSidebar footer. The heavy leaves (UserSidebar,
 * the lists) become placeholders — the focus is the STRUCTURE and the behavior
 * of the Mine group: the click on the rail, the remembered open/closed state,
 * the list that closes without unmounting, and mounting only after hydration.
 */

// jsdom has no matchMedia; SidebarProvider (useIsMobile) needs it. What
// decides phone × desktop is `innerWidth` — the hook reads the width, not `matches`.
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

// The session is MUTABLE: the role decides whether the brand is a link, and both
// cases need the same render. `vi.hoisted` because the `vi.mock` factory is hoisted.
// `status` and `erro` override the role derivation: that's how the test turns
// into the anonymous shell (no session) and the expired-session one.
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

// UserSidebar captures the portals' palette prop; the Chats list counts
// MOUNTS (mount effect), not renders — that's what distinguishes "hid" from
// "unmounted and remounted".
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
import { useHomeStore, DEFAULT_MINE } from "@/app/stores/homeStore"

const realHydrate = useHomeStore.getState().hidratar

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
  useHomeStore.setState({ conversaId: null, hidratado: false, meu: { ...DEFAULT_MINE }, hidratar: realHydrate, entrada: null })
  sessao.papel = "admin"
  sessao.status = undefined
  sessao.erro = undefined
  espiao.chatsMontou.mockClear()
})

function withoutSession() {
  sessao.papel = undefined
  sessao.status = "unauthenticated"
}

describe("HomeSidebar — sem sessão", () => {
  it("a casca anônima: vitrine do catálogo no corpo, sem Nova conversa, sem o grupo Meus, sem a conta; Entrar e Criar conta pedem o modal", () => {
    withoutSession()
    montar()
    expect(screen.queryByText("Nova conversa")).toBeNull()
    for (const rotulo of ["Meus", "Chats", "Agendamentos", "Artefatos"]) expect(screen.queryByText(rotulo), rotulo).toBeNull()
    expect(screen.queryByTestId("chats-lista")).toBeNull()
    expect(espiao.chatsMontou).not.toHaveBeenCalled()
    expect(screen.queryByTestId("user-sidebar")).toBeNull()
    // The showcase: numbers from the constant (never from a GET — the anonymous
    // shell makes no requests) and the three labeled strips.
    expect(screen.getByText("No catálogo")).toBeTruthy()
    expect(screen.getByText(formatInteger(CATALOGO.camadas))).toBeTruthy()
    expect(screen.getByText(new RegExp(`de ${CATALOGO.instituicoes} instituições em ${CATALOGO.paises} países`))).toBeTruthy()
    expect(screen.getByText(/Pare de procurar dados/i)).toBeTruthy()
    for (const rotulo of ["Brasil", "Fora do Brasil"]) expect(screen.getByText(rotulo), rotulo).toBeTruthy()
    // The brand stays, inert; so does the landmark.
    expect(screen.getByText("Atlans").closest("a")).toBeNull()
    expect(screen.getByRole("navigation", { name: "Barra lateral da Home" })).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: "Entrar" }))
    expect(useHomeStore.getState().entrada).toBe("entrar")
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }))
    expect(useHomeStore.getState().entrada).toBe("cadastro")
  })

  it("cada nome da fita sai duas vezes — a segunda é a emenda do laço, e some do leitor de tela", () => {
    // The animation runs to -50%: without the copy, the wrap back to the start
    // flickers. But these are names, not decoration, so someone listening by
    // audio hears the list only once.
    withoutSession()
    montar()
    const copias = screen.getAllByText(ORGAOS_FEDERAIS[0].rotulo)
    expect(copias).toHaveLength(2)
    expect(copias[0].getAttribute("aria-hidden")).toBeNull()
    expect(copias[1].getAttribute("aria-hidden")).toBe("true")
  })

  it("um grupo Meus lembrado aberto por outra pessoa no mesmo navegador não monta nada sem sessão", () => {
    // ItemColapsavel mounts the list on `hidratado && aberto`: without a session
    // the group can't even exist, otherwise each list would fire its own GET.
    window.localStorage.setItem("atlans:home:meu", JSON.stringify({ agendamentos: true, artefatos: true, chats: true }))
    withoutSession()
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
    withoutSession()
    montar({ open: false })
    const entrar = screen.getByRole("button", { name: "Entrar" })
    expect(entrar.querySelector("svg")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Criar conta" }).querySelector("svg")).toBeTruthy()
    expect(screen.getByText("No catálogo").closest('[data-slot="sidebar-group"]')!.className).toContain("group-data-[collapsible=icon]:hidden")
    // On the phone the click closes the drawer before opening the modal —
    // covered by the provider's `setOpenMobile`; here only desktop.
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
    // Home becomes the only page for those who don't administer the system.
    // `Marca` without `href` becomes a `<span>`: both the destination AND the
    // affordance go away (the hover highlight that said "this is clickable").
    sessao.papel = "user"
    montar()
    expect(screen.getByText("Atlans")).toBeTruthy()
    expect(screen.getByText("Atlans").closest("a")).toBeNull()
  })

  it("enquanto a sessão carrega a marca fica inerte (falha fechada)", () => {
    // The opposite would flash a link to /projects that disappears on the next render.
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
    // It also paints the background: on the phone the panel is the SheetContent,
    // and without a background class INSIDE `.home` the background came from
    // the app's theme.
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
    // Collapsed by default; clicking the label opens the sublist.
    fireEvent.click(screen.getByText("Agendamentos"))
    expect(screen.getByTestId("agendamentos-lista")).toBeTruthy()
    fireEvent.click(screen.getByText("Artefatos"))
    expect(screen.getByTestId("artefatos-lista")).toBeTruthy()
  })
})

describe("HomeSidebar — o grupo Meus", () => {
  it("no trilho, clicar um item EXPANDE a barra e o abre — nunca alterna às cegas", () => {
    // The defect: when collapsed, the sublist is display:none and the click
    // only turned into invisible state — on expanding, the item was in the
    // OPPOSITE state from what the person left.
    const aoAbrir = vi.fn()
    montar({ open: false, onOpenChange: aoAbrir })
    fireEvent.click(screen.getByText("Agendamentos"))
    expect(aoAbrir).toHaveBeenLastCalledWith(true)
    expect(useHomeStore.getState().meu.agendamentos).toBe(true)
    // An item that is ALREADY open stays open: on the rail there's nothing to close.
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
    // `{aberto && children}` redid the requests on every reopening and lost
    // the "Ver mais" (see more) pages, the error and the scroll position.
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
    // The tree's memory is gone; the store goes back to default — only the browser remembers.
    useHomeStore.setState({ meu: { ...DEFAULT_MINE }, hidratado: false })
    montar()
    expect(screen.getByTestId("artefatos-lista")).toBeTruthy()
  })

  it("tem o trilho arrastável do shadcn no desktop", () => {
    montar()
    expect(document.querySelector('[data-sidebar="rail"]')).toBeTruthy()
  })

  it("no telefone a lista de Chats NÃO monta antes de a gaveta abrir", () => {
    // The first render is still the desktop branch (`useIsMobile` starts
    // undefined): mounting there fired a GET that was thrown away when the
    // Sheet took over.
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
