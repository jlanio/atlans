import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"

/**
 * The sign-in modal in English and Spanish. With the `LanguageProvider`, what the
 * Home chooses — titles, supporting sentences, labels, hints, buttons and the errors
 * built on the client — follows the language; the message the SERVER returns
 * shows up as it came. Portuguese (no provider) is covered by modal-de-entrada.test.
 */
const http = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock("axios", () => {
  class AxiosError extends Error {}
  return { default: { post: http.post, get: http.get }, AxiosError }
})
const auth = vi.hoisted(() => ({ signIn: vi.fn() }))
vi.mock("next-auth/react", () => ({ signIn: auth.signIn }))

import ModalDeEntrada from "@/app/components/home/entrada/modal-de-entrada"
import * as entrada from "@/app/components/home/i18n/secoes/entrada"
import { LanguageProvider } from "@/context/IdiomaContext"
import type { Idioma } from "@/lib/idioma"

beforeEach(() => {
  cleanup()
  http.post.mockReset()
  http.get.mockReset()
  auth.signIn.mockReset()
})
afterEach(cleanup)

function montar(idioma: Idioma, props: Partial<React.ComponentProps<typeof ModalDeEntrada>> = {}) {
  return render(
    <LanguageProvider inicial={{ idioma, detectado: idioma, escolhido: idioma }}>
      <ModalDeEntrada modo="entrar" onFechar={() => {}} onEntrou={() => {}} {...props} />
    </LanguageProvider>,
  )
}

// `selector: "input"`: in the new password panel the dialog title and the field
// label are the same text.
function campo(rotulo: string) {
  return screen.getByLabelText(rotulo, { selector: "input" }) as HTMLInputElement
}

function preencher(rotulo: string, valor: string) {
  const alvo = campo(rotulo)
  fireEvent.change(alvo, { target: { value: valor } })
  return alvo
}

function submeter(alvo: HTMLElement) {
  fireEvent.submit(alvo.closest("form")!)
}

function textos(o: unknown): string[] {
  if (typeof o === "string") return [o]
  if (o && typeof o === "object") return Object.values(o).flatMap(textos)
  return []
}

/** No Portuguese sign-in text on screen — except what is the same in both languages ("Enviando…"). */
function withoutPortuguese(idioma: "en" | "es", texto: string) {
  const fromLanguage = new Set(textos(entrada[idioma]))
  for (const pt of textos(entrada.pt)) {
    if (!fromLanguage.has(pt)) expect(texto, pt).not.toContain(pt)
  }
}

/** The body the server's `http_exception_handler` writes — the one for every refusal of ITS OWN. */
function fromServer(status: number, message: string, headers: Record<string, string> = {}) {
  return { response: { status, headers, data: { error: "http_exception", message, status_code: status } } }
}

// What is NOT a server refusal: the per-IP limiter, the /terra proxy being
// down, the unexpected 500 and a CDN's error page.
const RATE_LIMITER_429 = { response: { status: 429, headers: {}, data: { detail: "Too Many Requests" } } }
const PROXY_502 = { response: { status: 502, headers: {}, data: { detail: "Serviço indisponível" } } }
const UNEXPECTED_500 = {
  response: { status: 500, headers: {}, data: { error: "internal_server_error", message: "Unexpected error occurred" } },
}
const CDN_403 = { response: { status: 403, headers: {}, data: "<html><body>Access denied</body></html>" } }

const EXPECTED = {
  en: {
    tituloEntrar: "Sign in",
    apoioEntrar: "Sign in to continue.",
    identificador: "Email or username",
    senha: "Password",
    esqueceu: "Forgot your password?",
    entrar: "Sign in",
    naoTemConta: "Don’t have an account?",
    criarConta: "Sign up",
    semConexao: "Can’t reach the server. Check your network.",
    erroAoEntrar: "Something went wrong while signing in.",
    erroDeSessao: "Couldn’t start your session. Please try again.",
    credenciais: "Invalid credentials.",
    naoVerificado: "Email not verified. Check your inbox or request a new link.",
    bloqueada15: "Try again in 15 minutes.",
    bloqueada2: "Account locked after too many attempts. Try again in 2 minutes.",
    bloqueadaSemPrazo: "Account locked after too many attempts. Try again later.",
    contaIndisponivel: "This account can’t sign in. Contact the administrator.",
    limitePorConexao: "Too many sign-in attempts from this connection. Wait a minute and try again.",
    linkMuitasTentativas: "Too many attempts. Wait a minute and try again.",
    servidorIndisponivel: "Couldn’t reach the server. Try again in a moment.",
    jaEmUso: "Username or email already in use.",
    erroAoCriarConta: "Couldn’t create your account. Please try again.",
    reenviado: "If the email is registered and not yet verified, a new link will be sent.",
    tituloCadastro: "Create account",
    apoioCadastro: "Fill in your details to sign up.",
    usuario: "Username",
    regraDoUsuario: "Only lowercase letters, numbers, and underscores (_)",
    exemploDeUsuario: "lowercase letters, numbers, and _",
    email: "Email",
    confirmarSenha: "Confirm password",
    senhasNaoCoincidem: "Passwords don’t match.",
    cadastrar: "Create account",
    jaTemConta: "Already have an account?",
    irParaEntrar: "Sign in",
    muitasTentativas: "Too many sign-up attempts. Please wait and try again.",
    tituloRecuperar: "Forgot your password?",
    enviarLink: "Send reset link",
    avisoDoLink: "check your spam folder",
    voltarParaEntrar: "Back to sign in",
    tituloRedefinir: "New password",
    novaSenha: "New password",
    confirmarNovaSenha: "Confirm new password",
    redefinirSenha: "Reset password",
    linkInvalido: "This reset link is invalid or has already been used.",
    pedirLinkNovo: "Request a new link",
    tituloVerificar: "Verify your email",
    abraOLink: "Open the link in the email to activate your account.",
    naoRecebeu: "Didn’t get it? Resend to:",
    exemploDeEmail: "you@example.com",
    erroAoReenviar: "Couldn’t resend. Please try again.",
    jaVerifiquei: "Already verified: sign in",
    tituloFalhou: "Verification failed",
    tokenInvalido: "Invalid or expired token.",
    reenviarPara: "Resend verification to:",
  },
  es: {
    tituloEntrar: "Iniciar sesión",
    apoioEntrar: "Inicia sesión para continuar.",
    identificador: "Correo o nombre de usuario",
    senha: "Contraseña",
    esqueceu: "¿Olvidaste tu contraseña?",
    entrar: "Iniciar sesión",
    naoTemConta: "¿No tienes una cuenta?",
    criarConta: "Regístrate",
    semConexao: "Sin conexión con el servidor. Revisa tu red.",
    erroAoEntrar: "Ocurrió un error al intentar iniciar sesión.",
    erroDeSessao: "No se pudo iniciar la sesión. Inténtalo de nuevo.",
    credenciais: "Credenciales inválidas.",
    naoVerificado: "Correo no verificado. Revisa tu bandeja de entrada o solicita un nuevo enlace.",
    bloqueada15: "Inténtalo de nuevo en 15 minutos.",
    bloqueada2: "Cuenta bloqueada por demasiados intentos. Inténtalo de nuevo en 2 minutos.",
    bloqueadaSemPrazo: "Cuenta bloqueada por demasiados intentos. Inténtalo de nuevo más tarde.",
    contaIndisponivel: "Esta cuenta no puede iniciar sesión. Contacta al administrador.",
    limitePorConexao: "Demasiados intentos de inicio de sesión desde esta conexión. Espera un minuto e inténtalo de nuevo.",
    linkMuitasTentativas: "Demasiados intentos. Espera un minuto e inténtalo de nuevo.",
    servidorIndisponivel: "No se pudo contactar con el servidor. Inténtalo de nuevo en unos instantes.",
    jaEmUso: "Usuario o correo ya en uso.",
    erroAoCriarConta: "No se pudo crear la cuenta. Inténtalo de nuevo.",
    reenviado: "Si el correo está registrado y sin verificar, se enviará un nuevo enlace.",
    tituloCadastro: "Crear cuenta",
    apoioCadastro: "Completa tus datos para registrarte.",
    usuario: "Nombre de usuario",
    regraDoUsuario: "Solo letras minúsculas, números y guion bajo (_)",
    exemploDeUsuario: "letras minúsculas, números y _",
    email: "Correo",
    confirmarSenha: "Confirmar contraseña",
    senhasNaoCoincidem: "Las contraseñas no coinciden.",
    cadastrar: "Crear cuenta",
    jaTemConta: "¿Ya tienes una cuenta?",
    irParaEntrar: "Inicia sesión",
    muitasTentativas: "Demasiados intentos de registro. Espera un momento e inténtalo de nuevo.",
    tituloRecuperar: "¿Olvidaste tu contraseña?",
    enviarLink: "Enviar enlace de restablecimiento",
    avisoDoLink: "revisa la carpeta de spam",
    voltarParaEntrar: "Volver a iniciar sesión",
    tituloRedefinir: "Nueva contraseña",
    novaSenha: "Nueva contraseña",
    confirmarNovaSenha: "Confirmar nueva contraseña",
    redefinirSenha: "Restablecer contraseña",
    linkInvalido: "Este enlace de restablecimiento no es válido o ya se usó.",
    pedirLinkNovo: "Solicitar un enlace nuevo",
    tituloVerificar: "Verifica tu correo",
    abraOLink: "Abre el enlace del correo electrónico para activar tu cuenta.",
    naoRecebeu: "¿No lo recibiste? Reenvíalo a:",
    exemploDeEmail: "tu@correo.com",
    erroAoReenviar: "No se pudo reenviar. Inténtalo de nuevo.",
    jaVerifiquei: "Ya verifiqué: iniciar sesión",
    tituloFalhou: "Falló la verificación",
    tokenInvalido: "Token inválido o expirado.",
    reenviarPara: "Reenviar verificación a:",
  },
} satisfies Record<"en" | "es", Record<string, string>>

describe.each(["en", "es"] as const)("entrada em %s", (idioma) => {
  const txt = EXPECTED[idioma]

  it("entrar: título, apoio, rótulos, botões e rodapé — sem português", () => {
    montar(idioma)
    const dialogo = screen.getByRole("dialog", { name: txt.tituloEntrar })
    expect(dialogo.textContent).toContain(txt.apoioEntrar)
    expect(campo(txt.identificador)).toBeTruthy()
    expect(campo(txt.senha)).toBeTruthy()
    expect(screen.getByRole("button", { name: txt.esqueceu })).toBeTruthy()
    expect(screen.getByRole("button", { name: txt.entrar })).toBeTruthy()
    expect(dialogo.textContent).toContain(txt.naoTemConta)
    withoutPortuguese(idioma, dialogo.textContent ?? "")

    fireEvent.click(screen.getByRole("button", { name: txt.criarConta }))
    expect(screen.getByRole("dialog", { name: txt.tituloCadastro })).toBeTruthy()
  })

  it("entrar: os erros montados no cliente seguem o idioma", async () => {
    http.post.mockRejectedValueOnce({})
    montar(idioma)
    preencher(txt.identificador, "fulana")
    const senha = preencher(txt.senha, "x")
    submeter(senha)
    expect((await screen.findByRole("alert")).textContent).toContain(txt.semConexao)

    // The server refused without saying why: the message is ours.
    http.post.mockRejectedValueOnce({ response: { status: 500, headers: {}, data: {} } })
    submeter(senha)
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(txt.erroAoEntrar))

    // O POST passou e o signIn falhou.
    http.post.mockResolvedValueOnce({ data: { access_token: "a", refresh_token: "r" } })
    auth.signIn.mockResolvedValueOnce({ ok: false, error: "CredentialsSignin" })
    submeter(senha)
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(txt.erroDeSessao))
  })

  it("entrar: as recusas fixas do servidor saem no idioma; uma desconhecida, como veio", async () => {
    // The server only speaks Portuguese. The login's FIXED refusals have the text in the
    // language, chosen by the status (and by X-Error-Code); the rest passes through.
    montar(idioma)
    preencher(txt.identificador, "fulana")
    const senha = preencher(txt.senha, "x")
    const alerta = () => screen.getByRole("alert").textContent ?? ""
    const recusa = async (erro: unknown, esperado: string) => {
      http.post.mockRejectedValueOnce(erro)
      submeter(senha)
      await waitFor(() => expect(alerta()).toContain(esperado))
      withoutPortuguese(idioma, alerta())
    }

    await recusa(fromServer(401, "Credenciais inválidas."), txt.credenciais)
    await recusa(
      fromServer(403, "E-mail não verificado. Verifique sua caixa de entrada.", { "x-error-code": "email_not_verified" }),
      txt.naoVerificado,
    )
    // Suspended, deleted or deactivated: the status does not say which.
    await recusa(fromServer(403, "Conta suspensa. Entre em contato com o administrador."), txt.contaIndisponivel)
    expect(alerta()).not.toMatch(/Conta suspensa/)

    // A server refusal the screen does not know passes through as it came.
    http.post.mockRejectedValueOnce(fromServer(400, "Mensagem nova do servidor."))
    submeter(senha)
    await waitFor(() => expect(alerta()).toContain("Mensagem nova do servidor."))
  })

  it("entrar: o que não é recusa do servidor não vira recusa da conta", async () => {
    // The proxy being down, the unexpected 500 and a CDN's page: neither their
    // text (the proxy's is Portuguese), nor "esta conta não pode entrar" (this account cannot sign in).
    montar(idioma)
    preencher(txt.identificador, "fulana")
    const senha = preencher(txt.senha, "x")
    const alerta = () => screen.getByRole("alert").textContent ?? ""
    for (const erro of [PROXY_502, UNEXPECTED_500, CDN_403]) {
      http.post.mockRejectedValueOnce(erro)
      submeter(senha)
      await waitFor(() => expect(alerta()).toContain(txt.erroAoEntrar))
      expect(alerta()).not.toContain(txt.contaIndisponivel)
      expect(alerta()).not.toMatch(/Serviço indisponível|Unexpected|Access denied/)
    }
  })

  it.each([
    ["o bloqueio da conta, com os minutos do Retry-After (arredondados para cima)", "61", "bloqueada2"],
    ["o bloqueio da conta sem Retry-After", null, "bloqueadaSemPrazo"],
  ] as const)("entrar: %s", async (_, retryAfter, chave) => {
    http.post.mockRejectedValueOnce(
      fromServer(429, "Conta bloqueada por excesso de tentativas. Tente novamente em 2 minuto(s).", retryAfter ? { "retry-after": retryAfter } : {}),
    )
    montar(idioma)
    preencher(txt.identificador, "fulana")
    submeter(preencher(txt.senha, "x"))
    const alerta = await screen.findByRole("alert")
    expect(alerta.textContent).toContain(txt[chave])
    expect(alerta.textContent).not.toMatch(/Conta bloqueada/)
    // The block locks the button.
    expect((screen.getByRole("button", { name: txt.entrar }) as HTMLButtonElement).disabled).toBe(true)
  })

  it("entrar: o 429 do limitador por conexão não diz que a conta foi bloqueada", async () => {
    http.post.mockRejectedValueOnce(RATE_LIMITER_429)
    montar(idioma)
    preencher(txt.identificador, "fulana")
    submeter(preencher(txt.senha, "x"))
    const alerta = await screen.findByRole("alert")
    expect(alerta.textContent).toContain(txt.limitePorConexao)
    expect(alerta.textContent).not.toContain(txt.bloqueadaSemPrazo)
  })

  it("cadastro: o 'já em uso' do servidor sai no idioma; o proxy fora do ar, no texto do idioma", async () => {
    http.post.mockRejectedValueOnce(fromServer(400, "Usuário ou e-mail já em uso."))
    montar(idioma, { modo: "cadastro" })
    preencher(txt.usuario, "fulana")
    preencher(txt.email, "fulana@exemplo.com")
    preencher(txt.senha, "S3nha-forte")
    const confirmar = preencher(txt.confirmarSenha, "S3nha-forte")
    submeter(confirmar)
    expect((await screen.findByRole("alert")).textContent).toContain(txt.jaEmUso)

    // The proxy being down, and the 500 from the database permission — which carries `message`,
    // in Portuguese, and is not a sign-up refusal.
    const permissao = {
      response: {
        status: 500,
        headers: {},
        data: { error: "database_permission_denied", message: "O usuário do banco de dados da API não tem privilégio." },
      },
    }
    for (const erro of [PROXY_502, permissao]) {
      http.post.mockRejectedValueOnce(erro)
      submeter(confirmar)
      await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(txt.erroAoCriarConta))
      expect(screen.getByRole("alert").textContent).not.toMatch(/banco de dados|Serviço indisponível/)
    }
  })

  it("verificar: o 'link reenviado' do servidor sai no idioma", async () => {
    http.post.mockResolvedValueOnce({ data: { message: "Se o e-mail estiver cadastrado e não verificado, um novo link será enviado." } })
    montar(idioma, { modo: "verificar" })
    submeter(preencher(txt.naoRecebeu, "ana@exemplo.com"))
    expect((await screen.findByRole("status")).textContent).toContain(txt.reenviado)
  })

  it("cadastro: rótulos, regra e exemplo do usuário, senhas diferentes e o rodapé", async () => {
    montar(idioma, { modo: "cadastro" })
    const dialogo = screen.getByRole("dialog", { name: txt.tituloCadastro })
    expect(dialogo.textContent).toContain(txt.apoioCadastro)
    const usuario = preencher(txt.usuario, "fulana")
    expect(usuario.getAttribute("title")).toBe(txt.regraDoUsuario)
    expect(usuario.getAttribute("placeholder")).toBe(txt.exemploDeUsuario)
    preencher(txt.email, "fulana@exemplo.com")
    preencher(txt.senha, "S3nha-forte")
    submeter(preencher(txt.confirmarSenha, "outra"))

    expect((await screen.findByRole("alert")).textContent).toContain(txt.senhasNaoCoincidem)
    // O aviso sob o campo e o erro do envio.
    expect(screen.getAllByText(txt.senhasNaoCoincidem)).toHaveLength(2)
    expect(http.post).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: txt.cadastrar })).toBeTruthy()
    expect(dialogo.textContent).toContain(txt.jaTemConta)
    withoutPortuguese(idioma, dialogo.textContent ?? "")

    fireEvent.click(screen.getByRole("button", { name: txt.irParaEntrar }))
    expect(screen.getByRole("dialog", { name: txt.tituloEntrar })).toBeTruthy()
  })

  it("cadastro: o 429 sem mensagem do servidor cai no texto do idioma", async () => {
    http.post.mockRejectedValue({ response: { status: 429, data: {} } })
    montar(idioma, { modo: "cadastro" })
    preencher(txt.usuario, "fulana")
    preencher(txt.email, "fulana@exemplo.com")
    preencher(txt.senha, "S3nha-forte")
    submeter(preencher(txt.confirmarSenha, "S3nha-forte"))
    expect((await screen.findByRole("alert")).textContent).toContain(txt.muitasTentativas)
  })

  it("recuperar: o pedido, o aviso da caixa de entrada e a volta ao login", async () => {
    http.post.mockResolvedValue({ data: {} })
    montar(idioma, { modo: "recuperar" })
    expect(screen.getByRole("dialog", { name: txt.tituloRecuperar })).toBeTruthy()
    expect(screen.getByRole("button", { name: txt.enviarLink })).toBeTruthy()
    withoutPortuguese(idioma, screen.getByRole("dialog").textContent ?? "")
    submeter(preencher(txt.email, "ana@exemplo.com"))
    expect(await screen.findByText(new RegExp(txt.avisoDoLink))).toBeTruthy()
    withoutPortuguese(idioma, screen.getByRole("dialog").textContent ?? "")
    fireEvent.click(screen.getByRole("button", { name: txt.voltarParaEntrar }))
    expect(screen.getByRole("dialog", { name: txt.tituloEntrar })).toBeTruthy()
  })

  it("redefinir: os rótulos e, sem token, o link inválido", () => {
    montar(idioma, { modo: "redefinir", tokenDoLink: "tok-123" })
    expect(screen.getByRole("dialog", { name: txt.tituloRedefinir })).toBeTruthy()
    preencher(txt.novaSenha, "senha-nova-1") // pragma: allowlist secret
    submeter(preencher(txt.confirmarNovaSenha, "outra-senha-9")) // pragma: allowlist secret
    expect(screen.getAllByText(txt.senhasNaoCoincidem).length).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: txt.redefinirSenha })).toBeTruthy()
    expect(http.post).not.toHaveBeenCalled()
    withoutPortuguese(idioma, screen.getByRole("dialog").textContent ?? "")

    cleanup()
    montar(idioma, { modo: "redefinir" })
    expect(screen.getByText(txt.linkInvalido)).toBeTruthy()
    expect(screen.getByRole("button", { name: txt.pedirLinkNovo })).toBeTruthy()
    withoutPortuguese(idioma, screen.getByRole("dialog").textContent ?? "")
  })

  it("redefinir: o token recusado pelo servidor sai no idioma", async () => {
    http.post.mockRejectedValueOnce(fromServer(400, "Token inválido ou expirado."))
    montar(idioma, { modo: "redefinir", tokenDoLink: "tok-velho" })
    preencher(txt.novaSenha, "Senha-nova-1") // pragma: allowlist secret
    const confirmar = preencher(txt.confirmarNovaSenha, "Senha-nova-1") // pragma: allowlist secret
    submeter(confirmar)
    expect((await screen.findByRole("alert")).textContent).toContain(txt.tokenInvalido)
    withoutPortuguese(idioma, screen.getByRole("dialog").textContent ?? "")

    http.post.mockRejectedValueOnce(RATE_LIMITER_429)
    submeter(confirmar)
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(txt.linkMuitasTentativas))
  })

  it("verificar sem token: 'abra o link', o exemplo de e-mail e o reenvio que falha", async () => {
    http.post.mockRejectedValue(new Error("500"))
    montar(idioma, { modo: "verificar" })
    expect(screen.getByRole("dialog", { name: txt.tituloVerificar })).toBeTruthy()
    expect(screen.getByText(new RegExp(txt.abraOLink))).toBeTruthy()
    const reenvio = preencher(txt.naoRecebeu, "ana@exemplo.com")
    expect(reenvio.getAttribute("placeholder")).toBe(txt.exemploDeEmail)
    submeter(reenvio)
    expect((await screen.findByRole("alert")).textContent).toContain(txt.erroAoReenviar)
    expect(screen.getByRole("button", { name: txt.jaVerifiquei })).toBeTruthy()
    withoutPortuguese(idioma, screen.getByRole("dialog").textContent ?? "")
  })

  it.each([
    ["o token recusado (400)", fromServer(400, "Token inválido ou expirado."), "tokenInvalido"],
    ["a conta que sumiu (404)", fromServer(404, "Usuário não encontrado."), "tokenInvalido"],
    ["o limite por conexão (429)", RATE_LIMITER_429, "linkMuitasTentativas"],
    ["o proxy fora do ar (502)", PROXY_502, "servidorIndisponivel"],
    ["sem resposta", new Error("Network Error"), "servidorIndisponivel"],
  ] as const)("verificar: %s sai no idioma, não no português do servidor", async (_, erro, chave) => {
    http.get.mockRejectedValue(erro)
    montar(idioma, { modo: "verificar", tokenDoLink: "tok-velho" })
    const alerta = await screen.findByRole("alert")
    expect(alerta.textContent).toContain(txt[chave])
    withoutPortuguese(idioma, alerta.textContent ?? "")
    expect(alerta.textContent).not.toMatch(/Token inválido ou expirado|Usuário não encontrado|Serviço indisponível/)
  })

  it("verificar: a tela da falha — título, reenvio e volta — no idioma", async () => {
    http.get.mockRejectedValue(fromServer(400, "Token inválido ou expirado."))
    montar(idioma, { modo: "verificar", tokenDoLink: "tok-velho" })
    expect((await screen.findByRole("alert")).textContent).toContain(txt.tokenInvalido)
    expect(await screen.findByRole("dialog", { name: txt.tituloFalhou })).toBeTruthy()
    expect(campo(txt.reenviarPara)).toBeTruthy()
    expect(screen.getByRole("button", { name: txt.voltarParaEntrar })).toBeTruthy()
  })
})

describe.each(["en", "es"] as const)("as peças de components/auth em %s", (idioma) => {
  const auth = entrada[idioma].auth
  const txt = EXPECTED[idioma]

  it("campo de senha: mostrar/ocultar e o aviso de Caps Lock", () => {
    montar(idioma)
    fireEvent.click(screen.getByRole("button", { name: auth.mostrarSenha }))
    expect(campo(txt.senha).type).toBe("text")
    expect(screen.getByRole("button", { name: auth.ocultarSenha })).toBeTruthy()

    fireEvent.keyDown(campo(txt.senha), { key: "A", modifierCapsLock: true })
    expect(screen.getByRole("status").textContent).toBe(auth.capsLock)
  })

  it("medidor de força: as regras no idioma", () => {
    montar(idioma, { modo: "cadastro" })
    preencher(txt.senha, "a")
    for (const regra of Object.values(auth.regrasDaSenha)) {
      expect(screen.getByText(regra)).toBeTruthy()
    }
  })

  it("o 403 de e-mail não verificado oferece o reenvio no idioma", async () => {
    http.post.mockRejectedValue({
      response: { status: 403, headers: { "x-error-code": "email_not_verified" }, data: {} },
    })
    montar(idioma)
    preencher(txt.identificador, "fulana")
    submeter(preencher(txt.senha, "x"))
    expect(await screen.findByRole("button", { name: auth.reenviarVerificacao })).toBeTruthy()
  })

  it("o X do diálogo se anuncia no idioma", () => {
    montar(idioma)
    const fechar = { en: "Close", es: "Cerrar" }[idioma]
    expect(screen.getByRole("button", { name: fechar })).toBeTruthy()
  })
})

describe("em português, a recusa do servidor como veio", () => {
  // Portuguese's byte-for-byte promise: no swapping the server's message
  // for the dictionary text. Each message here DIFFERS from the dictionary's, so
  // that a `traduzir` wired in by mistake shows up.
  const alerta = () => screen.getByRole("alert").textContent ?? ""

  it("entrar: 401, 403 (com e sem código) e o 429 do servidor", async () => {
    montar("pt-BR")
    preencher("E-mail ou usuário", "fulana")
    const senha = preencher("Senha", "x")
    for (const [erro, esperado] of [
      [fromServer(401, "Credenciais inválidas X."), "Credenciais inválidas X."],
      [fromServer(403, "Conta suspensa X."), "Conta suspensa X."],
      [fromServer(403, "E-mail não verificado X.", { "x-error-code": "email_not_verified" }), "E-mail não verificado X."],
      [PROXY_502, "Serviço indisponível"],
      [fromServer(429, "Conta bloqueada X.", { "retry-after": "61" }), "Conta bloqueada X."],
    ] as const) {
      http.post.mockRejectedValueOnce(erro)
      submeter(senha)
      await waitFor(() => expect(alerta()).toContain(esperado))
    }
  })

  it("cadastro: o 400 e o 429 do servidor", async () => {
    montar("pt-BR", { modo: "cadastro" })
    preencher("Usuário", "fulana")
    preencher("E-mail", "fulana@exemplo.com")
    preencher("Senha", "S3nha-forte")
    const confirmar = preencher("Confirmar senha", "S3nha-forte")
    for (const [erro, esperado] of [
      [fromServer(400, "Já em uso X."), "Já em uso X."],
      [fromServer(429, "Devagar X."), "Devagar X."],
    ] as const) {
      http.post.mockRejectedValueOnce(erro)
      submeter(confirmar)
      await waitFor(() => expect(alerta()).toContain(esperado))
    }
  })

  it("verificar e redefinir: o token recusado", async () => {
    http.get.mockRejectedValue(fromServer(400, "Token recusado X."))
    montar("pt-BR", { modo: "verificar", tokenDoLink: "tok-velho" })
    expect((await screen.findByRole("alert")).textContent).toContain("Token recusado X.")

    cleanup()
    http.post.mockRejectedValueOnce(fromServer(400, "Token recusado Y."))
    montar("pt-BR", { modo: "redefinir", tokenDoLink: "tok-velho" })
    preencher("Nova senha", "Senha-nova-1") // pragma: allowlist secret
    submeter(preencher("Confirmar nova senha", "Senha-nova-1")) // pragma: allowlist secret
    expect((await screen.findByRole("alert")).textContent).toContain("Token recusado Y.")
  })
})

describe("o dicionário da entrada", () => {
  function chaves(o: unknown, prefixo = ""): string[] {
    if (!o || typeof o !== "object") return [prefixo]
    return Object.entries(o).flatMap(([k, v]) => chaves(v, prefixo ? `${prefixo}.${k}` : k)).sort()
  }

  it("en e es têm as mesmas chaves do pt, e nenhum texto vazio", () => {
    expect(chaves(entrada.en)).toEqual(chaves(entrada.pt))
    expect(chaves(entrada.es)).toEqual(chaves(entrada.pt))
    for (const texto of [...textos(entrada.pt), ...textos(entrada.en), ...textos(entrada.es)]) {
      expect(texto.trim()).not.toBe("")
    }
  })

  it("com o provider em pt-BR, o português de sempre", () => {
    montar("pt-BR")
    expect(screen.getByRole("dialog", { name: "Entrar" }).textContent).toContain("Faça login para continuar.")
    expect(campo("E-mail ou usuário")).toBeTruthy()
  })
})
