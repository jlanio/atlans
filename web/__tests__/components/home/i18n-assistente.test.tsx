/**
 * A Home em três idiomas — o que o dicionário e as funções puras garantem:
 * as mesmas chaves nos três (o `typeof pt` já cobra na compilação; aqui é a
 * rede em tempo de execução, incluindo o que é `Record`), nenhum texto vazio,
 * e o português idêntico ao de antes nas funções que ganharam idioma.
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { textosDe, useTextos } from "@/app/components/home/i18n"
import { rotuloDaFerramenta } from "@/app/components/home/assistente/rotulos"
import { descreverAlvo } from "@/app/components/home/assistente/cartao-confirmacao"
import { etapaDaConversa } from "@/app/components/home/assistente/etapa"
import { textoDoErro } from "@/app/components/home/assistente/conversa"
import { detalheDaCota } from "@/app/components/home/assistente/uso-da-cota"
import { quandoReabre } from "@/app/components/home/assistente/aviso-de-cota"
import { comReferencia, sugestaoParaAnexos } from "@/app/components/home/assistente/anexos"
import { EscopoPelaRota, IdiomaProvider } from "@/context/IdiomaContext"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import type { Anexo } from "@/app/stores/homeStore"

const rota = vi.hoisted(() => ({ atual: "/" }))
vi.mock("next/navigation", () => ({ usePathname: () => rota.atual }))

/** Todas as folhas (caminho → valor), descendo em objetos e listas. */
function folhas(valor: unknown, caminho = ""): Array<[string, unknown]> {
  if (valor && typeof valor === "object") {
    return Object.entries(valor).flatMap(([k, v]) => folhas(v, caminho ? `${caminho}.${k}` : k))
  }
  return [[caminho, valor]]
}

describe("dicionário da Home", () => {
  it("inglês e espanhol têm exatamente as chaves do português", () => {
    const chaves = (idioma: "pt-BR" | "en" | "es") => folhas(textosDe(idioma)).map(([c]) => c).sort()
    expect(chaves("en")).toEqual(chaves("pt-BR"))
    expect(chaves("es")).toEqual(chaves("pt-BR"))
  })

  it("nenhum texto vazio (a dica vazia dos erros é a única ausência permitida)", () => {
    for (const idioma of ["pt-BR", "en", "es"] as const) {
      for (const [caminho, valor] of folhas(textosDe(idioma))) {
        if (caminho.startsWith("assistente.erros.") && caminho.endsWith(".hint")) continue
        if (typeof valor === "string") expect(valor.trim(), `${idioma}:${caminho}`).not.toBe("")
      }
    }
  })

  it("as sugestões e os chips têm o mesmo tamanho nos três (o ciclo da barra depende disso)", () => {
    const pt = textosDe("pt-BR").assistente.barra
    for (const idioma of ["en", "es"] as const) {
      expect(textosDe(idioma).assistente.barra.sugestoes).toHaveLength(pt.sugestoes.length)
      expect(textosDe(idioma).assistente.barra.chips).toHaveLength(pt.chips.length)
    }
  })
})

describe("rótulos das ferramentas", () => {
  it("português de sempre por padrão; inglês e espanhol quando pedido", () => {
    expect(rotuloDaFerramenta("search_nodes")).toBe("Procurando nós")
    expect(rotuloDaFerramenta("search_nodes", "en")).toBe("Searching nodes")
    expect(rotuloDaFerramenta("run_workflow", "es")).toBe("Ejecutando el flujo")
  })

  it("as ferramentas de fonte externa não vazam mais o nome cru da API", () => {
    for (const nome of ["search_sources", "describe_source", "probe_source", "register_source"]) {
      for (const idioma of ["pt-BR", "en", "es"] as const) {
        expect(rotuloDaFerramenta(nome, idioma), `${idioma}:${nome}`).not.toBe(nome)
      }
    }
  })

  it("nome desconhecido volta cru — inclusive os do protótipo de Object", () => {
    expect(rotuloDaFerramenta("ferramenta_nova")).toBe("ferramenta_nova")
    expect(rotuloDaFerramenta("toString", "en")).toBe("toString")
  })
})

describe("confirmação, etapa e erros", () => {
  it("descreverAlvo: rótulos e sim/não no idioma, português por padrão", () => {
    const args = { workflow_name: "Focos", active: true }
    expect(descreverAlvo(args)).toEqual([["Fluxo", "Focos"], ["Ativo", "sim"]])
    expect(descreverAlvo(args, "en")).toEqual([["Workflow", "Focos"], ["Active", "yes"]])
    expect(descreverAlvo(args, "es")).toEqual([["Flujo", "Focos"], ["Activo", "sí"]])
  })

  it("etapaDaConversa: o 'pensando' no idioma", () => {
    const turnos: TurnoDoAssistente[] = [{ id: "a", papel: "assistant", blocos: [] }]
    expect(etapaDaConversa(turnos, true)?.rotulo).toBe("Pensando")
    expect(etapaDaConversa(turnos, true, "en")?.rotulo).toBe("Thinking")
  })

  it("textoDoErro: em português a mensagem do servidor COMO VEIO", () => {
    const erro = { code: "loop_limit", message: "A conversa passou de 28 rodadas de ferramenta sem concluir.", hint: "dica do servidor", teto: 28 }
    expect(textoDoErro(erro, "pt-BR")).toEqual({ message: erro.message, hint: "dica do servidor" })
  })

  it("textoDoErro: em inglês/espanhol o código conhecido vira o texto do idioma, com o teto", () => {
    const erro = { code: "loop_limit", message: "A conversa passou de 28 rodadas…", teto: 28 }
    expect(textoDoErro(erro, "en").message).toBe("The chat went past 28 tool rounds without finishing.")
    expect(textoDoErro(erro, "es").message).toContain("28")
    // Sem teto no quadro (backend antigo): a frase sem número.
    expect(textoDoErro({ code: "loop_limit", message: "…" }, "en").message).not.toMatch(/\d/)
  })

  it("textoDoErro: a cota diária não vira 'espere um instante'", () => {
    // `rate_limited` no stream é a cota DIÁRIA; o 429 da rota é outro código.
    const cota = { code: "rate_limited", message: "Você atingiu a cota diária do assistente.", hint: "a cota reabre…" }
    expect(textoDoErro(cota, "en")).toEqual({
      message: "You’ve used up the assistant’s daily quota.",
      hint: "the quota reopens 24 hours after your first chat",
    })
    expect(textoDoErro(cota, "es").message).toBe("Alcanzaste la cuota diaria del asistente.")
    expect(textoDoErro({ code: "muitas_requisicoes", message: "…" }, "en").message)
      .toBe("Too many messages in a short time. Please wait a moment.")
  })

  it("textoDoErro: a conversa travada por outra aba sai no idioma", () => {
    // A trava da conversa (assistente_service.trava_exclusiva) — recusa fixa do servidor.
    const trava = {
      code: "conversa_em_andamento",
      message: "Já há uma conversa em andamento para este fluxo.",
      hint: "espere a resposta terminar, ou recarregue a aba que ficou aberta",
    }
    expect(textoDoErro(trava, "pt-BR")).toEqual({ message: trava.message, hint: trava.hint })
    expect(textoDoErro(trava, "en")).toEqual({
      message: "A reply is already in progress in this chat.",
      hint: "wait for it to finish, or reload the other open tab",
    })
    expect(textoDoErro(trava, "es").message).toBe("Ya hay una respuesta en curso en esta conversación.")
  })

  it("textoDoErro: código desconhecido aparece como veio", () => {
    const erro = { code: "coisa_nova", message: "Mensagem nova do servidor.", hint: "h" }
    expect(textoDoErro(erro, "en")).toEqual({ message: "Mensagem nova do servidor.", hint: "h" })
  })
})

describe("cota e anexos", () => {
  const cota = { gasto: 1284, teto: 10000, reabre_em_segundos: 3600 }

  it("detalheDaCota: português de sempre; inglês com o separador de milhar do idioma", () => {
    expect(detalheDaCota(cota)).toBe("1.284 de 10.000 tokens (13%) · a janela renova em 1 h.")
    expect(detalheDaCota(cota, "en")).toBe("1,284 of 10,000 tokens (13%) · the window renews in 1 h.")
  })

  it("quandoReabre: no idioma", () => {
    expect(quandoReabre(cota)).toBe("Ela reabre em 1 h.")
    expect(quandoReabre(cota, "es")).toBe("Se reabre en 1 h.")
    expect(quandoReabre({ ...cota, reabre_em_segundos: null }, "en")).toBe("It reopens a few hours after your first chat.")
  })

  const pronto = (nome: string): Anexo => ({ id: nome, nome, bytes: 1, estado: "pronto" })

  it("a referência aos anexos vai na língua da pessoa (ela a vê na bolha)", () => {
    expect(comReferencia("", [pronto("a.shp")])).toBe("Arquivos que acabei de enviar ao Drive deste workspace: a.shp")
    expect(comReferencia("oi", [pronto("a.shp")], "en")).toBe("oi\n\nFiles I just uploaded to this workspace’s Drive: a.shp")
  })

  it("a sugestão de anexos, com o plural do idioma", () => {
    expect(sugestaoParaAnexos([pronto("a.shp"), pronto("b.shp")])).toBe("Analise a.shp e mais 1 arquivo")
    expect(sugestaoParaAnexos([pronto("a.shp"), pronto("b.shp"), pronto("c.shp")], "en")).toBe("Analyze a.shp and 2 more files")
    expect(sugestaoParaAnexos([pronto("a.shp")], "es")).toBe("Analiza a.shp")
  })
})

describe("o escopo: só a Home segue o idioma", () => {
  function Rotulo() {
    return <span>{useTextos().casca.barraLateral.novaConversa}</span>
  }
  const montar = () =>
    render(
      <IdiomaProvider inicial={{ idioma: "en", detectado: "en", escolhido: "en" }}>
        <EscopoPelaRota>
          <Rotulo />
        </EscopoPelaRota>
      </IdiomaProvider>,
    )

  it("na Home (`/`) o texto segue o idioma da pessoa", () => {
    rota.atual = "/"
    montar()
    expect(screen.getByText("New chat")).toBeTruthy()
  })

  it("fora da Home o componente compartilhado continua em português", () => {
    rota.atual = "/projects"
    montar()
    expect(screen.getByText("Nova conversa")).toBeTruthy()
  })
})
