"use client"
import { useEffect, useState } from "react"
import { TbLoader2 } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import {
  Dialog, DialogClose, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import type { IConversationSummary } from "@/service/types"
import type { WriteResult } from "@/app/hooks/home/useConversas"
import { useShellTexts } from "../i18n/da-casca"

interface RenameDialogProps {
  /** The conversation being edited; `null` keeps the dialog closed. */
  conversa: IConversationSummary | null
  onClose: () => void
  /** May be async; the dialog waits and locks while saving. The result's `erro`
   *  becomes the message in the box — a boolean alone left the dialog open and
   *  identical, and the person clicked Salvar again thinking the click had not
   *  registered. */
  onRenomear: (id: string, titulo: string) => Promise<WriteResult> | WriteResult
}

/**
 * Renames a conversation. Enter saves; an empty title is rejected (the backend
 * requires 1..120). Controlled by the presence of `conversa` — that way Radix
 * animates entry and exit, and an effect resets the field for each new conversation.
 */
export function RenameDialog({ conversa, onClose, onRenomear }: RenameDialogProps) {
  const textos = useShellTexts()
  const t = textos.listas.renomear
  const [titulo, setTitle] = useState("")
  const [salvando, setSaving] = useState(false)
  const [erro, setError] = useState<string | null>(null)

  useEffect(() => {
    if (conversa) { setTitle(conversa.titulo ?? ""); setError(null) }
  }, [conversa])

  async function salvar() {
    const limpo = titulo.trim()
    if (!limpo || salvando || !conversa) return
    setSaving(true)
    setError(null)
    try {
      const r = await onRenomear(conversa.id, limpo)
      if (r.ok) onClose()
      else setError(r.erro ?? t.falhou)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={!!conversa} onOpenChange={(v) => { if (!v && !salvando) onClose() }}>
      {/* `home-portal`: the dialog is portaled to <body>, OUTSIDE the tree that
          declares the Home palette — without the class it opens in the app's
          light palette over the near-black Home. */}
      <DialogContent closeDisabled={salvando} className="home-portal" closeLabel={textos.comum.fechar}>
        <DialogHeader>
          <DialogTitle>{t.titulo}</DialogTitle>
          <DialogDescription>{t.descricao}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-1.5">
          <Label htmlFor="titulo-conversa">{t.campo}</Label>
          <Input
            id="titulo-conversa"
            value={titulo}
            maxLength={120}
            autoFocus
            disabled={salvando}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); salvar() } }}
          />
          {erro && (
            <p role="alert" className="text-xs text-destructive">{erro}</p>
          )}
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={salvando}>{textos.comum.cancelar}</Button>
          </DialogClose>
          <Button onClick={salvar} disabled={salvando || !titulo.trim()} className="gap-1">
            {salvando && <TbLoader2 className="size-4 animate-spin" aria-hidden />}
            {salvando ? t.salvando : textos.comum.salvar}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
