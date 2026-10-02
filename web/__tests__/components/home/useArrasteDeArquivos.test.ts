/**
 * O arraste de arquivos sobre a Home.
 *
 * Três coisas delicadas, e é por elas que existe um hook e não um `onDrop` numa
 * div:
 *
 *  1. **Só ARQUIVOS acendem a caixa.** Arrastar texto ou um link seleciona
 *     dispara os mesmos eventos; acender para eles seria uma promessa falsa.
 *  2. **O contador de profundidade.** `dragleave` dispara ao cruzar a fronteira
 *     de cada filho; sem o contador, atravessar a barra lateral apagaria o
 *     realce no meio do caminho.
 *  3. **`preventDefault` no dragover/drop.** Sem ele o navegador ABRE o arquivo
 *     solto, trocando a Home por um GeoJSON cru — e perdendo a conversa.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"

import { useArrasteDeArquivos } from "@/app/hooks/home/useArrasteDeArquivos"

function evento(tipo: string, tipos: string[], arquivos: File[] = []) {
  const e = new Event(tipo, { bubbles: true, cancelable: true }) as DragEvent & { dataTransfer: unknown }
  Object.defineProperty(e, "dataTransfer", {
    value: { types: tipos, files: arquivos, dropEffect: "none" },
    configurable: true,
  })
  return e as DragEvent
}

const COM_ARQUIVO = ["Files"]
const SO_TEXTO = ["text/plain"]

let aoArrastar: ReturnType<typeof vi.fn<(arrastando: boolean) => void>>
let aoSoltar: ReturnType<typeof vi.fn<(arquivos: File[]) => void>>

function montar(ativo = true) {
  aoArrastar = vi.fn<(arrastando: boolean) => void>()
  aoSoltar = vi.fn<(arquivos: File[]) => void>()
  return renderHook(() => useArrasteDeArquivos({ ativo, aoArrastar, aoSoltar }))
}

beforeEach(() => vi.restoreAllMocks())

describe("useArrasteDeArquivos", () => {
  it("acende ao entrar com arquivo e apaga ao sair", () => {
    montar()
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    expect(aoArrastar).toHaveBeenLastCalledWith(true)
    window.dispatchEvent(evento("dragleave", COM_ARQUIVO))
    expect(aoArrastar).toHaveBeenLastCalledWith(false)
  })

  it("ignora arraste que não é de arquivo (texto, link)", () => {
    montar()
    window.dispatchEvent(evento("dragenter", SO_TEXTO))
    expect(aoArrastar).not.toHaveBeenCalled()
  })

  it("o contador aguenta a fronteira dos filhos: só apaga quando de fato saiu", () => {
    montar()
    // Entra na página, depois cruza para dentro de um filho (2 enters), e sai
    // de um (1 leave): ainda está sobre a Home.
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    window.dispatchEvent(evento("dragleave", COM_ARQUIVO))
    expect(aoArrastar).toHaveBeenLastCalledWith(true)
    // Sai do último: agora apaga.
    window.dispatchEvent(evento("dragleave", COM_ARQUIVO))
    expect(aoArrastar).toHaveBeenLastCalledWith(false)
  })

  it("soltar entrega os arquivos, apaga o realce e barra o navegador (preventDefault)", () => {
    montar()
    const f = new File(["x"], "um.csv")
    const ev = evento("drop", COM_ARQUIVO, [f])
    window.dispatchEvent(ev)

    expect(aoSoltar).toHaveBeenCalledWith([f])
    expect(aoArrastar).toHaveBeenLastCalledWith(false)
    expect(ev.defaultPrevented).toBe(true)
  })

  it("dragover de arquivo é sempre prevenido — senão o drop nem acontece", () => {
    montar()
    const ev = evento("dragover", COM_ARQUIVO)
    window.dispatchEvent(ev)
    expect(ev.defaultPrevented).toBe(true)
  })

  it("soltar sem nenhum arquivo não chama aoSoltar", () => {
    montar()
    window.dispatchEvent(evento("drop", COM_ARQUIVO, []))
    expect(aoSoltar).not.toHaveBeenCalled()
  })

  it("desligado (ativo=false), não escuta nada", () => {
    montar(false)
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    window.dispatchEvent(evento("drop", COM_ARQUIVO, [new File(["x"], "a.csv")]))
    expect(aoArrastar).not.toHaveBeenCalled()
    expect(aoSoltar).not.toHaveBeenCalled()
  })

  it("desmontar limpa os listeners e zera o realce", () => {
    const { unmount } = montar()
    unmount()
    // O cleanup avisa `false` uma vez; e um evento posterior não chama mais nada.
    expect(aoArrastar).toHaveBeenLastCalledWith(false)
    aoArrastar.mockClear()
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    expect(aoArrastar).not.toHaveBeenCalled()
  })
})
