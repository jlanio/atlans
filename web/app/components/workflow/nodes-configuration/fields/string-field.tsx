import { FieldLabel } from "./field-label"
import { Input } from "@/app/components/ui/input"
import { INodeContext } from "@/context/useFlowContext"
import ExpressionInput from "./expression-input"
import { useCallback, useState } from "react"
import type { FieldProps } from "./types"

type StringFieldProps = FieldProps<{
  nodeFound?: INodeContext
  /** Column names seen in the previous node's last execution. Offered below
   *  the field — clicking fills it in. It is a hint, not validation: the
   *  workflow may have changed since then, and writing a name outside the list
   *  is still valid. */
  sugestoes?: string[]
  /** true when the suggestions came from re-hydrating a PERSISTED run (not
   *  from this session): the label changes to warn that the list may have
   *  changed — claiming "last execution" with old data would be lying. */
  sugestoesDesatualizadas?: boolean
  /** true when the source stat came truncated — the label warns "partial
   *  list" instead of claiming completeness. */
  sugestoesParciais?: boolean
}>

const StringField = ({ field, values, setNodeField, nodeFound, sugestoes = [], sugestoesDesatualizadas = false, sugestoesParciais = false }: StringFieldProps) => {
  const currentValue = `${values?.[field.name] ?? ""}`
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const text = e.dataTransfer.getData("text/plain")
    if (text) {
      // Appends the expression to the current value (or replaces it if empty)
      const newValue = currentValue ? `${currentValue} ${text}` : text
      setNodeField(field.name, newValue)
    }
  }, [currentValue, field.name, setNodeField])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "copy"
    setDragOver(true)
  }, [])

  return (
    <div
      className={`flex flex-col gap-1 rounded transition-colors ${dragOver ? "bg-blue-50 dark:bg-blue-950 ring-2 ring-blue-400" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragOver(false)}
    >
      <FieldLabel field={field} />
      {nodeFound ? (
        // No `placeholder={field.description}`: it was the SAME sentence that showed
        // in the paragraph below, so the whole description was displayed twice.
        // A placeholder should be an example value, not the field's documentation.
        <ExpressionInput
          id={field.name}
          value={currentValue}
          onChange={v => setNodeField(field.name, v)}
          nodeFound={nodeFound}
          placeholder={field.placeholder}
        />
      ) : (
        <Input
          id={field.name}
          onChange={e => setNodeField(field.name, e.target.value)}
          value={currentValue}
          placeholder={field.placeholder}
        />
      )}

      {sugestoes.length > 0 && (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-[11px] text-muted-foreground">
            {sugestoesDesatualizadas
              ? "Vistas em execução anterior (podem ter mudado)"
              : "Vistas na última execução"}
            {sugestoesParciais && " (lista parcial)"}:
          </span>
          {sugestoes.map(nome => (
            <button
              key={nome}
              type="button"
              onClick={() => setNodeField(field.name, nome)}
              className={`rounded border px-1.5 py-px font-mono text-[11px] transition-colors ${
                currentValue === nome
                  ? "border-primary/60 bg-primary/10 text-foreground"
                  : "border-dashed border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {nome}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default StringField
