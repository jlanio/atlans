"use client"

// O formulário de cadastro do modal de entrada. A lógica é a da antiga página
// /register, movida para cá: no sucesso não há toast nem navegação — o modal
// troca para o painel "Verifique seu e-mail" (o cadastro exige verificar o
// e-mail antes do primeiro login).

import { useState } from "react"
import axios, { AxiosError } from "axios"

import { API_URL } from "@/utils/env"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { AuthError, type AuthErrorInfo } from "@/app/components/auth/AuthError"
import { AuthPasswordField } from "@/app/components/auth/AuthPasswordField"
import { AuthPasswordStrength } from "@/app/components/auth/AuthPasswordStrength"
import { useIdiomaDaTela, useTextos } from "@/app/components/home/i18n"
import { BotaoDoModal, LinkDoModal } from "./botao-do-modal"
import { ehRecusaDoServidor } from "./recusas"

interface Props {
  onEnviando: (enviando: boolean) => void
  /** A conta foi criada: leva o e-mail, para o reenvio já sair preenchido. */
  onCadastrou: (email: string) => void
  /** "Já tem conta? Entrar": troca para o painel de login. */
  onEntrar: () => void
}

export function FormularioDeCadastro({ onEnviando, onCadastrou, onEntrar }: Props) {
  const t = useTextos().entrada.formularioDeCadastro
  // Em português a recusa do servidor como veio; nos outros, o texto do idioma
  // (ver ./recusas).
  const traduzir = useIdiomaDaTela() !== "pt-BR"
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
      // O erro é um bloco inline persistente (role="alert"), não um toast
      // efêmero — a pessoa lê no ritmo dela e corrige o campo.
      if (!axiosErr.response) {
        setError({ message: t.semConexao })
      } else if (status === 429) {
        setError({ message: (traduzir ? null : data?.message) ?? t.muitasTentativas })
      } else if (data?.error === "validation_error" && Array.isArray(data.details)) {
        setError({ message: data.details.map((d) => d.msg).join(" • ") || t.dadosInvalidos })
      } else if (traduzir && !ehRecusaDoServidor(data)) {
        // O proxy fora do ar, um 500 inesperado, a página de erro de uma CDN.
        setError({ message: t.erroAoCriarConta })
      } else if (traduzir && status === 400) {
        // O único 400 do cadastro (a mesma frase para usuário e e-mail).
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

        <BotaoDoModal loading={loading} loadingLabel={t.cadastrando} disabled={passwordMismatch} className="mt-1">
          {t.criarConta}
        </BotaoDoModal>
      </form>

      <p className="text-center text-[12.5px] text-muted-foreground">
        {t.jaTemConta} <LinkDoModal onClick={onEntrar}>{t.entrar}</LinkDoModal>
      </p>
    </>
  )
}
