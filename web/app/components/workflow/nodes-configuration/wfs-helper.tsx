"use client"

import { useState, useCallback } from "react"
import { Label } from "@/app/components/ui/label"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"
import { TbRefresh, TbWorldSearch } from "react-icons/tb"
import axios from "axios"
import { API_URL } from "@/utils/env"

interface WFSLayer {
  name: string
  title: string
}

interface WFSHelperProps {
  values: Record<string, string | number | boolean> | undefined
  setNodeField(field: string, value: string | number | boolean): void
  // O fluxo em edição: é por ele (e não por um workspace escolhido aqui) que o
  // servidor alcança as credenciais compartilhadas com o workspace do fluxo.
  workflowId?: string
}

/**
 * Extrai o endpoint base de uma URL OWS (WFS/WMS/WMTS), descartando query e
 * fragment. Espelha flow/utils/geo_helpers.normalize_ows_endpoint_url no
 * backend — operacao idempotente, segura aplicar sempre.
 */
function normalizeOwsEndpoint(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return ""
  try {
    const u = new URL(trimmed)
    if (u.protocol !== "http:" && u.protocol !== "https:") return trimmed
    const path = u.pathname.replace(/\/+$/, "")
    return `${u.protocol}//${u.host}${path}`
  } catch {
    // URL invalida — devolve original para o usuario corrigir
    return trimmed
  }
}

const WFSHelper = ({ values, setNodeField, workflowId }: WFSHelperProps) => {
  const [layers, setLayers] = useState<WFSLayer[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [discovered, setDiscovered] = useState(false)
  // A credencial com que a lista foi buscada. Trocada a do nó, a lista deixa de
  // valer: um GeoServer mostra camadas diferentes a cada chave (e ao anônimo).
  const [listadaCom, setListadaCom] = useState("")

  const url = String(values?.url ?? "").trim()
  const credentialId = String(values?.credential_id ?? "")
  const listaValida = discovered && layers.length > 0 && listadaCom === credentialId

  const discoverLayers = useCallback(async () => {
    if (!url) {
      setError("Informe a URL do serviço WFS primeiro.")
      return
    }

    // Normaliza antes do fetch e ja persiste no node (caso usuario clicou
    // sem disparar onBlur do input).
    const normalized = normalizeOwsEndpoint(url)
    if (normalized !== url) {
      setNodeField("url", normalized)
    }

    setLoading(true)
    setError(null)
    setLayers([])
    // A busca é com a credencial de agora: se ela falhar, o aviso de "a
    // credencial mudou" não tem mais o que pedir — fica só o erro.
    setListadaCom(credentialId)

    try {
      // Com a credencial do nó, a lista é a que a execução vai ver — as camadas
      // protegidas incluídas. O fluxo alcança as compartilhadas com o workspace dele.
      const params: Record<string, string> = { url: normalized }
      if (credentialId) params.credential_id = credentialId
      if (credentialId && workflowId) params.workflow_id = workflowId
      const res = await axios.get<{ layers: WFSLayer[] }>(
        `${API_URL}/nodes/wfs/layers`,
        { params }
      )
      const parsed = res.data.layers ?? []
      if (parsed.length === 0) {
        throw new Error("Nenhuma camada encontrada no servidor WFS.")
      }
      setLayers(parsed)
      setDiscovered(true)
    } catch (err) {
      // O corpo de erro da API é `{message}`; `detail` fica para respostas antigas.
      const doServidor = axios.isAxiosError(err)
        ? (err.response?.data?.message ?? err.response?.data?.detail)
        : undefined
      if (typeof doServidor === "string" && doServidor) {
        setError(doServidor)
      } else {
        const msg = err instanceof Error ? err.message : String(err)
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [url, credentialId, workflowId, setNodeField])

  const currentTypeName = String(values?.typeName ?? "")
  // A camada gravada fora da lista (buscada com outra chave, ou sem chave): sem
  // um item com este valor o Select cairia no placeholder e pareceria vazio.
  const gravadaForaDaLista = !!currentTypeName && !layers.some(l => l.name === currentTypeName)

  return (
    <div className="flex flex-col gap-2">
      {/* URL do WFS */}
      <div className="flex flex-col gap-1">
        <Label>URL do serviço WFS</Label>
        <div className="flex gap-1">
          <Input
            value={url}
            onChange={e => setNodeField("url", e.target.value)}
            onBlur={e => {
              const normalized = normalizeOwsEndpoint(e.target.value)
              if (normalized !== e.target.value) {
                setNodeField("url", normalized)
              }
            }}
            onPaste={e => {
              const pasted = e.clipboardData.getData("text")
              const normalized = normalizeOwsEndpoint(pasted)
              if (normalized !== pasted) {
                e.preventDefault()
                setNodeField("url", normalized)
              }
            }}
            placeholder="https://exemplo.com/geoserver/ows"
            className="flex-1 h-8 text-sm"
          />
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={discoverLayers}
            disabled={loading || !url}
            title="Buscar camadas disponíveis"
          >
            {loading
              ? <TbRefresh className="h-3.5 w-3.5 animate-spin" />
              : <TbWorldSearch className="h-3.5 w-3.5" />
            }
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground italic">
          Cole a URL completa do GetCapabilities — query string e fragment são descartados automaticamente.
        </p>
      </div>

      {/* Erro */}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {/* Camada: dropdown se descobriu, input manual caso contrário */}
      <div className="flex flex-col gap-1">
        <Label>Camada (typeName)</Label>
        {listaValida ? (
          <Select
            value={currentTypeName || "__none__"}
            onValueChange={v => setNodeField("typeName", v === "__none__" ? "" : v)}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="Selecione uma camada" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__" disabled>Selecione uma camada</SelectItem>
              {gravadaForaDaLista && (
                <SelectItem value={currentTypeName}>
                  <span className="font-mono text-xs">{currentTypeName}</span>
                  <span className="text-muted-foreground ml-1 text-xs">— não listada</span>
                </SelectItem>
              )}
              {layers.map(layer => (
                <SelectItem key={layer.name} value={layer.name}>
                  <span className="font-mono text-xs">{layer.name}</span>
                  {layer.title !== layer.name && (
                    <span className="text-muted-foreground ml-1 text-xs">— {layer.title}</span>
                  )}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Input
            value={currentTypeName}
            onChange={e => setNodeField("typeName", e.target.value)}
            placeholder="namespace:camada"
            className="h-8 text-sm font-mono"
          />
        )}
        {listaValida && (
          <p className="text-[10px] text-muted-foreground">
            {layers.length} camada(s) encontrada(s){listadaCom ? " com a credencial do nó" : ""}
          </p>
        )}
        {discovered && !listaValida && listadaCom !== credentialId && (
          <p className="text-[10px] text-muted-foreground">
            A credencial do nó mudou — busque as camadas de novo para ver as que ela alcança.
          </p>
        )}
      </div>
    </div>
  )
}

export default WFSHelper
