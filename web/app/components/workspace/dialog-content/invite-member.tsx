"use client"

import { useEffect, useId, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { TbCheck, TbLoader2, TbX } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select"
import { GisFlowService } from "@/service/GisFlowService"
import type { IUserSearchResult, IWorkspaceMember } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { ROLE_DESCRIPTIONS, ROLE_LABELS, ROLE_OPTIONS } from "../role-labels"

// A busca resolve pelo e-mail EXATO (o backend não faz mais busca por parte do
// e-mail — evita coletar a base inteira, auditoria SEG-06). Só dispara quando o
// texto parece um e-mail completo.
const _RE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
function pareceEmail(v: string): boolean {
  return _RE_EMAIL.test(v)
}

interface Props {
  workspaceId: string
  onClose: () => void
  onInvited: (member: IWorkspaceMember) => void
}

export function InviteMemberDialog({ workspaceId, onClose, onInvited }: Props) {
  const emailId = useId()
  const roleId = useId()

  const [email, setEmail] = useState("")
  const [role, setRole] = useState<string>("editor")
  const [results, setResults] = useState<IUserSearchResult[]>([])
  const [selected, setSelected] = useState<IUserSearchResult | null>(null)
  // Três estados em vez de um booleano: sem o "idle", a tela dizia "Nenhum
  // usuário encontrado" assim que o terceiro caractere era digitado — antes de
  // qualquer busca ter acontecido.
  const [status, setStatus] = useState<"idle" | "searching" | "done">("idle")
  const [inviting, setInviting] = useState(false)

  const termo = email.trim()

  useEffect(() => {
    if (selected) return
    if (!pareceEmail(termo)) {
      setResults([])
      setStatus("idle")
      return
    }

    setStatus("searching")
    let cancelado = false
    // Debounce: a busca era manual, atrás de um botão. Digitar e não perceber
    // que ainda faltava clicar em "Buscar" fazia a tela parecer quebrada.
    const timer = setTimeout(async () => {
      const res = await GisFlowService.searchUsersByEmail(termo)
      if (cancelado) return
      if (res.error) {
        createToast.error(res.error.message ?? "Erro ao buscar usuários.")
        setResults([])
      } else {
        setResults(res.data ?? [])
      }
      setStatus("done")
    }, 400)

    return () => { cancelado = true; clearTimeout(timer) }
  }, [termo, selected])

  async function handleInvite() {
    if (!selected || inviting) return
    setInviting(true)
    const res = await GisFlowService.inviteWorkspaceMember(workspaceId, selected.email, role)
    setInviting(false)
    if (res.error || !res.data) {
      createToast.error(res.error?.message ?? "Erro ao convidar membro.")
      return
    }
    createToast.success(`${selected.username} adicionado como ${ROLE_LABELS[role]}.`)
    onInvited(res.data)
  }

  return (
    <Dialog open onOpenChange={o => { if (!o && !inviting) onClose() }}>
      <DialogContent
        bloqueado={inviting}
      >
        <DialogHeader>
          <DialogTitle>Adicionar membro</DialogTitle>
          <DialogDescription>
            Digite o e-mail completo de quem já tem conta na plataforma.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-1">
          <div className="grid gap-1.5">
            <Label htmlFor={emailId}>E-mail</Label>
            <div className="relative">
              <Input
                id={emailId}
                placeholder="usuario@email.com"
                value={email}
                disabled={inviting}
                onChange={e => { setEmail(e.target.value); setSelected(null) }}
              />
              {status === "searching" && (
                <TbLoader2
                  className="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground"
                  aria-hidden="true"
                />
              )}
            </div>
            {termo.length > 0 && !pareceEmail(termo) && !selected && (
              <p className="text-xs text-muted-foreground">
                Digite o e-mail completo do usuário.
              </p>
            )}
          </div>

          <AnimatePresence>
            {results.length > 0 && !selected && (
              // Anima só opacity/y: animar `height` de 0 a auto forçava reflow a
              // cada frame. A altura agora fica no fluxo natural do layout.
              <motion.div
                className="divide-y overflow-hidden rounded-md border"
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
              >
                {results.map(u => (
                  <button
                    key={u.id_hash}
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-accent"
                    onClick={() => { setSelected(u); setResults([]) }}
                  >
                    <span className="font-medium">{u.username}</span>
                    <span className="truncate text-xs text-muted-foreground">{u.email}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {status === "done" && results.length === 0 && !selected && (
            <p className="text-xs text-muted-foreground">
              Nenhum usuário encontrado. Só é possível adicionar quem já tem conta.
            </p>
          )}

          <AnimatePresence>
            {selected && (
              <motion.div
                className="flex items-center gap-2 rounded-md bg-accent px-3 py-2 text-sm"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
              >
                <TbCheck className="size-4 shrink-0 text-green-500" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <span className="font-medium">{selected.username}</span>
                  <span className="ml-1.5 truncate text-xs text-muted-foreground">{selected.email}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  disabled={inviting}
                  aria-label="Limpar seleção"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <TbX className="size-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="grid gap-1.5">
            <Label htmlFor={roleId}>Papel</Label>
            <Select value={role} onValueChange={setRole} disabled={inviting}>
              <SelectTrigger id={roleId} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLE_OPTIONS.map(r => (
                  <SelectItem key={r} value={r}>
                    <span className="flex flex-col items-start">
                      <span>{ROLE_LABELS[r]}</span>
                      <span className="text-xs text-muted-foreground">{ROLE_DESCRIPTIONS[r]}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={inviting}>Cancelar</Button>
          <Button onClick={handleInvite} disabled={!selected || inviting} className="gap-1.5">
            {inviting && <TbLoader2 className="size-4 animate-spin" aria-hidden="true" />}
            {inviting ? "Adicionando…" : "Adicionar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
