import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"

/**
 * O modal de entrada da Home: a lógica das antigas páginas /login e /register
 * (POST + signIn sem redirect; POST /auth/register → "Verifique seu e-mail"),
 * fechável — menos com um envio em voo — e no tema da Home.
 */
const http = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock("axios", () => {
  class AxiosError extends Error {}
  return { default: { post: http.post, get: http.get }, AxiosError }
})
const auth = vi.hoisted(() => ({ signIn: vi.fn() }))
vi.mock("next-auth/react", () => ({ signIn: auth.signIn }))

import ModalDeEntrada from "@/app/components/home/entrada/modal-de-entrada"
import { CodigoFonteProvider } from "@/app/components/share/codigo-fonte"
import { NomeNaTelaProvider } from "@/app/components/share/nome-na-tela"

const onFechar = vi.fn()
const onEntrou = vi.fn()

beforeEach(() => {
  cleanup()
  http.post.mockReset()
  http.get.mockReset()
  auth.signIn.mockReset()
  onFechar.mockClear()
  onEntrou.mockClear()
})
afterEach(cleanup)

function montar(props: Partial<React.ComponentProps<typeof ModalDeEntrada>> = {}) {
  return render(<ModalDeEntrada modo="entrar" onFechar={onFechar} onEntrou={onEntrou} {...props} />)
}

function preencher(rotulo: RegExp | string, valor: string, opcoes?: { selector?: string }) {
  const campo = screen.getByLabelText(rotulo, opcoes)
  fireEvent.change(campo, { target: { value: valor } })
  return campo
}

function submeter(campo: HTMLElement) {
  fireEvent.submit(campo.closest("form")!)
}

describe("ModalDeEntrada — entrar", () => {
  it("POST /auth/login → signIn sem redirect → onEntrou", async () => {
    http.post.mockResolvedValue({ data: { access_token: "acesso", refresh_token: "renova" } })
    auth.signIn.mockResolvedValue({ ok: true, error: null })
    montar()
    preencher(/E-mail ou usuário/i, "fulana")
    const senha = preencher(/^Senha$/i, "s3nha-forte")
    submeter(senha)

    await waitFor(() => expect(onEntrou).toHaveBeenCalledTimes(1))
    expect(http.post).toHaveBeenCalledWith(expect.stringMatching(/\/auth\/login$/), { identifier: "fulana", password: "s3nha-forte" }) // pragma: allowlist secret
    expect(auth.signIn).toHaveBeenCalledWith("credentials", { access_token: "acesso", refresh_token: "renova", redirect: false })
  })

  it("403 email_not_verified: a variante amarela com o reenvio, sem onEntrou", async () => {
    http.post.mockRejectedValue({ response: { status: 403, headers: { "x-error-code": "email_not_verified" }, data: { message: "Confirme seu e-mail antes de entrar." } } })
    montar()
    preencher(/E-mail ou usuário/i, "fulana")
    submeter(preencher(/^Senha$/i, "x"))

    const alerta = await screen.findByRole("alert")
    expect(alerta.textContent).toContain("Confirme seu e-mail antes de entrar.")
    expect(onEntrou).not.toHaveBeenCalled()
    expect(auth.signIn).not.toHaveBeenCalled()

    // O atalho é um BOTÃO: era um <Link href="/verify-email"> e navegar levava
    // para fora da Home, junto com a mensagem que esperava o login.
    const atalho = screen.getByRole("button", { name: /Reenviar e-mail de verificação/i })
    expect(atalho.closest("a")).toBeNull()
    fireEvent.click(atalho)
    expect(screen.getByTestId("modal-de-entrada").getAttribute("data-painel")).toBe("verificar")
  })

  it("429: conta travada, o botão desabilita", async () => {
    http.post.mockRejectedValue({ response: { status: 429, headers: {}, data: { message: "Muitas tentativas." } } })
    montar()
    preencher(/E-mail ou usuário/i, "fulana")
    submeter(preencher(/^Senha$/i, "x"))

    expect((await screen.findByRole("alert")).textContent).toContain("Muitas tentativas.")
    expect((screen.getByRole("button", { name: "Entrar" }) as HTMLButtonElement).disabled).toBe(true)
  })

  it("sem resposta do servidor: a mensagem de rede", async () => {
    http.post.mockRejectedValue({})
    montar()
    preencher(/E-mail ou usuário/i, "fulana")
    submeter(preencher(/^Senha$/i, "x"))
    expect((await screen.findByRole("alert")).textContent).toContain("Sem conexão com o servidor")
  })

  it("o signIn que falha depois do POST não conta como entrada", async () => {
    http.post.mockResolvedValue({ data: { access_token: "a", refresh_token: "r" } })
    auth.signIn.mockResolvedValue({ ok: false, error: "CredentialsSignin" })
    montar()
    preencher(/E-mail ou usuário/i, "fulana")
    submeter(preencher(/^Senha$/i, "x"))
    expect((await screen.findByRole("alert")).textContent).toContain("Erro ao iniciar sessão")
    expect(onEntrou).not.toHaveBeenCalled()
  })

  it("os links de rodapé trocam Entrar ↔ Criar conta", () => {
    montar()
    expect(screen.getByRole("dialog", { name: "Entrar" })).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }))
    expect(screen.getByRole("dialog", { name: "Criar conta" })).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }))
    expect(screen.getByRole("dialog", { name: "Entrar" })).toBeTruthy()
  })
})

describe("ModalDeEntrada — criar conta", () => {
  function preencherCadastro(confirmacao = "S3nha-forte") {
    preencher(/^Usuário$/i, "fulana")
    preencher(/^E-mail$/i, "fulana@exemplo.com")
    preencher(/^Senha$/i, "S3nha-forte")
    return preencher(/Confirmar senha/i, confirmacao)
  }

  it("senhas diferentes: erro inline, sem POST", async () => {
    montar({ modo: "cadastro" })
    submeter(preencherCadastro("outra"))
    expect((await screen.findByRole("alert")).textContent).toContain("As senhas não coincidem.")
    expect(http.post).not.toHaveBeenCalled()
  })

  it("cadastro ok → 'Verifique seu e-mail', reenvio já preenchido, e a volta ao Entrar", async () => {
    http.post.mockResolvedValueOnce({ data: { message: "Conta criada." } })
    montar({ modo: "cadastro" })
    submeter(preencherCadastro())

    expect(await screen.findByRole("dialog", { name: "Verifique seu e-mail" })).toBeTruthy()
    expect(http.post).toHaveBeenCalledWith(expect.stringMatching(/\/auth\/register$/), {
      username: "fulana", email: "fulana@exemplo.com", password: "S3nha-forte", password_confirm: "S3nha-forte", // pragma: allowlist secret
    })
    const reenvio = screen.getByLabelText(/Não recebeu\?/i) as HTMLInputElement
    expect(reenvio.value).toBe("fulana@exemplo.com")

    http.post.mockResolvedValueOnce({ data: { message: "E-mail reenviado." } })
    submeter(reenvio)
    expect((await screen.findByRole("status")).textContent).toContain("E-mail reenviado.")
    expect(http.post).toHaveBeenLastCalledWith(expect.stringMatching(/\/auth\/resend-verification$/), { email: "fulana@exemplo.com" })

    fireEvent.click(screen.getByRole("button", { name: /Já verifiquei: entrar/i }))
    expect(screen.getByRole("dialog", { name: "Entrar" })).toBeTruthy()
  })
})

describe("ModalDeEntrada — fechar e o tema", () => {
  it("Esc e o X fecham (chamam onFechar)", async () => {
    montar()
    fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" })
    await waitFor(() => expect(onFechar).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole("button", { name: "Fechar" }))
    await waitFor(() => expect(onFechar).toHaveBeenCalledTimes(2))
  })

  it("com um envio em voo, Esc não fecha e o X desabilita", async () => {
    http.post.mockReturnValue(new Promise(() => {}))   // nunca resolve: o envio fica em voo
    montar()
    preencher(/E-mail ou usuário/i, "fulana")
    submeter(preencher(/^Senha$/i, "x"))
    await waitFor(() => expect((screen.getByRole("button", { name: "Fechar" }) as HTMLButtonElement).disabled).toBe(true))

    await act(async () => { fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" }) })
    expect(onFechar).not.toHaveBeenCalled()
  })

  it("fechado, nada é renderizado", () => {
    montar({ modo: null })
    expect(screen.queryByRole("dialog")).toBeNull()
  })

  it("é a paleta da Home, com o véu levemente ofuscado, e o título é acessível", () => {
    montar({ comEnvioPendente: true })
    const dialogo = screen.getByRole("dialog", { name: "Entrar" })
    expect(dialogo.className).toContain("home-portal")
    expect(dialogo.className).toContain("sm:max-w-sm")
    expect(dialogo.textContent).toContain("Entre para mandar sua mensagem ao assistente.")
    const veu = document.querySelector('[data-slot="dialog-overlay"]')!
    expect(veu.className).toContain("bg-black/40")
    expect(veu.className).not.toContain("bg-black/50")
  })

  it("sem envio pendente, a frase de apoio é a genérica", () => {
    montar()
    expect(screen.getByRole("dialog").textContent).toContain("Faça login para continuar.")
  })
})

describe("ModalDeEntrada — o caminho da senha", () => {
  it("'Esqueceu a senha?' troca de painel, sem navegar", () => {
    // Era um <Link href="/forgot-password">: levava para fora da Home e, com
    // ela, ia embora a mensagem que esperava o login.
    montar()
    const gatilho = screen.getByRole("button", { name: /esqueceu a senha/i })
    expect(gatilho.closest("a")).toBeNull()
    fireEvent.click(gatilho)
    expect(screen.getByTestId("modal-de-entrada").getAttribute("data-painel")).toBe("recuperar")
    expect(screen.getByRole("heading", { name: /esqueceu a senha/i })).toBeTruthy()
  })

  it("recuperar: POST /auth/forgot-password e o aviso de caixa de entrada", async () => {
    http.post.mockResolvedValue({ data: {} })
    montar({ modo: "recuperar" })
    submeter(preencher(/e-mail/i, "ana@exemplo.com"))
    await waitFor(() => expect(http.post).toHaveBeenCalled())
    const [url, corpo] = http.post.mock.calls[0]
    expect(url).toMatch(/\/auth\/forgot-password$/)
    expect(corpo).toEqual({ email: "ana@exemplo.com" })
    expect(await screen.findByText(/confira o spam/i)).toBeTruthy()
  })

  it("recuperar: o e-mail que não existe mostra o MESMO sucesso (anti-enumeração)", async () => {
    // Dizer "este e-mail não está cadastrado" entrega quem tem conta aqui. O
    // backend responde igual nos dois casos; a interface não pode desmentir.
    http.post.mockRejectedValue(new Error("404"))
    montar({ modo: "recuperar" })
    submeter(preencher(/e-mail/i, "ninguem@exemplo.com"))
    expect(await screen.findByText(/confira o spam/i)).toBeTruthy()
    expect(screen.queryByText(/não (existe|encontrado)/i)).toBeNull()
  })

  it("redefinir: manda o token do link e volta ao login com o aviso", async () => {
    http.post.mockResolvedValue({ data: {} })
    montar({ modo: "redefinir", tokenDoLink: "tok-123" })
    preencher("Nova senha", "senha-nova-1", { selector: "input" })  // pragma: allowlist secret
    submeter(preencher("Confirmar nova senha", "senha-nova-1", { selector: "input" }))  // pragma: allowlist secret
    await waitFor(() => expect(http.post).toHaveBeenCalled())
    const [url, corpo] = http.post.mock.calls[0]
    expect(url).toMatch(/\/auth\/reset-password$/)
    expect(corpo).toEqual({ token: "tok-123", password: "senha-nova-1", password_confirm: "senha-nova-1" })  // pragma: allowlist secret
    await waitFor(() =>
      expect(screen.getByTestId("modal-de-entrada").getAttribute("data-painel")).toBe("entrar"),
    )
    expect(screen.getByText(/senha redefinida/i)).toBeTruthy()
  })

  it("redefinir: senhas diferentes não chegam a fazer POST", () => {
    montar({ modo: "redefinir", tokenDoLink: "tok-123" })
    preencher("Nova senha", "senha-nova-1", { selector: "input" })  // pragma: allowlist secret
    submeter(preencher("Confirmar nova senha", "outra-senha-9", { selector: "input" }))  // pragma: allowlist secret
    expect(http.post).not.toHaveBeenCalled()
    expect(screen.getAllByText(/não coincidem/i).length).toBeGreaterThan(0)
  })

  it("redefinir sem token: o link é inválido, e o caminho de volta é um clique", () => {
    montar({ modo: "redefinir" })
    expect(screen.getByText(/inválido ou já foi usado/i)).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: /pedir um link novo/i }))
    expect(screen.getByTestId("modal-de-entrada").getAttribute("data-painel")).toBe("recuperar")
  })

  it("voltar ao 'Esqueceu a senha?' pede o e-mail de novo, sem o aviso da vez passada", async () => {
    http.post.mockResolvedValue({ data: {} })
    montar({ modo: "recuperar" })
    submeter(preencher(/e-mail/i, "ana@exemplo.com"))
    expect(await screen.findByText(/confira o spam/i)).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: /voltar para entrar/i }))
    fireEvent.click(screen.getByRole("button", { name: /esqueceu a senha/i }))
    expect(screen.queryByText(/confira o spam/i)).toBeNull()
    expect(screen.getByLabelText(/e-mail/i)).toBeTruthy()
  })
})

describe("ModalDeEntrada — a verificação de e-mail", () => {
  it("com o token do link: GET /auth/verify-email e a volta ao login com o aviso", async () => {
    http.get.mockResolvedValue({ data: { message: "E-mail verificado." } })
    montar({ modo: "verificar", tokenDoLink: "tok-abc" })

    await waitFor(() => expect(http.get).toHaveBeenCalled())
    const [url, config] = http.get.mock.calls[0]
    expect(url).toMatch(/\/auth\/verify-email$/)
    expect(config).toEqual({ params: { token: "tok-abc" } })

    await waitFor(() =>
      expect(screen.getByTestId("modal-de-entrada").getAttribute("data-painel")).toBe("entrar"),
    )
    expect(screen.getByText(/e-mail verificado/i)).toBeTruthy()
  })

  it("o token só é gasto UMA vez, mesmo com o painel montando de novo", async () => {
    // Ele é de uso único: um segundo GET voltaria "inválido" e apagaria o
    // sucesso do primeiro.
    http.get.mockResolvedValue({ data: {} })
    montar({ modo: "verificar", tokenDoLink: "tok-abc" })
    await waitFor(() =>
      expect(screen.getByTestId("modal-de-entrada").getAttribute("data-painel")).toBe("entrar"),
    )
    expect(http.get).toHaveBeenCalledTimes(1)

    // De volta ao painel (o 403 do login leva a ele): a tela é a do reenvio,
    // sem gastar o link outra vez.
    http.post.mockRejectedValue({ response: { status: 403, headers: { "x-error-code": "email_not_verified" }, data: { message: "Confirme seu e-mail." } } })
    preencher(/E-mail ou usuário/i, "fulana")
    submeter(preencher(/^Senha$/i, "x"))
    fireEvent.click(await screen.findByRole("button", { name: /Reenviar e-mail de verificação/i }))

    expect(screen.getByRole("dialog", { name: "Verifique seu e-mail" })).toBeTruthy()
    expect(http.get).toHaveBeenCalledTimes(1)
  })

  it("token inválido: a mensagem do servidor e o reenvio, sem sair do modal", async () => {
    http.get.mockRejectedValue({ response: { data: { message: "Token inválido ou expirado." } } })
    montar({ modo: "verificar", tokenDoLink: "tok-velho" })

    expect((await screen.findByRole("alert")).textContent).toContain("Token inválido ou expirado.")
    // O cabeçalho é do modal, e chega um render depois do painel: o estado sobe
    // por efeito, que é o que deixa o `DialogTitle` sempre montado.
    expect(await screen.findByRole("dialog", { name: "Falha na verificação" })).toBeTruthy()
    expect(screen.getByTestId("modal-de-entrada").getAttribute("data-painel")).toBe("verificar")

    http.post.mockResolvedValue({ data: { message: "E-mail reenviado." } })
    submeter(preencher(/Reenviar verificação para:/i, "ana@exemplo.com"))
    expect((await screen.findByRole("status")).textContent).toContain("E-mail reenviado.")
    expect(http.post).toHaveBeenLastCalledWith(expect.stringMatching(/\/auth\/resend-verification$/), { email: "ana@exemplo.com" })
  })

  it("sem token: a tela de 'abra o link', e nada é gasto", () => {
    montar({ modo: "verificar" })
    expect(screen.getByRole("dialog", { name: "Verifique seu e-mail" })).toBeTruthy()
    expect(screen.getByText(/Abra o link do e-mail/i)).toBeTruthy()
    expect(http.get).not.toHaveBeenCalled()
  })

  it("o 403 do login leva o e-mail digitado para o reenvio — e o usuário, não", async () => {
    http.post.mockRejectedValue({ response: { status: 403, headers: { "x-error-code": "email_not_verified" }, data: { message: "Confirme seu e-mail." } } })
    montar()
    preencher(/E-mail ou usuário/i, "ana@exemplo.com")
    submeter(preencher(/^Senha$/i, "x"))
    fireEvent.click(await screen.findByRole("button", { name: /Reenviar e-mail de verificação/i }))
    expect((screen.getByLabelText(/Não recebeu\?/i) as HTMLInputElement).value).toBe("ana@exemplo.com")

    // O campo aceita e-mail OU usuário; "fulana" não é um e-mail para reenviar.
    cleanup()
    montar()
    preencher(/E-mail ou usuário/i, "fulana")
    submeter(preencher(/^Senha$/i, "x"))
    fireEvent.click(await screen.findByRole("button", { name: /Reenviar e-mail de verificação/i }))
    expect((screen.getByLabelText(/Não recebeu\?/i) as HTMLInputElement).value).toBe("")
  })
})

describe("ModalDeEntrada — o código-fonte da instalação (AGPL §13)", () => {
  // Quem usa a instalação pela rede acha o código dela antes mesmo de entrar;
  // sem CODIGO_FONTE_URL não há link, porque o código não traz endereço nenhum.
  it("com a URL no provider, o cabeçalho tem o link, que abre fora", () => {
    render(
      <CodigoFonteProvider url="https://codigo.example.org/fulana/atlans">
        <ModalDeEntrada modo="entrar" onFechar={onFechar} onEntrou={onEntrou} />
      </CodigoFonteProvider>,
    )
    const link = screen.getByRole("link", { name: "Código-fonte" })
    expect(link.getAttribute("href")).toBe("https://codigo.example.org/fulana/atlans")
    expect(link.getAttribute("target")).toBe("_blank")
    expect(link.getAttribute("rel")).toContain("noopener")
  })

  it("sem a URL, nenhum link", () => {
    montar()
    expect(screen.queryByRole("link", { name: "Código-fonte" })).toBeNull()
  })
})

describe("ModalDeEntrada — o nome da instalação no cabeçalho", () => {
  it("sem NOME_NA_TELA mostra «Atlans»; com ela, o nome da instalação", () => {
    montar()
    expect(screen.getByText(/^\s*Atlans\s*$/)).toBeTruthy()
    cleanup()
    render(
      <NomeNaTelaProvider nome="Geo Exemplo">
        <ModalDeEntrada modo="entrar" onFechar={onFechar} onEntrou={onEntrou} />
      </NomeNaTelaProvider>,
    )
    expect(screen.getByText(/Geo Exemplo/)).toBeTruthy()
  })
})
