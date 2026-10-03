import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { IConversationSummary } from "@/service/types"

/**
 * The "Meu → Chats" panel (the "Recentes"): each conversation's row, the active one, the
 * ⋯ menu (rename/delete), the list states and the dialogs in the Home's
 * palette. The data hook is a controllable double; the menu is a passthrough (no
 * Radix portal/pointer), so the items are directly clickable.
 */

const H = vi.hoisted(() => ({
  hook: {
    conversas: [] as IConversationSummary[],
    carregando: false, atualizando: false, jaCarregou: true, erro: null as string | null,
    total: 0, carregandoMais: false,
    recarregar: vi.fn(), carregarMais: vi.fn(), tentarDeNovo: vi.fn(), anunciar: vi.fn(),
    renomear: vi.fn(), apagar: vi.fn(),
  },
  toastErro: vi.fn(),
}))

vi.mock("@/app/hooks/home/useConversas", () => ({ useConversas: () => H.hook }))
vi.mock("@/utils/createToast", () => ({ createToast: { success: vi.fn(), error: (...a: unknown[]) => H.toastErro(...a) } }))
// Menu passthrough: without portal/pointer, the items stay in the DOM and clickable. The
// `className` PASSES THROUGH on purpose — it is through it that the theme (`home-portal`)
// and touch target (40px) tests see what the component asked for.
vi.mock("@/app/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DropdownMenuContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="menu" className={className}>{children}</div>
  ),
  DropdownMenuItem: ({ children, onSelect, className }: { children: React.ReactNode; onSelect?: () => void; className?: string }) => (
    <button onClick={onSelect} className={className}>{children}</button>
  ),
}))

import { SidebarProvider } from "@/app/components/ui/sidebar"
import { ChatsLista } from "@/app/components/home/chats/lista"
import { useHomeStore } from "@/app/stores/homeStore"

const conversa = (extra: Partial<IConversationSummary> = {}): IConversationSummary => ({
  id: "c1", titulo: "Focos em Rondônia", workflow_id: null, tokens_total: 0,
  created_at: "2026-09-10T12:00:00Z", updated_at: "2026-09-10T12:00:00Z",
  ...extra,
})

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

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
  Object.assign(H.hook, {
    conversas: [conversa(), conversa({ id: "c2", titulo: "  " })],
    carregando: false, atualizando: false, jaCarregou: true, erro: null, total: 2, carregandoMais: false,
  })
  useHomeStore.setState({ conversaId: null, painel: "barra", anuncioDeConversa: null })
})

function montar() {
  return render(
    <SidebarProvider>
      <ChatsLista />
    </SidebarProvider>,
  )
}

const triggerFor = (rotulo: string) => screen.getByRole("button", { name: `Ações de "${rotulo}"` })

describe("ChatsLista — a linha", () => {
  it("lista as conversas; a sem título vira 'Sem título'", () => {
    montar()
    expect(screen.getByText("Focos em Rondônia")).toBeTruthy()
    expect(screen.getByText("Sem título")).toBeTruthy()
  })

  it("o principal ocupa o espaço que existe e trunca — o ⋯ é irmão no flex, nunca por cima", () => {
    // The defect this locks: the `nowrap` title in a `<button>` with no
    // width overflowed the whole row up to the edge of the bar, without truncating;
    // and the `absolute` ⋯ with `pr-7` reserved by hand had zero slack.
    montar()
    const botao = screen.getByTitle("Focos em Rondônia")
    for (const c of ["min-w-0", "flex-1", "text-left"]) expect(botao.className).toContain(c)
    expect(botao.querySelector("span")!.className).toContain("truncate")

    // The menu mock wraps the trigger in a <div>; in the real DOM Radix adds no
    // wrapper. What matters: both live in the SAME flex row.
    const gatilho = triggerFor("Focos em Rondônia")
    const linha = botao.closest('[data-slot="linha-do-meu"]')!
    expect(gatilho.closest('[data-slot="linha-do-meu"]')).toBe(linha)
    expect(linha.className).toContain("flex")
    expect(gatilho.className).not.toMatch(/\babsolute\b/)
    expect(botao.className).not.toMatch(/\bpr-7\b/)
  })

  it("a ativa é anunciada por aria-current e pintada pela linha; clicar noutra seleciona e abre o painel", () => {
    useHomeStore.setState({ conversaId: "c1" })
    montar()
    const ativa = screen.getByTitle("Focos em Rondônia")
    expect(ativa.getAttribute("aria-current")).toBe("true")
    expect(ativa.parentElement!.getAttribute("data-active")).toBe("true")
    const outra = screen.getByTitle("Sem título")
    expect(outra.hasAttribute("aria-current")).toBe(false)

    fireEvent.click(outra)
    expect(useHomeStore.getState().conversaId).toBe("c2")
    expect(useHomeStore.getState().painel).toBe("aberto")
  })

  it("o menu herda a paleta da Home e seus itens têm alvo de 40px", () => {
    montar()
    const menu = screen.getAllByTestId("menu")[0]
    expect(menu.className).toContain("home-portal")
    for (const rotulo of ["Renomear", "Apagar"]) {
      expect(within(menu).getByText(rotulo).className).toContain("max-md:min-h-10")
    }
  })
})

describe("ChatsLista — estados", () => {
  it("esqueleto na 1ª carga", () => {
    Object.assign(H.hook, { conversas: [], carregando: true, jaCarregou: false })
    montar()
    expect(screen.getByRole("status", { name: "Carregando as conversas" })).toBeTruthy()
  })

  it("erro de 1ª carga oferece 'Tentar de novo'", () => {
    Object.assign(H.hook, { conversas: [], erro: "Não foi possível carregar as conversas.", jaCarregou: false })
    montar()
    expect(screen.getByRole("alert")).toBeTruthy()
    fireEvent.click(screen.getByText("Tentar de novo"))
    expect(H.hook.recarregar).toHaveBeenCalled()
  })

  it("lista vazia", () => {
    Object.assign(H.hook, { conversas: [], total: 0 })
    montar()
    expect(screen.getByText("Nenhuma conversa ainda.")).toBeTruthy()
  })

  it("diz quantas o servidor tem e 'Ver mais' pede a página seguinte", () => {
    Object.assign(H.hook, { total: 300 })
    montar()
    expect(screen.getByText(/mostrando 2 de 300/)).toBeTruthy()
    fireEvent.click(screen.getByText("Ver mais"))
    expect(H.hook.carregarMais).toHaveBeenCalled()
  })

  it("recarga que falha com a lista na tela vira o aviso do rodapé, não o bloco de erro", () => {
    Object.assign(H.hook, { erro: "Não foi possível atualizar as conversas.", jaCarregou: true })
    montar()
    expect(screen.getByText("Focos em Rondônia")).toBeTruthy()
    expect(screen.queryByRole("alert")).toBeNull()
    expect(screen.getByText(/Não foi possível atualizar as conversas/)).toBeTruthy()
  })

  it("o 'Tentar de novo' do rodapé refaz o que FALHOU, não a lista inteira", () => {
    // After a failed "Ver mais", reloading everything cost N GETs, did not
    // bring the missing page and still returned the list to the ceiling of 100.
    Object.assign(H.hook, { erro: "Não foi possível carregar mais conversas.", jaCarregou: true })
    montar()
    fireEvent.click(within(screen.getByRole("status")).getByText("Tentar de novo"))
    expect(H.hook.tentarDeNovo).toHaveBeenCalledTimes(1)
    expect(H.hook.recarregar).not.toHaveBeenCalled()
  })
})

describe("ChatsLista — renomear e apagar", () => {
  it("Renomear abre o diálogo com o título atual, na paleta da Home", async () => {
    montar()
    fireEvent.click(within(screen.getAllByTestId("menu")[0]).getByText("Renomear"))
    expect(await screen.findByDisplayValue("Focos em Rondônia")).toBeTruthy()
    expect(document.querySelector('[data-slot="dialog-content"]')!.className).toContain("home-portal")
  })

  it("Apagar abre o DeleteDialog na paleta da Home; a falha vira toast", async () => {
    // The `DeleteDialog` is shared by the whole app and is born without a palette: the
    // Home has to pass `home-portal`, otherwise it opened white over #050505.
    H.hook.apagar.mockResolvedValue({ ok: false, erro: "servidor fora" })
    montar()
    fireEvent.click(within(screen.getAllByTestId("menu")[0]).getByText("Apagar"))
    const dialogo = await screen.findByRole("dialog")
    expect(within(dialogo).getByText("Apagar conversa")).toBeTruthy()
    expect(dialogo.className).toContain("home-portal")

    fireEvent.click(within(dialogo).getByRole("button", { name: "Apagar" }))
    await waitFor(() => expect(H.hook.apagar).toHaveBeenCalledWith("c1"))
    await waitFor(() => expect(H.toastErro).toHaveBeenCalledWith("Não foi possível apagar a conversa", "servidor fora"))
  })
})

describe("ChatsLista — o anúncio do stream chega à lista", () => {
  const announcement = { id: "c9", titulo: "Nova conversa", nova: true }

  it("um anúncio depois de montar vai ao hook — é assim que a conversa nova entra sem F5", () => {
    montar()
    act(() => { useHomeStore.getState().anunciarConversa(announcement) })
    expect(H.hook.anunciar).toHaveBeenCalledTimes(1)
    expect(H.hook.anunciar).toHaveBeenCalledWith(announcement)
  })

  it("o que já estava na store ao montar é passado — a carga de montagem traz a verdade", () => {
    // On the phone the list remounts every time the drawer opens; reapplying an
    // old announcement over the freshly loaded list would be double work.
    useHomeStore.getState().anunciarConversa(announcement)
    montar()
    expect(H.hook.anunciar).not.toHaveBeenCalled()
  })

  it("com uma carga em voo o anúncio espera, e é aplicado quando ela acaba", () => {
    // The load response REPLACES the list: applied in the middle, the announcement vanished.
    Object.assign(H.hook, { carregando: true, jaCarregou: false, conversas: [] })
    const { rerender } = montar()
    act(() => { useHomeStore.getState().anunciarConversa(announcement) })
    expect(H.hook.anunciar).not.toHaveBeenCalled()

    Object.assign(H.hook, { carregando: false, jaCarregou: true, conversas: [conversa()] })
    rerender(<SidebarProvider><ChatsLista /></SidebarProvider>)
    expect(H.hook.anunciar).toHaveBeenCalledWith(announcement)
  })
})

describe("ChatsLista — apagar a conversa ativa", () => {
  /** Deletes "c1" through the menu and waits for the dialog to close (the outcome has already been applied). */
  async function deleteFirst() {
    fireEvent.click(within(screen.getAllByTestId("menu")[0]).getByText("Apagar"))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.click(within(dialogo).getByRole("button", { name: "Apagar" }))
    await waitFor(() => expect(H.hook.apagar).toHaveBeenCalledWith("c1"))
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
  }

  it("apagar a ATIVA limpa a seleção — a Home fica como no botão 'Nova conversa'", async () => {
    // Without this the panel kept showing the dead conversation and the next
    // message went out with the deleted id: 404.
    H.hook.apagar.mockResolvedValue({ ok: true })
    useHomeStore.setState({ conversaId: "c1" })
    montar()
    await deleteFirst()
    expect(useHomeStore.getState().conversaId).toBeNull()
  })

  it("apagar OUTRA não mexe na seleção", async () => {
    H.hook.apagar.mockResolvedValue({ ok: true })
    useHomeStore.setState({ conversaId: "c2" })
    montar()
    await deleteFirst()
    expect(useHomeStore.getState().conversaId).toBe("c2")
  })

  it("a exclusão que falha deixa a seleção como estava", async () => {
    H.hook.apagar.mockResolvedValue({ ok: false, erro: "servidor fora" })
    useHomeStore.setState({ conversaId: "c1" })
    montar()
    await deleteFirst()
    expect(H.toastErro).toHaveBeenCalled()
    expect(useHomeStore.getState().conversaId).toBe("c1")
  })
})
