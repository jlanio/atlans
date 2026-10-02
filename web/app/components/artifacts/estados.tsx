"use client"

import { TbFolders } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"
import type { ArtifactTab } from "@/app/(dashboard)/artifacts/use-artifacts-query"

/**
 * Estados da tela de Artefatos (contrato §3): skeleton da 1ª carga, erro de
 * espinha em cartão, vazio de primeiro uso vs sem resultado, e o aviso âmbar de
 * recarga que falhou sobre uma lista já pronta. A precedência (carregando →
 * erro só se nunca houve carga → primeiro uso → conteúdo) fica na página; aqui
 * ficam o skeleton e as frases, com a moldura de `shared/estados.tsx`.
 */

/**
 * Primeira carga: o cabeçalho real fica por cima (a página o renderiza sempre)
 * e aqui vai o desenho da tabela — a mesma moldura, os mesmos cinco blocos de
 * linha na altura real — para a troca para o conteúdo não pular a página.
 */
export function SkeletonDeArtefatos() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os artefatos"
      className="overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      <div className="flex flex-col gap-2 p-4">
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="size-4 shrink-0 rounded" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="hidden h-4 w-24 sm:block" />
            <Skeleton className="hidden h-4 w-20 md:block" />
            <Skeleton className="h-7 w-20 rounded-md" />
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * A listagem caiu na 1ª carga (sem `atualizadoEm` ainda): sem ela não há
 * tabela, então o cartão de erro toma o lugar. Uma recarga que falha sobre uma
 * lista pronta NÃO chega aqui — vira o aviso âmbar e a tabela permanece.
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os artefatos" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * Primeiro uso: o workspace/aba não tem nenhum artefato e não há recorte ativo.
 * Diferente de "sem resultado" — aqui não há o que limpar, só a explicação de
 * onde os artefatos nascem.
 */
export function VazioPrimeiroUso({ tab }: { tab: ArtifactTab }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbFolders}
      titulo={tab === "execution" ? "Nenhum artefato ainda" : "Nenhuma publicação ainda"}
      descricao={tab === "execution"
        ? "Quando um workflow rodar e gerar uma saída, o arquivo aparece aqui — pronto para baixar."
        : "Quando um workflow publicar uma camada num portal, a versão servida aparece aqui."}
    />
  )
}

/**
 * Busca ou chip de formato sem nenhuma linha. Ao contrário do primeiro uso, há
 * um recorte a desfazer — a saída óbvia é "Limpar filtros", e a tela oferece.
 */
export function SemResultado({ q, formato, tab, onLimpar }: {
  q: string
  formato: string | null
  tab: ArtifactTab
  onLimpar: () => void
}) {
  return <Estado.SemResultado texto={textoDeSemResultado(q, formato, tab)} onLimpar={onLimpar} />
}

/** "Nenhum artefato com «q»" / "Nenhuma publicação em GEOJSON" — o substantivo
 *  acompanha a aba (execução → artefato; publicação → publicação). */
export function textoDeSemResultado(termo: string, formato: string | null, tab: ArtifactTab): string {
  const nada = tab === "execution" ? "Nenhum artefato" : "Nenhuma publicação"
  const fmt = formato && formato !== "all" ? formato.toUpperCase() : null
  return Estado.textoDeSemResultado({
    nada,
    termo,
    comFiltro: fmt != null,
    sufixoFiltro: fmt ? `em ${fmt}` : undefined,
    semRecorte: `${nada} com este filtro`,
  })
}

/**
 * Recarga que falhou com a lista já na tela (§3.4): uma linha âmbar discreta,
 * não derruba a tabela. Cobre também o "Ver mais" que errou — o botão continua
 * lá para tentar de novo.
 */
export function AvisoDeRecarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.AvisoAmbar onTentar={onTentar}>{mensagem}</Estado.AvisoAmbar>
}
