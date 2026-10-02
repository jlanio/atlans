"use client"

// web/app/hooks/home/useAnexos.ts
//
// Os arquivos soltos sobre a Home, a caminho do Drive do workspace.
//
// **Por que isto existe.** A tela `/drive` tem a zona de envio desde sempre,
// mas o middleware devolve `/` para quem não administra o sistema
// (`web/proxy.ts`), então na prática o usuário comum nunca alcançou um
// campo de upload. A Home é a única página dele — e a regra da casa manda todo
// fluxo visual para dentro dela.
//
// **Os filtros são os mesmos, e é o servidor quem os aplica.** Extensão
// permitida, extensão interna perigosa (`notas.sh.csv`), teto em MB, arquivo
// vazio e papel no workspace vivem todos no backend (`drive_service.py`,
// `drive_router.py`), valem para qualquer caminho de upload e não são
// reescritos aqui: este hook manda o arquivo e traduz a recusa com o MESMO
// `classifyUploadError` da tela `/drive` — pelo código que o servidor manda,
// não pela frase. Duas cópias da regra divergiriam — e a que estivesse errada
// seria a do cliente, que é a que a pessoa lê.
//
// A única coisa julgada ANTES de mandar é o papel no workspace, porque ele já
// está no cliente (`useWorkspace().canEdit`, o espelho do papel `editor` que o
// Drive exige): subir um arquivo inteiro para colher um 403 que
// dava para prever é desperdício de rede de quem está do outro lado.

import { useCallback } from "react"

import { classifyUploadError } from "@/app/components/drive/resultado-upload"
import { useHomeStore, type Anexo } from "@/app/stores/homeStore"
import { GisFlowService } from "@/service/GisFlowService"
import { useTextos } from "@/app/components/home/i18n"

/** Quantos arquivos um único gesto pode trazer. Além disso é engano. */
export const MAXIMO_POR_GESTO = 10

// Sequência dos ids de chip. **De MÓDULO, não um `useRef`**: os anexos vivem na
// store (persiste), mas um `useRef` zera quando a HomeView desmonta e remonta
// (o admin sai de `/` e volta). Se sobrasse um `anexo-0` na store, o próximo
// gesto criaria outro `anexo-0` — chave de React duplicada e um
// `atualizarAnexo` que casaria as DUAS linhas. Um contador de módulo é
// monotônico pela vida da aba, então nunca colide.
let _sequencia = 0

export interface UseAnexos {
  /** Recebe o que foi solto (ou escolhido no seletor) e leva ao Drive. */
  receber: (arquivos: File[]) => void
}

export function useAnexos({
  workspaceId,
  podeEnviar,
  anonimo,
  aoExigirLogin,
  aoAvisar,
}: {
  /** O workspace ativo da Home. `null` enquanto a lista não chegou. */
  workspaceId: string | null
  /** `canEdit` do workspace ativo: o espelho do papel `editor` que o Drive exige. */
  podeEnviar: boolean
  /** Sem sessão a Home abre anônima — arrastar pede a entrada. */
  anonimo: boolean
  aoExigirLogin: () => void
  /** Recusas que nem chegam a virar chip (sem workspace, sem papel, lote grande). */
  aoAvisar: (titulo: string, detalhe?: string) => void
}): UseAnexos {
  // Ações da store só: este hook não LÊ os anexos (a barra e o painel os
  // desenham), então não se inscreve neles — assim não re-renderiza a Home a
  // cada byte de progresso.
  const adicionarAnexos = useHomeStore((s) => s.adicionarAnexos)
  const atualizarAnexo = useHomeStore((s) => s.atualizarAnexo)
  const t = useTextos().assistente.anexos

  const receber = useCallback((arquivos: File[]) => {
    if (arquivos.length === 0) return

    if (anonimo) {
      aoExigirLogin()
      return
    }
    if (!workspaceId) {
      aoAvisar(t.semWorkspace, t.semWorkspaceDica)
      return
    }
    if (!podeEnviar) {
      aoAvisar(t.semPapel, t.semPapelDica)
      return
    }

    const lote = arquivos.slice(0, MAXIMO_POR_GESTO)
    if (arquivos.length > lote.length) {
      aoAvisar(t.lote(MAXIMO_POR_GESTO), t.loteDica(arquivos.length))
    }

    // O id não pode vir do nome: soltar o mesmo arquivo duas vezes é legítimo
    // (a pessoa corrigiu o conteúdo e soltou de novo) e as duas linhas precisam
    // existir separadas.
    const novos: Anexo[] = lote.map((arquivo) => ({
      id: `anexo-${_sequencia++}`,
      nome: arquivo.name,
      bytes: arquivo.size,
      estado: "enviando",
    }))
    adicionarAnexos(novos)

    // Em série, como a tela `/drive` sempre fez: em paralelo, dez arquivos
    // grandes disputam a mesma banda e todos demoram mais — e o servidor
    // acumula cada corpo na memória do worker enquanto lê.
    void (async () => {
      for (let i = 0; i < lote.length; i++) {
        const arquivo = lote[i]
        const { id } = novos[i]
        const res = await GisFlowService.uploadDriveFile(workspaceId, arquivo)
        if (res.error) {
          atualizarAnexo(id, {
            estado: "recusado",
            motivo: res.error.message ?? t.naoEnviou(arquivo.name),
            tipo: classifyUploadError(res.status, res.error.code),
          })
        } else {
          atualizarAnexo(id, { estado: "pronto" })
        }
      }
    })()
  }, [anonimo, workspaceId, podeEnviar, aoExigirLogin, aoAvisar, adicionarAnexos, atualizarAnexo, t])

  return { receber }
}
