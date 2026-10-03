"use client"

// "Esqueceu a senha?", inside the modal: what the /forgot-password page did,
// without leaving the Home. Asks for the e-mail, sends the reset link and shows
// the "check your inbox" notice in the same place — the panel switches, the
// modal does not close, and the message left in the bar keeps waiting.

import { useState } from "react"
import axios from "axios"
import { TbMailCheck } from "react-icons/tb"

import { API_URL } from "@/utils/env"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { useTextos } from "@/app/components/home/i18n"
import { BotaoDoModal, LinkDoModal } from "./botao-do-modal"

interface Props {
  onEnviando: (enviando: boolean) => void
  /** "Lembrou a senha? Entrar" — switches to the login panel. */
  onEntrar: () => void
  /** The request went out: the modal changes the header description. */
  onEnviado: (enviado: boolean) => void
}

export function PainelRecuperar({ onEnviando, onEntrar, onEnviado }: Props) {
  const t = useTextos().entrada.painelRecuperar
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [enviado, setEnviado] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    onEnviando(true)
    try {
      await axios.post(`${API_URL}/auth/forgot-password`, { email })
    } catch {
      // Success is shown even on error, ON PURPOSE: saying "this e-mail does not
      // exist" gives away who has an account here (enumeration). The backend
      // already answers the same in both cases; the interface must not contradict that.
    } finally {
      setLoading(false)
      onEnviando(false)
      setEnviado(true)
      onEnviado(true)
    }
  }

  if (enviado) {
    return (
      <>
        <div className="flex items-start gap-3 rounded-md border border-border bg-muted/40 px-3 py-2.5 text-sm text-muted-foreground">
          <TbMailCheck size={20} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
          <span>{t.avisoDoLink}</span>
        </div>
        <BotaoDoModal type="button" onClick={onEntrar}>
          {t.voltarParaEntrar}
        </BotaoDoModal>
      </>
    )
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="recuperar-email" className="auth-label text-sm">
            {t.email}
          </Label>
          <Input
            id="recuperar-email"
            type="email"
            autoComplete="email"
            required
            disabled={loading}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input h-11 text-sm"
          />
        </div>

        <BotaoDoModal loading={loading} loadingLabel={t.enviando} className="mt-1">
          {t.enviarLink}
        </BotaoDoModal>
      </form>

      <p className="text-center text-[12.5px] text-muted-foreground">
        {t.lembrouASenha} <LinkDoModal onClick={onEntrar}>{t.entrar}</LinkDoModal>
      </p>
    </>
  )
}
