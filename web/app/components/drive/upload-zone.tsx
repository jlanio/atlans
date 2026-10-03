"use client"

import { forwardRef, useImperativeHandle, useRef, useState } from "react"
import { TbCloudUpload } from "react-icons/tb"
import { cn } from "@/lib/utils"

/** Handle to open the picker from outside (the first-use state's CTA uses it). */
export interface UploadZoneHandle {
  abrirSeletor: () => void
}

/**
 * Drag-and-drop + click upload zone. The area is a keyboard-accessible
 * `role="button"` (Enter/Space open the picker) — before it was a clickable `div`
 * the keyboard couldn't reach. The drag colors moved from literal orange to the
 * tokens (`primary`/`ring`), so they follow the theme.
 */
export const UploadZone = forwardRef<UploadZoneHandle, {
  uploading: boolean
  onFiles: (files: FileList) => void
}>(function UploadZone({ uploading, onFiles }, ref) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)

  const abrir = () => { if (!uploading) inputRef.current?.click() }
  useImperativeHandle(ref, () => ({ abrirSeletor: abrir }))

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDrag(false)
    if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files)
  }

  return (
    <div
      role="button"
      tabIndex={uploading ? -1 : 0}
      aria-label="Enviar arquivos: arraste para cá ou tecle Enter para selecionar"
      aria-disabled={uploading || undefined}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      onClick={abrir}
      onKeyDown={e => {
        // Enter/Space are the keyboard contract of a role="button".
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir() }
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-8 py-10 text-center transition-colors outline-none select-none",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        drag ? "border-primary bg-primary/5" : "border-border hover:border-primary/60 hover:bg-primary/5",
        uploading && "pointer-events-none opacity-60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={e => e.target.files && onFiles(e.target.files)}
      />
      <TbCloudUpload size={36} className={drag ? "text-primary" : "text-muted-foreground"} aria-hidden="true" />
      <div>
        <p className="text-sm font-medium text-foreground">
          {uploading ? "Enviando arquivos…" : "Arraste arquivos aqui ou clique para selecionar"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          GeoJSON, Shapefile, CSV, KML, GeoPackage, XLSX, ZIP e outros
        </p>
      </div>
    </div>
  )
})
