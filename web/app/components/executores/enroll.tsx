"use client"

// Enrollment flow (single-use OTP, connection methods and desktop app).
//
// STANDARDIZATION, not a rewrite: the OTP logic, the commands per method/OS,
// the installer cache and the app deep link remain EXACTLY as they were.
// Only the presentation was aligned with the contract: motion under
// `motion-safe:` and visible focus (`ring-[3px] ring-ring/50`) on the custom toggles.

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

// ── Enrollment addresses ─────────────────────────────────────────────────────
//
// None is fixed: the server returns its own along with the OTP (`server_url`,
// the executors' host; `public_url`, the site). Without `server_url` (the
// installation didn't configure AGENTS_URL and has no domain for the
// convention), the commands carry this placeholder, and the screen warns that
// it must be replaced.

export const SERVER_PLACEHOLDER = "https://agents.SEU-DOMINIO"

export type RunMode = "app" | "quickstart" | "python" | "docker"
export type OsMode = "linux" | "windows"

// ── Windows installer cache ──────────────────────────────────────────────────
//
// Module cache: the Windows installer metadata hits the GitHub API.
// Fetching once per session avoids spending rate limit every time the
// "Conectar" step is revisited (the panel remounts when navigating between steps).
let _installerCache: Promise<{ versao: string; tamanho: number; url: string } | null> | null = null
export function fetchInstallerOnce() {
  if (!_installerCache) {
    _installerCache = GisFlowService.getDesktopInstaller()
      .then(res => (res.error || !res.data ? null : res.data))
      .catch(() => null)
  }
  return _installerCache
}

// ── "Conectar": connection method first; activation adapts to it ─────────────
//
// The method choice comes BEFORE any credential. The Windows app carries the
// Executor ID and the OTP embedded in the "Abrir no app" deep link — there is no
// reason to show the OTP there. Only the manual methods (Docker/Python/Quickstart)
// show the command, which already embeds the OTP; the single-use warning goes
// with the command.

export function EnrollConnect({ otp }: {
  otp: IExecutorEnrollmentOtpResponse
}) {
  const servidor = otp.server_url || SERVER_PLACEHOLDER
  const site = otp.public_url || (typeof window !== "undefined" ? window.location.origin : "")
  // Preselects based on the OS of the operator who opened the dialog (best-effort);
  // the operator can switch manually.
  const ehWindows = typeof navigator !== "undefined" && /Win/i.test(navigator.platform)
  const [osMode, setOsMode]   = useState<OsMode>(ehWindows ? "windows" : "linux")
  // "app" is only preselected when the UI runs INSIDE the desktop app (where
  // "Abrir no app" resolves locally). In a regular browser — even on Windows —
  // the default falls to a method with a COPYABLE credential (quickstart):
  // otherwise an admin generating the OTP for a remote operator would open the
  // app tab, which no longer exposes the OTP, and would have nothing to hand
  // over. See the note on `ehWindows` (it is the OS of whoever generates, not the
  // operator's — best-effort only for the OS toggle).
  const [runMode, setRunMode] = useState<RunMode>(() => ponteDesktop() != null ? "app" : "quickstart")
  const [appInfo, setAppInfo] = useState<{ versao: string; tamanho: number; url: string } | null>(null)
  const [appUnavailable, setAppUnavailable] = useState(false)
  const [copied, setCopied]   = useState(false)

  // Windows installer metadata — only when the app tab is visible.
  useEffect(() => {
    if (runMode !== "app" || appInfo || appUnavailable) return
    fetchInstallerOnce().then(data => {
      // 404 is a normal state: no version published yet.
      if (!data) setAppUnavailable(true)
      else setAppInfo(data)
    })
  }, [runMode, appInfo, appUnavailable])

  // Python local: grava EXECUTOR_ID em ./executor/.env automaticamente.
  const pythonLinux = otp
    ? `python -m executor enroll \\\n    --executor-id=${otp.executor_id} \\\n    --otp=${otp.otp} \\\n    --server=${servidor} \\\n    --cert-dir=./certs`
    : ""
  const pythonWindows = otp
    ? `python -m executor enroll \`\n    --executor-id=${otp.executor_id} \`\n    --otp=${otp.otp} \`\n    --server=${servidor} \`\n    --cert-dir=.\\certs`
    : ""

  // Docker: a r/w bind mount on executor/.env lets the container write
  // EXECUTOR_ID into the host's .env (the operator doesn't need to edit it manually).
  // - touch + chmod 666 (Linux): ensures the container user (uid 1000)
  //   can write to the bind-mounted .env (preserves the host owner).
  // - SSL_CERT_FILE = root cert of the internal CA (the executors' host cert is
  //   signed by the private step-ca and the system's default trust store
  //   doesn't trust it).
  const dockerLinux = otp
    ? `touch executor/.env && chmod 666 executor/.env && docker compose -f docker-compose.executor.yml run --rm \\\n    --entrypoint "" \\\n    -v ~/atlans-root.crt:/atlans-root.crt:ro \\\n    -v "$(pwd)/executor/.env:/app/executor/.env" \\\n    -e SSL_CERT_FILE=/atlans-root.crt \\\n    -e REQUESTS_CA_BUNDLE=/atlans-root.crt \\\n    executor \\\n    python -m executor enroll \\\n        --executor-id=${otp.executor_id} \\\n        --otp=${otp.otp} \\\n        --server=${servidor} \\\n        --cert-dir=/data/certs`
    : ""
  // PowerShell:
  // - No chmod (Windows doesn't use POSIX permissions on bind mounts; the host
  //   file is writable by default for the container user).
  // - New-Item -Force truncates content; Test-Path + New-Item is idempotent.
  // - ${HOME} and ${PWD} interpolated explicitly. We use FORWARD SLASHES
  //   in the mount paths: backslash + $HOME (= C:\Users\X) produces "C:\Users\X\foo"
  //   which has multiple ":" and confuses the parser of `-v host:container`. Docker
  //   Desktop accepts "C:/Users/X/foo:/path" without ambiguity.
  const dockerWindows = otp
    ? `if (-not (Test-Path executor/.env)) { New-Item -ItemType File -Path executor/.env | Out-Null }; \`\ndocker compose -f docker-compose.executor.yml run --rm \`\n    --entrypoint '""' \`\n    -v "\${HOME}/atlans-root.crt:/atlans-root.crt:ro" \`\n    -v "\${PWD}/executor/.env:/app/executor/.env" \`\n    -e SSL_CERT_FILE=/atlans-root.crt \`\n    -e REQUESTS_CA_BUNDLE=/atlans-root.crt \`\n    executor \`\n    python -m executor enroll \`\n        --executor-id=${otp.executor_id} \`\n        --otp=${otp.otp} \`\n        --server=${servidor} \`\n        --cert-dir=/data/certs`
    : ""

  // Quickstart: 1 line that does git clone + ca-bundle + build + enroll + up.
  // A new operator needs nothing beyond docker + git installed. Without
  // `server_url`, the served install.sh comes without the executors' host and
  // asks for the flag: the command already carries it, with the placeholder the
  // warning says to replace.
  const quickstartLinux = otp
    ? `curl -fsSL ${site}/executores/install | bash -s -- \\\n    --executor-id=${otp.executor_id} \\\n    --otp=${otp.otp}`
      + (otp.server_url ? "" : ` \\\n    --server=${servidor}`)
    : ""
  // Windows: installs via Git Bash or WSL (install.sh is bash). The command is
  // the same as Linux's, but the UI explicitly says where to paste it — in plain
  // PS, `curl` is an alias for Invoke-WebRequest (doesn't support -fsSL), `| bash`
  // doesn't exist, and `\` line continuation doesn't work.
  const quickstartWindows = quickstartLinux

  const enrollCommand = (() => {
    if (runMode === "quickstart") return osMode === "windows" ? quickstartWindows : quickstartLinux
    if (runMode === "docker")     return osMode === "windows" ? dockerWindows     : dockerLinux
    return osMode === "windows" ? pythonWindows : pythonLinux
  })()

  // Keeps the timer id: without this, closing the dialog before 2s lets the
  // setTimeout fire setCopied on an already unmounted component. We clear it on
  // rearm and on unmount.
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  useEffect(() => () => clearTimeout(copiedTimer.current), [])

  function copyCmd() {
    navigator.clipboard.writeText(enrollCommand)
    setCopied(true)
    clearTimeout(copiedTimer.current)
    copiedTimer.current = setTimeout(() => setCopied(false), 2000)
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
            comandos abaixo, troque <code>{SERVER_PLACEHOLDER}</code> por ele.
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

          {appUnavailable ? (
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

          {/* For whoever has ALREADY installed: opens the app with both values filled in. */}
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
          {/* The command already embeds the OTP — the single-use warning comes with it,
              not in a separate step. */}
          <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-2 text-[11px]">
            <TbClock className="mt-0.5 size-3.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
            <span>O comando abaixo já traz o vínculo embutido — <strong>uso único</strong>, expira em {formatLocal(otp.expires_at)}. Se expirar, gere outro.</span>
          </div>

          {/* Host OS toggle */}
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

          {/* Command block */}
          <div className="flex items-start gap-2">
            {/* `whitespace-pre-wrap break-all`: preserves line breaks/indentation AND
                wraps long lines (the Docker command exceeds 680px) to fit the
                modal width, instead of clipping. The Copiar button delivers the
                exact command, so the visual wrapping does no harm. */}
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

          {/* Prerequisites per method */}
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

// ── OTP generation dialog (existing executors) ───────────────────────────────

interface EnrollmentOtpDialogProps {
  agentId: string
  agentStatus: IExecutor["status"]
  /**
   * Element that triggers opening — can be a DropdownMenuItem or a Button.
   * Use onSelect={e => e.preventDefault()} on DropdownMenuItem to prevent
   * the menu from closing prematurely.
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
      // Clears the OTP from memory on close — defense in depth.
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
    // If status='active', shows the confirmation screen before generating.
    // Otherwise, generates directly.
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

        {/* ── Confirmation for 'active' executors ──────────────────────────── */}
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

        {/* ── Link generated: connection method directly (no OTP step) ─────── */}
        {otp && (
          <>
            {/* `min-w-0`: child of the DialogContent grid. Without this, wide content
                (the Docker command) forces the grid width above `max-w-lg` and
                overflows/clips the modal instead of fitting. */}
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
