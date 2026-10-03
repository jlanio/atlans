// desktop/src/renderer/components/Onboarding.tsx
//
// Linking this computer to an executor, without a terminal.
//
// Replaces the `python -m executor setup` wizard, which depends on `input()` and
// therefore does not run under the app. Before this screen, anyone who installed
// the app without an enrollment saw only the executor's error message telling
// them to run a command — in a terminal the installer does not assume exists.
import { useEffect, useState } from 'react'
import { TbCircleCheck, TbDeviceDesktop, TbKey, TbLoader2 } from 'react-icons/tb'
import type { ConfigState } from '../../main/state/config.js'
import type { EnrollResult } from '../../main/python/enroll.js'
import type { DeepLinkRequest } from '../../main/deeplink.js'
import { Alerta } from './Alerta.js'
import { Button } from './ui/button.js'
import { Input } from './ui/input.js'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card.js'
import { SERVIDOR } from '../../shared/servidor.js'
import { cn } from '../lib/utils.js'

/** Translates the Python `codigo` into something that says what to DO. */
const REMEDY: Record<string, string> = {
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
  /** Marks the field pointed to by the enrollment failure. */
  invalido?: boolean
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{rotulo}</span>
      {/* `ui/input.tsx` instead of an `<input>` rebuilt by hand: it was the
          third copy of the same classes in the app, and each one diverged in
          a detail (here, a `shadow-xs` the primitive does not have and no
          handling of `aria-invalid`). */}
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
  config: ConfigState
  aoConcluir: () => void
}) {
  const [executorId, setExecutorId] = useState(config.executorId ?? '')
  const [otp, setOtp] = useState('')
  const [enviando, setSending] = useState(false)
  const [resultado, setResult] = useState<EnrollResult | null>(null)
  // Request coming from `atlans://enroll?…`. It stays pending until the user
  // confirms: any web page can fire a deep link, so linking on its own would
  // hand this machine over to whoever wrote the page.
  const [linkRequest, setLinkRequest] = useState<DeepLinkRequest | null>(null)

  // The ID comes from the web dashboard and does not change; if it was already in
  // `.env` (partial enrollment, deleted certificate), the field starts filled in.
  useEffect(() => {
    if (config.executorId) setExecutorId(config.executorId)
  }, [config.executorId])

  // Deep link: what arrived before mounting (invoke) and what arrives after (push).
  useEffect(() => {
    void window.atlas.deepLinkPendente().then((p) => { if (p) setLinkRequest(p) })
    return window.atlas.aoReceberDeepLink(setLinkRequest)
  }, [])

  const podeEnviar = executorId.trim() && otp.trim() && !enviando

  async function enviar(e: React.FormEvent) {
    e.preventDefault()
    if (!podeEnviar) return
    setSending(true)
    setResult(null)
    try {
      const r = await window.atlas.enrolar({ executorId: executorId.trim(), otp: otp.trim() })
      setResult(r)
      if (r.ok) {
        setOtp('')      // single use: keeping it on screen only risks a resubmission
        aoConcluir()
      }
    } finally {
      setSending(false)
    }
  }

  const onlyCertMissing = config.falta === 'enrollment'

  function applyRequest() {
    if (!linkRequest) return
    setExecutorId(linkRequest.executorId)
    setOtp(linkRequest.otp)
    setLinkRequest(null)
  }

  return (
    <main className="flex w-full flex-1 justify-center overflow-y-auto">
      <div className="flex w-full max-w-2xl flex-col gap-6 px-8 py-12">
        <header className="flex flex-col gap-1.5">
          <h1 className="flex items-center gap-2.5 text-2xl font-semibold">
            {/* A glyph in the title gives the screen a mark before any text is
                read — it is the first thing someone sees after installing. */}
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <TbDeviceDesktop size={20} />
            </span>
            Vincular este computador
          </h1>
          <p className="text-sm text-muted-foreground">
            {onlyCertMissing
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

        {linkRequest && (
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
                  {linkRequest.executorId}</span>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={applyRequest}>Preencher o formulário</Button>
                <Button size="sm" variant="ghost" onClick={() => setLinkRequest(null)}>
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
          {/* The server is not a field: it is fixed in this app (see
              shared/servidor.ts). It stays VISIBLE because whoever links the
              machine has the right to know whom it will obey — it is just not
              editable. */}
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

        {/* The raw Python message accompanies the remedy: when the generic one
            is not enough, it is what support needs to read. `Alerta` brings
            the icon and `role="alert"` — this is the result of an action the
            person just triggered, and it used to be born mute to screen
            readers. */}
        {resultado && !resultado.ok && (
          <Alerta
            tom="erro"
            titulo="Não foi possível vincular."
            remedio={REMEDY[resultado.codigo] ?? 'Falha no enrollment.'}
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
