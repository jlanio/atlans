/**
 * Dragging files over the Home.
 *
 * Three delicate things, and they are why there is a hook and not an `onDrop` on a
 * div:
 *
 *  1. **Only FILES light up the box.** Dragging text or a link selection
 *     fires the same events; lighting up for them would be a false promise.
 *  2. **The depth counter.** `dragleave` fires when crossing the boundary
 *     of each child; without the counter, crossing the sidebar would turn off the
 *     highlight midway.
 *  3. **`preventDefault` on dragover/drop.** Without it the browser OPENS the dropped
 *     file, replacing the Home with raw GeoJSON — and losing the conversation.
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
    // Enters the page, then crosses into a child (2 enters), and leaves
    // one (1 leave): still over the Home.
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    window.dispatchEvent(evento("dragleave", COM_ARQUIVO))
    expect(aoArrastar).toHaveBeenLastCalledWith(true)
    // Leaves the last one: now it turns off.
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
    // The cleanup reports `false` once; and a later event no longer calls anything.
    expect(aoArrastar).toHaveBeenLastCalledWith(false)
    aoArrastar.mockClear()
    window.dispatchEvent(evento("dragenter", COM_ARQUIVO))
    expect(aoArrastar).not.toHaveBeenCalled()
  })
})
