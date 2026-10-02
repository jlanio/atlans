"use client"

// "Verifique seu e-mail", dentro do modal: o que a página /verify-email fazia,
// sem sair da Home. São os mesmos dois caminhos dela —
//
//   COM token (o link que chegou por e-mail): o GET /auth/verify-email gasta o
//   token e ATIVA a conta. No sucesso o modal volta ao login com o aviso; na
//   falha, a mensagem do servidor e o reenvio, aqui mesmo.
//   SEM token (recém-cadastrado, ou o acesso direto): a mensagem de "abra o
//   link do e-mail", o reenvio (POST /auth/resend-verification, já preenchido
//   com o e-mail do cadastro) e a volta ao login.
//
// — e a mensagem que ficou na barra espera esse login nos dois.

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

/** O que o painel está mostrando — o modal titula o diálogo por ele. */
export type EstadoDaVerificacao = "sem-token" | "verificando" | "falhou"

interface Props {
  /** O e-mail do cadastro — o reenvio já nasce preenchido. */
  email: string
  /** O token do link do e-mail; ausente = a tela de "abra o link". */
  token?: string
  onEnviando: (enviando: boolean) => void
  /** "Já verifiquei: entrar" — troca para o painel de login. */
  onEntrar: () => void
  /** A conta foi ativada: o modal volta ao login com o aviso. */
  onVerificou: () => void
  /** O cabeçalho do modal acompanha o estado (título e frase de apoio). */
  onEstado: (estado: EstadoDaVerificacao) => void
  /**
   * O token acabou de ser gasto — o modal para de passá-lo. Quem VOLTA a este
   * painel depois (pelo 403 do login, ou pelo "Reenviar" de uma falha) quer
   * outro e-mail, não gastar de novo o link que já usou: sem isto, o painel
   * remontava com o mesmo token da URL e repetia o GET.
   */
  onGastouToken: () => void
}

export function PainelVerificar({ email, token, onEnviando, onEntrar, onVerificou, onEstado, onGastouToken }: Props) {
  const t = useTextos().entrada.painelVerificar
  // O servidor só fala português (a recusa do token, a resposta do reenvio):
  // nos outros idiomas, o texto do idioma (ver ./recusas).
  const traduzir = useIdiomaDaTela() !== "pt-BR"
  const [estado, setEstado] = useState<EstadoDaVerificacao>(token ? "verificando" : "sem-token")
  // A recusa do token como veio. O texto sai no render, no idioma da tela (o
  // efeito do GET não precisa depender dele).
  const [recusaDoToken, setRecusaDoToken] = useState<unknown>(null)
  const [resendEmail, setResendEmail] = useState(email)
  const [resending, setResending] = useState(false)
  const [resendMsg, setResendMsg] = useState("")
  // Sucesso e erro separados: a cor e o `role` acompanham o que aconteceu.
  const [resendOk, setResendOk] = useState(false)

  // Desmontado (o modal fechou, ou trocou de painel) nada mais pode ser escrito
  // — a resposta do GET ainda pode estar a caminho.
  const vivo = useRef(true)
  useEffect(() => () => { vivo.current = false }, [])

  // O GET que GASTA o token, uma vez só. A guarda não é zelo: o token é de uso
  // único, então um segundo GET (o StrictMode em desenvolvimento invoca o
  // efeito duas vezes, e as duas callbacks correriam) voltaria "inválido" e
  // apagaria o sucesso do primeiro. Por isso a marca é posta ANTES do envio, e
  // não depois.
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

  // O cabeçalho do modal é de lá, não daqui: o `DialogTitle` tem de existir
  // sempre (é o nome acessível do diálogo), então quem o troca é o modal.
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

  // O GET em voo. Não trava o fechamento do modal (`onEnviando`) de propósito:
  // ele começa sozinho, sem ninguém pedir, e prender Esc por causa de uma
  // requisição que a pessoa não disparou seria surpresa. Fechar no meio também
  // não custa nada — o backend ativa a conta do mesmo jeito, e o login seguinte
  // simplesmente funciona.
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
