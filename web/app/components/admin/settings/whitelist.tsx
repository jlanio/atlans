"use client"

// Seção «Webhook Whitelist» das Configurações do admin.

import { useState } from "react"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { TbPlus } from "react-icons/tb"

// ── Webhook Whitelist ──────────────────────────────────────────────────────────

export function WhitelistSection({
  domains: initialDomains, onSave,
}: { domains: string[]; onSave: (d: string[]) => Promise<void> }) {
  const [domains, setDomains] = useState(initialDomains)
  const [newDomain, setNewDomain] = useState("")
  const [saving, setSaving] = useState(false)

  function add() {
    const d = newDomain.trim().toLowerCase()
    if (!d || domains.includes(d)) return
    setDomains(prev => [...prev, d])
    setNewDomain("")
  }

  function remove(d: string) {
    setDomains(prev => prev.filter(x => x !== d))
  }

  async function save() {
    setSaving(true)
    await onSave(domains)
    setSaving(false)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <Input
          placeholder="exemplo.com"
          value={newDomain}
          onChange={e => setNewDomain(e.target.value)}
          onKeyDown={e => e.key === "Enter" && add()}
          className="max-w-xs max-md:h-10"
        />
        <Button variant="outline" size="icon" onClick={add} className="max-md:size-10" aria-label="Adicionar domínio"><TbPlus size={14} /></Button>
      </div>
      {domains.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {domains.map(d => (
            <Badge key={d} variant="secondary" className="gap-1.5 text-xs">
              {d}
              <button onClick={() => remove(d)} className="transition-colors hover:text-destructive" aria-label={`Remover ${d}`}>×</button>
            </Badge>
          ))}
        </div>
      ) : (
        // Não é vazio "de primeiro uso": lista vazia é uma configuração VÁLIDA
        // (não restringe o destino), então explica o efeito em vez de ilustrar
        // com ícone-em-círculo, que sugeriria "falta cadastrar".
        <p className="text-xs text-muted-foreground">
          Nenhum domínio configurado — o webhook pode ser enviado a qualquer destino.
        </p>
      )}
      <div>
        <Button onClick={save} disabled={saving} size="sm" className="max-md:h-10">
          {saving ? "Salvando…" : "Salvar whitelist"}
        </Button>
      </div>
    </div>
  )
}
