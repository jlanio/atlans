"use client"

// The sign-up form of the sign-in modal. The logic is that of the old
// /register page, moved here: on success there is no toast or navigation — the
// modal switches to the "Verifique seu e-mail" panel (sign-up requires verifying
// the e-mail before the first login).

import { useState } from "react"
import axios, { AxiosError } from "axios"

import { API_URL } from "@/utils/env"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { AuthError, type AuthErrorInfo } from "@/app/components/auth/AuthError"
import { AuthPasswordField } from "@/app/components/auth/AuthPasswordField"
import { AuthPasswordStrength } from "@/app/components/auth/AuthPasswordStrength"
import { useScreenLanguage, useTexts } from "@/app/components/home/i18n"
import { ModalButton, LinkDoModal } from "./botao-do-modal"
import { isServerRejection } from "./recusas"

interface Props {
  onEnviando: (enviando: boolean) => void
  /** The account was created: carries the e-mail, so the resend comes prefilled. */
  onCadastrou: (email: string) => void
  /** "Já tem conta? Entrar": switches to the login panel. */
  onEntrar: () => void
}

export function SignUpForm({ onEnviando, onCadastrou, onEntrar }: Props) {
  const t = useTexts().entrada.formularioDeCadastro
  // In Portuguese the server's rejection as it came; in the others, the language's
  // text (see ./recusas).
  const traduzir = useScreenLanguage() !== "pt-BR"
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<AuthErrorInfo | null>(null)

  const passwordMismatch = confirmPassword.length > 0 && password !== confirmPassword

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirmPassword) {
      setError({ message: t.senhasNaoCoincidem })
      return
    }
    setLoading(true)
    onEnviando(true)
    setError(null)
    try {
      await axios.post(`${API_URL}/auth/register`, {
        username, email, password, password_confirm: confirmPassword,
      })
      onCadastrou(email)
    } catch (err) {
      const axiosErr = err as AxiosError<{ error?: string; message?: string; details?: { msg: string }[] }>
      const status = axiosErr.response?.status
      const data = axiosErr.response?.data
      // The error is a persistent inline block (role="alert"), not an ephemeral
      // toast — the person reads at their own pace and fixes the field.
      if (!axiosErr.response) {
        setError({ message: t.semConexao })
      } else if (status === 429) {
        setError({ message: (traduzir ? null : data?.message) ?? t.muitasTentativas })
      } else if (data?.error === "validation_error" && Array.isArray(data.details)) {
        setError({ message: data.details.map((d) => d.msg).join(" • ") || t.dadosInvalidos })
      } else if (traduzir && !isServerRejection(data)) {
        // The proxy down, an unexpected 500, a CDN's error page.
        setError({ message: t.erroAoCriarConta })
      } else if (traduzir && status === 400) {
        // The only 400 from sign-up (the same sentence for username and e-mail).
        setError({ message: t.jaEmUso })
      } else {
        setError({ message: data?.message ?? t.erroAoCriarConta })
      }
    } finally {
      setLoading(false)
      onEnviando(false)
    }
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="username" className="auth-label text-sm">
            {t.usuario}
          </Label>
          <Input
            id="username"
            type="text"
            autoComplete="username"
            required
            minLength={3}
            maxLength={50}
            pattern="[a-z0-9_]+"
            title={t.regraDoUsuario}
            placeholder={t.exemploDeUsuario}
            disabled={loading}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="auth-input h-11 text-sm"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email" className="auth-label text-sm">
            {t.email}
          </Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            disabled={loading}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="auth-input h-11 text-sm"
          />
        </div>

        <AuthPasswordField
          id="password"
          label={t.senha}
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
          id="confirm-password"
          label={t.confirmarSenha}
          value={confirmPassword}
          onChange={setConfirmPassword}
          autoComplete="new-password"
          required
          minLength={8}
          disabled={loading}
        >
          {passwordMismatch && <p className="text-xs text-red-400">{t.senhasNaoCoincidem}</p>}
        </AuthPasswordField>

        {error && <AuthError error={error} />}

        <ModalButton loading={loading} loadingLabel={t.cadastrando} disabled={passwordMismatch} className="mt-1">
          {t.criarConta}
        </ModalButton>
      </form>

      <p className="text-center text-[12.5px] text-muted-foreground">
        {t.jaTemConta} <LinkDoModal onClick={onEntrar}>{t.entrar}</LinkDoModal>
      </p>
    </>
  )
}
