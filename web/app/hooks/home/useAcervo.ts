"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import {
  normalizarArtefato, normalizarArquivoDoDrive, type ItemDoAcervo,
} from "@/app/components/home/artefatos/normalizar"

/** Qual das duas fontes caiu com a outra de pé — a degradação é por fonte, e
 *  cada metade precisa do seu aviso (antes só o Drive tinha). */
export interface AvisosDoAcervo {
  artefatos: boolean
  drive: boolean
}

export interface UseAcervo {
  itens: ItemDoAcervo[]
  /** Só a PRIMEIRA carga (o esqueleto). Recarga não volta a ligá-lo. */
  carregando: boolean
  /** Recarga em voo sobre a lista já na tela — vira `aria-busy`, não esqueleto. */
  atualizando: boolean
  /** Já houve uma carga aceita. O bloco de erro só toma a lista antes disso (§3). */
  jaCarregou: boolean
  /** Só quando AMBAS as fontes falham. */
  erro: string | null
  avisos: AvisosDoAcervo
  /** Quantos itens o servidor diz existir nas duas fontes somadas; `null` quando
   *  uma delas falhou e não dá para somar. */
  total: number | null
  recarregar: () => void
  /** Remove (otimista) o item da lista após o backend confirmar. */
  remover: (item: ItemDoAcervo) => Promise<boolean>
}

const LIMITE = 200

const SEM_AVISOS: AvisosDoAcervo = { artefatos: false, drive: false }

/**
 * O acervo do workspace atual: artefatos de execução + arquivos do Drive na
 * mesma lista (decisão 8). Dois endpoints prontos, com auth própria — o merge é
 * no cliente, via `Promise.allSettled`, para que a falha de UMA fonte não derrube
 * a outra (o Drive fora do ar não some com os artefatos). Ordena por data, mais
 * recente primeiro. Sem workspace ativo, lista vazia.
 *
 * Precedência de estados do §3 do padrão de telas: uma recarga que falha NÃO
 * apaga o que já está na tela. Os `set` de lista só acontecem quando ao menos
 * uma fonte respondeu; no fracasso total sobra o `erro`, que a lista mostra como
 * aviso âmbar quando já havia conteúdo e como bloco só na primeira carga.
 */
export function useAcervo(workspaceId: string | null | undefined): UseAcervo {
  const [itens, setItens] = useState<ItemDoAcervo[]>([])
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [jaCarregou, setJaCarregou] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [avisos, setAvisos] = useState<AvisosDoAcervo>(SEM_AVISOS)
  const [total, setTotal] = useState<number | null>(null)
  const geracao = useRef(0)
  // Espelha `jaCarregou` para o callback decidir esqueleto × `aria-busy` sem
  // entrar nas dependências (o `recarregar` precisa ser estável para o efeito
  // não relançar a cada carga).
  const jaCarregouRef = useRef(false)

  const recarregar = useCallback(() => {
    if (!workspaceId) {
      setItens([]); setErro(null); setAvisos(SEM_AVISOS); setTotal(null)
      setCarregando(false); setAtualizando(false)
      return
    }
    const minha = ++geracao.current
    if (jaCarregouRef.current) setAtualizando(true)
    else setCarregando(true)
    Promise.allSettled([
      GisFlowService.getArtifacts({ workspace_id: workspaceId, limit: LIMITE }),
      GisFlowService.getDriveFiles({ workspace_id: workspaceId, page_size: LIMITE }),
    ]).then(([resArt, resDrive]) => {
      if (minha !== geracao.current) return
      const acervo: ItemDoAcervo[] = []
      let artOk = false
      let driveOk = false
      let totalArt = 0
      let totalDrive = 0
      if (resArt.status === "fulfilled" && resArt.value.success && resArt.value.data) {
        artOk = true
        totalArt = resArt.value.data.total ?? resArt.value.data.items.length
        for (const a of resArt.value.data.items) acervo.push(normalizarArtefato(a))
      }
      if (resDrive.status === "fulfilled" && resDrive.value.success && resDrive.value.data) {
        driveOk = true
        totalDrive = resDrive.value.data.total ?? resDrive.value.data.items.length
        for (const f of resDrive.value.data.items) acervo.push(normalizarArquivoDoDrive(f))
      }
      if (artOk || driveOk) {
        // Mais recente primeiro; sem data por último. `ordenadoEm` é a última
        // escrita de conteúdo no Drive — a mesma ordem que /drive mostra.
        acervo.sort((x, y) => (y.ordenadoEm ?? "").localeCompare(x.ordenadoEm ?? ""))
        setItens(acervo)
        setErro(null)
        setTotal(artOk && driveOk ? totalArt + totalDrive : null)
        jaCarregouRef.current = true
        setJaCarregou(true)
      } else {
        // Fracasso total: mantém a lista anterior (§3) e só sinaliza a falha.
        setErro("Não foi possível carregar o acervo.")
      }
      setAvisos({ artefatos: !artOk && driveOk, drive: artOk && !driveOk })
      setCarregando(false)
      setAtualizando(false)
    })
  }, [workspaceId])

  // Trocar de workspace é uma lista NOVA: zera o que havia e o esqueleto volta.
  // O `recarregar` só muda de identidade quando o `workspaceId` muda, então este
  // efeito não dispara na recarga manual (o botão "Tentar de novo").
  useEffect(() => {
    jaCarregouRef.current = false
    setJaCarregou(false)
    setItens([])
    setTotal(null)
    recarregar()
  }, [recarregar])

  const remover = useCallback(async (item: ItemDoAcervo) => {
    const res = item.fonte === "artefato"
      ? await GisFlowService.deleteArtifact(item.id)
      : await GisFlowService.deleteDriveFile(item.id)
    if (res.success) {
      setItens((atual) => atual.filter((i) => i.chave !== item.chave))
      // O total vem do servidor e alimenta o "mostrando N de M": sem descontar,
      // a linha de corte passaria a mentir logo após uma exclusão.
      setTotal((t) => (t == null ? t : Math.max(0, t - 1)))
      return true
    }
    return false
  }, [])

  return { itens, carregando, atualizando, jaCarregou, erro, avisos, total, recarregar, remover }
}
