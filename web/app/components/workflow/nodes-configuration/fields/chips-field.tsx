"use client"

/**
 * List of names as chips — the look "Remover campos" (Remove fields) already uses.
 *
 * As a FIELD, not a helper: node-config-form's `HELPER_MAP` replaces the whole
 * form, and in a node like Join por Atributo (attribute join) the other fields
 * (key, join type, what to do with duplicates) need to stay visible alongside.
 *
 * Comma-separated text worked, but didn't show what was already there: a
 * single line, with names stuck together, with no way to remove one from the
 * middle other than editing the string. Each name becomes a chip with its own
 * button.
 *
 * Pasting is still the fast path: "a, b, c" at once becomes three chips.
 */
import { useMemo, useState } from "react"
import { TbX } from "react-icons/tb"

import { Badge } from "@/app/components/ui/badge"
import { Input } from "@/app/components/ui/input"
import { FieldLabel } from "./field-label"
import ColumnSuggestions from "./sugestoes-de-colunas"
import type { FieldProps } from "./types"

/** Mirrors the executor's ceiling (`MAX_COLUMNS` in flow/executor/utils.py). It
 *  only serves to warn that the list came truncated — diverging just hides the warning. */
export const MAX_SUGGESTED_COLUMNS = 200

type ChipsFieldProps = FieldProps<{
  /** Names seen in the previous node's last execution, to click instead of
   *  typing. It is a hint, not validation: the workflow may have changed since
   *  then, and nothing prevents writing a name outside the list. */
  sugestoes?: string[]
  /** true when the suggestions came from re-hydrating a PERSISTED run (not
   *  from this session): the label changes to warn that the list may have
   *  changed — claiming "last execution" with old data would be lying. */
  sugestoesDesatualizadas?: boolean
  /** true when the source stat came truncated — the label warns "partial
   *  list" instead of claiming completeness. */
  sugestoesParciais?: boolean
}>

/**
 * Reads the stored value, whether it comes as a list, JSON or comma-separated text.
 *
 * The field's old format was comma-separated text, and it remains in already
 * saved definitions — reading both is what makes migrating data unnecessary.
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
      // Falls through to the text format below.
    }
  }
  return texto.split(",").map(c => c.trim()).filter(Boolean)
}

/** Names from a typing or paste, minus those already in the list. */
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
  const [rascunho, setDraft] = useState("")
  // Only what hasn't been chosen yet — offering what is already a chip is noise.
  const disponiveis = useMemo(
    () => sugestoes.filter(s => !fichas.includes(s)),
    [sugestoes, fichas],
  )

  // Writes in the format EVERY reader understands — including an executor with
  // a flow/ older than the migration of these fields to chips, which still
  // parses with `split(",")`: a JSON string there would become phantom columns
  // ('["a"'…) and, in the ChangeDetector, a silently wrong hash. CSV is the
  // format the old field always wrote; JSON is only for the case CSV never
  // represented (a name with a comma). Empty writes "" — "[]" under split(",")
  // became the phantom column "[]". `lerFichas` and the backend parser read all
  // three formats.
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
    setDraft("")
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      adicionar(rascunho)
      return
    }
    // Backspace in an empty field removes the last one — the shortcut expected of
    // any chips field.
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
        onChange={e => setDraft(e.target.value)}
        onKeyDown={aoTeclar}
        // Leaving the field with something typed adds it: losing what you wrote
        // because you clicked outside is the classic defect of this kind of field.
        onBlur={() => adicionar(rascunho)}
        placeholder={fichas.length ? "Adicionar outra…" : "Nome da coluna + Enter"}
        className="h-8 font-mono text-xs"
      />

      <ColumnSuggestions
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
