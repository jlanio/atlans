"use client"

// The login form of the sign-in modal. The logic is that of the old /login
// page, moved here without the navigation: POST /auth/login returns the tokens,
// next-auth's `signIn` (without redirect) writes the cookie AND updates the
// tab's `useSession` — the modal closes and the Home stays in place.

import { useState } from "react"
import { signIn } from "next-auth/react"
import axios, { AxiosError } from "axios"

import { API_URL } from "@/utils/env"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { AuthError, type AuthErrorInfo } from "@/app/components/auth/AuthError"
import { AuthPasswordField } from "@/app/components/auth/AuthPasswordField"
import { useScreenLanguage, useTexts } from "@/app/components/home/i18n"
import { ModalButton, LinkDoModal } from "./botao-do-modal"
import { isServerRejection } from "./recusas"

interface Props {
  /** Um envio em voo: o modal trava o fechamento enquanto durar. */
  onEnviando: (enviando: boolean) => void
  /** Login succeeded — the session is already updated. */
  onEntrou: () => void
  /** "Não tem conta? Criar conta": switches to the sign-up panel. */
  onCriarConta: () => void
  /** "Esqueceu a senha?": switches to the recovery panel. */
  onRecuperar: () => void
  /**
   * "Reenviar e-mail de verificação" (the 403 for an unverified account):
   * switches to the verification panel. Carries what was typed when it is
   * already an e-mail — the field accepts e-mail OR username, and the resend
   * only knows e-mail.
   */
  onVerificar: (email: string) => void
}

export function SignInForm({ onEnviando, onEntrou, onCriarConta, onRecuperar, onVerificar }: Props) {
  const t = useTexts().entrada.formularioDeEntrada
  // In Portuguese, the server's rejection AS IT CAME (as always); in English and
  // Spanish, the same rejection via the language's text — the server only speaks
  // Portuguese (see ./recusas).
  const traduzir = useScreenLanguage() !== "pt-BR"
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<AuthErrorInfo | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    onEnviando(true)
    setError(null)
    try {
      const { data: tokens } = await axios.post(`${API_URL}/auth/login`, { identifier, password })
      const result = await signIn("credentials", {
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        redirect: false,
      })
      if (result?.error) {
        setError({ message: t.erroAoIniciarSessao })
      } else {
        onEntrou()
      }
    } catch (err) {
      const axiosErr = err as AxiosError<{ error?: string; message?: string; detail?: string }>
      const status = axiosErr.response?.status
      const errCode = axiosErr.response?.headers?.["x-error-code"]
      const data = axiosErr.response?.data
      const message = data?.message ?? data?.detail ?? t.erroAoEntrar
      const fromServer = isServerRejection(data)
      if (!axiosErr.response) {
        setError({ message: t.semConexao })
      } else if (status === 403 && errCode === "email_not_verified") {
        setError({ message: traduzir ? t.emailNaoVerificado : message, emailNotVerified: true })
      } else if (status === 429) {
        // Two different 429s: the ACCOUNT lockout (from the server, with
        // Retry-After) and the per-connection limit (5 per minute, from the
        // limiter — no account locked, and the window passes in a minute).
        const minutos = retryAfterMinutes(axiosErr.response.headers?.["retry-after"])
        const texto = fromServer ? t.contaBloqueada(minutos) : t.muitasTentativas
        setError({ message: traduzir ? texto : message, locked: true })
      } else if (traduzir && !fromServer) {
        // The proxy down, an unexpected 500, a CDN's error page.
        setError({ message: t.erroAoEntrar })
      } else if (traduzir && status === 401) {
        setError({ message: t.credenciaisInvalidas })
      } else if (traduzir && status === 403) {
        // Account suspended, deleted or deactivated: the status does not say which.
        setError({ message: t.contaIndisponivel })
      } else {
        setError({ message })
      }
    } finally {
      setLoading(false)
      onEnviando(false)
    }
  }

  const bloqueado = loading || !!error?.locked

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="identifier" className="auth-label text-sm">
            {t.emailOuUsuario}
          </Label>
          <Input
            id="identifier"
            type="text"
            autoComplete="username"
            required
            disabled={bloqueado}
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            className="auth-input h-11 text-sm"
          />
        </div>

        <AuthPasswordField
          id="password"
          label={t.senha}
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          required
          disabled={bloqueado}
          labelRight={
            // Button, not link: recovery became a panel of this same modal
            // (/forgot-password only redirects here). Navigating would take the
            // person out of the Home and throw away the pending message.
            <LinkDoModal onClick={onRecuperar} className="text-xs underline-offset-2">
              {t.esqueceuASenha}
            </LinkDoModal>
          }
        />

        {error && (
          <AuthError
            error={error}
            onReenviarVerificacao={() => onVerificar(identifier.includes("@") ? identifier : "")}
          />
        )}

        <ModalButton loading={loading} loadingLabel={t.entrando} disabled={!!error?.locked} className="mt-1">
          {t.entrar}
        </ModalButton>
      </form>

      <p className="text-center text-[12.5px] text-muted-foreground">
        {t.naoTemConta} <LinkDoModal onClick={onCriarConta}>{t.criarConta}</LinkDoModal>
      </p>
    </>
  )
}

/** `Retry-After` in seconds → whole minutes for the sentence (null when absent). */
function retryAfterMinutes(valor: unknown): number | null {
  const segundos = Number(valor)
  return Number.isFinite(segundos) && segundos > 0 ? Math.ceil(segundos / 60) : null
}
