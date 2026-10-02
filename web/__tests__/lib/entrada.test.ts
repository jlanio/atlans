/**
 * Os caminhos da entrada: só um caminho interno serve de volta (open redirect),
 * e "ir para o login" é "ir para a Home com o modal aberto".
 */
import { describe, it, expect } from "vitest"
import { caminhoInterno, destinoDaEntrada, destinoDaRedefinicao, destinoDaVerificacao, ehPainelDeEmail } from "@/lib/entrada"

describe("caminhoInterno", () => {
  it("aceita um caminho interno", () => {
    expect(caminhoInterno("/projects")).toBe("/projects")
    expect(caminhoInterno("/")).toBe("/")
    expect(caminhoInterno("/workflow/abc?x=1")).toBe("/workflow/abc?x=1")
  })

  it("rejeita o que levaria a outro host, o que não é string e o vazio", () => {
    for (const v of ["//evil.example", "/\\evil.example", "https://evil.example/x", "projects", "", null, undefined, 42, ["/projects"]]) {
      expect(caminhoInterno(v), String(v)).toBeUndefined()
    }
  })

  it("rejeita caracteres de controle que o navegador remove (TAB/CR/LF → open redirect)", () => {
    for (const v of ["/\t/evil.example", "/\n//evil.example", "/\r/evil", "/x\u0000/y", "/\u0009evil"]) {
      expect(caminhoInterno(v), JSON.stringify(v)).toBeUndefined()
    }
  })
})

describe("destinoDaEntrada", () => {
  it("é a Home com o modal aberto no modo pedido", () => {
    expect(destinoDaEntrada("entrar")).toBe("/?entrar=1")
    expect(destinoDaEntrada("cadastro")).toBe("/?cadastro=1")
  })

  it("leva o callbackUrl só quando é interno e não é a própria Home", () => {
    expect(destinoDaEntrada("entrar", "/projects")).toBe("/?entrar=1&callbackUrl=%2Fprojects")
    expect(destinoDaEntrada("entrar", "/")).toBe("/?entrar=1")
    expect(destinoDaEntrada("entrar", "//evil.example")).toBe("/?entrar=1")
    expect(destinoDaEntrada("entrar", undefined)).toBe("/?entrar=1")
  })
})

describe("destinoDaRedefinicao", () => {
  it("leva o token do e-mail para o painel de nova senha", () => {
    expect(destinoDaRedefinicao("tok-123")).toBe("/?redefinir=1&token=tok-123")
  })

  it("escapa o token, que vem de fora", () => {
    expect(destinoDaRedefinicao("a b&c=d")).toBe("/?redefinir=1&token=a+b%26c%3Dd")
  })

  it("sem token não há o que redefinir: cai no painel que pede um link novo", () => {
    expect(destinoDaRedefinicao()).toBe("/?recuperar=1")
    expect(destinoDaRedefinicao("")).toBe("/?recuperar=1")
  })
})

describe("destinoDaVerificacao", () => {
  it("leva o token do e-mail para o painel de verificação", () => {
    expect(destinoDaVerificacao("tok-abc")).toBe("/?verificar=1&token=tok-abc")
  })

  it("escapa o token, que vem de fora", () => {
    expect(destinoDaVerificacao("a b&c=d")).toBe("/?verificar=1&token=a+b%26c%3Dd")
  })

  it("sem token, é a tela de 'abra o link do e-mail', com o reenvio", () => {
    expect(destinoDaVerificacao()).toBe("/?verificar=1")
    expect(destinoDaVerificacao("")).toBe("/?verificar=1")
  })
})

describe("ehPainelDeEmail", () => {
  it("são os painéis que vêm de um link de e-mail", () => {
    expect(ehPainelDeEmail("recuperar")).toBe(true)
    expect(ehPainelDeEmail("redefinir")).toBe(true)
    expect(ehPainelDeEmail("verificar")).toBe(true)
  })

  it("o portão de login não: entrar e cadastro só abrem sem sessão", () => {
    expect(ehPainelDeEmail("entrar")).toBe(false)
    expect(ehPainelDeEmail("cadastro")).toBe(false)
    expect(ehPainelDeEmail(null)).toBe(false)
    expect(ehPainelDeEmail(undefined)).toBe(false)
  })
})
