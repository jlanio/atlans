"use client"

import { TbShield, TbUsers } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/*
 * Os quatro estados da tela Admin › Usuários (contrato §3): skeleton da 1ª
 * carga espelhando a tabela, erro só quando nunca houve carga, vazio de
 * primeiro uso × sem resultado, e o cartão de sem-acesso. A composição e a
 * precedência vivem no `page.tsx`; aqui ficam o skeleton e as frases, com a
 * moldura de `shared/estados.tsx`.
 */

/**
 * Primeira carga: o cabeçalho e a toolbar reais ficam por cima (o `page.tsx`
 * os renderiza sempre) e aqui vai o desenho da tabela — cinco linhas com a
 * altura de verdade — para a troca para o conteúdo não pular a página.
 */
export function SkeletonDeUsuarios() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os usuários"
      className="overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b px-3 py-3 last:border-b-0">
          <Skeleton className="size-4 shrink-0 rounded" />
          <div className="flex flex-1 flex-col gap-1.5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-56" />
          </div>
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="hidden h-5 w-16 rounded-full sm:block" />
          <Skeleton className="hidden h-3.5 w-24 md:block" />
          <Skeleton className="size-8 shrink-0 rounded-md" />
        </div>
      ))}
    </div>
  )
}

/**
 * A listagem caiu na 1ª carga: sem ela não há tabela, então o bloco de erro
 * toma o lugar. Numa recarga que falha sobre uma lista já pronta isto NÃO
 * aparece — o `page.tsx` mantém o que havia e mostra só um toast (contrato §3.2).
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os usuários" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * Nenhum usuário e nenhum recorte: primeiro uso da instância. Raro numa tela de
 * admin (sempre há ao menos o próprio admin), mas o contrato pede a distinção
 * entre "não há nada" e "o filtro escondeu tudo".
 */
export function VazioPrimeiroUso() {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbUsers}
      titulo="Nenhum usuário ainda"
      descricao="Assim que as primeiras contas forem criadas, elas aparecem aqui para gestão."
    />
  )
}

/**
 * Busca ou filtro sem nenhuma linha: a saída óbvia é limpar o recorte, e a
 * tela diz isso (contrato §3.3, ícone `TbFilterOff`). A página só passa a
 * busca: sem termo, o que zerou a lista é o recorte de status e role.
 */
export function SemResultado({ q, onLimpar }: { q: string; onLimpar: () => void }) {
  return (
    <Estado.SemResultado
      texto={Estado.textoDeSemResultado({ nada: "Nenhum usuário", termo: q, comFiltro: q.trim() === "" })}
      dica="Ajuste a busca ou o recorte de status e role."
      onLimpar={onLimpar}
    />
  )
}

/** Não-admin: a tela inteira dá lugar ao cartão centralizado de sem-acesso. */
export function SemAcesso() {
  return (
    <Estado.CartaoDeEstado
      icone={TbShield}
      tamanho="amplo"
      titulo="Acesso restrito"
      descricao="Esta área é exclusiva de administradores da plataforma."
    />
  )
}
