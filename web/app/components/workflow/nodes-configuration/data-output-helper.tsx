"use client"
import { LuFileOutput } from "react-icons/lu"

interface Props {
  label?: string
}

// A aba mostrava também o endpoint e um snippet (cURL/Python/JS) para baixar o
// artefato por `GET /artifacts/runs/<task_id>/<arquivo>`. A rota não era
// publicada em produção e devolvia um JSON com a URL, não o arquivo — o
// snippet não funcionava. Saiu junto com a rota; fica o que continua valendo.
export default function DataOutputHelper({ label }: Props) {
  return (
    <div className="flex flex-col gap-3 px-3 mt-3 pb-4">
        {/* Título */}
        <div className="flex items-center gap-1.5">
          <LuFileOutput className="h-3.5 w-3.5 text-muted-foreground" />
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Arquivo gerado
          </p>
        </div>

        {/* Aviso sobre label */}
        {!label?.trim() && (
          <div className="flex items-start gap-2 bg-amber-500/8 border border-amber-500/20 rounded-md px-2.5 py-2">
            <span className="text-amber-500 text-[10px] font-bold mt-0.5 shrink-0">⚠</span>
            <p className="text-[11px] text-foreground/70 leading-relaxed">
              Defina o campo <span className="font-mono bg-muted px-1 rounded text-foreground/90">label</span> para
              determinar o nome do arquivo gerado.
            </p>
          </div>
        )}

        {/* Info sobre formato */}
        <div className="flex items-start gap-2 bg-muted/60 border border-border rounded-md px-2.5 py-2">
          <p className="text-[11px] text-foreground/70 leading-relaxed">
            O formato é determinado automaticamente:{" "}
            <span className="font-mono bg-muted px-1 rounded text-foreground/90">.geojson</span> para GeoDataFrame,{" "}
            <span className="font-mono bg-muted px-1 rounded text-foreground/90">.json</span> para dict/list.
            Depois de cada execução, o arquivo fica em Artefatos — ou no Drive, se esse for o destino.
          </p>
        </div>
    </div>
  )
}
