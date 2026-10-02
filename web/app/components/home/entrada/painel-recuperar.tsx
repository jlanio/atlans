"use client"

// "Esqueceu a senha?", dentro do modal: o que a página /forgot-password fazia,
// sem sair da Home. Pede o e-mail, dispara o link de redefinição e mostra o
// aviso de "olhe a caixa de entrada" no mesmo lugar — o painel troca, o modal
// não fecha, e a mensagem que ficou na barra continua esperando.

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
  /** "Lembrou a senha? Entrar" — troca para o painel de login. */
  onEntrar: () => void
  /** O pedido saiu: o modal troca a descrição do cabeçalho. */
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
      // O sucesso é mostrado mesmo no erro, DE PROPÓSITO: dizer "este e-mail
      // não existe" entrega quem tem conta aqui (enumeração). O backend já
      // responde igual nos dois casos; a interface não pode desmentir isso.
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
