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
import type { IConversaResumo } from "@/service/types"
import type { ResultadoDaEscrita } from "@/app/hooks/home/useConversas"
import { useTextosDaCasca } from "../i18n/da-casca"

interface RenomearDialogProps {
  /** A conversa em edição; `null` mantém o diálogo fechado. */
  conversa: IConversaResumo | null
  onClose: () => void
  /** Pode ser async; o diálogo aguarda e trava enquanto salva. O `erro` do
   *  resultado vira a mensagem na caixa — um booleano sozinho deixava o diálogo
   *  aberto e idêntico, e a pessoa clicava Salvar de novo achando que o clique
   *  não registrara. */
  onRenomear: (id: string, titulo: string) => Promise<ResultadoDaEscrita> | ResultadoDaEscrita
}

/**
 * Renomeia uma conversa. Enter salva; título vazio é rejeitado (o backend exige
 * 1..120). Controlado pela presença de `conversa` — assim o Radix anima entrada
 * e saída, e um efeito reinicia o campo a cada conversa nova.
 */
export function RenomearDialog({ conversa, onClose, onRenomear }: RenomearDialogProps) {
  const textos = useTextosDaCasca()
  const t = textos.listas.renomear
  const [titulo, setTitulo] = useState("")
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (conversa) { setTitulo(conversa.titulo ?? ""); setErro(null) }
  }, [conversa])

  async function salvar() {
    const limpo = titulo.trim()
    if (!limpo || salvando || !conversa) return
    setSalvando(true)
    setErro(null)
    try {
      const r = await onRenomear(conversa.id, limpo)
      if (r.ok) onClose()
      else setErro(r.erro ?? t.falhou)
    } finally {
      setSalvando(false)
    }
  }

  return (
    <Dialog open={!!conversa} onOpenChange={(v) => { if (!v && !salvando) onClose() }}>
      {/* `home-portal`: o diálogo é portado para o <body>, FORA da árvore que
          declara a paleta da Home — sem a classe ele abre na paleta clara do
          app por cima da Home quase preta. */}
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
            onChange={(e) => setTitulo(e.target.value)}
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
