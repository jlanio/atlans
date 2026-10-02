"use client"

// O formulário de login do modal de entrada. A lógica é a da antiga página
// /login, movida para cá sem a navegação: o POST /auth/login devolve os tokens,
// o `signIn` do next-auth (sem redirect) grava o cookie E atualiza o
// `useSession` da aba — o modal fecha e a Home segue no lugar.

import { useState } from "react"
import { signIn } from "next-auth/react"
import axios, { AxiosError } from "axios"

import { API_URL } from "@/utils/env"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { AuthError, type AuthErrorInfo } from "@/app/components/auth/AuthError"
import { AuthPasswordField } from "@/app/components/auth/AuthPasswordField"
import { useIdiomaDaTela, useTextos } from "@/app/components/home/i18n"
import { BotaoDoModal, LinkDoModal } from "./botao-do-modal"
import { ehRecusaDoServidor } from "./recusas"

interface Props {
  /** Um envio em voo: o modal trava o fechamento enquanto durar. */
  onEnviando: (enviando: boolean) => void
  /** O login deu certo — a sessão já está atualizada. */
  onEntrou: () => void
  /** "Não tem conta? Criar conta": troca para o painel de cadastro. */
  onCriarConta: () => void
  /** "Esqueceu a senha?": troca para o painel de recuperação. */
  onRecuperar: () => void
  /**
   * "Reenviar e-mail de verificação" (o 403 de conta não verificada): troca
   * para o painel de verificação. Leva o que foi digitado quando isso já é um
   * e-mail — o campo aceita e-mail OU usuário, e o reenvio só sabe e-mail.
   */
  onVerificar: (email: string) => void
}

export function FormularioDeEntrada({ onEnviando, onEntrou, onCriarConta, onRecuperar, onVerificar }: Props) {
  const t = useTextos().entrada.formularioDeEntrada
  // Em português, a recusa do servidor COMO VEIO (a de sempre); em inglês e
  // espanhol, a mesma recusa pelo texto do idioma — o servidor só fala
  // português (ver ./recusas).
  const traduzir = useIdiomaDaTela() !== "pt-BR"
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
      const doServidor = ehRecusaDoServidor(data)
      if (!axiosErr.response) {
        setError({ message: t.semConexao })
      } else if (status === 403 && errCode === "email_not_verified") {
        setError({ message: traduzir ? t.emailNaoVerificado : message, emailNotVerified: true })
      } else if (status === 429) {
        // Dois 429 diferentes: o bloqueio da CONTA (do servidor, com
        // Retry-After) e o limite por conexão (5 por minuto, do limitador —
        // conta nenhuma bloqueada, e a janela passa em um minuto).
        const minutos = minutosDoRetryAfter(axiosErr.response.headers?.["retry-after"])
        const texto = doServidor ? t.contaBloqueada(minutos) : t.muitasTentativas
        setError({ message: traduzir ? texto : message, locked: true })
      } else if (traduzir && !doServidor) {
        // O proxy fora do ar, um 500 inesperado, a página de erro de uma CDN.
        setError({ message: t.erroAoEntrar })
      } else if (traduzir && status === 401) {
        setError({ message: t.credenciaisInvalidas })
      } else if (traduzir && status === 403) {
        // Conta suspensa, excluída ou desativada: o status não diz qual.
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
            // Botão, não link: a recuperação virou um painel deste mesmo modal
            // (/forgot-password só redireciona para cá). Navegar levaria a
            // pessoa para fora da Home e jogaria fora a mensagem pendente.
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

        <BotaoDoModal loading={loading} loadingLabel={t.entrando} disabled={!!error?.locked} className="mt-1">
          {t.entrar}
        </BotaoDoModal>
      </form>

      <p className="text-center text-[12.5px] text-muted-foreground">
        {t.naoTemConta} <LinkDoModal onClick={onCriarConta}>{t.criarConta}</LinkDoModal>
      </p>
    </>
  )
}

/** `Retry-After` em segundos → minutos inteiros para a frase (null quando não veio). */
function minutosDoRetryAfter(valor: unknown): number | null {
  const segundos = Number(valor)
  return Number.isFinite(segundos) && segundos > 0 ? Math.ceil(segundos / 60) : null
}
