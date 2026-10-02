"use client"

import { forwardRef, useImperativeHandle, useRef, useState } from "react"
import { TbCloudUpload } from "react-icons/tb"
import { cn } from "@/lib/utils"

/** Handle para abrir o seletor de fora (o CTA do estado de primeiro uso o usa). */
export interface UploadZoneHandle {
  abrirSeletor: () => void
}

/**
 * Zona de envio drag-and-drop + clique. A área é `role="button"` acessível por
 * teclado (Enter/Espaço abrem o seletor) — antes era um `div` clicável que o
 * teclado não alcançava. As cores de arraste saíram do laranja literal para os
 * tokens (`primary`/`ring`), então acompanham o tema.
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
        // Enter/Espaço são o contrato de teclado de um role="button".
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
