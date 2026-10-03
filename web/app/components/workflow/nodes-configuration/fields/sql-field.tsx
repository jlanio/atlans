"use client"

import { FieldLabel } from "./field-label"
// `Label` is still used for the query's named parameters, which don't come
// from the node schema and therefore don't go through FieldLabel.
import { Label } from "@/app/components/ui/label"
import { Input } from "@/app/components/ui/input"
import { useCallback, useMemo, useRef, useState } from "react"
import { TbVariable } from "react-icons/tb"
import dynamic from "next/dynamic"
import { extrairPlaceholders } from "@/lib/sql-literals"
import type { FieldProps } from "./types"

// Lazy-load Monaco — it weighs ~2.5MB and is only needed when sql-field mounts.
const MonacoCodeEditor = dynamic(() => import("./monaco-code-editor"), {
  ssr: false,
  loading: () => <div className="w-full h-44 animate-pulse rounded-md bg-[#272822]" />,
})

type SqlFieldProps = FieldProps<{
  /** Name of the associated queryParams field (e.g. "queryParams"). When
   *  provided, renders named inputs for each :placeholder in the query. */
  paramsFieldName?: string
}>

const SqlField = ({ field, values, setNodeField, paramsFieldName }: SqlFieldProps) => {
  const insertFnRef = useRef<((text: string) => void) | null>(null)

  function insertAtCursor(text: string) {
    insertFnRef.current?.(text)
  }

  const [dragOver, setDragOver] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const text = e.dataTransfer.getData("text/plain")
    if (text) insertAtCursor(text)
  }, [])

  const sqlValue = String(values?.[field.name] ?? "")

  // Placeholders found in the query. `extrairPlaceholders` ignores what is
  // inside strings or comments — before, the regex scanned the raw text, and
  // `WHERE obs = 'urgente:revisar'` made the panel offer a `:revisar` that
  // doesn't exist (and the backend rejected the whole query because of it).
  const paramNames = useMemo(() => extrairPlaceholders(sqlValue), [sqlValue])

  // Current param values (object stored as the value of the paramsFieldName field)
  const currentParams: Record<string, string> = useMemo(() => {
    if (!paramsFieldName) return {}
    const raw = values?.[paramsFieldName]
    if (typeof raw === "object" && raw !== null) return raw as unknown as Record<string, string>
    if (typeof raw === "string") {
      try { return JSON.parse(raw) } catch { return {} }
    }
    return {}
  }, [paramsFieldName, values])

  function setParamValue(name: string, value: string) {
    if (!paramsFieldName) return
    const atuais = { ...currentParams, [name]: value }

    // Only the placeholders the query asks for NOW survive. Before, the write
    // was a plain `{...currentParams, [name]: value}`, and nothing ever left:
    // whoever renamed `:bairro` to `:cidade` left `bairro` in the saved
    // definition forever — invisible on screen, but written to the workflow and
    // to the whole version history, with whatever value it held.
    //
    // Pruning happens when editing a VALUE, not when editing the SQL. Pruning
    // on every editor keystroke would erase the value of `:bairro` the instant
    // the query said `:bairr` — the user would lose what they typed in the
    // middle of a rename. When editing values, the query is already in the
    // shape they wanted, and what gets saved becomes exactly what is on screen.
    const next: Record<string, string> = {}
    for (const chave of paramNames) {
      if (chave in atuais) next[chave] = atuais[chave]
    }
    setNodeField(paramsFieldName, next as unknown as string)
  }

  // Snippets SQL comuns
  const SQL_SNIPPETS = [
    { label: "SELECT", text: "SELECT * FROM " },
    { label: "WHERE", text: "WHERE " },
    { label: "JOIN", text: "INNER JOIN  ON " },
    { label: "GROUP BY", text: "GROUP BY " },
    { label: "ORDER BY", text: "ORDER BY " },
    { label: "LIMIT", text: "LIMIT " },
    { label: "ST_Within", text: "ST_Within(geom, ST_GeomFromText('', 4326))" },
    { label: "ST_Buffer", text: "ST_Buffer(geom, )" },
    { label: "ST_Area", text: "ST_Area(geom::geography)" },
  ]

  return (
    <div
      className={`flex flex-col gap-2 rounded transition-colors ${dragOver ? "bg-blue-50 dark:bg-blue-950 ring-2 ring-blue-400" : ""}`}
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
    >
      {/* `htmlFor={null}`: Monaco is third-party and doesn't expose an id. */}
      <FieldLabel field={field} htmlFor={null} />

      <MonacoCodeEditor
        value={sqlValue}
        onChange={v => setNodeField(field.name, v)}
        onEditorReady={fn => { insertFnRef.current = fn }}
        label={field.name}
        language="sql"
        minHeight={120}
      />

      {/* SQL snippets panel */}
      <div className="rounded-md border bg-muted/40 px-3 py-2 flex flex-col gap-2 text-xs">
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground shrink-0 flex items-center gap-1">
            <TbVariable className="w-3.5 h-3.5" />
            SQL:
          </span>
          {SQL_SNIPPETS.map(s => (
            <button
              key={s.label}
              type="button"
              title={`Inserir ${s.label}`}
              onClick={() => insertAtCursor(s.text)}
              className="rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 px-1.5 py-0.5 font-mono hover:bg-blue-500/20 transition-colors"
            >
              {s.label}
            </button>
          ))}
        </div>

        <p className="text-[10px] text-muted-foreground">
          Use <code className="px-1 bg-muted rounded">:param</code> para placeholders e
          <code className="px-1 bg-muted rounded">{"{{ $Alias }}"}</code> para expressoes dinamicas.
          Apenas consultas SELECT sao permitidas.
        </p>
      </div>

      {/* Inputs gerados automaticamente a partir dos :placeholders */}
      {paramsFieldName && paramNames.length > 0 && (
        <div className="rounded-md border bg-muted/40 px-3 py-2 flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
            <TbVariable className="w-3.5 h-3.5" />
            Parametros detectados
          </span>
          <div className="flex flex-col gap-2">
            {paramNames.map(name => (
              <div key={name} className="flex flex-col gap-0.5">
                <Label className="text-xs font-mono flex items-center gap-1">
                  <code className="px-1 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 text-[11px]">
                    :{name}
                  </code>
                </Label>
                <Input
                  value={currentParams[name] ?? ""}
                  onChange={e => setParamValue(name, e.target.value)}
                  placeholder={`Valor para :${name}`}
                  className="h-8 text-sm font-mono"
                />
              </div>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground">
            Aceita valor fixo ou expressao — <code className="px-1 bg-muted rounded">{"{{ $Alias.campo }}"}</code> e
            resolvido antes da consulta, preservando o tipo (numero segue numero).
            Tambem da para mandar o objeto inteiro conectando um node anterior com a
            chave <code className="px-1 bg-muted rounded">queryParams</code>.
          </p>
        </div>
      )}
    </div>
  )
}

export default SqlField
