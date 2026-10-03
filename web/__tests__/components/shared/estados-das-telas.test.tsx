/**
 * Screen states (contract screen-patterns.md §3 and §5), screen by screen.
 *
 * The error/empty card was re-copied in each `estados.tsx` (and inline in six
 * more screens), and the copies diverged: only Plans, Tokens and Admin ›
 * Settings announced the error (`role="alert"`, §5); Projects didn't paint the
 * destructive border; Credentials and Tokens had nowhere to put the server's
 * message. Here each screen is checked in the error state — announcement, title,
 * message, destructive frame and "Tentar de novo" (try again) — and, in the
 * empty and no-results states, that each one's text is still the usual one.
 * (An extension's screens are checked in its own folder, in `__tests__/extensoes/`.)
 */
import type { ReactElement } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"

import * as Credenciais from "@/app/components/credentials/estados"
import * as Tokens from "@/app/components/tokens/estados"
import * as Drive from "@/app/components/drive/estados"
import * as Usuarios from "@/app/components/admin/users/estados"
import * as Projetos from "@/app/components/projects/estados"
import * as Artefatos from "@/app/components/artifacts/estados"
import * as Executores from "@/app/components/executores/estados"
import * as Dashboard from "@/app/components/dashboard/estados"
import * as Configuracoes from "@/app/components/admin/settings/estados"
import { TabelaExecucoes } from "@/app/components/observability/tabela-execucoes"
import { VisaoExecutores } from "@/app/components/observability/visao-executores"
import { VisaoWorkflows } from "@/app/components/observability/visao-workflows"
import { TbDatabase } from "react-icons/tb"

afterEach(cleanup)

const MENSAGEM = "Serviço indisponível (503)"

const TABELA = {
  runs: [], total: 0, hasMore: false, carregando: false, carregandoMais: false, filtrado: false,
  onCarregarMais: () => {}, onAbrir: () => {},
}

type Caso = [tela: string, montar: (onTentar: () => void) => ReactElement, titulo: string, mensagem: string]

const ERROS: Caso[] = [
  ["Credenciais", t => <Credenciais.ErroDeCarga mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar as credenciais.", MENSAGEM],
  ["Tokens de acesso", t => <Tokens.ErroDeCarga mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar os tokens de acesso.", MENSAGEM],
  ["Drive", t => <Drive.ErroDeCarga mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar os arquivos", MENSAGEM],
  ["Admin › Usuários", t => <Usuarios.ErroDeCarga mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar os usuários", MENSAGEM],
  ["Projetos", t => <Projetos.ErroDeCarga mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar os projetos", MENSAGEM],
  ["Artefatos", t => <Artefatos.ErroDeCarga mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar os artefatos", MENSAGEM],
  ["Executores", t => <Executores.ErroDosExecutores mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar os executores", MENSAGEM],
  ["Dashboard", t => <Dashboard.ErroDoPainel mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar o painel", MENSAGEM],
  ["Admin › Configurações", t => <Configuracoes.CartaoDeErro mensagem={MENSAGEM} onTentar={t} />, "Não foi possível carregar as configurações", MENSAGEM],
  [
    "Histórico (tabela de execuções)",
    t => <TabelaExecucoes {...TABELA} falhou onRecarregar={t} />,
    "Não foi possível carregar as execuções",
    "A lista não está vazia — só não pôde ser lida agora.",
  ],
]

describe("erro de carga: cada tela anuncia a falha, com a mensagem, na moldura destrutiva", () => {
  it.each(ERROS)("%s", (_tela, montar, titulo, mensagem) => {
    const onTentar = vi.fn()
    render(montar(onTentar))

    // §5: `role="alert"` — the screen reader announces the failure right away.
    const alerta = screen.getByRole("alert")
    expect(alerta).toHaveTextContent(titulo)
    expect(alerta).toHaveTextContent(mensagem)
    // §3.2: the error frame is destructive, on the border and on the icon circle.
    expect(alerta).toHaveClass("border-destructive/20")

    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar de novo" }))
    expect(onTentar).toHaveBeenCalledTimes(1)
  })

  it.each([
    ["Credenciais", <Credenciais.ErroDeCarga key="c" onTentar={() => {}} />],
    ["Tokens de acesso", <Tokens.ErroDeCarga key="t" onTentar={() => {}} />],
  ])("%s: sem a mensagem do servidor, a frase de sempre", (_tela, elemento) => {
    render(elemento)
    expect(screen.getByRole("alert")).toHaveTextContent("Verifique a conexão e tente novamente.")
  })
})

describe("vazio e sem resultado: cada tela mantém o seu texto (e nada disso é alerta)", () => {
  it("Credenciais", () => {
    const onCriar = vi.fn()
    const { unmount } = render(<Credenciais.VazioPrimeiroUso canEdit onCriar={onCriar} />)
    expect(screen.getByText("Comece pela primeira credencial")).toBeInTheDocument()
    expect(screen.getByText(/Credenciais guardam as conexões privadas — bancos, APIs e serviços —/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Criar credencial" }))
    expect(onCriar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("alert")).toBeNull()
    unmount()

    render(<Credenciais.VazioPrimeiroUso canEdit={false} onCriar={() => {}} />)
    expect(screen.getByText("Peça a um editor do workspace para criar a primeira credencial.")).toBeInTheDocument()
    expect(screen.queryByRole("button")).toBeNull()
    cleanup()

    const onLimpar = vi.fn()
    render(<Credenciais.SemResultado q=" pg " comFiltro onLimpar={onLimpar} />)
    expect(screen.getByText("Nenhuma credencial com «pg» e este filtro")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("alert")).toBeNull()

    expect(Credenciais.textoDeSemResultado("pg", false)).toBe("Nenhuma credencial com «pg»")
    expect(Credenciais.textoDeSemResultado("", true)).toBe("Nenhuma credencial com este filtro")
    expect(Credenciais.textoDeSemResultado(" ", false)).toBe("Nenhuma credencial corresponde ao filtro")
  })

  it("Tokens de acesso", () => {
    const onCriar = vi.fn()
    render(<Tokens.VazioPrimeiroUso onCriar={onCriar} />)
    expect(screen.getByText("Crie o primeiro token de acesso")).toBeInTheDocument()
    expect(screen.getByText(/Um token deixa um agente de IA ou uma integração usar o Atlans em seu nome/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Criar o primeiro token" }))
    expect(onCriar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("Drive", () => {
    const onEnviar = vi.fn()
    const { unmount } = render(<Drive.VazioPrimeiroUso canEdit onEnviar={onEnviar} />)
    expect(screen.getByText("Nenhum arquivo ainda")).toBeInTheDocument()
    expect(screen.getByText(/Os arquivos de entrada — GeoJSON, Shapefile, CSV, KML, GeoPackage e outros —/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Enviar arquivos" }))
    expect(onEnviar).toHaveBeenCalledTimes(1)
    unmount()

    render(<Drive.VazioPrimeiroUso canEdit={false} onEnviar={() => {}} />)
    expect(screen.getByText("Peça a um editor do workspace para enviar os primeiros arquivos.")).toBeInTheDocument()
    expect(screen.queryByRole("button")).toBeNull()
    cleanup()

    render(<Drive.SemResultado busca="bacia" ext="csv" onLimpar={() => {}} />)
    expect(screen.getByText("Nenhum arquivo com «bacia» e este filtro")).toBeInTheDocument()
    expect(screen.getByText("Ajuste a busca ou o tipo, ou limpe o recorte.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Limpar filtros" })).toBeInTheDocument()
    expect(screen.queryByRole("alert")).toBeNull()

    expect(Drive.textoDeSemResultado("bacia", "")).toBe("Nenhum arquivo com «bacia»")
    expect(Drive.textoDeSemResultado("", "csv")).toBe("Nenhum arquivo com este filtro")
    expect(Drive.textoDeSemResultado("", "")).toBe("Nenhum arquivo")
  })

  it("Admin › Usuários", () => {
    const { unmount } = render(<Usuarios.VazioPrimeiroUso />)
    expect(screen.getByText("Nenhum usuário ainda")).toBeInTheDocument()
    expect(screen.getByText("Assim que as primeiras contas forem criadas, elas aparecem aqui para gestão.")).toBeInTheDocument()
    unmount()

    const onLimpar = vi.fn()
    const { rerender } = render(<Usuarios.SemResultado q=" ana " onLimpar={onLimpar} />)
    expect(screen.getByText("Nenhum usuário com «ana»")).toBeInTheDocument()
    expect(screen.getByText("Ajuste a busca ou o recorte de status e role.")).toBeInTheDocument()
    rerender(<Usuarios.SemResultado q="" onLimpar={onLimpar} />)
    expect(screen.getByText("Nenhum usuário com este filtro")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
    cleanup()

    render(<Usuarios.SemAcesso />)
    expect(screen.getByText("Acesso restrito")).toBeInTheDocument()
    expect(screen.getByText("Esta área é exclusiva de administradores da plataforma.")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("Artefatos: o substantivo acompanha a aba", () => {
    const { rerender } = render(<Artefatos.VazioPrimeiroUso tab="execution" />)
    expect(screen.getByText("Nenhum artefato ainda")).toBeInTheDocument()
    expect(screen.getByText("Quando um workflow rodar e gerar uma saída, o arquivo aparece aqui — pronto para baixar.")).toBeInTheDocument()
    rerender(<Artefatos.VazioPrimeiroUso tab="publication" />)
    expect(screen.getByText("Nenhuma publicação ainda")).toBeInTheDocument()
    expect(screen.getByText("Quando um workflow publicar uma camada num portal, a versão servida aparece aqui.")).toBeInTheDocument()
    expect(screen.queryByRole("button")).toBeNull()
    cleanup()

    const onLimpar = vi.fn()
    render(<Artefatos.SemResultado q=" bacia " formato="geojson" tab="execution" onLimpar={onLimpar} />)
    expect(screen.getByText("Nenhum artefato com «bacia» em GEOJSON")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("alert")).toBeNull()

    expect(Artefatos.textoDeSemResultado("bacia", null, "publication")).toBe("Nenhuma publicação com «bacia»")
    expect(Artefatos.textoDeSemResultado("", "csv", "execution")).toBe("Nenhum artefato em CSV")
    expect(Artefatos.textoDeSemResultado("", "all", "execution")).toBe("Nenhum artefato com este filtro")
  })

  it("Executores: o vazio muda com o papel; o recorte oferece limpar", () => {
    const { unmount } = render(<Executores.VazioDeExecutores isAdmin acao={<button type="button">Novo executor</button>} />)
    expect(screen.getByText("Nenhum executor ainda")).toBeInTheDocument()
    expect(screen.getByText(/Executores são as máquinas que rodam seus workflows de forma distribuída/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Novo executor" })).toBeInTheDocument()
    unmount()

    render(<Executores.VazioDeExecutores isAdmin={false} acao={<button type="button">Novo executor</button>} />)
    expect(screen.getByText("Nenhum executor disponível para você")).toBeInTheDocument()
    expect(screen.getByText(/Peça a um administrador acesso a um executor dedicado ou ao pool compartilhado/)).toBeInTheDocument()
    expect(screen.queryByRole("button")).toBeNull()
    cleanup()

    const onLimpar = vi.fn()
    render(<Executores.SemResultado onLimpar={onLimpar} />)
    expect(screen.getByText("Nenhum executor com este filtro")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("Dashboard", () => {
    const { unmount } = render(<Dashboard.VazioDePrimeiroUso canEdit onCriar={() => {}} />)
    expect(screen.getByText("Nada rodou ainda")).toBeInTheDocument()
    expect(screen.getByText(/o\s+painel passa a mostrar a saúde, o que precisa de você e como o período andou/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Criar workflow" })).toBeInTheDocument()
    unmount()

    render(<Dashboard.VazioDePrimeiroUso canEdit={false} onCriar={() => {}} />)
    expect(screen.getByText("Peça a um editor do workspace para criar o primeiro workflow.")).toBeInTheDocument()
    expect(screen.queryByRole("button")).toBeNull()
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("Admin › Configurações: o vazio da seção", () => {
    render(<Configuracoes.VazioEmCirculo icone={TbDatabase} titulo="Nenhum arquivo armazenado" descricao="Nenhum workspace consumiu disco do MinIO ainda." />)
    expect(screen.getByText("Nenhum arquivo armazenado")).toBeInTheDocument()
    expect(screen.getByText("Nenhum workspace consumiu disco do MinIO ainda.")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("Histórico: tabela vazia, tabela filtrada e as duas visões sem linhas", () => {
    const onLimpar = vi.fn()
    const { rerender } = render(<TabelaExecucoes {...TABELA} falhou={false} />)
    expect(screen.getByText("Nenhuma execução no período")).toBeInTheDocument()
    expect(screen.getByText("Quando um workflow rodar, ele aparece aqui com status, duração e executor.")).toBeInTheDocument()
    rerender(<TabelaExecucoes {...TABELA} falhou={false} filtrado onLimparFiltros={onLimpar} />)
    expect(screen.getByText("Nada com esses filtros")).toBeInTheDocument()
    expect(screen.getByText("Nenhuma execução no período combina com os filtros escolhidos.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    expect(onLimpar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("alert")).toBeNull()
    cleanup()

    render(<VisaoExecutores linhas={[]} carregando={false} onVerExecucoes={() => {}} />)
    expect(screen.getByText("Nenhum executor no escopo")).toBeInTheDocument()
    expect(screen.getByText("Registre um executor, ou espere um deles processar uma execução.")).toBeInTheDocument()
    cleanup()

    render(<VisaoWorkflows linhas={[]} carregando={false} isAdmin onVerExecucoes={() => {}} onAlternarAtivo={() => {}} />)
    expect(screen.getByText("Nenhum workflow no escopo")).toBeInTheDocument()
    expect(screen.getByText("Crie um workflow, ou troque o workspace do filtro.")).toBeInTheDocument()
  })
})

describe("aviso âmbar de falha parcial: uma linha de status, com o texto de cada tela", () => {
  it.each([
    ["Projetos", (t: () => void) => <Projetos.MetricasIndisponiveis onTentar={t} />, "Sem dados de execução agora — a lista continua completa."],
    ["Executores", (t: () => void) => <Executores.AvisoDeMetricas onTentar={t} />, "Sem dados de execução agora — a lista continua completa."],
    ["Dashboard", (t: () => void) => <Dashboard.AvisoDeSecao onTentar={t}>Não foi possível carregar as próximas execuções.</Dashboard.AvisoDeSecao>, "Não foi possível carregar as próximas execuções."],
    ["Admin › Configurações", (t: () => void) => <Configuracoes.AvisoDeSecao onTentar={t}>Não foi possível carregar as extensões.</Configuracoes.AvisoDeSecao>, "Não foi possível carregar as extensões."],
    ["Artefatos", (t: () => void) => <Artefatos.AvisoDeRecarga mensagem="Não foi possível atualizar a lista." onTentar={t} />, "Não foi possível atualizar a lista."],
  ])("%s", (_tela, montar, texto) => {
    const onTentar = vi.fn()
    render(montar(onTentar))
    const aviso = screen.getByRole("status")
    expect(aviso).toHaveTextContent(texto)
    expect(aviso).toHaveClass("border-amber-500/30")
    expect(screen.queryByRole("alert")).toBeNull()
    fireEvent.click(within(aviso).getByRole("button", { name: "Tentar de novo" }))
    expect(onTentar).toHaveBeenCalledTimes(1)
  })
})
