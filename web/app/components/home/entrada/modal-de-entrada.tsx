"use client"

// web/app/components/home/entrada/modal-de-entrada.tsx
//
// A ENTRADA do site — login e cadastro — como um modal sobre o globo da Home,
// no tema dela (`home-portal`) e com o fundo levemente ofuscado (o globo
// continua à vista por trás). Substitui as telas /login e /register, que hoje
// só redirecionam para cá: a Home abre sem sessão e o primeiro envio à barra
// abre este modal; o login bem-sucedido o fecha, e a mensagem que ficou
// pendente vai sozinha (HomeView).
//
// CINCO painéis num só diálogo: Entrar, Criar conta, "Verifique seu e-mail",
// "Esqueceu a senha?" e "Nova senha". Os três últimos eram as páginas
// /verify-email, /forgot-password e /reset-password, do modelo antigo de
// página inteira, que hoje só redirecionam para cá — com elas foi embora a
// última tela de `AuthShell` deste fluxo. O caminho inteiro da conta acontece
// sem sair da Home: criar, ativar pelo link do e-mail, pedir o link da senha,
// voltar do e-mail e gravar a senha nova.
//
// FECHÁVEL — Esc, o X e o clique fora fecham, decisão do dono —, menos com um
// envio em voo: aí o X desabilita e Esc/clique fora são ignorados — o
// `bloqueado` do `DialogContent`.

import { useCallback, useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { GlifoDaMarca } from "@/app/components/sidebar/marca"
import { useCodigoFonte } from "@/app/components/share/codigo-fonte"
import { useNomeNaTela } from "@/app/components/share/nome-na-tela"
import { useTextos } from "@/app/components/home/i18n"
import type { ModoDeEntrada } from "@/lib/entrada"
import { FormularioDeEntrada } from "./formulario-de-entrada"
import { FormularioDeCadastro } from "./formulario-de-cadastro"
import { PainelVerificar, type EstadoDaVerificacao } from "./painel-verificar"
import { PainelRecuperar } from "./painel-recuperar"
import { PainelRedefinir } from "./painel-redefinir"

interface Props {
  /** O modal pedido; `null` = fechado. */
  modo: ModoDeEntrada | null
  /**
   * O token do link que trouxe a pessoa — o da redefinição de senha
   * (`?redefinir=1&token=…`) ou o da verificação (`?verificar=1&token=…`). É
   * um só porque os painéis são excludentes: quem chega por um não chega pelo
   * outro.
   */
  tokenDoLink?: string
  /** Há uma mensagem esperando o login (o primeiro envio): muda a frase de apoio. */
  comEnvioPendente?: boolean
  /** Fechar SEM entrar (Esc, X, clique fora). */
  onFechar: () => void
  /** O login deu certo — a sessão da aba já está atualizada (`signIn` sem redirect). */
  onEntrou: () => void
}

export default function ModalDeEntrada({
  modo, tokenDoLink, comEnvioPendente = false, onFechar, onEntrou,
}: Props) {
  const textos = useTextos()
  const codigoFonte = useCodigoFonte()
  const nomeNaTela = useNomeNaTela()
  const t = textos.entrada.modal
  const [painel, setPainel] = useState<ModoDeEntrada>(modo ?? "entrar")
  const [enviando, setEnviando] = useState(false)
  const [emailCadastrado, setEmailCadastrado] = useState("")
  // O pedido do link saiu: o mesmo painel troca de cara, e o cabeçalho com ele.
  const [linkEnviado, setLinkEnviado] = useState(false)
  // A senha acabou de ser trocada: o login ganha um aviso em vez de um toast,
  // que sumiria atrás do modal.
  const [senhaTrocada, setSenhaTrocada] = useState(false)
  // A conta acabou de ser ativada pelo link do e-mail — mesmo aviso, mesmo
  // motivo.
  const [emailVerificado, setEmailVerificado] = useState(false)
  // Em qual dos três estados o painel de verificação está (o GET do token
  // começa sozinho): o título e a frase de apoio do diálogo saem daqui.
  const [estadoDaVerificacao, setEstadoDaVerificacao] = useState<EstadoDaVerificacao>("sem-token")
  // O token do link vale UMA vez por modal, não uma por montagem do painel: ele
  // continua na URL depois de gasto, e sem esta marca voltar ao painel (pelo
  // 403 do login, ou pelo "Reenviar" de uma falha) repetiria o GET com um token
  // que já não vale.
  const [tokenGasto, setTokenGasto] = useState(false)
  // Reabrir noutro modo (Criar conta pelo sidebar depois de um Entrar) troca o
  // painel; fechado (`null`) nada muda.
  useEffect(() => {
    if (modo) setPainel(modo)
  }, [modo])

  // Estável de propósito: o painel a tem nas dependências do efeito que gasta
  // o token, e uma identidade nova a cada render o mandaria rodar de novo.
  const marcarTokenGasto = useCallback(() => setTokenGasto(true), [])

  function irPara(destino: ModoDeEntrada) {
    // Sair de um painel zera o que era dele: voltar ao "Esqueceu a senha?" tem
    // de pedir o e-mail de novo, e o login não pode guardar para sempre o aviso
    // de uma senha trocada (ou de um e-mail verificado) três painéis atrás.
    if (destino !== "recuperar") setLinkEnviado(false)
    if (destino !== "entrar") { setSenhaTrocada(false); setEmailVerificado(false) }
    if (destino !== "verificar") setEstadoDaVerificacao("sem-token")
    setPainel(destino)
  }

  const titulo =
    painel === "verificar" && estadoDaVerificacao === "verificando"
      ? t.tituloVerificando
      : painel === "verificar" && estadoDaVerificacao === "falhou"
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
            : estadoDaVerificacao === "verificando"
              ? t.descricoes.verificando
              : estadoDaVerificacao === "falhou"
                ? t.descricoes.verificacaoFalhou
                : t.descricoes.verificar

  return (
    <Dialog open={modo !== null} onOpenChange={(aberto) => { if (!aberto && !enviando) onFechar() }}>
      <DialogContent
        className="home-portal w-full max-w-[calc(100%-2rem)] gap-5 rounded-xl border-border bg-background p-6 text-foreground sm:max-w-sm"
        // O fundo levemente ofuscado: o globo continua visível por trás.
        overlayClassName="bg-black/40 backdrop-blur-[2px]"
        bloqueado={enviando}
        closeLabel={textos.comum.fechar}
        data-testid="modal-de-entrada"
        data-painel={painel}
      >
        <DialogHeader className="gap-3 text-left">
          <p className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <GlifoDaMarca /> {nomeNaTela}
            {/* AGPL §13: quem usa a instalação pela rede acha o código-fonte dela
                daqui, antes mesmo de entrar. Só quando a instalação o declara. */}
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
          <FormularioDeEntrada
            onEnviando={setEnviando}
            onEntrou={onEntrou}
            onCriarConta={() => irPara("cadastro")}
            onRecuperar={() => irPara("recuperar")}
            onVerificar={(email) => { if (email) setEmailCadastrado(email); irPara("verificar") }}
          />
        )}
        {painel === "cadastro" && (
          <FormularioDeCadastro
            onEnviando={setEnviando}
            onCadastrou={(email) => { setEmailCadastrado(email); irPara("verificar") }}
            onEntrar={() => irPara("entrar")}
          />
        )}
        {painel === "verificar" && (
          <PainelVerificar
            email={emailCadastrado}
            token={tokenGasto ? undefined : tokenDoLink}
            onEnviando={setEnviando}
            onEntrar={() => irPara("entrar")}
            onVerificou={() => { setPainel("entrar"); setEmailVerificado(true) }}
            onEstado={setEstadoDaVerificacao}
            onGastouToken={marcarTokenGasto}
          />
        )}
        {painel === "recuperar" && (
          <PainelRecuperar
            onEnviando={setEnviando}
            onEntrar={() => irPara("entrar")}
            onEnviado={setLinkEnviado}
          />
        )}
        {painel === "redefinir" && (
          <PainelRedefinir
            token={tokenDoLink}
            onEnviando={setEnviando}
            onRedefiniu={() => { setPainel("entrar"); setSenhaTrocada(true) }}
            onRecuperar={() => irPara("recuperar")}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}
