"use client"

import { useState, useEffect, useCallback } from "react"
import { Label } from "@/app/components/ui/label"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"
import { TbPlus, TbTrash } from "react-icons/tb"
import type { FieldProps } from "./types"

// ── Tipos ────────────────────────────────────────────────────────────────────

interface SchemaField {
  name: string
  type: "string" | "number" | "boolean" | "object" | "array"
  required: boolean
}

const TYPE_OPTIONS: { value: SchemaField["type"]; label: string }[] = [
  { value: "string",  label: "Texto" },
  { value: "number",  label: "Numero" },
  { value: "boolean", label: "Booleano" },
  { value: "object",  label: "Objeto" },
  { value: "array",   label: "Lista" },
]

// ── Conversao tabela <-> JSON Schema ─────────────────────────────────────────

function fieldsToJsonSchema(fields: SchemaField[]): Record<string, unknown> {
  if (fields.length === 0) return {}
  const required = fields.filter(f => f.required).map(f => f.name)
  return {
    type: "object",
    ...(required.length > 0 ? { required } : {}),
    properties: Object.fromEntries(
      fields.map(f => [f.name, { type: f.type }])
    ),
  }
}

function jsonSchemaToFields(schema: unknown): SchemaField[] {
  if (!schema || typeof schema !== "object") return []
  const s = schema as Record<string, unknown>
  const props = s.properties as Record<string, { type?: string }> | undefined
  if (!props) return []
  const req = new Set((s.required as string[]) ?? [])
  return Object.entries(props).map(([name, prop]) => ({
    name,
    type: (prop.type ?? "string") as SchemaField["type"],
    required: req.has(name),
  }))
}

// ── Componente ───────────────────────────────────────────────────────────────

type PayloadSchemaEditorProps = FieldProps

export default function PayloadSchemaEditor({ field, values, setNodeField }: PayloadSchemaEditorProps) {
  // Carrega estado inicial do schema salvo
  const [fields, setFields] = useState<SchemaField[]>(() => {
    const raw = values?.[field.name]
    if (!raw) return []
    const parsed = typeof raw === "string" ? (() => { try { return JSON.parse(raw) } catch { return null } })() : raw
    return jsonSchemaToFields(parsed)
  })

  // Sincroniza mudanças para o nó
  const syncToNode = useCallback((updated: SchemaField[]) => {
    setFields(updated)
    setNodeField(field.name, fieldsToJsonSchema(updated) as unknown as string)
  }, [field.name, setNodeField])

  // Recarrega se o valor externo mudar (ex: undo)
  useEffect(() => {
    const raw = values?.[field.name]
    if (!raw) return
    const parsed = typeof raw === "string" ? (() => { try { return JSON.parse(raw) } catch { return null } })() : raw
    const fromSchema = jsonSchemaToFields(parsed)
    // Evita loop: só atualiza se realmente diferente
    if (JSON.stringify(fromSchema) !== JSON.stringify(fields)) {
      setFields(fromSchema)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values?.[field.name]])

  function addField() {
    syncToNode([...fields, { name: "", type: "string", required: false }])
  }

  function removeField(index: number) {
    syncToNode(fields.filter((_, i) => i !== index))
  }

  function updateField(index: number, key: keyof SchemaField, value: string | boolean) {
    const updated = fields.map((f, i) => i === index ? { ...f, [key]: value } : f)
    syncToNode(updated)
  }

  return (
    <div className="flex flex-col gap-2">
      <Label>{field.description ?? "Schema do payload"}</Label>

      {fields.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {/* Cabecalho */}
          <div className="grid grid-cols-[1fr_100px_60px_28px] gap-1.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-0.5">
            <span>Campo</span>
            <span>Tipo</span>
            <span className="text-center">Obrig.</span>
            <span />
          </div>

          {/* Linhas */}
          {fields.map((f, i) => (
            <div key={i} className="grid grid-cols-[1fr_100px_60px_28px] gap-1.5 items-center">
              <Input
                value={f.name}
                onChange={e => updateField(i, "name", e.target.value)}
                placeholder="nome_do_campo"
                className="h-8 text-xs font-mono"
              />
              <Select
                value={f.type}
                onValueChange={v => updateField(i, "type", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value} className="text-xs">
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex justify-center">
                <input
                  type="checkbox"
                  checked={f.required}
                  onChange={e => updateField(i, "required", e.target.checked)}
                  className="h-4 w-4 rounded border-border accent-primary cursor-pointer"
                />
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                onClick={() => removeField(i)}
              >
                <TbTrash className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <Button
        type="button"
        variant="outline"
        size="sm"
        className="w-full text-xs gap-1.5"
        onClick={addField}
      >
        <TbPlus className="h-3.5 w-3.5" />
        Adicionar campo
      </Button>

      {fields.length === 0 && (
        <p className="text-[11px] text-muted-foreground">
          Nenhum campo definido — qualquer payload sera aceito.
        </p>
      )}
    </div>
  )
}
