// desktop/src/renderer/components/Onboarding.tsx
//
// Vincular este computador a um executor, sem terminal.
//
// Substitui o wizard `python -m executor setup`, que depende de `input()` e por
// isso nao roda sob o app. Antes desta tela, quem instalasse o app e nao
// tivesse enrollment via apenas a mensagem de erro do executor mandando rodar
// um comando — em um terminal que o instalador nao pressupoe que exista.
import { useEffect, useState } from 'react'
import { TbCircleCheck, TbDeviceDesktop, TbKey, TbLoader2 } from 'react-icons/tb'
import type { EstadoConfiguracao } from '../../main/state/config.js'
import type { ResultadoEnroll } from '../../main/python/enroll.js'
import type { PedidoDeepLink } from '../../main/deeplink.js'
import { Alerta } from './Alerta.js'
import { Button } from './ui/button.js'
import { Input } from './ui/input.js'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card.js'
import { SERVIDOR } from '../../shared/servidor.js'
import { cn } from '../lib/utils.js'

/** Traduz o `codigo` do Python para algo que diga o que FAZER. */
const REMEDIO: Record<string, string> = {
  otp_ausente: 'O OTP não chegou ao processo de enrollment. Tente novamente.',
  executor_id_ausente: 'Informe o ID do executor, copiado do painel web.',
  enroll_recusado: 'O servidor recusou o enrollment. Confira se o OTP não expirou (validade de 24 h, uso único) e se o ID do executor está correto.',
  signing_key_conflict: 'O certificado foi emitido, mas a chave de assinatura deste servidor não confere com a já fixada nesta máquina. Isso costuma indicar que o executor foi enrolado antes contra outro servidor — apague a pasta de certificados e refaça.',
  saida_invalida: 'O enrollment terminou de forma inesperada. O log abaixo tem o detalhe.',
  timeout: 'O servidor não respondeu. Verifique o endereço e a conexão de rede.',
}

function Campo({
  rotulo, valor, aoMudar, placeholder, descricao, mono, tipo = 'text', desabilitado, invalido,
}: {
  rotulo: string
  valor: string
  aoMudar: (v: string) => void
  placeholder?: string
  descricao?: string
  mono?: boolean
  tipo?: string
  desabilitado?: boolean
  /** Marca o campo apontado pela falha do enrollment. */
  invalido?: boolean
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{rotulo}</span>
      {/* `ui/input.tsx` em vez de um `<input>` remontado à mão: era a terceira
          cópia das mesmas classes no app, e cada uma divergia num detalhe
          (aqui, um `shadow-xs` que o primitivo não tem e nenhum tratamento de
          `aria-invalid`). */}
      <Input
        type={tipo}
        value={valor}
        disabled={desabilitado}
        placeholder={placeholder}
        onChange={(e) => aoMudar(e.target.value)}
        spellCheck={false}
        autoComplete="off"
        aria-invalid={invalido || undefined}
        className={cn('select-text', mono && 'font-mono text-xs')}
      />
      {descricao && <span className="text-xs text-muted-foreground">{descricao}</span>}
    </label>
  )
}

export function Onboarding({
  config, aoConcluir,
}: {
  config: EstadoConfiguracao
  aoConcluir: () => void
}) {
  const [executorId, setExecutorId] = useState(config.executorId ?? '')
  const [otp, setOtp] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<ResultadoEnroll | null>(null)
  // Pedido vindo de `atlans://enroll?…`. Fica em espera até o usuário confirmar:
  // qualquer página web pode disparar um deep link, então vincular sozinho
  // entregaria esta máquina a quem escreveu a página.
  const [pedidoLink, setPedidoLink] = useState<PedidoDeepLink | null>(null)

  // O ID vem do painel web e nao muda; se ja estava no `.env` (enrollment
  // parcial, certificado apagado), o campo nasce preenchido.
  useEffect(() => {
    if (config.executorId) setExecutorId(config.executorId)
  }, [config.executorId])

  // Deep link: o que chegou antes de montar (invoke) e o que chega depois (push).
  useEffect(() => {
    void window.atlas.deepLinkPendente().then((p) => { if (p) setPedidoLink(p) })
    return window.atlas.aoReceberDeepLink(setPedidoLink)
  }, [])

  const podeEnviar = executorId.trim() && otp.trim() && !enviando

  async function enviar(e: React.FormEvent) {
    e.preventDefault()
    if (!podeEnviar) return
    setEnviando(true)
    setResultado(null)
    try {
      const r = await window.atlas.enrolar({ executorId: executorId.trim(), otp: otp.trim() })
      setResultado(r)
      if (r.ok) {
        setOtp('')      // uso único: manter na tela só arrisca reenvio
        aoConcluir()
      }
    } finally {
      setEnviando(false)
    }
  }

  const soFaltaCert = config.falta === 'enrollment'

  function aplicarPedido() {
    if (!pedidoLink) return
    setExecutorId(pedidoLink.executorId)
    setOtp(pedidoLink.otp)
    setPedidoLink(null)
  }

  return (
    <main className="flex w-full flex-1 justify-center overflow-y-auto">
      <div className="flex w-full max-w-2xl flex-col gap-6 px-8 py-12">
        <header className="flex flex-col gap-1.5">
          <h1 className="flex items-center gap-2.5 text-2xl font-semibold">
            {/* Um glifo no título dá à tela uma marca antes de qualquer texto
                ser lido — é a primeira coisa que alguém vê ao instalar. */}
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <TbDeviceDesktop size={20} />
            </span>
            Vincular este computador
          </h1>
          <p className="text-sm text-muted-foreground">
            {soFaltaCert
              ? 'O certificado deste executor não foi encontrado. Gere um OTP novo no painel web e refaça o enrollment.'
              : 'Para executar workflows nesta máquina, vincule-a a um executor cadastrado no Atlans Studio.'}
          </p>
        </header>

        <Card>
          <CardHeader className="px-6">
            <CardTitle className="text-base font-medium">Onde encontrar estes dados</CardTitle>
            <CardDescription>
              No Atlans Studio, abra <strong>Executores</strong>, crie ou selecione um executor e
              clique em <strong>Gerar OTP</strong>. O código é de uso único e vale por 24 horas.
            </CardDescription>
          </CardHeader>
        </Card>

        {pedidoLink && (
          <Card className="border-primary/50 bg-primary/5 py-4">
            <CardContent className="flex flex-col gap-3 px-6">
              <div className="flex flex-col gap-1.5">
                <p className="text-sm font-medium">Vincular este computador?</p>
                <p className="text-sm text-muted-foreground">
                  O navegador pediu para vincular este computador ao executor
                  abaixo. Confira o identificador antes de continuar — qualquer
                  página pode disparar este pedido.
                </p>
              </div>
              <div className="flex flex-col gap-1 rounded-md border bg-background/60 px-3 py-2 font-mono text-xs select-text">
                <span><span className="text-muted-foreground">servidor: </span>
                  <strong>{SERVIDOR}</strong></span>
                <span><span className="text-muted-foreground">executor: </span>
                  {pedidoLink.executorId}</span>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={aplicarPedido}>Preencher o formulário</Button>
                <Button size="sm" variant="ghost" onClick={() => setPedidoLink(null)}>
                  Ignorar
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <form onSubmit={enviar} className="flex flex-col gap-4">
          <Campo
            rotulo="ID do executor"
            valor={executorId}
            aoMudar={setExecutorId}
            placeholder="00000000-0000-0000-0000-000000000000"
            invalido={resultado?.ok === false && resultado.codigo === 'executor_id_ausente'}
            descricao="Identificador mostrado no painel, ao lado do nome do executor."
            desabilitado={enviando}
            mono
          />
          <Campo
            rotulo="OTP de enrollment"
            valor={otp}
            aoMudar={setOtp}
            tipo="password"
            placeholder="cole aqui o código gerado"
            invalido={resultado?.ok === false
              && (resultado.codigo === 'otp_ausente' || resultado.codigo === 'enroll_recusado')}
            descricao="Uso único, validade de 24 horas."
            desabilitado={enviando}
            mono
          />
          {/* O servidor não é campo: é fixo neste app (ver shared/servidor.ts).
              Continua VISÍVEL porque quem vincula a máquina tem o direito de
              saber a quem ela vai obedecer — só não é editável. */}
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">Servidor</span>
            <div className="flex h-9 items-center rounded-md border border-input bg-muted/40 px-3 font-mono text-xs text-muted-foreground select-text">
              {SERVIDOR}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={!podeEnviar}>
              {enviando
                ? <><TbLoader2 size={15} className="animate-spin" /> Vinculando…</>
                : <><TbKey size={15} /> Vincular computador</>}
            </Button>
            {enviando && (
              <span className="text-xs text-muted-foreground">
                Gerando as chaves e solicitando o certificado…
              </span>
            )}
          </div>
        </form>

        {/* A mensagem crua do Python acompanha o remédio: quando o genérico não
            basta, é ela que o suporte precisa ler. O `Alerta` traz o ícone e o
            `role="alert"` — este é o retorno de uma ação que a pessoa acabou de
            disparar, e ele nascia mudo para leitor de tela. */}
        {resultado && !resultado.ok && (
          <Alerta
            tom="erro"
            titulo="Não foi possível vincular."
            remedio={REMEDIO[resultado.codigo] ?? 'Falha no enrollment.'}
            bruto={resultado.erro}
          />
        )}

        {resultado?.ok && (
          <Card
            role="status"
            aria-live="polite"
            className="border-green-500/40 bg-green-500/5 py-4 animate-in fade-in-0 zoom-in-95 duration-300"
          >
            <CardContent className="flex items-start gap-2.5 px-6">
              <TbCircleCheck size={17} className="mt-0.5 shrink-0 text-green-500" aria-hidden="true" />
              <div className="flex min-w-0 flex-col gap-1.5">
                <p className="text-sm font-medium">Computador vinculado.</p>
                <p className="text-sm text-muted-foreground">
                  Certificado válido até {resultado.expires_at ?? '—'}. Iniciando o executor…
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  )
}
