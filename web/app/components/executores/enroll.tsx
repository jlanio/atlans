"use client"

// Fluxo de enrollment (OTP de uso único, métodos de conexão e app desktop).
//
// PADRONIZAÇÃO, não reescrita: a lógica de OTP, os comandos por método/SO, o
// cache do instalador e o deep link do app permanecem EXATAMENTE como estavam.
// Só a apresentação foi alinhada ao contrato: movimento sob `motion-safe:` e
// foco visível (`ring-[3px] ring-ring/50`) nos toggles próprios.

import React, { useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { ponteDesktop } from "@/lib/desktop"
import { cn } from "@/lib/utils"
import { Button } from "@/app/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/app/components/ui/dialog"
import { formatLocal } from "@/lib/dayjs"
import { createToast } from "@/utils/createToast"
import { API_URL } from "@/utils/env"
import {
  TbCopy, TbCheck, TbAlertTriangle, TbDownload, TbExternalLink,
  TbClock,
  TbBrandWindows, TbBrandDocker, TbBrandPython, TbBolt,
} from "react-icons/tb"
import type { IExecutor } from "@/service/GisFlowService"
import type { IExecutorEnrollmentOtpResponse } from "@/service/types"
import { SelectCard } from "./dialogs"

// ── Endereços do enrollment ──────────────────────────────────────────────────
//
// Nenhum é fixo: o servidor devolve os dele junto com o OTP (`server_url`, o
// host dos executores; `public_url`, o site). Sem `server_url` (a instalação não
// configurou AGENTS_URL e não tem domínio para a convenção), os comandos levam
// este marcador, e a tela avisa que ele precisa ser trocado.

export const SERVIDOR_A_PREENCHER = "https://agents.SEU-DOMINIO"

export type RunMode = "app" | "quickstart" | "python" | "docker"
export type OsMode = "linux" | "windows"

// ── Cache do instalador Windows ──────────────────────────────────────────────
//
// Cache de modulo: os metadados do instalador Windows batem na API do GitHub.
// Buscar uma vez por sessao evita gastar rate limit cada vez que o passo
// "Conectar" e revisitado (o painel remonta ao navegar entre passos).
let _installerCache: Promise<{ versao: string; tamanho: number; url: string } | null> | null = null
export function fetchInstallerOnce() {
  if (!_installerCache) {
    _installerCache = GisFlowService.getDesktopInstaller()
      .then(res => (res.error || !res.data ? null : res.data))
      .catch(() => null)
  }
  return _installerCache
}

// ── "Conectar": método de conexão primeiro; a ativação se adapta a ele ───────
//
// A escolha do método vem ANTES de qualquer credencial. O app Windows leva o
// Executor ID e o OTP embutidos no deep link "Abrir no app" — não há por que
// exibir o OTP ali. Só os métodos manuais (Docker/Python/Quickstart) mostram o
// comando, que já traz o OTP embutido; o aviso de uso único acompanha o comando.

export function EnrollConnect({ otp }: {
  otp: IExecutorEnrollmentOtpResponse
}) {
  const servidor = otp.server_url || SERVIDOR_A_PREENCHER
  const site = otp.public_url || (typeof window !== "undefined" ? window.location.origin : "")
  // Pre-seleciona com base no SO do operador que abriu o dialog (best-effort);
  // operador pode trocar manualmente.
  const ehWindows = typeof navigator !== "undefined" && /Win/i.test(navigator.platform)
  const [osMode, setOsMode]   = useState<OsMode>(ehWindows ? "windows" : "linux")
  // "app" só é pré-selecionado quando a UI roda DENTRO do app desktop (onde o
  // "Abrir no app" resolve localmente). Num navegador comum — mesmo no Windows —
  // o padrão cai num método de credencial COPIÁVEL (quickstart): senão um admin
  // gerando o OTP para um operador remoto abriria a aba do app, que agora não
  // expõe o OTP, e ficaria sem nada a entregar. Ver a nota de `ehWindows` (é o
  // SO de quem gera, não o do operador — best-effort só para o toggle de OS).
  const [runMode, setRunMode] = useState<RunMode>(() => ponteDesktop() != null ? "app" : "quickstart")
  const [appInfo, setAppInfo] = useState<{ versao: string; tamanho: number; url: string } | null>(null)
  const [appIndisponivel, setAppIndisponivel] = useState(false)
  const [copied, setCopied]   = useState(false)

  // Metadados do instalador Windows — so quando a aba do app esta visivel.
  useEffect(() => {
    if (runMode !== "app" || appInfo || appIndisponivel) return
    fetchInstallerOnce().then(data => {
      // 404 e estado normal: nenhuma versao publicada ainda.
      if (!data) setAppIndisponivel(true)
      else setAppInfo(data)
    })
  }, [runMode, appInfo, appIndisponivel])

  // Python local: grava EXECUTOR_ID em ./executor/.env automaticamente.
  const pythonLinux = otp
    ? `python -m executor enroll \\\n    --executor-id=${otp.executor_id} \\\n    --otp=${otp.otp} \\\n    --server=${servidor} \\\n    --cert-dir=./certs`
    : ""
  const pythonWindows = otp
    ? `python -m executor enroll \`\n    --executor-id=${otp.executor_id} \`\n    --otp=${otp.otp} \`\n    --server=${servidor} \`\n    --cert-dir=.\\certs`
    : ""

  // Docker: bind mount r/w em executor/.env permite que o container grave
  // EXECUTOR_ID no .env do host (operador nao precisa editar manualmente).
  // - touch + chmod 666 (Linux): garante que o user do container (uid 1000)
  //   consiga escrever no .env bind-mountado (preserva owner do host).
  // - SSL_CERT_FILE = root cert da CA interna (cert do host dos executores e
  //   assinado pela step-ca privada e o trust store padrao do sistema nao
  //   confia nela).
  const dockerLinux = otp
    ? `touch executor/.env && chmod 666 executor/.env && docker compose -f docker-compose.executor.yml run --rm \\\n    --entrypoint "" \\\n    -v ~/atlans-root.crt:/atlans-root.crt:ro \\\n    -v "$(pwd)/executor/.env:/app/executor/.env" \\\n    -e SSL_CERT_FILE=/atlans-root.crt \\\n    -e REQUESTS_CA_BUNDLE=/atlans-root.crt \\\n    executor \\\n    python -m executor enroll \\\n        --executor-id=${otp.executor_id} \\\n        --otp=${otp.otp} \\\n        --server=${servidor} \\\n        --cert-dir=/data/certs`
    : ""
  // PowerShell:
  // - Sem chmod (Windows nao usa permissoes POSIX em bind mount; arquivo do
  //   host fica writeable por padrao para o user do container).
  // - New-Item -Force trunca conteudo; Test-Path + New-Item idempotente.
  // - ${HOME} e ${PWD} interpolados explicitamente. Usamos FORWARD SLASHES
  //   nos paths de mount: backslash + $HOME (= C:\Users\X) gera "C:\Users\X\foo"
  //   que tem multiplos ":" e confunde o parser do `-v host:container`. Docker
  //   Desktop aceita "C:/Users/X/foo:/path" sem ambiguidade.
  const dockerWindows = otp
    ? `if (-not (Test-Path executor/.env)) { New-Item -ItemType File -Path executor/.env | Out-Null }; \`\ndocker compose -f docker-compose.executor.yml run --rm \`\n    --entrypoint '""' \`\n    -v "\${HOME}/atlans-root.crt:/atlans-root.crt:ro" \`\n    -v "\${PWD}/executor/.env:/app/executor/.env" \`\n    -e SSL_CERT_FILE=/atlans-root.crt \`\n    -e REQUESTS_CA_BUNDLE=/atlans-root.crt \`\n    executor \`\n    python -m executor enroll \`\n        --executor-id=${otp.executor_id} \`\n        --otp=${otp.otp} \`\n        --server=${servidor} \`\n        --cert-dir=/data/certs`
    : ""

  // Quickstart: 1 linha que faz git clone + ca-bundle + build + enroll + up.
  // Operador novo nao precisa nada alem de docker + git instalados. Sem
  // `server_url`, o install.sh servido sai sem o host dos executores e pede a
  // flag: o comando ja a leva, com o marcador que o aviso manda trocar.
  const quickstartLinux = otp
    ? `curl -fsSL ${site}/executores/install | bash -s -- \\\n    --executor-id=${otp.executor_id} \\\n    --otp=${otp.otp}`
      + (otp.server_url ? "" : ` \\\n    --server=${servidor}`)
    : ""
  // Windows: instala via Git Bash ou WSL (install.sh e bash). O comando e o
  // mesmo do Linux, mas a UI orienta explicitamente onde colar — em PS puro,
  // `curl` e alias para Invoke-WebRequest (nao suporta -fsSL), `| bash` nao
  // existe, e `\` line continuation nao funciona.
  const quickstartWindows = quickstartLinux

  const enrollCommand = (() => {
    if (runMode === "quickstart") return osMode === "windows" ? quickstartWindows : quickstartLinux
    if (runMode === "docker")     return osMode === "windows" ? dockerWindows     : dockerLinux
    return osMode === "windows" ? pythonWindows : pythonLinux
  })()

  // Guarda o id do timer: sem isto, fechar o diálogo antes de 2s deixa o
  // setTimeout disparar setCopied num componente já desmontado. Limpamos ao
  // rearmar e no unmount.
  const timerCopiado = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  useEffect(() => () => clearTimeout(timerCopiado.current), [])

  function copyCmd() {
    navigator.clipboard.writeText(enrollCommand)
    setCopied(true)
    clearTimeout(timerCopiado.current)
    timerCopiado.current = setTimeout(() => setCopied(false), 2000)
  }

  const methods: { v: RunMode; icon: React.ReactNode; title: string; desc: string; badge?: string }[] = [
    { v: "app",        icon: <TbBrandWindows />, title: "App Windows", desc: "Instalador, sem Docker nem terminal.", badge: "Recomendado" },
    { v: "docker",     icon: <TbBrandDocker />,  title: "Docker",       desc: "Um comando, container isolado." },
    { v: "python",     icon: <TbBrandPython />,  title: "Python local", desc: "Python 3.12 com as deps." },
    { v: "quickstart", icon: <TbBolt />,         title: "Quickstart",   desc: "curl | bash — faz tudo sozinho." },
  ]

  return (
    <div className="flex flex-col gap-3 py-1">
      <p className="text-xs text-muted-foreground">Como o executor vai rodar — na sua máquina ou na do operador?</p>

      {!otp.server_url && (
        <div role="alert" className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-2 text-[11px]">
          <TbAlertTriangle className="mt-0.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
          <span>
            Este servidor não sabe o endereço do host dos executores (<code>AGENTS_URL</code>). Nos
            comandos abaixo, troque <code>{SERVIDOR_A_PREENCHER}</code> por ele.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {methods.map(m => (
          <SelectCard
            key={m.v}
            active={runMode === m.v}
            onClick={() => setRunMode(m.v)}
            icon={m.icon}
            title={m.title}
            desc={m.desc}
            badge={m.badge}
          />
        ))}
      </div>

      {runMode === "app" ? (
        <div className="flex flex-col gap-2.5">
          <ol className="flex flex-col gap-2">
            <li className="flex items-start gap-2.5 text-xs text-muted-foreground">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/10 tabular-nums text-[11px] font-bold text-primary">1</span>
              <span>Baixe e instale o app (por usuário, sem admin).</span>
            </li>
            <li className="flex items-start gap-2.5 text-xs text-muted-foreground">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/10 tabular-nums text-[11px] font-bold text-primary">2</span>
              <span>Clique em <strong>Abrir no app</strong> — ele preenche e vincula este computador sozinho. Nada para copiar.</span>
            </li>
          </ol>

          {appIndisponivel ? (
            <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-2 text-[11px]">
              <TbAlertTriangle className="mt-0.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
              <div>
                <strong>Nenhuma versão publicada ainda.</strong> Use{" "}
                <strong>Python local</strong> ou <strong>Docker</strong> por enquanto.
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <Button asChild size="sm" className="gap-1.5 max-md:h-10">
                <a href={`${API_URL}/executores/install/windows`} download>
                  <TbDownload aria-hidden="true" /> Baixar app para Windows
                </a>
              </Button>
              {appInfo && (
                <span className="text-[10px] tabular-nums text-muted-foreground">
                  v{appInfo.versao} · {(appInfo.tamanho / 1048576).toFixed(0)} MB
                </span>
              )}
            </div>
          )}

          {/* Para quem JA instalou: abre o app com os dois valores preenchidos. */}
          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-2.5">
            <Button asChild size="sm" variant="outline" className="gap-1.5 max-md:h-10">
              <a href={`atlans://enroll?executor_id=${encodeURIComponent(otp.executor_id)}&otp=${encodeURIComponent(otp.otp)}&server=${encodeURIComponent(servidor)}`}>
                <TbExternalLink aria-hidden="true" /> Abrir no app
              </a>
            </Button>
            <span className="text-[10px] text-muted-foreground">
              Já tem o app instalado? Isso preenche o formulário para você.
            </span>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {/* O comando já embute o OTP — o aviso de uso único vem junto dele, não
              num passo separado. */}
          <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-2 text-[11px]">
            <TbClock className="mt-0.5 size-3.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
            <span>O comando abaixo já traz o vínculo embutido — <strong>uso único</strong>, expira em {formatLocal(otp.expires_at)}. Se expirar, gere outro.</span>
          </div>

          {/* Toggle de SO do host */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">Sistema do host do executor</span>
            <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
              <button
                type="button"
                onClick={() => setOsMode("linux")}
                aria-pressed={osMode === "linux"}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium outline-none transition-colors",
                  "focus-visible:ring-[3px] focus-visible:ring-ring/50",
                  osMode === "linux" ? "bg-background text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground",
                )}
              >
                Linux / macOS
              </button>
              <button
                type="button"
                onClick={() => setOsMode("windows")}
                aria-pressed={osMode === "windows"}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium outline-none transition-colors",
                  "focus-visible:ring-[3px] focus-visible:ring-ring/50",
                  osMode === "windows" ? "bg-background text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground",
                )}
              >
                Windows
              </button>
            </div>
          </div>

          {/* Quickstart em Windows precisa de Git Bash/WSL */}
          {runMode === "quickstart" && osMode === "windows" && (
            <div className="flex gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-2 text-[11px]">
              <TbAlertTriangle className="mt-0.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
              <div>
                <strong>PowerShell NÃO suporta este comando.</strong> Abra <strong>Git Bash</strong>{" "}
                (vem com Git for Windows) ou um terminal <strong>WSL</strong> e cole lá. O instalador é
                um script bash que usa <code className="rounded bg-muted px-1 font-mono">curl</code>,{" "}
                <code className="rounded bg-muted px-1 font-mono">|</code> e{" "}
                <code className="rounded bg-muted px-1 font-mono">\</code> como continuação de linha.
              </div>
            </div>
          )}

          {/* Bloco de comando */}
          <div className="flex items-start gap-2">
            {/* `whitespace-pre-wrap break-all`: preserva quebras/indentação E
                quebra linhas longas (o comando Docker passa de 680px) para caber
                na largura do modal, em vez de recortar. O botão Copiar entrega o
                comando exato, então a quebra visual não atrapalha. */}
            <pre className="min-w-0 flex-1 whitespace-pre-wrap break-all rounded-lg border border-border bg-muted/60 px-3 py-2.5 font-mono text-[11px] leading-relaxed">
              {enrollCommand}
            </pre>
            <Button
              size="icon"
              variant="outline"
              className="shrink-0 max-md:size-10"
              onClick={copyCmd}
              title="Copiar comando"
              aria-label="Copiar comando"
            >
              {copied ? <TbCheck className="text-green-500" aria-hidden="true" /> : <TbCopy aria-hidden="true" />}
            </Button>
          </div>

          {/* Pre-requisitos por metodo */}
          {runMode === "quickstart" && osMode === "linux" && (
            <p className="text-[10px] text-muted-foreground">
              Pré-requisitos: <code className="rounded bg-muted px-1 font-mono">docker</code>,{" "}
              <code className="rounded bg-muted px-1 font-mono">docker compose</code>,{" "}
              <code className="rounded bg-muted px-1 font-mono">git</code>,{" "}
              <code className="rounded bg-muted px-1 font-mono">curl</code>. Tudo o mais (root cert,
              clone do repo, build, enroll, up) é automático.
            </p>
          )}
          {runMode === "docker" && (
            <p className="text-[10px] text-muted-foreground">
              Pré-requisito: root cert da CA interna em{" "}
              <code className="rounded bg-muted px-1 font-mono">
                {osMode === "windows" ? "${HOME}/atlans-root.crt" : "~/atlans-root.crt"}
              </code>.{" "}
              {osMode === "windows" ? (
                <>Rode em <strong>PowerShell</strong> (5.1+ ou 7+). Use o <strong>Quickstart</strong> se não tem o cert.</>
              ) : (
                <>Use o <strong>Quickstart</strong> se não tem.</>
              )}
            </p>
          )}
          {runMode === "python" && (
            <p className="text-[10px] text-muted-foreground">
              Pré-requisito: Python 3.12 com deps do executor instaladas
              (<code className="rounded bg-muted px-1 font-mono">pip install -r requirements.txt</code>).{" "}
              {osMode === "windows" && (
                <>Rode em <strong>PowerShell</strong> — o comando usa backtick (<code className="rounded bg-muted px-1 font-mono">`</code>) como continuação.</>
              )}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Dialog de geração de OTP (executores já existentes) ──────────────────────

interface EnrollmentOtpDialogProps {
  agentId: string
  agentStatus: IExecutor["status"]
  /**
   * Elemento que dispara a abertura — pode ser DropdownMenuItem ou Button.
   * Use onSelect={e => e.preventDefault()} em DropdownMenuItem para evitar
   * que o menu feche prematuramente.
   */
  trigger: React.ReactNode
}

export function EnrollmentOtpDialog({ agentId, agentStatus, trigger }: EnrollmentOtpDialogProps) {
  const [open, setOpen]                   = useState(false)
  const [loading, setLoading]             = useState(false)
  const [otp, setOtp]                     = useState<IExecutorEnrollmentOtpResponse | null>(null)
  const [confirmActive, setConfirmActive] = useState(false)

  const isActive = agentStatus === "active"

  function handleClose(val: boolean) {
    if (!val) {
      // Limpa o OTP da memoria ao fechar — defesa em profundidade.
      setOtp(null)
      setConfirmActive(false)
    }
    setOpen(val)
  }

  async function generate() {
    setLoading(true)
    const res = await GisFlowService.generateEnrollmentOtp(agentId)
    setLoading(false)
    if (res.error || !res.data) {
      createToast.error("Erro ao gerar OTP.", res.error?.message)
      return
    }
    setOtp(res.data)
    setConfirmActive(false)
  }

  function onTriggerOpen() {
    setOpen(true)
    // Se status='active', exibe a tela de confirmacao antes de gerar.
    // Caso contrario, gera direto.
    if (isActive) {
      setConfirmActive(true)
    } else {
      generate()
    }
  }

  // Wrap trigger to intercept open
  const wrappedTrigger = (
    <span
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        onTriggerOpen()
      }}
    >
      {trigger}
    </span>
  )

  const title = otp ? "Conectar o executor" : "Gerar OTP de enrollment"
  const desc = otp
    ? "Escolha como o operador vai rodá-lo — o comando ou o app já trazem o vínculo."
    : "OTP de uso único válido por 24h. Entregue ao operador via canal seguro."

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger asChild>{wrappedTrigger}</DialogTrigger>

      <DialogContent>
        <DialogHeader className="pr-6">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{desc}</DialogDescription>
        </DialogHeader>

        {/* ── Confirmação para executores 'active' ─────────────────────────── */}
        {confirmActive && !otp && (
          <div className="flex flex-col gap-3 py-2">
            <div className="flex gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
              <TbAlertTriangle className="mt-0.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
              <div>
                <p className="font-medium">Este executor está ativo.</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Gerar um OTP novo permite re-enrollar este executor. Quando o operador rodar o
                  enrollment, o cert mTLS atual será substituído e a conexão WebSocket será derrubada.
                </p>
              </div>
            </div>
            <DialogFooter className="border-t border-border pt-4">
              <Button variant="outline" onClick={() => handleClose(false)}>Cancelar</Button>
              <Button onClick={generate} disabled={loading}>
                {loading ? "Gerando…" : "Gerar mesmo assim"}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* ── Loading ──────────────────────────────────────────────────────── */}
        {!confirmActive && !otp && loading && (
          <div className="py-10 text-center text-sm text-muted-foreground">Gerando OTP…</div>
        )}

        {/* ── Vínculo gerado: método de conexão direto (sem passo de OTP) ───── */}
        {otp && (
          <>
            {/* `min-w-0`: filho do grid do DialogContent. Sem isto, um conteúdo largo
                (o comando Docker) força a largura do grid acima do `max-w-lg` e
                estoura/recorta o modal em vez de caber. */}
            <div className="min-w-0 motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-200">
              <EnrollConnect otp={otp} />
            </div>
            <DialogFooter className="border-t border-border pt-4">
              <Button onClick={() => handleClose(false)}>Concluir</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
