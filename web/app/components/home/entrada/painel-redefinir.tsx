"use client"

// "Nova senha", dentro do modal: o que a página /reset-password fazia. O token
// vem do link do e-mail, pela query da Home (`/?redefinir=1&token=…`), e é
// SÓ isto que esta tela recebe de fora — ela não sabe de quem é a conta, e não
// precisa saber.
//
// No sucesso não há navegação: o painel troca para o login, já com o aviso de
// que a senha foi trocada. Se a pessoa chegou aqui pela barra (com uma mensagem
// pendente), ela continua esperando o login.

import { useState } from "react"
import axios from "axios"

import { API_URL } from "@/utils/env"
import { AuthError } from "@/app/components/auth/AuthError"
import { AuthPasswordField } from "@/app/components/auth/AuthPasswordField"
import { AuthPasswordStrength } from "@/app/components/auth/AuthPasswordStrength"
import { useIdiomaDaTela, useTextos } from "@/app/components/home/i18n"
import { BotaoDoModal, LinkDoModal } from "./botao-do-modal"
import { textoDaRecusaDoLink } from "./recusas"

interface Props {
  /** O token do link do e-mail. Vazio = link inválido ou truncado. */
  token?: string
  onEnviando: (enviando: boolean) => void
  /** A senha foi trocada: o modal volta ao login com o aviso. */
  onRedefiniu: () => void
  /** Pedir um link novo — o painel de "Esqueceu a senha?". */
  onRecuperar: () => void
}

export function PainelRedefinir({ token, onEnviando, onRedefiniu, onRecuperar }: Props) {
  const t = useTextos().entrada.painelRedefinir
  // O servidor só fala português: nos outros idiomas, a recusa pelo texto do
  // idioma (ver ./recusas).
  const traduzir = useIdiomaDaTela() !== "pt-BR"
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
      setError(textoDaRecusaDoLink(err, traduzir, t))
    } finally {
      setLoading(false)
      onEnviando(false)
    }
  }

  // Sem token não há o que redefinir. Em vez do beco sem saída que a página
  // antiga dava ("Link inválido" + um link para outra página), o caminho de
  // volta é um clique, no mesmo modal.
  if (!token) {
    return (
      <>
        <AuthError error={{ message: t.linkInvalido }} />
        <BotaoDoModal type="button" onClick={onRecuperar}>
          {t.pedirLinkNovo}
        </BotaoDoModal>
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

      <BotaoDoModal loading={loading} loadingLabel={t.redefinindo} disabled={passwordMismatch} className="mt-1">
        {t.redefinirSenha}
      </BotaoDoModal>

      <p className="text-center text-[12.5px] text-muted-foreground">
        {t.linkExpirou} <LinkDoModal onClick={onRecuperar}>{t.pedirOutro}</LinkDoModal>
      </p>
    </form>
  )
}
