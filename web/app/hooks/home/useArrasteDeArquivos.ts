"use client"

// web/app/hooks/home/useArrasteDeArquivos.ts
//
// O arraste de arquivos sobre a Home.
//
// **A área que ACEITA é a janela inteira; quem ACENDE é a caixa do assistente.**
// Mirar uma barra de 44 px de altura com o arquivo na mão é hostil — e ancorar
// o alvo visual na caixa é justamente a escolha da opção C, para não cobrir o
// globo com um véu a cada arraste. Então o listener é global e o realce é da
// caixa (`data-arraste` em `barra.tsx` e `painel.tsx`).
//
// Escutar em `window` tem um segundo efeito, necessário: sem `preventDefault`
// no `dragover`/`drop` o navegador ABRE o arquivo solto, trocando a Home por um
// GeoJSON cru — e perdendo a conversa em curso. Com o listener global, soltar
// em qualquer canto da página é tratado por nós.
//
// O `dragleave` não é confiável sozinho: ele dispara ao cruzar a fronteira de
// cada elemento filho, então um arraste que atravesse a barra lateral apagaria
// o realce no meio do caminho. Daí o contador de entradas/saídas — o realce só
// cai quando o arraste de fato deixou a janela.

import { useEffect, useRef } from "react"

/** O arraste traz ARQUIVOS? Texto e links selecionados também disparam estes
 *  eventos, e acender a caixa para eles seria uma promessa falsa. */
function temArquivos(e: DragEvent): boolean {
  const tipos = e.dataTransfer?.types
  if (!tipos) return false
  return Array.from(tipos).includes("Files")
}

export function useArrasteDeArquivos({
  ativo,
  aoArrastar,
  aoSoltar,
}: {
  /** Desligado enquanto a Home não pode receber (ex.: nem montou a barra). */
  ativo: boolean
  aoArrastar: (arrastando: boolean) => void
  aoSoltar: (arquivos: File[]) => void
}): void {
  // Em refs para o efeito não se reinscrever a cada render: `aoSoltar` vem de
  // um `useCallback` cujas dependências mudam (o workspace ativo, por exemplo),
  // e reinscrever no meio de um arraste zeraria o contador — o realce ficaria
  // aceso para sempre.
  const refArrastar = useRef(aoArrastar)
  const refSoltar = useRef(aoSoltar)
  refArrastar.current = aoArrastar
  refSoltar.current = aoSoltar

  useEffect(() => {
    if (!ativo) return
    let profundidade = 0

    function entrou(e: DragEvent) {
      if (!temArquivos(e)) return
      profundidade++
      refArrastar.current(true)
    }
    function sobre(e: DragEvent) {
      if (!temArquivos(e)) return
      // Sem isto o `drop` nem chega a acontecer — o navegador trata o arquivo.
      e.preventDefault()
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy"
    }
    function saiu(e: DragEvent) {
      if (!temArquivos(e)) return
      profundidade = Math.max(0, profundidade - 1)
      if (profundidade === 0) refArrastar.current(false)
    }
    function soltou(e: DragEvent) {
      if (!temArquivos(e)) return
      e.preventDefault()
      profundidade = 0
      refArrastar.current(false)
      const arquivos = e.dataTransfer?.files
      if (arquivos && arquivos.length > 0) refSoltar.current(Array.from(arquivos))
    }
    // Sair da janela com o arquivo ainda na mão não dispara `dragleave` em todo
    // navegador; `dragend` é a rede de segurança para o realce não ficar aceso.
    function acabou() {
      profundidade = 0
      refArrastar.current(false)
    }

    window.addEventListener("dragenter", entrou)
    window.addEventListener("dragover", sobre)
    window.addEventListener("dragleave", saiu)
    window.addEventListener("drop", soltou)
    window.addEventListener("dragend", acabou)
    return () => {
      window.removeEventListener("dragenter", entrou)
      window.removeEventListener("dragover", sobre)
      window.removeEventListener("dragleave", saiu)
      window.removeEventListener("drop", soltou)
      window.removeEventListener("dragend", acabou)
      // Desmontar no meio de um arraste deixaria o realce ligado na store.
      refArrastar.current(false)
    }
  }, [ativo])
}
