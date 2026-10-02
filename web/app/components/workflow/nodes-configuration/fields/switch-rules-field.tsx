"use client"

/**
 * Editor estruturado das `rules` do nó Switch.
 *
 * Antes o campo era `object` cru: cada regra era um dict digitado à mão num
 * editor de JSON — `{"field":"uf","operator":"==","value":"MT","output":
 * "output_1"}` — com operador e saída fáceis de errar e nenhum lugar para as
 * colunas conhecidas. Aqui cada regra é uma linha campo+operador+valor+saída,
 * com selects para o que é enumerável.
 *
 * O valor persiste como a MESMA lista de dicts que o execute lê — um fluxo
 * salvo pelo editor de JSON abre aqui, e vice-versa.
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

/** Espelha `_OP_FUNCS` + extras do switch.py — a fonte é o backend. */
export const OPERADORES_DO_SWITCH = ["==", "!=", ">", "<", ">=", "<=", "contains", "starts", "ends"] as const

/** As saídas que o descriptor do Switch declara (outputs output_0..3).
 *  output_0 é a saída padrão/fallback — as regras normalmente apontam 1..3. */
export const SAIDAS_DO_SWITCH = ["output_0", "output_1", "output_2", "output_3"] as const

/** Colunas da grade de regras (cabeçalho e linhas): campo, operador, valor,
 *  saída, remover. As trilhas fixas cabem o valor mais largo em fonte mono —
 *  "contains" no operador, "Saída padrão" na saída —, e os triggers ocupam a
 *  trilha inteira (`w-full min-w-0`) em vez de `w-fit`: um trigger que passa da
 *  própria trilha fica por cima do botão "Remover regra", e o clique na seta do
 *  select apagava a regra. */
const COLUNAS_DAS_REGRAS = "grid-cols-[1fr_6.75rem_1fr_8.75rem_auto]"

export interface RegraDoSwitch {
  field: string
  operator: string
  value: string
  /** "" = SEM `output` na regra: o execute roteia para o fallback
   *  (`rule.get("output", fallback)`). Não é um estado inventável — uma
   *  definition legada sem a chave TEM esse comportamento, e normalizá-la
   *  para "output_1" mudaria o roteamento na primeira edição salva. */
  output: string
}

/** Lê o valor salvo, venha como lista (ObjectField/definition) ou JSON-string.
 *
 * `field`/`operator`/`value` ganham os MESMOS defaults do execute
 * (`rule.get("field","")`, `"=="`, `""`), então normalizá-los não muda
 * comportamento. `output` é o único cuja ausência significa outra coisa
 * (fallback) — fica "" e a serialização omite a chave. */
export function lerRegras(bruto: unknown): RegraDoSwitch[] {
  let lista: unknown = bruto
  if (typeof bruto === "string" && bruto.trim().startsWith("[")) {
    try { lista = JSON.parse(bruto) } catch { lista = [] }
  }
  if (!Array.isArray(lista)) return []
  return lista
    .filter((r): r is Record<string, unknown> => !!r && typeof r === "object")
    .map(r => ({
      field: String(r.field ?? ""),
      operator: String(r.operator ?? "=="),
      value: String(r.value ?? ""),
      output: r.output != null ? String(r.output) : "",
    }))
}

/** O que vai para a definition: a regra como o execute a lê — sem `output`
 *  quando a regra roteia para o fallback. */
export function serializarRegras(regras: RegraDoSwitch[]): Record<string, string>[] {
  return regras.map(({ field, operator, value, output }) => ({
    field, operator, value,
    ...(output ? { output } : {}),
  }))
}

/** Valor do SelectItem da saída padrão — Select não aceita item com value "". */
const FALLBACK = "__fallback__"

type SwitchRulesFieldProps = FieldProps<{
  sugestoes?: string[]
  sugestoesDesatualizadas?: boolean
  sugestoesParciais?: boolean
}>

const SwitchRulesField = ({ field, values, setNodeField, sugestoes = [], sugestoesDesatualizadas = false, sugestoesParciais = false }: SwitchRulesFieldProps) => {
  const regras = lerRegras(values?.[field.name])

  // A lista REAL, não JSON-string — mesmo cast do SetFieldsHelper. Serializa
  // pelo contrato do execute: regra de fallback vai SEM a chave `output`.
  const gravar = (next: RegraDoSwitch[]) =>
    setNodeField(field.name, serializarRegras(next) as unknown as string)

  const editar = (idx: number, mudanca: Partial<RegraDoSwitch>) =>
    gravar(regras.map((r, i) => (i === idx ? { ...r, ...mudanca } : r)))

  const novaRegra = (nomeDoCampo = ""): RegraDoSwitch =>
    ({ field: nomeDoCampo, operator: "==", value: "", output: "output_1" })

  // Clique numa sugestão: preenche a primeira regra sem campo ou abre uma
  // nova — nunca substitui o que já foi digitado. A MESMA coluna pode reger
  // várias regras (uf == MT → 1, uf == GO → 2), então aqui a lista não é
  // filtrada pelo que já está em uso.
  function escolher(nome: string) {
    const vazia = regras.findIndex(r => r.field.trim() === "")
    if (vazia >= 0) editar(vazia, { field: nome })
    else gravar([...regras, novaRegra(nome)])
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <FieldLabel field={field} />
        <Button
          size="icon" variant="ghost" className="h-6 w-6"
          aria-label="Adicionar regra"
          onClick={() => gravar([...regras, novaRegra()])}
        >
          <TbPlus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {regras.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic px-1">
          Nenhuma regra: tudo cai na saída padrão. Clique em + para adicionar.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className={`grid ${COLUNAS_DAS_REGRAS} gap-1.5 px-1`}>
            <span className="text-[10px] font-medium text-muted-foreground">Campo</span>
            <span className="text-[10px] font-medium text-muted-foreground">Operador</span>
            <span className="text-[10px] font-medium text-muted-foreground">Valor</span>
            <span className="text-[10px] font-medium text-muted-foreground">Saída</span>
            <span />
          </div>

          {regras.map((regra, idx) => (
            <div key={idx} className={`grid ${COLUNAS_DAS_REGRAS} gap-1.5 items-center`}>
              <Input
                value={regra.field}
                placeholder="coluna"
                className="h-7 text-xs font-mono"
                onChange={e => editar(idx, { field: e.target.value })}
              />
              <Select value={regra.operator} onValueChange={v => editar(idx, { operator: v })}>
                <SelectTrigger className="h-7 w-full min-w-0 text-xs font-mono">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {/* Operador fora do vocabulário (definition editada à mão):
                      vira item para o valor aparecer e sobreviver à edição —
                      um Select mudo apagaria a escolha na primeira gravação. */}
                  {!OPERADORES_DO_SWITCH.includes(regra.operator as never) && (
                    <SelectItem value={regra.operator} className="font-mono text-xs">{regra.operator}</SelectItem>
                  )}
                  {OPERADORES_DO_SWITCH.map(op => (
                    <SelectItem key={op} value={op} className="font-mono text-xs">{op}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                value={regra.value}
                placeholder="valor"
                className="h-7 text-xs font-mono"
                onChange={e => editar(idx, { value: e.target.value })}
              />
              <Select
                value={regra.output || FALLBACK}
                onValueChange={v => editar(idx, { output: v === FALLBACK ? "" : v })}
              >
                <SelectTrigger className="h-7 w-full min-w-0 text-xs font-mono">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {/* Regra sem `output` roteia para a saída padrão E encerra a
                      avaliação — é um estado legítimo de definition legada,
                      não um buraco a preencher. */}
                  <SelectItem value={FALLBACK} className="text-xs">Saída padrão</SelectItem>
                  {regra.output !== "" && !SAIDAS_DO_SWITCH.includes(regra.output as never) && (
                    <SelectItem value={regra.output} className="font-mono text-xs">{regra.output}</SelectItem>
                  )}
                  {SAIDAS_DO_SWITCH.map(saida => (
                    <SelectItem key={saida} value={saida} className="font-mono text-xs">{saida}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="icon" variant="ghost"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                aria-label={`Remover regra ${idx + 1}`}
                onClick={() => gravar(regras.filter((_, i) => i !== idx))}
              >
                <TbTrash className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <SugestoesDeColunas
        nomes={sugestoes}
        onEscolher={escolher}
        totalConhecido={sugestoes.length}
        desatualizadas={sugestoesDesatualizadas}
        parciais={sugestoesParciais}
      />
    </div>
  )
}

export default SwitchRulesField
