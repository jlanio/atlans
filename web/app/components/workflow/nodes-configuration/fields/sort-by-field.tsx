"use client"

/**
 * Editor estruturado do `sort_by` do nó Ordenar.
 *
 * Antes o campo era `object` cru: a pessoa digitava
 * `[{"field":"area","direction":"desc"}]` num editor de JSON — hostil mesmo
 * sem sugestão, e sem lugar para oferecer as colunas conhecidas. Aqui cada
 * critério é uma linha campo+direção, com as colunas da última execução a um
 * clique.
 *
 * É um FIELD, não um helper: os campos irmãos do nó continuam visíveis ao
 * lado (a mesma razão registrada no cabeçalho do chips-field).
 *
 * O valor persiste como a MESMA lista `[{field, direction}]` que o execute do
 * backend já lê — nada de formato novo: um fluxo salvo pelo editor de JSON
 * abre aqui, e um salvo aqui roda em executor antigo.
 */
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"
import { TbPlus, TbTrash } from "react-icons/tb"

import { FieldLabel } from "./field-label"
import SugestoesDeColunas from "./sugestoes-de-colunas"
import type { FieldProps } from "./types"

export interface CriterioDeOrdenacao {
  field: string
  direction: "asc" | "desc"
}

/** Lê o valor salvo, venha como lista (ObjectField/definition) ou JSON-string. */
export function lerCriterios(bruto: unknown): CriterioDeOrdenacao[] {
  let lista: unknown = bruto
  if (typeof bruto === "string" && bruto.trim().startsWith("[")) {
    try { lista = JSON.parse(bruto) } catch { lista = [] }
  }
  if (!Array.isArray(lista)) return []
  return lista
    .filter((c): c is Record<string, unknown> => !!c && typeof c === "object")
    .map(c => ({
      field: String(c.field ?? ""),
      direction: String(c.direction ?? "asc").toLowerCase() === "desc" ? "desc" as const : "asc" as const,
    }))
}

type SortByFieldProps = FieldProps<{
  sugestoes?: string[]
  sugestoesDesatualizadas?: boolean
  sugestoesParciais?: boolean
}>

const SortByField = ({ field, values, setNodeField, sugestoes = [], sugestoesDesatualizadas = false, sugestoesParciais = false }: SortByFieldProps) => {
  const criterios = lerCriterios(values?.[field.name])

  // A lista REAL, não JSON-string: é o que o execute lê hoje — e o cast é o
  // mesmo do SetFieldsHelper, porque `setNodeField` só tipa escalares.
  const gravar = (next: CriterioDeOrdenacao[]) =>
    setNodeField(field.name, next as unknown as string)

  const editar = (idx: number, mudanca: Partial<CriterioDeOrdenacao>) =>
    gravar(criterios.map((c, i) => (i === idx ? { ...c, ...mudanca } : c)))

  // Clique numa sugestão: preenche a primeira linha vazia ou abre uma nova —
  // nunca substitui o que já foi digitado.
  function escolher(nome: string) {
    const vazia = criterios.findIndex(c => c.field.trim() === "")
    if (vazia >= 0) editar(vazia, { field: nome })
    else gravar([...criterios, { field: nome, direction: "asc" }])
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <FieldLabel field={field} />
        <Button
          size="icon" variant="ghost" className="h-6 w-6"
          aria-label="Adicionar critério"
          onClick={() => gravar([...criterios, { field: "", direction: "asc" }])}
        >
          <TbPlus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {criterios.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic px-1">
          Nenhum critério. Clique em + (ou numa coluna abaixo) para adicionar.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {criterios.map((criterio, idx) => (
            <div key={idx} className="grid grid-cols-[1fr_7.5rem_auto] gap-1.5 items-center">
              <Input
                value={criterio.field}
                placeholder="nome_da_coluna"
                className="h-7 text-xs font-mono"
                onChange={e => editar(idx, { field: e.target.value })}
              />
              <Select
                value={criterio.direction}
                onValueChange={v => editar(idx, { direction: v as CriterioDeOrdenacao["direction"] })}
              >
                <SelectTrigger className="h-7 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="asc">Crescente</SelectItem>
                  <SelectItem value="desc">Decrescente</SelectItem>
                </SelectContent>
              </Select>
              <Button
                size="icon" variant="ghost"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                aria-label={`Remover critério ${idx + 1}`}
                onClick={() => gravar(criterios.filter((_, i) => i !== idx))}
              >
                <TbTrash className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <SugestoesDeColunas
        nomes={sugestoes.filter(s => !criterios.some(c => c.field === s))}
        onEscolher={escolher}
        totalConhecido={sugestoes.length}
        desatualizadas={sugestoesDesatualizadas}
        parciais={sugestoesParciais}
      />
    </div>
  )
}

export default SortByField
