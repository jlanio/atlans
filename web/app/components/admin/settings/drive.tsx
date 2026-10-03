"use client"

// "Drive — Upload de Arquivos" (file upload) section of the admin Settings.

import { useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useFetchData } from "@/app/hooks/useFetchData"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { TbPackage, TbPlus, TbTrash } from "react-icons/tb"
import { createToast } from "@/utils/createToast"
import { AvisoDeSecao, CartaoDeErro, FormSkeleton, VazioEmCirculo } from "./estados"

// ── Drive: global upload settings ────────────────────────────────────────────

// `token` is no longer a prop: the GisFlowService interceptor attaches the JWT.
export function DriveSettingsSection() {
  const [maxMb,    setMaxMb]    = useState("")
  const [savingMb, setSavingMb] = useState(false)
  const [newExt,   setNewExt]   = useState("")
  const [addingExt, setAddingExt] = useState(false)

  const {
    data: settings, firstLoad: settingsFirst, error: settingsError, refetch: refetchSettings,
  } = useFetchData(
    async () => {
      const res = await GisFlowService.getAdminDriveSettings()
      if (res.error) return { error: { message: "Erro ao carregar configurações do Drive." } }
      return { data: res.data }
    },
    "Erro ao carregar configurações do Drive.",
  )

  const {
    data: extensions, firstLoad: extFirst, error: extError, refetch: refetchExt,
  } = useFetchData(
    async () => {
      const res = await GisFlowService.getAdminDriveExtensions()
      if (res.error) return { error: { message: "Erro ao carregar extensões." } }
      return { data: res.data }
    },
    "Erro ao carregar extensões.",
  )

  async function saveMaxMb() {
    const val = parseInt(maxMb)
    if (isNaN(val) || val < 1) { createToast.error("Informe um valor em MB maior que 0."); return }
    setSavingMb(true)
    const res = await GisFlowService.updateAdminDriveSettings(val)
    if (res.error) {
      createToast.error("Erro ao salvar.")
    } else {
      createToast.success("Tamanho máximo atualizado.")
      refetchSettings()
      setMaxMb("")
    }
    setSavingMb(false)
  }

  async function addExtension() {
    const ext = newExt.trim().toLowerCase().replace(/^\./, "")
    if (!ext) return
    setAddingExt(true)
    const res = await GisFlowService.addAdminDriveExtension(ext)
    if (res.error) {
      // The backend's `detail` explains WHY the extension was refused
      // (duplicated, invalid format); `resolveAxiosError` already puts it here.
      createToast.error(res.error.message ?? "Erro ao adicionar.")
    } else {
      createToast.success(`Extensão .${ext} adicionada.`)
      refetchExt()
      setNewExt("")
    }
    setAddingExt(false)
  }

  async function removeExtension(ext: string) {
    const res = await GisFlowService.removeAdminDriveExtension(ext)
    if (res.error) {
      createToast.error("Erro ao remover extensão.")
    } else {
      createToast.success(`Extensão .${ext} removida.`)
      refetchExt()
    }
  }

  // 1st load: body skeleton. The error only takes over the section when NOTHING
  // loaded — either of the two reads is enough to show the form. Before, the
  // `error` was ignored and the section stayed blank.
  if (settingsFirst || extFirst) return <FormSkeleton rotulo="Carregando as configurações do Drive" />
  if (settingsError && !settings && extError && !extensions) {
    return <CartaoDeErro mensagem={settingsError} onTentar={() => { refetchSettings(); refetchExt() }} />
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Maximum size */}
      <div className="flex flex-col gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Tamanho máximo de arquivo
        </p>
        {settingsError && settings ? (
          <AvisoDeSecao onTentar={refetchSettings}>Não foi possível recarregar o tamanho máximo.</AvisoDeSecao>
        ) : (
          <p className="text-sm">
            Atual: <span className="font-semibold tabular-nums">{settings?.max_size_mb ?? "—"} MB</span>
          </p>
        )}
        <div className="flex items-center gap-2">
          <Input
            type="number"
            min={1}
            placeholder="Ex: 200"
            value={maxMb}
            onChange={e => setMaxMb(e.target.value)}
            className="max-w-[120px] max-md:h-10"
            onKeyDown={e => e.key === "Enter" && saveMaxMb()}
          />
          <span className="text-sm text-muted-foreground">MB</span>
          <Button size="sm" onClick={saveMaxMb} disabled={savingMb} className="max-md:h-10">
            {savingMb ? "Salvando…" : "Salvar"}
          </Button>
        </div>
      </div>

      {/* Allowed extensions */}
      <div className="flex flex-col gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Extensões permitidas
        </p>
        <div className="flex gap-2">
          <Input
            placeholder=".geojson"
            value={newExt}
            onChange={e => setNewExt(e.target.value)}
            onKeyDown={e => e.key === "Enter" && addExtension()}
            className="max-w-[160px] font-mono text-sm max-md:h-10"
          />
          <Button variant="outline" size="icon" onClick={addExtension} disabled={addingExt} className="max-md:size-10" aria-label="Adicionar extensão">
            <TbPlus size={14} />
          </Button>
        </div>
        {extError && !extensions ? (
          <AvisoDeSecao onTentar={refetchExt}>Não foi possível carregar as extensões.</AvisoDeSecao>
        ) : extensions && extensions.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {extensions.map(({ extension }) => (
              <Badge key={extension} variant="secondary" className="gap-1.5 font-mono text-xs">
                .{extension}
                <button
                  onClick={() => removeExtension(extension)}
                  className="transition-colors hover:text-destructive"
                  aria-label={`Remover .${extension}`}
                >
                  <TbTrash size={10} />
                </button>
              </Badge>
            ))}
          </div>
        ) : (
          <VazioEmCirculo icone={TbPackage} titulo="Nenhuma extensão cadastrada" descricao="Adicione as extensões que a plataforma deve aceitar no Drive." />
        )}
      </div>
    </div>
  )
}
