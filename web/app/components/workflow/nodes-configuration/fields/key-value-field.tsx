"use client"

import { useState } from "react"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { TbPlus, TbTrash } from "react-icons/tb"
import { FieldLabel } from "./field-label"
import type { FieldProps } from "./types"

/**
 * Key/value pair editor — HTTP headers, query string and the like.
 *
 * `ObjectField` (the JSON tree editor) is still right for nested structures,
 * but a header isn't a structure: it is a flat two-column list. In that editor,
 * writing `Content-Type: application/json` costs navigating a tree, choosing
 * the value type and confirming — for data the user already knows how to type
 * by heart. Here it is two fields and a button.
 *
 * The persisted value is still the SAME object as before; only the way it is
 * edited changes. Switching the field type in the schema migrates nothing and
 * doesn't invalidate saved workflows.
 */

type KeyValueFieldProps = FieldProps

/** Accepts an object or a JSON string — the saved value may come in either form. */
function paraObjeto(bruto: unknown): Record<string, string> {
  if (bruto && typeof bruto === "object") return bruto as Record<string, string>
  if (typeof bruto === "string" && bruto.trim()) {
    try {
      const lido = JSON.parse(bruto)
      if (lido && typeof lido === "object") return lido as Record<string, string>
    } catch { /* an invalid string becomes an empty object, as in the old editor */ }
  }
  return {}
}

/** Pairs in the order they appear in the saved object, with the value always a string. */
function paraPares(objeto: Record<string, string>): [string, string][] {
  return Object.entries(objeto).map(([k, v]) => [k, String(v ?? "")])
}

const KeyValueField = ({ field, values, setNodeField }: KeyValueFieldProps) => {

  const objeto = paraObjeto(values?.[field.name])
  const assinatura = JSON.stringify(objeto)

  // The rows live in LOCAL STATE, not derived from the saved object.
  //
  // The object doesn't allow an empty key — and an empty-key row is exactly
  // what a freshly created row is. While the list was recomputed from the saved
  // value, `Adicionar` (Add) wrote the blank row, the write discarded it, the
  // component re-rendered from the saved value and the row didn't appear: the
  // button simply did nothing, and the HttpRequest `headers` and `params` could
  // not be filled from the interface. For the same reason, clearing the name to
  // rename a header deleted the whole row mid-edit.
  const [pares, setPares] = useState<[string, string][]>(() => paraPares(objeto))

  // Seed: the last shape of the object THIS component knows. The path is
  // controlled (the modal hands back what we wrote, with no state of its own), so
  // without this marker every keystroke would come back as "changed from
  // outside" and drop the unnamed row the user is filling in. When the
  // difference is real — another node selected, value reset from outside — the
  // rows are reseeded.
  const [semente, setSemente] = useState(assinatura)
  if (assinatura !== semente) {
    setSemente(assinatura)
    setPares(paraPares(objeto))
  }

  function gravar(novosPares: [string, string][]) {
    setPares(novosPares)
    const saida: Record<string, string> = {}
    for (const [chave, valor] of novosPares) {
      const limpa = chave.trim()
      // An unnamed row stays on screen, but doesn't become a header: the value that
      // leaves the component is still only what can be sent.
      if (limpa) saida[limpa] = valor
    }
    setSemente(JSON.stringify(saida))
    setNodeField(field.name, saida as unknown as string)
  }

  function alterar(indice: number, coluna: 0 | 1, texto: string) {
    const copia = pares.map(p => [...p] as [string, string])
    copia[indice][coluna] = texto
    gravar(copia)
  }

  function remover(indice: number) {
    gravar(pares.filter((_, i) => i !== indice))
  }

  function adicionar() {
    gravar([...pares, ["", ""]])
  }

  return (
    <div>
      <FieldLabel field={field} htmlFor={null} />

      <div className="flex flex-col gap-1.5">
        {pares.length === 0 && (
          <p className="text-xs text-muted-foreground py-1">
            Nenhum item. Use o botão abaixo para adicionar.
          </p>
        )}

        {pares.map(([chave, valor], i) => (
          <div key={i} className="flex items-center gap-1.5">
            <Input
              value={chave}
              onChange={e => alterar(i, 0, e.target.value)}
              placeholder="Nome"
              className="h-8 text-xs font-mono flex-1 min-w-0"
              aria-label={`Nome do item ${i + 1}`}
            />
            <Input
              value={String(valor ?? "")}
              onChange={e => alterar(i, 1, e.target.value)}
              placeholder="Valor"
              className="h-8 text-xs font-mono flex-1 min-w-0"
              aria-label={`Valor do item ${i + 1}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => remover(i)}
              className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
              aria-label={`Remover item ${i + 1}`}
            >
              <TbTrash size={14} />
            </Button>
          </div>
        ))}

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={adicionar}
          className="h-8 gap-1.5 self-start"
        >
          <TbPlus size={14} />
          Adicionar
        </Button>
      </div>
    </div>
  )
}

export default KeyValueField
