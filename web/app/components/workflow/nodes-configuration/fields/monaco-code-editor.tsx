"use client"

import { useState, useCallback, useRef } from "react"
import Editor, { loader, OnMount } from "@monaco-editor/react"
import type * as Monaco from "monaco-editor"
import { TbArrowsMaximize, TbArrowsMinimize } from "react-icons/tb"
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/app/components/ui/dialog"

interface MonacoCodeEditorProps {
  value: string
  onChange(value: string): void
  onEditorReady?(insertFn: (text: string) => void): void
  minHeight?: number
  label?: string
  /** Editor language (default: "python") */
  language?: string
}

/**
 * Monaco comes from our own origin (`public/monaco/vs`, copied from the
 * installed package by `scripts/copiar-monaco.mjs` on build and dev), not from
 * the CDN.
 *
 * The @monaco-editor/loader default is jsdelivr, and the blocking CSP
 * (next.config.ts) only accepts scripts from the origin: the AMD loader would be
 * refused and the editor would stay on the skeleton forever. The workers come
 * from the same folder — Monaco starts them through a `blob:` that does
 * `importScripts` of this URL, covered by `worker-src blob:` and
 * `script-src 'self'`. As a bonus, the editor no longer depends on allowed
 * egress and runs the version that is in package-lock.
 *
 * Here, at module scope: it applies before the first `<Editor>` mounts, which
 * is when the loader resolves the paths.
 */
loader.config({ paths: { vs: "/monaco/vs" } })

const BASE_OPTIONS: Monaco.editor.IStandaloneEditorConstructionOptions = {
  fontSize: 12,
  fontFamily: "'Fira Code', 'Consolas', 'Menlo', monospace",
  minimap: { enabled: false },
  lineNumbers: "on",
  scrollBeyondLastLine: false,
  wordWrap: "on",
  tabSize: 4,
  insertSpaces: true,
  automaticLayout: true,
  padding: { top: 8, bottom: 8 },
  scrollbar: { vertical: "auto", horizontal: "hidden" },
  overviewRulerLanes: 0,
  renderLineHighlight: "line",
  smoothScrolling: true,
  cursorBlinking: "smooth",
  fixedOverflowWidgets: true,
}

/**
 * Embedded Monokai theme, ported from monaco-themes (MIT, © Brijesh Bittu; the
 * license is in LICENSE.monaco-themes.txt, in this folder).
 *
 * It used to be a module-scope `fetch` to cdn.jsdelivr.net that fired the
 * instant the chunk was evaluated and stored the result in a global. That made
 * the editor depend on allowed egress — on a corporate network it stayed on the
 * skeleton and then silently fell back to vs-dark — and it also pointed to a
 * different package version than the installed one. It is 3 KB: embedding costs
 * less than any way of fetching it.
 */
const MONOKAI: Monaco.editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { background: "272822", token: "" },
    { foreground: "75715e", token: "comment" },
    { foreground: "e6db74", token: "string" },
    { foreground: "ae81ff", token: "constant.numeric" },
    { foreground: "ae81ff", token: "constant.language" },
    { foreground: "ae81ff", token: "constant.character" },
    { foreground: "ae81ff", token: "constant.other" },
    { foreground: "f92672", token: "keyword" },
    { foreground: "f92672", token: "storage" },
    { foreground: "66d9ef", fontStyle: "italic", token: "storage.type" },
    { foreground: "a6e22e", fontStyle: "underline", token: "entity.name.class" },
    { foreground: "a6e22e", fontStyle: "italic underline", token: "entity.other.inherited-class" },
    { foreground: "a6e22e", token: "entity.name.function" },
    { foreground: "fd971f", fontStyle: "italic", token: "variable.parameter" },
    { foreground: "f92672", token: "entity.name.tag" },
    { foreground: "a6e22e", token: "entity.other.attribute-name" },
    { foreground: "66d9ef", token: "support.function" },
    { foreground: "66d9ef", token: "support.constant" },
    { foreground: "66d9ef", fontStyle: "italic", token: "support.type" },
    { foreground: "66d9ef", fontStyle: "italic", token: "support.class" },
    { foreground: "f8f8f0", background: "f92672", token: "invalid" },
    { foreground: "f8f8f0", background: "ae81ff", token: "invalid.deprecated" },
    { foreground: "cfcfc2", token: "meta.structure.dictionary.json string.quoted.double.json" },
    { foreground: "75715e", token: "meta.diff" },
    { foreground: "75715e", token: "meta.diff.header" },
    { foreground: "f92672", token: "markup.deleted" },
    { foreground: "a6e22e", token: "markup.inserted" },
    { foreground: "e6db74", token: "markup.changed" },
    { foreground: "ae81ffa0", token: "constant.numeric.line-number.find-in-files - match" },
    { foreground: "e6db74", token: "entity.name.filename.find-in-files" },
  ],
  colors: {
    "editor.foreground": "#F8F8F2",
    "editor.background": "#272822",
    "editor.selectionBackground": "#49483E",
    "editor.lineHighlightBackground": "#3E3D32",
    "editorCursor.foreground": "#F8F8F0",
    "editorWhitespace.foreground": "#3B3A32",
    "editorIndentGuide.activeBackground": "#9D550FB0",
    "editor.selectionHighlightBorder": "#222218",
  },
}

function EditorSkeleton({ height }: { height: number }) {
  return (
    <div
      className="w-full animate-pulse rounded-md bg-[#272822]"
      style={{ height }}
    />
  )
}

function applyMonokaiTheme(monaco: typeof Monaco) {
  monaco.editor.defineTheme("monokai", MONOKAI)
  monaco.editor.setTheme("monokai")
}

function exposeInsert(
  editor: Monaco.editor.IStandaloneCodeEditor,
  onEditorReady?: (fn: (text: string) => void) => void,
) {
  onEditorReady?.((text: string) => {
    const selection = editor.getSelection()
    if (!selection) return
    editor.executeEdits("insert-hint", [{ range: selection, text, forceMoveMarkers: true }])
    editor.focus()
  })
}

// ─── Editor inline ─────────────────────────────────────────────────────────

function InlineEditor({ value, onChange, onEditorReady, minHeight = 180, language = "python", onExpand }: MonacoCodeEditorProps & { onExpand(): void }) {
  // Height in px managed as state — Monaco needs an explicit value
  const [height, setHeight] = useState(minHeight)
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)

  const handleMount: OnMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    applyMonokaiTheme(monaco)
    exposeInsert(editor, onEditorReady)

    const updateHeight = () => {
      const lineCount = editor.getModel()?.getLineCount() ?? 1
      const lineHeight = editor.getOption(monaco.editor.EditorOption.lineHeight)
      const next = Math.max(minHeight, lineCount * lineHeight + 24)
      setHeight(next)
    }
    editor.onDidChangeModelContent(updateHeight)
    updateHeight()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleDrop(e: React.DragEvent) {
    const text = e.dataTransfer.getData("text/plain")
    if (!text || !editorRef.current) return
    e.preventDefault()
    e.stopPropagation()
    const editor = editorRef.current
    const target = editor.getTargetAtClientPoint(e.clientX, e.clientY)
    const pos = target?.position ?? editor.getPosition()
    if (!pos) return
    editor.executeEdits("drag-drop", [{
      range: { startLineNumber: pos.lineNumber, startColumn: pos.column, endLineNumber: pos.lineNumber, endColumn: pos.column },
      text,
      forceMoveMarkers: true,
    }])
    editor.setPosition({ lineNumber: pos.lineNumber, column: pos.column + text.length })
    editor.focus()
  }

  return (
    <div
      className="relative rounded-md border overflow-hidden group"
      onKeyDown={(e) => e.stopPropagation()}
      onKeyUp={(e) => e.stopPropagation()}
      onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
      onDrop={handleDrop}
    >
      {/* Expand button — appears on hover */}
      <button
        type="button"
        title="Expandir editor"
        onClick={onExpand}
        className="
          absolute top-2 right-2 z-10
          flex items-center gap-1 px-1.5 py-0.5 rounded text-xs
          bg-black/40 text-white/70
          opacity-0 coarse:opacity-100 group-hover:opacity-100
          hover:bg-black/60 hover:text-white
          transition-all duration-150
        "
      >
        <TbArrowsMaximize className="w-3.5 h-3.5" />
        <span>Expandir</span>
      </button>

      <Editor
        height={height}
        defaultLanguage={language}
        theme="vs-dark"
        value={value}
        onChange={(v) => onChange(v ?? "")}
        onMount={handleMount}
        options={BASE_OPTIONS}
        loading={<EditorSkeleton height={height} />}
      />
    </div>
  )
}

// ─── Editor fullscreen ──────────────────────────────────────────────────────

function FullscreenEditor({ value, onChange, label, language = "python", open, onClose }: {
  value: string
  onChange(value: string): void
  label?: string
  language?: string
  open: boolean
  onClose(): void
}) {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)

  const handleMount: OnMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    applyMonokaiTheme(monaco)
  }, [])

  function handleDrop(e: React.DragEvent) {
    const text = e.dataTransfer.getData("text/plain")
    if (!text || !editorRef.current) return
    e.preventDefault()
    e.stopPropagation()
    const editor = editorRef.current
    const target = editor.getTargetAtClientPoint(e.clientX, e.clientY)
    const pos = target?.position ?? editor.getPosition()
    if (!pos) return
    editor.executeEdits("drag-drop", [{
      range: { startLineNumber: pos.lineNumber, startColumn: pos.column, endLineNumber: pos.lineNumber, endColumn: pos.column },
      text,
      forceMoveMarkers: true,
    }])
    editor.setPosition({ lineNumber: pos.lineNumber, column: pos.column + text.length })
    editor.focus()
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent
        className="!max-w-[95vw] w-[95vw] h-[90vh] flex flex-col gap-0 p-0 overflow-hidden !z-[80]"
        showCloseButton={false}
        onKeyDown={(e) => e.stopPropagation()}
        onKeyUp={(e) => e.stopPropagation()}
      >
        {/* Monokai-style title bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-[#272822] shrink-0">
          <DialogTitle className="text-sm font-mono text-white/80">
            {label ?? "Código"}
            <span className="ml-2 text-xs text-white/40 font-normal">{language === "sql" ? "SQL" : "Python"}</span>
          </DialogTitle>
          <button
            type="button"
            onClick={onClose}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs text-white/60 hover:text-white hover:bg-white/10 transition-colors"
          >
            <TbArrowsMinimize className="w-4 h-4" />
            <span>Fechar</span>
          </button>
        </div>

        <div
          className="flex-1 overflow-hidden"
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
          onDrop={handleDrop}
        >
          <Editor
            height="100%"
            defaultLanguage={language}
            theme="vs-dark"
            value={value}
            onChange={(v) => onChange(v ?? "")}
            onMount={handleMount}
            options={{
              ...BASE_OPTIONS,
              fontSize: 13,
              minimap: { enabled: true },
              scrollBeyondLastLine: true,
            }}
            loading={<div className="w-full h-full animate-pulse bg-[#272822]" />}
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ─── Export ─────────────────────────────────────────────────────────────────

export default function MonacoCodeEditor(props: MonacoCodeEditorProps) {
  const [expanded, setExpanded] = useState(false)
  return (
    <>
      <InlineEditor {...props} onExpand={() => setExpanded(true)} />
      <FullscreenEditor
        value={props.value}
        onChange={props.onChange}
        label={props.label}
        language={props.language}
        open={expanded}
        onClose={() => setExpanded(false)}
      />
    </>
  )
}
