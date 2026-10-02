/**
 * O hook que recebe os arquivos soltos sobre a Home e os leva ao Drive.
 *
 * O que ele protege é a fronteira com o backend: os filtros (extensão, teto,
 * vazio, papel) são do servidor e NÃO são reescritos aqui — o hook manda ao
 * `POST /drive/upload` e traduz a recusa com a mesma `classifyUploadError` da
 * tela `/drive`, pelo CÓDIGO (`error` do corpo) e pelo status, nunca pelo
 * texto. As únicas decisões locais são as que já estão no cliente e poupariam
 * uma viagem inútil: sem sessão vai para o login, sem papel de editor nem
 * tenta, e um gesto grande demais é aparado.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"

const servico = vi.hoisted(() => ({ uploadDriveFile: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

import { useAnexos, MAXIMO_POR_GESTO } from "@/app/hooks/home/useAnexos"
import { useHomeStore } from "@/app/stores/homeStore"

const estado = () => useHomeStore.getState()
const ok = (idHash: string) => ({ success: true, status: 201, data: { id_hash: idHash } })
/** A recusa como `resolveAxiosError` a entrega: a frase do servidor em `message` e o `error` do corpo em `code`. */
const erro = (status: number, message: string, code?: string) =>
  ({ success: false, status, error: { name: "AxiosError", message, ...(code ? { code } : {}) }, data: undefined })

function arquivo(nome: string, bytes = 1024): File {
  return new File([new Uint8Array(bytes)], nome, { type: "application/octet-stream" })
}

function montar(over: Partial<Parameters<typeof useAnexos>[0]> = {}) {
  const aoExigirLogin = vi.fn()
  const aoAvisar = vi.fn()
  const r = renderHook(() =>
    useAnexos({
      workspaceId: "ws-1",
      podeEnviar: true,
      anonimo: false,
      aoExigirLogin,
      aoAvisar,
      ...over,
    }),
  )
  return { r, aoExigirLogin, aoAvisar }
}

beforeEach(() => {
  servico.uploadDriveFile.mockReset()
  useHomeStore.setState({ anexos: [], arrastandoArquivo: false })
})

describe("useAnexos", () => {
  it("sobe cada arquivo e marca PRONTO", async () => {
    servico.uploadDriveFile.mockImplementation(async (_ws: string, f: File) => ok(`h-${f.name}`))
    const { r } = montar()

    act(() => r.result.current.receber([arquivo("um.csv"), arquivo("dois.geojson")]))
    await waitFor(() => expect(estado().anexos.every((a) => a.estado === "pronto")).toBe(true))

    expect(servico.uploadDriveFile).toHaveBeenCalledTimes(2)
    expect(estado().anexos.map((a) => a.nome)).toEqual(["um.csv", "dois.geojson"])
  })

  it("uma recusa do servidor vira anexo RECUSADO, com o tipo classificado", async () => {
    // A recusa como o backend a manda de verdade: 422, o código no `error` e a
    // frase SEM acento. A classificação por trecho do texto procurava
    // "extensão"/"não permitida" e mandava este caso para "outra falha".
    servico.uploadDriveFile.mockResolvedValue(erro(422, "Extensao '.pdf' nao permitida.", "extension_not_allowed"))
    const { r } = montar()

    act(() => r.result.current.receber([arquivo("relatorio.pdf")]))
    await waitFor(() => expect(estado().anexos[0]?.estado).toBe("recusado"))

    expect(estado().anexos[0]).toMatchObject({
      estado: "recusado", tipo: "extension", motivo: "Extensao '.pdf' nao permitida.",
    })
  })

  it.each([
    [422, "extension_not_allowed", "extension", "Arquivo sem extensao."],
    [422, "dangerous_inner_extension", "extension", "Nome de arquivo com extensao interna perigosa: '.sh'."],
    [422, "empty_file", "empty", "Arquivo vazio."],
    [413, "file_too_large", "size", "Arquivo excede 200MB."],
    // O teto do router é uma HTTPException, sem código de domínio: vale o status.
    [413, "http_exception", "size", "Arquivo excede 200MB."],
    [403, "http_exception", "permission", "Requer role 'editor' ou superior."],
  ] as const)("%i %s é classificado como %s", async (status, code, tipo, message) => {
    servico.uploadDriveFile.mockResolvedValue(erro(status, message, code))
    const { r } = montar()
    act(() => r.result.current.receber([arquivo("x.csv")]))
    await waitFor(() => expect(estado().anexos[0]?.tipo).toBe(tipo))
  })

  it("a frase NÃO classifica: sem o código de extensão, é outra falha", async () => {
    // "extensão" e "não permitida" no texto, mas o código é o genérico de um
    // servidor antigo — a regra é o código, e a frase pode mudar amanhã.
    servico.uploadDriveFile.mockResolvedValue(erro(422, "Extensão '.pdf' não permitida.", "file_validation_error"))
    const { r } = montar()
    act(() => r.result.current.receber([arquivo("relatorio.pdf")]))
    await waitFor(() => expect(estado().anexos[0]?.tipo).toBe("other"))
  })

  it("sem sessão NÃO sobe nada — abre o login", () => {
    const { r, aoExigirLogin } = montar({ anonimo: true })
    act(() => r.result.current.receber([arquivo("um.csv")]))
    expect(aoExigirLogin).toHaveBeenCalled()
    expect(servico.uploadDriveFile).not.toHaveBeenCalled()
    expect(estado().anexos).toHaveLength(0)
  })

  it("sem papel de editor NEM tenta — prevê o 403 e avisa", () => {
    const { r, aoAvisar } = montar({ podeEnviar: false })
    act(() => r.result.current.receber([arquivo("um.csv")]))
    expect(aoAvisar).toHaveBeenCalled()
    expect(servico.uploadDriveFile).not.toHaveBeenCalled()
  })

  it("sem workspace resolvido, avisa e espera — não manda para lugar nenhum", () => {
    const { r, aoAvisar } = montar({ workspaceId: null })
    act(() => r.result.current.receber([arquivo("um.csv")]))
    expect(aoAvisar).toHaveBeenCalled()
    expect(servico.uploadDriveFile).not.toHaveBeenCalled()
  })

  it("apara o gesto no teto e avisa quantos ficaram para trás", async () => {
    servico.uploadDriveFile.mockImplementation(async (_ws: string, f: File) => ok(`h-${f.name}`))
    const { r, aoAvisar } = montar()
    const muitos = Array.from({ length: MAXIMO_POR_GESTO + 3 }, (_, i) => arquivo(`f${i}.csv`))

    act(() => r.result.current.receber(muitos))
    await waitFor(() => expect(estado().anexos.every((a) => a.estado === "pronto")).toBe(true))

    expect(estado().anexos).toHaveLength(MAXIMO_POR_GESTO)
    expect(aoAvisar).toHaveBeenCalled()
  })

  it("lista vazia não faz nada", () => {
    const { r } = montar()
    act(() => r.result.current.receber([]))
    expect(servico.uploadDriveFile).not.toHaveBeenCalled()
  })
})
