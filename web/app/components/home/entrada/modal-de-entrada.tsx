"use client"

// web/app/components/home/entrada/modal-de-entrada.tsx
//
// The site's SIGN-IN — login and sign-up — as a modal over the Home globe, in
// its theme (`home-portal`) and with the background slightly dimmed (the globe
// stays visible behind it). Replaces the /login and /register screens, which
// now only redirect here: the Home opens without a session and the first
// submission to the bar opens this modal; a successful login closes it, and the
// pending message goes out on its own (HomeView).
//
// FIVE panels in a single dialog: Entrar, Criar conta, "Verifique seu e-mail",
// "Esqueceu a senha?" and "Nova senha". The last three were the
// /verify-email, /forgot-password and /reset-password pages, from the old
// full-page model, which now only redirect here — with them went the last
// `AuthShell` screen of this flow. The whole account journey happens without
// leaving the Home: create, activate via the e-mail link, request the password
// link, come back from the e-mail and save the new password.
//
// CLOSABLE — Esc, the X and clicking outside close it, the owner's decision —,
// except with a submission in flight: then the X is disabled and Esc/clicking
// outside are ignored — the `DialogContent`'s `bloqueado`.

import { useCallback, useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { BrandGlyph } from "@/app/components/sidebar/marca"
import { useSourceCode } from "@/app/components/share/codigo-fonte"
import { useDisplayName } from "@/app/components/share/nome-na-tela"
import { useTexts } from "@/app/components/home/i18n"
import type { EntryMode } from "@/lib/entrada"
import { SignInForm } from "./formulario-de-entrada"
import { SignUpForm } from "./formulario-de-cadastro"
import { VerifyPanel, type VerificationState } from "./painel-verificar"
import { RecoverPanel } from "./painel-recuperar"
import { ResetPanel } from "./painel-redefinir"

interface Props {
  /** O modal pedido; `null` = fechado. */
  modo: EntryMode | null
  /**
   * The token from the link that brought the person — the password reset one
   * (`?redefinir=1&token=…`) or the verification one (`?verificar=1&token=…`).
   * It is a single one because the panels are mutually exclusive: whoever
   * arrives through one does not arrive through the other.
   */
  tokenDoLink?: string
  /** There is a message waiting for login (the first submission): changes the supporting sentence. */
  comEnvioPendente?: boolean
  /** Fechar SEM entrar (Esc, X, clique fora). */
  onFechar: () => void
  /** Login succeeded — the tab's session is already updated (`signIn` without redirect). */
  onEntrou: () => void
}

export default function ModalDeEntrada({
  modo, tokenDoLink, comEnvioPendente = false, onFechar, onEntrou,
}: Props) {
  const textos = useTexts()
  const codigoFonte = useSourceCode()
  const displayName = useDisplayName()
  const t = textos.entrada.modal
  const [painel, setPanel] = useState<EntryMode>(modo ?? "entrar")
  const [enviando, setSending] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState("")
  // The link request went out: the same panel changes its face, and the header with it.
  const [linkEnviado, setLinkSent] = useState(false)
  // The password was just changed: the login gets a notice instead of a toast,
  // which would disappear behind the modal.
  const [senhaTrocada, setPasswordChanged] = useState(false)
  // The account was just activated via the e-mail link — same notice, same
  // reason.
  const [emailVerificado, setEmailVerified] = useState(false)
  // Which of the three states the verification panel is in (the token GET
  // starts on its own): the dialog's title and supporting sentence come from here.
  const [verificationState, setVerificationState] = useState<VerificationState>("sem-token")
  // The link token is valid ONCE per modal, not once per panel mount: it
  // stays in the URL after being spent, and without this mark going back to the
  // panel (via the login's 403, or via a failure's "Reenviar") would repeat the
  // GET with a token that is no longer valid.
  const [tokenSpent, setTokenSpent] = useState(false)
  // Reopening in another mode (Criar conta from the sidebar after an Entrar)
  // switches the panel; closed (`null`) nothing changes.
  useEffect(() => {
    if (modo) setPanel(modo)
  }, [modo])

  // Stable on purpose: the panel has it in the dependencies of the effect that
  // spends the token, and a new identity on every render would make it run again.
  const markTokenSpent = useCallback(() => setTokenSpent(true), [])

  function irPara(destino: EntryMode) {
    // Leaving a panel resets what was its own: going back to "Esqueceu a senha?"
    // has to ask for the e-mail again, and the login cannot keep forever the
    // notice of a changed password (or a verified e-mail) three panels ago.
    if (destino !== "recuperar") setLinkSent(false)
    if (destino !== "entrar") { setPasswordChanged(false); setEmailVerified(false) }
    if (destino !== "verificar") setVerificationState("sem-token")
    setPanel(destino)
  }

  const titulo =
    painel === "verificar" && verificationState === "verificando"
      ? t.tituloVerificando
      : painel === "verificar" && verificationState === "falhou"
        ? t.tituloFalhou
        : t.titulos[painel]

  const descricao =
    painel === "entrar"
      ? senhaTrocada
        ? t.descricoes.senhaTrocada
        : emailVerificado
          ? t.descricoes.emailVerificado
          : comEnvioPendente
            ? t.descricoes.comEnvioPendente
            : t.descricoes.entrar
      : painel === "cadastro"
        ? t.descricoes.cadastro
        : painel === "recuperar"
          ? linkEnviado
            ? t.descricoes.linkEnviado
            : t.descricoes.recuperar
          : painel === "redefinir"
            ? t.descricoes.redefinir
            : verificationState === "verificando"
              ? t.descricoes.verificando
              : verificationState === "falhou"
                ? t.descricoes.verificacaoFalhou
                : t.descricoes.verificar

  return (
    <Dialog open={modo !== null} onOpenChange={(aberto) => { if (!aberto && !enviando) onFechar() }}>
      <DialogContent
        className="home-portal w-full max-w-[calc(100%-2rem)] gap-5 rounded-xl border-border bg-background p-6 text-foreground sm:max-w-sm"
        // The slightly dimmed background: the globe stays visible behind it.
        overlayClassName="bg-black/40 backdrop-blur-[2px]"
        bloqueado={enviando}
        closeLabel={textos.comum.fechar}
        data-testid="modal-de-entrada"
        data-painel={painel}
      >
        <DialogHeader className="gap-3 text-left">
          <p className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <BrandGlyph /> {displayName}
            {/* AGPL §13: whoever uses the installation over the network finds its
                source code from here, even before signing in. Only when the installation declares it. */}
            {codigoFonte && (
              <a
                href={codigoFonte}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-xs font-normal underline-offset-4 hover:underline"
              >
                {textos.comum.codigoFonte}
              </a>
            )}
          </p>
          <DialogTitle className="text-xl">{titulo}</DialogTitle>
          <DialogDescription>{descricao}</DialogDescription>
        </DialogHeader>

        {painel === "entrar" && (
          <SignInForm
            onEnviando={setSending}
            onEntrou={onEntrou}
            onCriarConta={() => irPara("cadastro")}
            onRecuperar={() => irPara("recuperar")}
            onVerificar={(email) => { if (email) setRegisteredEmail(email); irPara("verificar") }}
          />
        )}
        {painel === "cadastro" && (
          <SignUpForm
            onEnviando={setSending}
            onCadastrou={(email) => { setRegisteredEmail(email); irPara("verificar") }}
            onEntrar={() => irPara("entrar")}
          />
        )}
        {painel === "verificar" && (
          <VerifyPanel
            email={registeredEmail}
            token={tokenSpent ? undefined : tokenDoLink}
            onEnviando={setSending}
            onEntrar={() => irPara("entrar")}
            onVerificou={() => { setPanel("entrar"); setEmailVerified(true) }}
            onEstado={setVerificationState}
            onGastouToken={markTokenSpent}
          />
        )}
        {painel === "recuperar" && (
          <RecoverPanel
            onEnviando={setSending}
            onEntrar={() => irPara("entrar")}
            onEnviado={setLinkSent}
          />
        )}
        {painel === "redefinir" && (
          <ResetPanel
            token={tokenDoLink}
            onEnviando={setSending}
            onRedefiniu={() => { setPanel("entrar"); setPasswordChanged(true) }}
            onRecuperar={() => irPara("recuperar")}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}
