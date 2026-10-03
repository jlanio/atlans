"use client"

// "Verifique seu e-mail", inside the modal: what the /verify-email page did,
// without leaving the Home. These are the same two paths it had —
//
//   WITH a token (the link that arrived by e-mail): GET /auth/verify-email spends
//   the token and ACTIVATES the account. On success the modal returns to login
//   with the notice; on failure, the server message and the resend, right here.
//   WITHOUT a token (just signed up, or direct access): the "open the e-mail
//   link" message, the resend (POST /auth/resend-verification, already prefilled
//   with the sign-up e-mail) and the way back to login.
//
// — and the message left in the bar waits for that login in both.

import { useEffect, useRef, useState } from "react"
import axios from "axios"
import { TbLoader2, TbMailCheck } from "react-icons/tb"

import { API_URL } from "@/utils/env"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { AuthError } from "@/app/components/auth/AuthError"
import { useIdiomaDaTela, useTextos } from "@/app/components/home/i18n"
import { BotaoDoModal } from "./botao-do-modal"
import { textoDaRecusaDoLink } from "./recusas"

/** What the panel is showing — the modal titles the dialog by it. */
export type EstadoDaVerificacao = "sem-token" | "verificando" | "falhou"

interface Props {
  /** The sign-up e-mail — the resend starts prefilled. */
  email: string
  /** The token from the e-mail link; absent = the "open the link" screen. */
  token?: string
  onEnviando: (enviando: boolean) => void
  /** "Já verifiquei: entrar" — switches to the login panel. */
  onEntrar: () => void
  /** The account was activated: the modal returns to login with the notice. */
  onVerificou: () => void
  /** The modal header follows the state (title and supporting sentence). */
  onEstado: (estado: EstadoDaVerificacao) => void
  /**
   * The token was just spent — the modal stops passing it. Whoever COMES BACK to
   * this panel later (via the login's 403, or via a failure's "Reenviar") wants
   * another e-mail, not to spend again the link already used: without this, the
   * panel remounted with the same token from the URL and repeated the GET.
   */
  onGastouToken: () => void
}

export function PainelVerificar({ email, token, onEnviando, onEntrar, onVerificou, onEstado, onGastouToken }: Props) {
  const t = useTextos().entrada.painelVerificar
  // The server only speaks Portuguese (the token rejection, the resend response):
  // in the other languages, the language's text (see ./recusas).
  const traduzir = useIdiomaDaTela() !== "pt-BR"
  const [estado, setEstado] = useState<EstadoDaVerificacao>(token ? "verificando" : "sem-token")
  // The token rejection as it came. The text is produced at render, in the
  // screen's language (the GET effect does not need to depend on it).
  const [recusaDoToken, setRecusaDoToken] = useState<unknown>(null)
  const [resendEmail, setResendEmail] = useState(email)
  const [resending, setResending] = useState(false)
  const [resendMsg, setResendMsg] = useState("")
  // Sucesso e erro separados: a cor e o `role` acompanham o que aconteceu.
  const [resendOk, setResendOk] = useState(false)

  // Once unmounted (the modal closed, or switched panels) nothing more may be
  // written — the GET response may still be on its way.
  const vivo = useRef(true)
  useEffect(() => () => { vivo.current = false }, [])

  // The GET that SPENDS the token, only once. The guard is not overcaution: the
  // token is single-use, so a second GET (StrictMode in development invokes the
  // effect twice, and both callbacks would run) would come back "inválido" and
  // erase the first one's success. That is why the mark is set BEFORE sending,
  // not after.
  const gastou = useRef(false)
  useEffect(() => {
    if (!token || gastou.current) return
    gastou.current = true
    onGastouToken()
    axios
      .get(`${API_URL}/auth/verify-email`, { params: { token } })
      .then(() => { if (vivo.current) onVerificou() })
      .catch((err) => {
        if (!vivo.current) return
        setRecusaDoToken(err)
        setEstado("falhou")
      })
  }, [token, onVerificou, onGastouToken])

  // The modal header belongs there, not here: the `DialogTitle` must always
  // exist (it is the dialog's accessible name), so the one that swaps it is the modal.
  useEffect(() => { onEstado(estado) }, [estado, onEstado])

  async function handleResend(e: React.FormEvent) {
    e.preventDefault()
    setResending(true)
    onEnviando(true)
    setResendMsg("")
    try {
      const res = await axios.post(`${API_URL}/auth/resend-verification`, { email: resendEmail })
      setResendOk(true)
      setResendMsg(traduzir ? t.reenviado : res.data.message)
    } catch {
      setResendOk(false)
      setResendMsg(t.erroAoReenviar)
    } finally {
      setResending(false)
      onEnviando(false)
    }
  }

  // The GET in flight. It does not lock the modal's closing (`onEnviando`) on
  // purpose: it starts on its own, without anyone asking, and holding Esc hostage
  // because of a request the person did not trigger would be a surprise. Closing
  // midway costs nothing either — the backend activates the account all the same,
  // and the next login simply works.
  if (estado === "verificando") {
    return (
      <div className="flex items-center gap-3 rounded-md border border-border bg-muted/40 px-3 py-2.5 text-sm text-muted-foreground">
        <TbLoader2 size={20} className="shrink-0 text-primary motion-safe:animate-spin" aria-hidden="true" />
        <span role="status">{t.verificandoEmail}</span>
      </div>
    )
  }

  return (
    <>
      {estado === "falhou" ? (
        <AuthError error={{ message: textoDaRecusaDoLink(recusaDoToken, traduzir, t) }} />
      ) : (
        <div className="flex items-start gap-3 rounded-md border border-border bg-muted/40 px-3 py-2.5 text-sm text-muted-foreground">
          <TbMailCheck size={20} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
          <span>{t.abraOLink}</span>
        </div>
      )}

      <form onSubmit={handleResend} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="resend-email" className="auth-label text-sm">
            {estado === "falhou" ? t.reenviarPara : t.naoRecebeu}
          </Label>
          <Input
            id="resend-email"
            type="email"
            required
            placeholder={t.exemploDeEmail}
            disabled={resending}
            value={resendEmail}
            onChange={(e) => setResendEmail(e.target.value)}
            className="auth-input h-11 text-sm"
          />
        </div>
        <BotaoDoModal variant="outline" loading={resending} loadingLabel={t.enviando}>
          {t.reenviarEmail}
        </BotaoDoModal>
        {resendMsg && (
          <p role={resendOk ? "status" : "alert"} className={`text-xs ${resendOk ? "text-green-400" : "text-red-400"}`}>
            {resendMsg}
          </p>
        )}
      </form>

      <BotaoDoModal type="button" onClick={onEntrar}>
        {estado === "falhou" ? t.voltarParaEntrar : t.jaVerifiquei}
      </BotaoDoModal>
    </>
  )
}
