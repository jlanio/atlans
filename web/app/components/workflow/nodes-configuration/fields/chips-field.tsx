"use client"

/**
 * Lista de nomes como fichas — o visual que o "Remover campos" já usa.
 *
 * Como CAMPO, e não helper: o `HELPER_MAP` do node-config-form substitui o
 * formulário inteiro, e num nó como o Join por Atributo os outros campos
 * (chave, tipo de junção, o que fazer com duplicata) precisam continuar
 * visíveis ao lado.
 *
 * O texto separado por vírgula funcionava, mas não mostrava o que já estava
 * lá: uma linha só, com nomes grudados, sem como remover um do meio senão
 * editando a string. Cada nome vira uma ficha com o seu próprio botão.
 *
 * Colar continua sendo o caminho rápido: "a, b, c" de uma vez vira três fichas.
 */
import { useMemo, useState } from "react"
import { TbX } from "react-icons/tb"

import { Badge } from "@/app/components/ui/badge"
import { Input } from "@/app/components/ui/input"
import { FieldLabel } from "./field-label"
import SugestoesDeColunas from "./sugestoes-de-colunas"
import type { FieldProps } from "./types"

/** Espelha o teto do executor (`MAX_COLUNAS` em flow/executor/utils.py). Serve
 *  só para avisar que a lista veio cortada — divergir apenas some com o aviso. */
export const MAX_COLUNAS_SUGERIDAS = 200

type ChipsFieldProps = FieldProps<{
  /** Nomes vistos na última execução do nó anterior, para clicar em vez de
   *  digitar. É dica, não validação: o fluxo pode ter mudado desde então, e
   *  nada impede escrever um nome fora da lista. */
  sugestoes?: string[]
  /** true quando as sugestões vieram da re-hidratação de um run PERSISTIDO
   *  (não desta sessão): o rótulo troca para avisar que a lista pode ter
   *  mudado — afirmar "última execução" com dado antigo seria mentir. */
  sugestoesDesatualizadas?: boolean
  /** true quando o stat de origem veio truncado — o rótulo avisa "lista
   *  parcial" em vez de afirmar completude. */
  sugestoesParciais?: boolean
}>

/**
 * Lê o valor guardado, venha como lista, JSON ou texto com vírgulas.
 *
 * O formato antigo do campo era texto separado por vírgula, e ele continua nas
 * definitions já salvas — ler os dois é o que dispensa migrar dado.
 */
export function lerFichas(bruto: unknown): string[] {
  if (Array.isArray(bruto)) {
    return bruto.map(x => String(x).trim()).filter(Boolean)
  }
  const texto = String(bruto ?? "").trim()
  if (!texto) return []

  if (texto.startsWith("[")) {
    try {
      const carregado = JSON.parse(texto)
      if (Array.isArray(carregado)) {
        return carregado.map(x => String(x).trim()).filter(Boolean)
      }
    } catch {
      // Cai no formato de texto abaixo.
    }
  }
  return texto.split(",").map(c => c.trim()).filter(Boolean)
}

/** Nomes de uma digitação ou colagem, sem os que já estão na lista. */
export function fichasNovas(entrada: string, existentes: string[]): string[] {
  const vistos = new Set(existentes)
  const saida: string[] = []
  for (const nome of entrada.split(",").map(c => c.trim()).filter(Boolean)) {
    if (vistos.has(nome)) continue
    vistos.add(nome)
    saida.push(nome)
  }
  return saida
}

const ChipsField = ({ field, values, setNodeField, sugestoes = [], sugestoesDesatualizadas = false, sugestoesParciais = false }: ChipsFieldProps) => {
  const fichas = useMemo(() => lerFichas(values?.[field.name]), [values, field.name])
  const [rascunho, setRascunho] = useState("")
  // Só o que ainda não foi escolhido — oferecer o que já é ficha vira ruído.
  const disponiveis = useMemo(
    () => sugestoes.filter(s => !fichas.includes(s)),
    [sugestoes, fichas],
  )

  // Grava no formato que TODO leitor entende — inclusive um executor com
  // flow/ anterior à migração destes campos para fichas, que ainda parseia
  // com `split(",")`: JSON-string lá viraria colunas fantasmas ('["a"'…) e,
  // no ChangeDetector, um hash silenciosamente errado. CSV é o formato que o
  // campo antigo sempre gravou; JSON fica só para o caso que o CSV nunca
  // representou (nome com vírgula). Vazio grava "" — "[]" no split(",")
  // virava a coluna fantasma "[]". `lerFichas` e o parser do backend leem os
  // três formatos.
  const gravar = (proximo: string[]) => {
    if (proximo.length === 0) return setNodeField(field.name, "")
    const texto = proximo.some(nome => nome.includes(","))
      ? JSON.stringify(proximo)
      : proximo.join(", ")
    setNodeField(field.name, texto)
  }

  function adicionar(entrada: string) {
    const novas = fichasNovas(entrada, fichas)
    if (novas.length) gravar([...fichas, ...novas])
    setRascunho("")
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      adicionar(rascunho)
      return
    }
    // Backspace num campo vazio remove a última — o atalho que se espera de
    // qualquer campo de fichas.
    if (e.key === "Backspace" && rascunho === "" && fichas.length) {
      gravar(fichas.slice(0, -1))
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <FieldLabel field={field} htmlFor={`chips-${field.name}`} />

      {fichas.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {fichas.map(nome => (
            <Badge
              key={nome}
              variant="secondary"
              className="cursor-default gap-1 pr-1 font-mono text-[11px]"
            >
              {nome}
              <button
                type="button"
                aria-label={`Remover ${nome}`}
                onClick={() => gravar(fichas.filter(f => f !== nome))}
                className="ml-0.5 rounded-full transition-colors hover:text-destructive"
              >
                <TbX className="h-2.5 w-2.5" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      <Input
        id={`chips-${field.name}`}
        value={rascunho}
        onChange={e => setRascunho(e.target.value)}
        onKeyDown={aoTeclar}
        // Sair do campo com algo digitado adiciona: perder o que se escreveu
        // por ter clicado fora é o defeito clássico deste tipo de campo.
        onBlur={() => adicionar(rascunho)}
        placeholder={fichas.length ? "Adicionar outra…" : "Nome da coluna + Enter"}
        className="h-8 font-mono text-xs"
      />

      <SugestoesDeColunas
        nomes={disponiveis}
        onEscolher={adicionar}
        totalConhecido={sugestoes.length}
        desatualizadas={sugestoesDesatualizadas}
        parciais={sugestoesParciais}
      />
    </div>
  )
}

export default ChipsField
