"use client"

import { FieldLabel } from "./field-label"
import { INodeContext } from "@/context/useFlowContext"
import { useRef } from "react"
import { TbPackage, TbArrowRight } from "react-icons/tb"
import dynamic from "next/dynamic"
import type { FieldProps } from "./types"

// Lazy-load Monaco — pesa ~2.5MB e só é necessário quando a aba do code-field é aberta.
const MonacoCodeEditor = dynamic(() => import("./monaco-code-editor"), {
  ssr: false,
  loading: () => <div className="w-full h-44 animate-pulse rounded-md bg-[#272822]" />,
})

type CodeFieldProps = FieldProps<{
  nodeFound: INodeContext
}>

const LIBS = ["pd", "gpd", "np", "shapely"]

const CodeField = ({ field, values, setNodeField }: CodeFieldProps) => {
  // Função de inserção exposta pelo Monaco via onEditorReady
  const insertFnRef = useRef<((text: string) => void) | null>(null)

  // Variáveis de saída definidas pelo usuário em output_vars
  const outputVarsRaw = String(values?.output_vars ?? "result")
  const outputVars = outputVarsRaw.split(",").map(v => v.trim()).filter(Boolean)

  function insertAtCursor(text: string) {
    insertFnRef.current?.(text)
  }

  return (
    <div className="flex flex-col gap-2">
      {/* `htmlFor={null}`: o Monaco e de terceiros e nao expoe id. */}
      <FieldLabel field={field} htmlFor={null} />

      <MonacoCodeEditor
        value={String(values?.[field.name] ?? "")}
        onChange={v => setNodeField(field.name, v)}
        onEditorReady={fn => { insertFnRef.current = fn }}
        label={field.name}
      />

      {/* Painel de hints */}
      <div className="rounded-md border bg-muted/40 px-3 py-2 flex flex-col gap-2 text-xs">

        {/* Libs */}
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground shrink-0 flex items-center gap-1">
            <TbPackage className="w-3.5 h-3.5" />
            Libs:
          </span>
          {LIBS.map(lib => (
            <button
              key={lib}
              type="button"
              title={`Inserir "${lib}"`}
              onClick={() => insertAtCursor(lib)}
              className="rounded bg-muted text-muted-foreground border px-1.5 py-0.5 font-mono hover:bg-accent transition-colors"
            >
              {lib}
            </button>
          ))}
        </div>

        {/* Saídas */}
        {outputVars.length > 0 && (
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-muted-foreground shrink-0 flex items-center gap-1">
              <TbArrowRight className="w-3.5 h-3.5" />
              Saídas:
            </span>
            {outputVars.map(v => (
              <button
                key={v}
                type="button"
                title={`Inserir "${v}"`}
                onClick={() => insertAtCursor(v)}
                className="rounded bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20 px-1.5 py-0.5 font-mono hover:bg-green-500/20 transition-colors"
              >
                {v}
              </button>
            ))}
          </div>
        )}

      </div>

    </div>
  )
}

export default CodeField
