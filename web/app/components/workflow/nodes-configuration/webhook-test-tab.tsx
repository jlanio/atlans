"use client"
import { useState, useMemo } from "react"
import { TbPlayerPlay, TbLoader2 } from "react-icons/tb"
import { Textarea } from "@/app/components/ui/textarea"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { Switch } from "@/app/components/ui/switch"
import { Button } from "@/app/components/ui/button"
import { StatusBadge } from "@/app/components/shared/StatusBadge"
import { useExecuteWorkflow } from "@/app/hooks/workflow/useExecuteWorkflow"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { generateSampleFromSchema } from "./webhook-sample"

// ── Helpers ──────────────────────────────────────────────────────────────────

interface SchemaField {
  name: string
  type: "string" | "number" | "integer" | "boolean" | "object" | "array"
  required: boolean
}

function parseSchemaFields(payloadSchema: unknown): SchemaField[] {
  let schema = payloadSchema
  if (typeof schema === "string") {
    try { schema = JSON.parse(schema) } catch { return [] }
  }
  if (!schema || typeof schema !== "object") return []
  const s = schema as Record<string, unknown>
  const props = s.properties as Record<string, { type?: string }> | undefined
  if (!props || Object.keys(props).length === 0) return []
  const req = new Set((s.required as string[]) ?? [])
  return Object.entries(props).map(([name, prop]) => ({
    name,
    type: (prop.type ?? "string") as SchemaField["type"],
    required: req.has(name),
  }))
}

const DEFAULTS: Record<string, unknown> = {
  string: "", number: 0, integer: 0, boolean: false, object: {}, array: [],
}

// ── Componente ───────────────────────────────────────────────────────────────

interface Props {
  workflowId: string | undefined
  outputKey: string
  payloadSchema?: unknown
}

export default function WebhookTestTab({ workflowId, outputKey, payloadSchema }: Props) {
  const fields = useMemo(() => parseSchemaFields(payloadSchema), [payloadSchema])
  const hasFields = fields.length > 0

  // Estado do formulário dinâmico
  const [fieldValues, setFieldValues] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(fields.map(f => {
      const def = DEFAULTS[f.type] ?? ""
      // Campos object/array usam Textarea — inicializar como string JSON
      if (f.type === "object" || f.type === "array") return [f.name, JSON.stringify(def, null, 2)]
      return [f.name, def]
    }))
  )

  // Estado do textarea (fallback sem schema)
  const jsonTemplate = useMemo(
    () => JSON.stringify(generateSampleFromSchema(outputKey, payloadSchema), null, 2),
    [outputKey, payloadSchema],
  )
  const [jsonBody, setJsonBody] = useState(jsonTemplate)
  const [jsonError, setJsonError] = useState<string | null>(null)

  const { executeWorkflow, isExecuting } = useExecuteWorkflow()
  const statusWorkflow = useWorkflowExecutionStore(s => s.statusWorkflow)

  // Monta o payload a partir dos campos ou do textarea
  function buildPayload(): Record<string, unknown> | null {
    if (hasFields) {
      const coerced: Record<string, unknown> = {}
      for (const f of fields) {
        const v = fieldValues[f.name]
        if (f.type === "number" || f.type === "integer") {
          coerced[f.name] = Number(v)
        } else if (f.type === "boolean") {
          coerced[f.name] = Boolean(v)
        } else if (f.type === "object" || f.type === "array") {
          try {
            coerced[f.name] = typeof v === "string" ? JSON.parse(v) : v
          } catch {
            setJsonError(`Campo "${f.name}": JSON inválido.`)
            return null
          }
        } else {
          coerced[f.name] = v
        }
      }
      // Envolve só se payloadField foi configurado pelo usuario; caso contrario
      // entrega os campos direto (mesma convencao que o webhook HTTP usa).
      return outputKey ? { [outputKey]: coerced } : coerced
    }
    try {
      const parsed = JSON.parse(jsonBody)
      setJsonError(null)
      return parsed
    } catch {
      setJsonError("JSON inválido — corrija a sintaxe antes de testar.")
      return null
    }
  }

  function handleTest() {
    const payload = buildPayload()
    if (payload) executeWorkflow(payload)
  }

  function handleFieldChange(name: string, value: unknown) {
    setFieldValues(prev => ({ ...prev, [name]: value }))
  }

  // Indicador de status da última execução
  const status = statusWorkflow?.status
  const showStatus = status && status !== "idle"

  return (
    <div className="flex flex-col gap-3 px-1 mt-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Payload de teste
      </p>

      {hasFields ? (
        <div className="flex flex-col gap-3">
          {fields.map(f => (
            <div key={f.name} className="flex flex-col gap-1">
              <Label htmlFor={`wh-test-${f.name}`} className="text-[11px]">
                {f.name}
                {f.required && <span className="text-red-500 ml-0.5">*</span>}
                <span className="ml-1 text-muted-foreground font-normal">({f.type})</span>
              </Label>

              {f.type === "boolean" ? (
                <div className="flex items-center gap-2">
                  <Switch
                    id={`wh-test-${f.name}`}
                    checked={!!fieldValues[f.name]}
                    onCheckedChange={v => handleFieldChange(f.name, v)}
                  />
                  <span className="text-[11px] text-muted-foreground">
                    {fieldValues[f.name] ? "true" : "false"}
                  </span>
                </div>
              ) : f.type === "object" || f.type === "array" ? (
                <Textarea
                  id={`wh-test-${f.name}`}
                  value={String(fieldValues[f.name] ?? "")}
                  onChange={e => handleFieldChange(f.name, e.target.value)}
                  placeholder={f.type === "array" ? "[...]" : "{...}"}
                  rows={5}
                  className="font-mono text-[11px] leading-relaxed resize-y"
                  spellCheck={false}
                />
              ) : (
                <Input
                  id={`wh-test-${f.name}`}
                  type={f.type === "number" || f.type === "integer" ? "number" : "text"}
                  value={String(fieldValues[f.name] ?? "")}
                  onChange={e => handleFieldChange(f.name, e.target.value)}
                  placeholder={`Valor para ${f.name}`}
                  className="text-[11px] h-8"
                />
              )}
            </div>
          ))}
        </div>
      ) : (
        <>
          <Textarea
            value={jsonBody}
            onChange={e => {
              setJsonBody(e.target.value)
              if (jsonError) setJsonError(null)
            }}
            rows={10}
            className="font-mono text-[11px] leading-relaxed resize-y"
            placeholder='{ }'
            spellCheck={false}
          />
          {jsonError && <p className="text-xs text-destructive">{jsonError}</p>}
        </>
      )}

      <div className="flex items-center justify-between gap-2">
        {showStatus ? <StatusBadge status={status} /> : <span />}

        <Button
          size="sm"
          className="gap-1.5"
          onClick={handleTest}
          disabled={isExecuting || !workflowId}
        >
          {isExecuting ? (
            <TbLoader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <TbPlayerPlay className="h-3.5 w-3.5" />
          )}
          {isExecuting ? "Executando…" : "Testar"}
        </Button>
      </div>

      <p className="text-[11px] text-muted-foreground leading-relaxed">
        O resultado será exibido no canvas, como uma execução normal.
      </p>
    </div>
  )
}
