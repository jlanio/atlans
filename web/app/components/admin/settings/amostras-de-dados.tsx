"use client"

// "Amostras de dados no editor" section of the admin Settings
// (docs/specs/node-data-panels.md §4.3).

import { useEffect, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { Switch } from "@/app/components/ui/switch"
import { createToast } from "@/utils/createToast"
import { FormSkeleton, CartaoDeErro } from "./estados"

export const DATA_PREVIEW_HELP_TEXT =
  "Quando ligado, execuções feitas pelo editor enviam as primeiras linhas de cada nó para os painéis Entradas e Saídas. Os dados ficam 1 hora no histórico da execução, visível a quem pode ver o workflow, e desligar aqui não apaga o que já foi enviado. Desligue onde os dados não podem sair dos executores, nem como amostra."

export function DataPreviewSection() {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)

  async function carregar() {
    setErro(null)
    const res = await GisFlowService.getDataPreviewSetting()
    if (res?.error) setErro(res.error.message ?? "Não foi possível ler a configuração.")
    else setEnabled(res?.data?.enabled ?? true)
  }

  useEffect(() => { void carregar() }, [])

  async function alternar(valor: boolean) {
    const anterior = enabled
    setEnabled(valor)
    setSalvando(true)
    const res = await GisFlowService.setDataPreviewSetting(valor)
    setSalvando(false)
    if (res?.error) {
      setEnabled(anterior)
      createToast.error(res.error.message ?? "Erro ao salvar")
      return
    }
    createToast.success(valor ? "Amostras de dados ligadas." : "Amostras de dados desligadas.")
  }

  if (erro && enabled === null) return <CartaoDeErro mensagem={erro} onTentar={carregar} />
  if (enabled === null) return <FormSkeleton rotulo="Carregando a configuração das amostras" />

  return (
    <div className="flex items-center gap-3">
      <Switch
        id="amostras-de-dados"
        checked={enabled}
        disabled={salvando}
        onCheckedChange={alternar}
        aria-describedby="amostras-de-dados-estado"
      />
      <label htmlFor="amostras-de-dados" className="text-sm">
        Enviar amostras de dados para o editor
      </label>
      <span id="amostras-de-dados-estado" className="text-xs text-muted-foreground">
        {enabled ? "ligado" : "desligado"}
      </span>
    </div>
  )
}
