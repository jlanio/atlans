"use client"

// "Nova senha", inside the modal: what the /reset-password page did. The token
// comes from the e-mail link, via the Home's query (`/?redefinir=1&token=…`), and
// it is the ONLY thing this screen receives from outside — it does not know
// whose account it is, and does not need to.
//
// On success there is no navigation: the panel switches to login, already with
// the notice that the password was changed. If the person got here via the bar
// (with a pending message), it keeps waiting for the login.

import { useState } from "react"
import axios from "axios"

import { API_URL } from "@/utils/env"
import { AuthError } from "@/app/components/auth/AuthError"
import { AuthPasswordField } from "@/app/components/auth/AuthPasswordField"
import { AuthPasswordStrength } from "@/app/components/auth/AuthPasswordStrength"
import { useScreenLanguage, useTexts } from "@/app/components/home/i18n"
import { ModalButton, LinkDoModal } from "./botao-do-modal"
import { linkRejectionText } from "./recusas"

interface Props {
  /** The token from the e-mail link. Empty = invalid or truncated link. */
  token?: string
  onEnviando: (enviando: boolean) => void
  /** The password was changed: the modal returns to login with the notice. */
  onRedefiniu: () => void
  /** Pedir um link novo — o painel de "Esqueceu a senha?". */
  onRecuperar: () => void
}

export function ResetPanel({ token, onEnviando, onRedefiniu, onRecuperar }: Props) {
  const t = useTexts().entrada.painelRedefinir
  // The server only speaks Portuguese: in the other languages, the rejection via
  // the language's text (see ./recusas).
  const traduzir = useScreenLanguage() !== "pt-BR"
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const passwordMismatch = confirmPassword.length > 0 && password !== confirmPassword

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirmPassword) {
      setError(t.senhasNaoCoincidem)
      return
    }
    setLoading(true)
    onEnviando(true)
    setError("")
    try {
      await axios.post(`${API_URL}/auth/reset-password`, {
        token,
        password,
        password_confirm: confirmPassword,
      })
      onRedefiniu()
    } catch (err) {
      setError(linkRejectionText(err, traduzir, t))
    } finally {
      setLoading(false)
      onEnviando(false)
    }
  }

  // Without a token there is nothing to reset. Instead of the dead end the old
  // page gave ("Link inválido" + a link to another page), the way back is one
  // click, in the same modal.
  if (!token) {
    return (
      <>
        <AuthError error={{ message: t.linkInvalido }} />
        <ModalButton type="button" onClick={onRecuperar}>
          {t.pedirLinkNovo}
        </ModalButton>
      </>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
      <AuthPasswordField
        id="nova-senha"
        label={t.novaSenha}
        value={password}
        onChange={setPassword}
        autoComplete="new-password"
        required
        minLength={8}
        disabled={loading}
      >
        <AuthPasswordStrength password={password} />
      </AuthPasswordField>

      <AuthPasswordField
        id="confirmar-nova-senha"
        label={t.confirmarNovaSenha}
        value={confirmPassword}
        onChange={setConfirmPassword}
        autoComplete="new-password"
        required
        minLength={8}
        disabled={loading}
      >
        {passwordMismatch && <p className="text-xs text-red-400">{t.senhasNaoCoincidem}</p>}
      </AuthPasswordField>

      {error && <AuthError error={{ message: error }} />}

      <ModalButton loading={loading} loadingLabel={t.redefinindo} disabled={passwordMismatch} className="mt-1">
        {t.redefinirSenha}
      </ModalButton>

      <p className="text-center text-[12.5px] text-muted-foreground">
        {t.linkExpirou} <LinkDoModal onClick={onRecuperar}>{t.pedirOutro}</LinkDoModal>
      </p>
    </form>
  )
}
