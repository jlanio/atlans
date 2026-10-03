"use client"
// Execution parameters dialog — generated dynamically from the workflow's params_schema
import { useState } from "react"
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { Switch } from "@/app/components/ui/switch"

export interface ParamSchema {
  type: "string" | "number" | "boolean" | "object"
  description?: string
  default?: unknown
  required?: boolean
}

interface ExecuteParamsDialogProps {
  open: boolean
  paramsSchema: Record<string, ParamSchema>
  onConfirm: (inputs: Record<string, unknown>) => void
  onCancel: () => void
  /** Home passes `home-portal`: the content is portaled to <body>, outside its palette. */
  className?: string
}

const ExecuteParamsDialog = ({
  open, paramsSchema, onConfirm, onCancel, className,
}: ExecuteParamsDialogProps) => {

  const fields = Object.entries(paramsSchema)

  const initialValues = () =>
    Object.fromEntries(
      fields.map(([key, schema]) => [key, schema.default ?? ""])
    )

  const [values, setValues] = useState<Record<string, unknown>>(initialValues)

  function handleChange(key: string, value: unknown) {
    setValues(prev => ({ ...prev, [key]: value }))
  }

  function handleConfirm() {
    // Converte tipos
    const coerced = Object.fromEntries(
      fields.map(([key, schema]) => {
        const v = values[key]
        if (schema.type === "number") return [key, Number(v)]
        if (schema.type === "boolean") return [key, Boolean(v)]
        return [key, v]
      })
    )
    onConfirm(coerced)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onCancel() }}>
      <DialogContent className={className}>
        <DialogHeader>
          <DialogTitle>Parâmetros de execução</DialogTitle>
          <DialogDescription>
            Preencha os parâmetros antes de executar o workflow.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          {fields.map(([key, schema]) => (
            <div key={key} className="flex flex-col gap-1">
              <Label htmlFor={key}>
                {key}
                {schema.required && <span className="text-red-500 ml-1">*</span>}
              </Label>

              {schema.type === "boolean" ? (
                <div className="flex items-center gap-2">
                  <Switch
                    id={key}
                    checked={!!values[key]}
                    onCheckedChange={(v) => handleChange(key, v)}
                  />
                  <span className="text-sm text-muted-foreground">
                    {values[key] ? "Verdadeiro" : "Falso"}
                  </span>
                </div>
              ) : (
                <Input
                  id={key}
                  type={schema.type === "number" ? "number" : "text"}
                  value={String(values[key] ?? "")}
                  onChange={(e) => handleChange(key, e.target.value)}
                  placeholder={schema.description ?? `Valor para ${key}`}
                />
              )}

              {schema.description && (
                <p className="text-xs text-muted-foreground">{schema.description}</p>
              )}
            </div>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>Cancelar</Button>
          <Button onClick={handleConfirm}>Executar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ExecuteParamsDialog
