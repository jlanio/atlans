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
  // The workflow being edited: it is through it (and not through a workspace
  // chosen here) that the server reaches the credentials shared with the
  // workflow's workspace.
  workflowId?: string
}

/**
 * Extracts the base endpoint of an OWS URL (WFS/WMS/WMTS), dropping query and
 * fragment. Mirrors flow/utils/geo_helpers.normalize_ows_endpoint_url in the
 * backend — an idempotent operation, safe to always apply.
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
  // The credential the list was fetched with. Once the node's credential changes,
  // the list no longer holds: a GeoServer shows different layers for each key
  // (and to anonymous users).
  const [listedWith, setListedWith] = useState("")

  const url = String(values?.url ?? "").trim()
  const credentialId = String(values?.credential_id ?? "")
  const listIsValid = discovered && layers.length > 0 && listedWith === credentialId

  const discoverLayers = useCallback(async () => {
    if (!url) {
      setError("Informe a URL do serviço WFS primeiro.")
      return
    }

    // Normalizes before the fetch and persists it in the node right away (in case
    // the user clicked without triggering the input's onBlur).
    const normalized = normalizeOwsEndpoint(url)
    if (normalized !== url) {
      setNodeField("url", normalized)
    }

    setLoading(true)
    setError(null)
    setLayers([])
    // The fetch uses the current credential: if it fails, the "credential
    // changed" warning has nothing left to ask for — only the error remains.
    setListedWith(credentialId)

    try {
      // With the node's credential, the list is the one the run will see — protected
      // layers included. The workflow reaches the ones shared with its workspace.
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
      // The API error body is `{message}`; `detail` is kept for older responses.
      const fromServer = axios.isAxiosError(err)
        ? (err.response?.data?.message ?? err.response?.data?.detail)
        : undefined
      if (typeof fromServer === "string" && fromServer) {
        setError(fromServer)
      } else {
        const msg = err instanceof Error ? err.message : String(err)
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [url, credentialId, workflowId, setNodeField])

  const currentTypeName = String(values?.typeName ?? "")
  // The saved layer is outside the list (fetched with another key, or no key):
  // without an item with this value the Select would fall back to the
  // placeholder and look empty.
  const savedOutsideList = !!currentTypeName && !layers.some(l => l.name === currentTypeName)

  return (
    <div className="flex flex-col gap-2">
      {/* WFS URL */}
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

      {/* Layer: dropdown if discovered, manual input otherwise */}
      <div className="flex flex-col gap-1">
        <Label>Camada (typeName)</Label>
        {listIsValid ? (
          <Select
            value={currentTypeName || "__none__"}
            onValueChange={v => setNodeField("typeName", v === "__none__" ? "" : v)}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="Selecione uma camada" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__" disabled>Selecione uma camada</SelectItem>
              {savedOutsideList && (
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
        {listIsValid && (
          <p className="text-[10px] text-muted-foreground">
            {layers.length} camada(s) encontrada(s){listedWith ? " com a credencial do nó" : ""}
          </p>
        )}
        {discovered && !listIsValid && listedWith !== credentialId && (
          <p className="text-[10px] text-muted-foreground">
            A credencial do nó mudou — busque as camadas de novo para ver as que ela alcança.
          </p>
        )}
      </div>
    </div>
  )
}

export default WFSHelper
