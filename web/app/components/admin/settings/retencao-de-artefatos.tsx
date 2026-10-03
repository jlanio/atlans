"use client"

// "Retenção de Artefatos" (artifact retention) section of the admin Settings.

import { useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { createToast } from "@/utils/createToast"

// ── Artifact retention ────────────────────────────────────────────────────────

export function ArtifactRetentionSection({
  initialDays,
}: { initialDays: number | null }) {
  const [days, setDays] = useState<string>(initialDays != null ? String(initialDays) : "")
  const [saving, setSaving] = useState(false)

  async function save() {
    const parsed = days.trim() === "" ? null : parseInt(days)
    if (parsed !== null && (isNaN(parsed) || parsed < 1)) {
      createToast.error("Informe um número inteiro maior ou igual a 1, ou deixe vazio para sem expiração.")
      return
    }
    setSaving(true)
    const res = await GisFlowService.updateArtifactSettings(parsed)
    setSaving(false)
    if (res?.error) createToast.error(res.error.message ?? "Erro ao salvar")
    else createToast.success("Configuração salva.")
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Input
          type="number"
          min={1}
          placeholder="Ex: 30"
          value={days}
          onChange={e => setDays(e.target.value)}
          className="max-w-[120px] max-md:h-10"
        />
        <span className="text-sm text-muted-foreground">dias</span>
      </div>
      <p className="text-xs text-muted-foreground">
        Deixe em branco para manter artefatos indefinidamente.
        Artefatos com prazo expirado são removidos automaticamente pelo scheduler.
      </p>
      <div>
        <Button onClick={save} disabled={saving} size="sm" className="max-md:h-10">
          {saving ? "Salvando…" : "Salvar"}
        </Button>
      </div>
    </div>
  )
}
