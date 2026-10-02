"use client"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { Separator } from "@/app/components/ui/separator"
import { Badge } from "@/app/components/ui/badge"
import {
  TbPlus, TbTrash, TbCode, TbArrowRight, TbX,
} from "react-icons/tb"
import { FiEdit } from "react-icons/fi"
import SugestoesDeColunas from "./fields/sugestoes-de-colunas"

// ── Tipos ────────────────────────────────────────────────────────────────────

interface SetEntry   { field: string; value: string }
interface RenameEntry { from: string; to: string }

interface Props {
  values: Record<string, string | number | boolean> | undefined
  setNodeField: (field: string, value: string | number | boolean) => void
  hasUnsaved: boolean
  /** Colunas conhecidas dos nós anteriores — cada seção oferece as que ainda
   *  fazem sentido nela. Este helper substitui o renderizador de campos, onde
   *  a sugestão nasce; sem receber a lista, o "redefinir campos" era o único
   *  nó de coluna do fluxo que nunca via uma dica. */
  sugestoesDeColunas: string[]
  sugestoesDesatualizadas: boolean
  sugestoesParciais: boolean
}

// ── Helpers de serialização ──────────────────────────────────────────────────

function parseObj(raw: unknown): Record<string, string> {
  if (!raw) return {}
  if (typeof raw === "object" && !Array.isArray(raw)) return raw as Record<string, string>
  try { return JSON.parse(String(raw)) } catch { return {} }
}

function parseList(raw: unknown): string[] {
  if (Array.isArray(raw)) return raw as string[]
  if (!raw) return []
  try {
    const parsed = JSON.parse(String(raw))
    return Array.isArray(parsed) ? parsed : []
  } catch { return [] }
}

function objToSetEntries(obj: Record<string, string>): SetEntry[] {
  return Object.entries(obj).map(([field, value]) => ({ field, value }))
}

function setEntriesToObj(entries: SetEntry[]): Record<string, string> {
  return Object.fromEntries(entries.map(e => [e.field, e.value]))
}

function objToRenameEntries(obj: Record<string, string>): RenameEntry[] {
  return Object.entries(obj).map(([from, to]) => ({ from, to }))
}

function renameEntriesToObj(entries: RenameEntry[]): Record<string, string> {
  return Object.fromEntries(entries.map(e => [e.from, e.to]))
}

const isJinja = (v: string) => v.includes("{{") || v.includes("{%")

// ── Componente principal ─────────────────────────────────────────────────────

export default function SetFieldsHelper({
  values, setNodeField, hasUnsaved, sugestoesDeColunas, sugestoesDesatualizadas, sugestoesParciais,
}: Props) {

  // ── Estado derivado ────────────────────────────────────────────────────────
  const setEntries  = objToSetEntries(parseObj(values?.setFields))
  const removeFields = parseList(
    typeof values?.removeFields === "object" && !Array.isArray(values?.removeFields)
      ? (values?.removeFields as Record<string, unknown>)?.fields
      : values?.removeFields
  )
  const renameEntries = objToRenameEntries(parseObj(values?.renameFields))

  // Cada seção só oferece o que ainda não usou — oferecer o que já está lá é
  // ruído (a mesma regra do campo de fichas).
  const sugerirParaDefinir  = sugestoesDeColunas.filter(s => !setEntries.some(e => e.field === s))
  const sugerirParaRemover  = sugestoesDeColunas.filter(s => !removeFields.includes(s))
  const sugerirParaRenomear = sugestoesDeColunas.filter(s => !renameEntries.some(e => e.from === s))

  // ── Mutações ───────────────────────────────────────────────────────────────

  function updateSetEntries(next: SetEntry[]) {
    setNodeField("setFields", setEntriesToObj(next) as unknown as string)
  }

  function updateSetEntry(idx: number, key: keyof SetEntry, val: string) {
    const next = setEntries.map((e, i) => i === idx ? { ...e, [key]: val } : e)
    updateSetEntries(next)
  }

  function addSetEntry() {
    updateSetEntries([...setEntries, { field: "", value: "" }])
  }

  function removeSetEntry(idx: number) {
    updateSetEntries(setEntries.filter((_, i) => i !== idx))
  }

  function updateRemoveFields(next: string[]) {
    setNodeField("removeFields", { fields: next } as unknown as string)
  }

  function addRemoveField(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter") return
    const input = e.currentTarget
    const val = input.value.trim()
    if (val && !removeFields.includes(val)) {
      updateRemoveFields([...removeFields, val])
    }
    input.value = ""
  }

  function removeRemoveField(field: string) {
    updateRemoveFields(removeFields.filter(f => f !== field))
  }

  // Clique numa sugestão: preenche a primeira linha cujo campo está vazio, se
  // houver, ou abre uma linha nova — o valor (ou o "Para") continua com a
  // pessoa. Substituir um campo já preenchido nunca: a dica não pode custar o
  // que já foi digitado.
  function escolherParaDefinir(nome: string) {
    const vazia = setEntries.findIndex(e => e.field.trim() === "")
    if (vazia >= 0) updateSetEntry(vazia, "field", nome)
    else updateSetEntries([...setEntries, { field: nome, value: "" }])
  }

  function escolherParaRenomear(nome: string) {
    const vazia = renameEntries.findIndex(e => e.from.trim() === "")
    if (vazia >= 0) updateRenameEntry(vazia, "from", nome)
    else updateRenameEntries([...renameEntries, { from: nome, to: "" }])
  }

  function updateRenameEntries(next: RenameEntry[]) {
    setNodeField("renameFields", renameEntriesToObj(next) as unknown as string)
  }

  function updateRenameEntry(idx: number, key: keyof RenameEntry, val: string) {
    const next = renameEntries.map((e, i) => i === idx ? { ...e, [key]: val } : e)
    updateRenameEntries(next)
  }

  function addRenameEntry() {
    updateRenameEntries([...renameEntries, { from: "", to: "" }])
  }

  function removeRenameEntry(idx: number) {
    updateRenameEntries(renameEntries.filter((_, i) => i !== idx))
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-5 px-3 py-4 overflow-y-auto">

      {/* ── 1. Definir / Atualizar Campos ─────────────────────────────────── */}
      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <FiEdit className="h-3.5 w-3.5 text-primary" />
            <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
              Definir / Atualizar campos
            </p>
          </div>
          <Button size="icon" variant="ghost" className="h-6 w-6" onClick={addSetEntry}>
            <TbPlus className="h-3.5 w-3.5" />
          </Button>
        </div>

        {setEntries.length === 0 ? (
          <p className="text-[11px] text-muted-foreground italic px-1">
            Nenhum campo definido. Clique em + para adicionar.
          </p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {/* Cabeçalho */}
            <div className="grid grid-cols-[1fr_1fr_auto] gap-1.5 px-1">
              <span className="text-[10px] font-medium text-muted-foreground">Campo</span>
              <span className="text-[10px] font-medium text-muted-foreground">Valor / Expressão</span>
              <span />
            </div>

            {setEntries.map((entry, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_1fr_auto] gap-1.5 items-center">
                <Input
                  value={entry.field}
                  placeholder="nome_campo"
                  className="h-7 text-xs font-mono"
                  onChange={e => updateSetEntry(idx, "field", e.target.value)}
                />
                <div className="relative">
                  <Input
                    value={entry.value}
                    placeholder='"ativo" ou {{ row.area }}'
                    className={`h-7 text-xs font-mono pr-6 ${isJinja(entry.value) ? "border-amber-500/60 bg-amber-500/5" : ""}`}
                    onChange={e => updateSetEntry(idx, "value", e.target.value)}
                  />
                  {isJinja(entry.value) && (
                    <TbCode className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-amber-500" />
                  )}
                </div>
                <Button
                  size="icon" variant="ghost"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive"
                  onClick={() => removeSetEntry(idx)}
                >
                  <TbTrash className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}

            <p className="text-[10px] text-muted-foreground/60 px-1 leading-relaxed">
              Use <span className="font-mono bg-muted px-0.5 rounded">{"{{ row.campo }}"}</span> para expressões Jinja por linha.
            </p>
          </div>
        )}

        <SugestoesDeColunas
          nomes={sugerirParaDefinir}
          onEscolher={escolherParaDefinir}
          totalConhecido={sugestoesDeColunas.length}
          desatualizadas={sugestoesDesatualizadas}
          parciais={sugestoesParciais}
        />
      </section>

      <Separator />

      {/* ── 2. Remover Campos ─────────────────────────────────────────────── */}
      <section className="flex flex-col gap-2">
        <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
          Remover campos
        </p>

        <div className="flex flex-wrap gap-1.5 min-h-[2rem]">
          {removeFields.map(field => (
            <Badge
              key={field}
              variant="secondary"
              className="gap-1 font-mono text-[11px] pr-1 cursor-default"
            >
              {field}
              <button
                onClick={() => removeRemoveField(field)}
                className="ml-0.5 rounded-full hover:text-destructive transition-colors"
              >
                <TbX className="h-2.5 w-2.5" />
              </button>
            </Badge>
          ))}
        </div>

        <Input
          placeholder="Nome do campo + Enter para adicionar"
          className="h-7 text-xs font-mono"
          onKeyDown={addRemoveField}
        />

        <SugestoesDeColunas
          nomes={sugerirParaRemover}
          onEscolher={nome => updateRemoveFields([...removeFields, nome])}
          totalConhecido={sugestoesDeColunas.length}
          desatualizadas={sugestoesDesatualizadas}
          parciais={sugestoesParciais}
        />
      </section>

      <Separator />

      {/* ── 3. Renomear Campos ────────────────────────────────────────────── */}
      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
            Renomear campos
          </p>
          <Button size="icon" variant="ghost" className="h-6 w-6" onClick={addRenameEntry}>
            <TbPlus className="h-3.5 w-3.5" />
          </Button>
        </div>

        {renameEntries.length === 0 ? (
          <p className="text-[11px] text-muted-foreground italic px-1">
            Nenhuma renomeação definida.
          </p>
        ) : (
          <div className="flex flex-col gap-1.5">
            <div className="grid grid-cols-[1fr_auto_1fr_auto] gap-1.5 px-1">
              <span className="text-[10px] font-medium text-muted-foreground">De</span>
              <span />
              <span className="text-[10px] font-medium text-muted-foreground">Para</span>
              <span />
            </div>

            {renameEntries.map((entry, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_auto_1fr_auto] gap-1.5 items-center">
                <Input
                  value={entry.from}
                  placeholder="nome_antigo"
                  className="h-7 text-xs font-mono"
                  onChange={e => updateRenameEntry(idx, "from", e.target.value)}
                />
                <TbArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <Input
                  value={entry.to}
                  placeholder="nome_novo"
                  className="h-7 text-xs font-mono"
                  onChange={e => updateRenameEntry(idx, "to", e.target.value)}
                />
                <Button
                  size="icon" variant="ghost"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive"
                  onClick={() => removeRenameEntry(idx)}
                >
                  <TbTrash className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}

        <SugestoesDeColunas
          nomes={sugerirParaRenomear}
          onEscolher={escolherParaRenomear}
          totalConhecido={sugestoesDeColunas.length}
          desatualizadas={sugestoesDesatualizadas}
          parciais={sugestoesParciais}
        />
      </section>

      <Separator />

      {hasUnsaved && (
        <p className="text-sm text-destructive self-end">Há alterações não salvas!</p>
      )}

    </div>
  )
}
