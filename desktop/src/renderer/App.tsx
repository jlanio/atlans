// desktop/src/renderer/App.tsx
//
// App shell: its own title bar, side navigation and the active tab's area —
// the same skeleton as Atlans Studio (.interface-design/system.md).
//
// The change from tabs at the top: what applies on every screen left the
// Painel header and became window chrome — the start/stop control in the
// sidebar, the connection state in the footer StatusBar. Before, switching
// tabs hid precisely what you want to keep an eye on while reading the log.
import { useCallback, useEffect, useState } from 'react'
import {
  TbActivity, TbBolt, TbChartBar, TbCircleOff, TbCpu, TbHandStop, TbKey, TbLoader,
  TbPlayerPlayFilled, TbPlugConnected, TbServer, TbTrendingUp,
} from 'react-icons/tb'
import type { AppState } from '../main/state/store.js'
import type { ConfigState } from '../main/state/config.js'
import type { InfoApp } from '../shared/ipc.js'
import { Ajustes } from './components/Ajustes.js'
import { Alerta } from './components/Alerta.js'
import { Copiavel } from './components/Copiavel.js'
import { Execucoes } from './components/Execucoes.js'
import { GeoSync } from './components/GeoSync.js'
import { Logs } from './components/Logs.js'
import { MetricCard } from './components/MetricCard.js'
import { Onboarding } from './components/Onboarding.js'
import { Sidebar, type Tab } from './components/Sidebar.js'
import { StatusBadge } from './components/StatusBadge.js'
import { StatusBar } from './components/StatusBar.js'
import { TitleBar } from './components/TitleBar.js'
import { Button } from './components/ui/button.js'
import { Card, CardContent } from './components/ui/card.js'
import { Skeleton } from './components/ui/skeleton.js'
import { SERVIDOR } from '../shared/servidor.js'
import { duracao } from './lib/formato.js'
import { SnapshotContext } from './lib/snapshot.js'
import { useLog } from './lib/useLog.js'

const CONNECTION: Record<string, string> = {
  offline: 'Offline',
  connecting: 'Conectando',
  connected: 'Conectado',
  reconnecting: 'Reconectando',
  terminal: 'Recusado pelo servidor',
}

/** Actionable message per failure step — it is what `state: failed` carries. */
const REMEDY: Record<string, string> = {
  config: 'Este computador ainda não foi vinculado a um executor. Gere um OTP no painel web, em Executores, e conclua o enrollment.',
  enrollment: 'O certificado mTLS não foi encontrado. Refaça o enrollment com um OTP novo.',
  server_key: 'Não foi possível obter a chave de assinatura do servidor. Verifique a conexão de rede e o endereço configurado.',
  // The KeywordDetector reacts to the name `private_key` and captures the
  // literal next to it — which here is a Portuguese sentence, not a key. The
  // pragma must stay on the SAME line as the hit; above it the detector
  // ignores it.
  private_key: 'A chave privada do executor está ausente ou ilegível. Refazer o enrollment gera um par novo.', // pragma: allowlist secret
  revoked: 'O servidor não reconhece mais este executor — ele foi removido ou revogado. O certificado guardado aqui continua válido localmente, mas é inútil: só um enrollment novo devolve o executor ao ar.',
}

/** Steps whose fix is redoing the link, not trying again. */
const NEEDS_NEW_ENROLLMENT = new Set(['revoked', 'enrollment', 'private_key'])

const TITLES: Record<Tab, string> = {
  painel: 'Painel',
  execucoes: 'Execuções',
  geosync: 'GeoSync',
  ajustes: 'Ajustes',
}

/**
 * Window dedicated to the log — opened by `openLogWindow` in main.
 *
 * The route is the URL hash, not a router: there are TWO screens, and pulling
 * in a whole router for that would cost more in dependencies than it saves in
 * code.
 */
function isLogWindow(): boolean {
  return window.location.hash === '#log'
}

/** Only the log, full screen, with the app's title bar on top. */
function LogWindow() {
  // It does not even subscribe to the state: this window only shows the log,
  // and the log channel is independent of the state channel. `info` comes in
  // because it is static — only the logs folder path, for the footer
  // shortcut.
  const linhas = useLog()
  const [info, setInfo] = useState<InfoApp | null>(null)
  useEffect(() => { void window.atlas.info().then(setInfo) }, [])

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TitleBar titulo="Log — Atlans Executor" />
      <main className="flex min-h-0 flex-1 flex-col px-4 py-3">
        <Logs linhas={linhas} pastaDeLogs={info?.logDir} />
      </main>
    </div>
  )
}

export function App() {
  // Before any hook: the two screens have different lifecycles, and mounting
  // one of them conditionally inside a single component would break the hook
  // order.
  return isLogWindow() ? <LogWindow /> : <MainWindow />
}

function MainWindow() {
  const [estado, setAppState] = useState<AppState | null>(null)
  const [info, setInfo] = useState<InfoApp | null>(null)
  const [config, setConfig] = useState<ConfigState | null>(null)
  /**
   * Redoing the link — the only action in the window that is REALLY blocking.
   *
   * Main needs to stop the executor before deleting the PEMs (they may be
   * open), and only then returns the new configuration. The other lifecycle
   * actions return immediately and disable nothing: a global "busy" tied to
   * the `parar` promise left the whole window gray during the drain,
   * including the "Forçar" (force) buttons, which are the way out of it.
   */
  const [refazendo, setRedoing] = useState(false)
  const [aba, setTab] = useState<Tab>('painel')
  /**
   * Screens with unsaved changes.
   *
   * It does not block navigation — the two form screens stay mounted and
   * nothing is lost when switching tabs. What this feeds is the MARKER in the
   * sidebar: a permanent, discreet notice that does not interrupt.
   *
   * A confirmation dialog on every switch would be worse: it always interrupts
   * to protect against a loss that no longer happens.
   */
  const [pendencias, setPending] = useState<Partial<Record<Tab, boolean>>>({})
  // The SAVED GeoSync folder, for the footer shortcut. It comes from the screen
  // itself, which is what knows when the `.env` changed.
  const [pastaGeosync, setPastaGeosync] = useState<string | null>(null)

  const markPending = useCallback((tela: Tab, pendente: boolean) => {
    setPending((atual) => (
      Boolean(atual[tela]) === pendente ? atual : { ...atual, [tela]: pendente }
    ))
  }, [])

  // Stable on purpose: they are props of memoized screens, and a new closure on
  // every render (that is, every second) would get through `memo` and also
  // make the `useEffect([sujo, aoMudarPendencia])` of both re-run with
  // nothing having changed.
  const geosyncPending = useCallback(
    (p: boolean) => markPending('geosync', p), [markPending],
  )
  const settingsPending = useCallback(
    (p: boolean) => markPending('ajustes', p), [markPending],
  )

  const reloadConfig = useCallback(() => {
    void window.atlas.configuracao().then(setConfig)
  }, [])

  useEffect(() => {
    void window.atlas.estado().then(setAppState)
    void window.atlas.info().then(setInfo)
    reloadConfig()
    // The unsubscribe returned by the preload must run in the cleanup, otherwise
    // each remount accumulates an IPC listener.
    return window.atlas.aoAtualizarEstado(setAppState)
  }, [reloadConfig])

  // A failure in `config`/`enrollment` means the `.env` or the certificates
  // changed from outside (folder deleted, cert expired and removed). Re-reading
  // takes the user back to the form instead of leaving them on a panel that
  // does not work.
  useEffect(() => {
    if (estado?.passoFase === 'config' || estado?.passoFase === 'enrollment') {
      reloadConfig()
    }
  }, [estado?.passoFase, reloadConfig])

  const refazerEnrollment = useCallback(async () => {
    setRedoing(true)
    try { setConfig(await window.atlas.refazerEnrollment()) }
    finally { setRedoing(false) }
  }, [])

  // The title bar belongs to the app (the window uses `frame: false`), so it
  // must wrap ALL states — including the loading one, otherwise the window
  // opens with no way to close it.
  if (!estado || !config) {
    return (
      <Frame>
        {/* Skeleton shaped like what is coming: the sidebar and the four cards
            of the Painel. A centered sentence says neither where the content
            will appear nor how much of it is coming — and it vanishes
            suddenly, in a jump. */}
        <div className="flex min-h-0 flex-1" aria-busy="true" aria-label="Carregando o estado do executor">
          <div className="flex w-56 shrink-0 flex-col gap-2 border-r border-sidebar-border bg-sidebar p-3">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
          <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-6 py-5">
            <Skeleton className="h-7 w-40" />
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {[0, 1, 2].map((i) => <Skeleton key={i} className="h-28 w-full" />)}
            </div>
          </div>
        </div>
      </Frame>
    )
  }

  // Without enrollment there is no panel to show, and no sidebar either: it
  // would only navigate between empty screens. The link takes up the whole
  // window.
  if (!config.configurado) {
    return (
      <Frame>
        <Onboarding config={config} aoConcluir={reloadConfig} />
      </Frame>
    )
  }

  const snap = estado.snapshot

  return (
    // The snapshot goes down through context: as a prop, it re-rendered GeoSync
    // and Ajustes entirely every second. See lib/snapshot.ts.
    <SnapshotContext.Provider value={snap}>
      <Frame barra={<StatusBar estado={estado} info={info}
                            pastaGeosync={pastaGeosync}
                            aoAbrirAjustes={() => setTab('ajustes')} />}>
        <div className="flex min-h-0 flex-1">
          <Sidebar
            aba={aba}
            aoTrocar={setTab}
            pendencias={pendencias}
            estado={estado}
            aoIniciar={() => void window.atlas.iniciar()}
            aoParar={() => void window.atlas.parar()}
            aoForcar={() => void window.atlas.forcar()}
          />

          <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
            {/* `max-w-5xl` + `mx-auto`: maximized on a wide monitor, each
                label/value row of the summary spread ~730px and the pair no
                longer read as a pair — which is the whole job the row does.
                1024px matches the default window of 980; the web uses
                `max-w-6xl` in a less dense layout (Layout > Page container,
                system.md). */}
            <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-6 py-5">

              {/* ── Page header ───────────────────────────────────────────
                  Only the title and what is specific to the screen: state and
                  lifecycle actions now live in the sidebar, and repeating
                  them here would cost height without saying anything new. */}
              <header className="flex min-h-8 items-center justify-between gap-4">
                <h1 className="text-lg font-semibold">{TITLES[aba]}</h1>
                {aba === 'painel' && estado.hello && (
                  <div className="flex items-center gap-3">
                    <Copiavel
                      valor={estado.hello.executor_id}
                      rotulo="ID do executor"
                      exibir={`${estado.hello.executor_id.slice(0, 8)}…`}
                    />
                    {/* The `title` lives on the SPAN, not on the button: the Button
                        base carries `disabled:pointer-events-none`, and without
                        hit-testing Chromium never shows a native tooltip — the
                        explanation only existed in the state where it could
                        not be read. */}
                    <span
                      className="inline-flex"
                      title={
                        snap?.conn_state === 'connected'
                          ? 'Já conectado ao servidor'
                          : estado.supervisor !== 'running'
                            ? 'O executor não está rodando'
                            : 'Interrompe a espera e tenta reconectar agora'
                      }
                    >
                      <Button size="sm" variant="secondary"
                              disabled={estado.supervisor !== 'running'
                                        || snap?.conn_state === 'connected'}
                              onClick={() => void window.atlas.comando('reconnect')}>
                        <TbPlugConnected size={15} /> Reconectar
                      </Button>
                    </span>
                  </div>
                )}
              </header>

              {/* ── Notices ───────────────────────────────────────────────
                  They apply on any tab: a boot failure or a drain in
                  progress matter as much while looking at the log as at the
                  panel. */}
              {estado.supervisor === 'failed' && (
                <Alerta
                  tom="erro"
                  titulo="O executor não está rodando."
                  remedio={estado.passoFase ? REMEDY[estado.passoFase] : undefined}
                  bruto={estado.detalheFase ?? estado.detalheSupervisor}
                >
                  {estado.passoFase && NEEDS_NEW_ENROLLMENT.has(estado.passoFase) && (
                    <Button size="sm" disabled={refazendo}
                            title="Descarta o certificado desta máquina. A configuração e os artefatos são mantidos."
                            onClick={() => void refazerEnrollment()}>
                      <TbKey size={15} /> Refazer enrollment
                    </Button>
                  )}
                </Alerta>
              )}

              {/* During the drain the snapshots keep arriving: we can show
                  real progress instead of a blind spinner. */}
              {estado.fase === 'draining' && snap && (
                <Alerta
                  tom="aviso"
                  titulo={`Encerrando — ${snap.running_count} execução(ões) em andamento`}
                  remedio={`${snap.result_queue_size} resultado(s) ainda a confirmar. O executor espera os workflows terminarem para não perder trabalho.`}
                >
                  {/* NEVER disabled: it is the way out of a wait that can reach
                      150 s, and disabling it during the wait left the window
                      with no possible action. */}
                  <Button size="sm" variant="destructive"
                          onClick={() => void window.atlas.forcar()}>
                    <TbHandStop size={15} /> Forçar agora
                  </Button>
                </Alerta>
              )}

              {/* ── Tab content ─────────────────────────────────────────────
                  GeoSync and Ajustes stay MOUNTED all the time, just hidden.
                  They are the two screens with forms, and unmounting them on
                  a tab switch would throw away unsaved edits — no warning, no
                  undo. Hidden, the state survives: the person goes to the Log
                  to check something, comes back, and picks up where they left
                  off.

                  The others are read-only and may unmount. The distinction is
                  worth keeping: `Logs` mounts hundreds of nodes, and keeping it
                  alive in the background would be needlessly expensive. */}
              {/* `key={aba}` on the always-mounted screens would make them
                  remount (and lose the edits). The entrance goes on the
                  wrapper, which React recreates only when `hidden` changes
                  value — enough for the tab switch to stop being a hard cut.
                  See the prefers-reduced-motion block in index.css. */}
              <div hidden={aba !== 'geosync'}
                   className={aba === 'geosync' ? 'animate-in fade-in-0 slide-in-from-bottom-1 duration-200' : undefined}>
                <GeoSync
                  rodando={estado.supervisor === 'running'}
                  visivel={aba === 'geosync'}
                  aoMudarPendencia={geosyncPending}
                  aoMudarPasta={setPastaGeosync}
                />
              </div>
              <div hidden={aba !== 'ajustes'}
                   className={aba === 'ajustes' ? 'animate-in fade-in-0 slide-in-from-bottom-1 duration-200' : undefined}>
                <Ajustes
                  info={info} rodando={estado.supervisor === 'running'}
                  aoMudarPendencia={settingsPending}
                />
              </div>

              {aba === 'execucoes' && (
                <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-200">
                  <Execucoes snapshot={snap} jobs={estado.jobs} />
                </div>
              )}
              {aba === 'painel' && (
                <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-200">
                  <Painel
                    estado={estado} info={info}
                    aoIniciar={() => void window.atlas.iniciar()}
                  />
                </div>
              )}
            </div>
          </main>
        </div>
      </Frame>
    </SnapshotContext.Provider>
  )
}

// ── Painel ───────────────────────────────────────────────────────────────────

function Painel({
  estado, info, aoIniciar,
}: {
  estado: AppState
  info: InfoApp | null
  aoIniciar: () => void
}) {
  const snap = estado.snapshot

  // Executor stopped by the user's decision: zeroed metrics say nothing, and
  // the obvious action needs to be in view.
  if (estado.supervisor === 'stopped') {
    return (
      <Card className="py-10">
        <CardContent className="flex flex-col items-center gap-4 px-6 text-center">
          {/* A large, faded icon fills the void the metrics left and states
              the status before any text is read. */}
          <span className="flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground/60">
            <TbCircleOff size={28} />
          </span>
          <div className="flex flex-col gap-1.5">
            <p className="text-base font-medium">O executor está parado.</p>
            <p className="max-w-md text-sm text-muted-foreground">
              {estado.detalheSupervisor ??
                'Enquanto estiver parado, esta máquina não recebe execuções.'}
            </p>
          </div>
          <Button onClick={aoIniciar}>
            <TbPlayerPlayFilled size={15} /> Iniciar executor
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* `md` and not `lg`: Tailwind's breakpoints measure the WINDOW, and the
          default window is now 980px — at `lg` (1024px) the four cards would
          never sit side by side at the size the app opens with. */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard
          icone={TbChartBar} titulo="Execuções"
          valor={snap ? String(snap.total_ok + snap.total_error) : '—'}
          rodape={snap ? `${snap.total_ok} ok · ${snap.total_error} com erro` : undefined}
          // Red only when there IS an error: a permanently colored card stops
          // meaning anything.
          tom={snap && snap.total_error > 0 ? 'erro' : undefined}
        />
        <MetricCard
          icone={TbLoader} titulo="Em andamento"
          valor={snap ? String(snap.running_count) : '—'}
          rodape={snap ? `fila ${snap.queued}/${snap.max_queue}` : undefined}
          tom={snap && snap.running_count > 0 ? 'ativo' : undefined}
        />
        <MetricCard
          icone={TbTrendingUp} titulo="Vazão"
          valor={snap ? `${snap.throughput_per_min.toFixed(1)}/min` : '—'}
          rodape={snap ? `p50 ${duracao(snap.p50_duration_s)}` : undefined}
        />
        <MetricCard
          icone={TbCpu} titulo="Memória"
          valor={snap?.proc_rss_mb ? `${snap.proc_rss_mb.toFixed(0)} MB` : '—'}
          rodape={snap ? `${snap.proc_threads ?? '—'} threads` : undefined}
        />
      </section>

      {/* The only block the Painel repeats from the Execuções tab — it is what
          justifies looking at the Painel while something runs. */}
      {snap && snap.running.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            <TbActivity size={13} className="shrink-0" />
            Em execução
          </h2>
          {snap.running.map((j) => (
            <Card
              key={j.job_id}
              className="gap-0 px-3 py-3 animate-in fade-in-0 slide-in-from-left-2 duration-300"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex min-w-0 flex-col gap-0.5">
                  <span className="truncate font-mono text-xs">{j.run_id ?? j.job_id}</span>
                  <span className="text-xs text-muted-foreground">{j.node ?? 'iniciando…'}</span>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {j.nodes_done}/{j.nodes_total ?? '?'} nós
                  </span>
                  <span className="text-sm tabular-nums">{duracao(j.elapsed_s)}</span>
                </div>
              </div>
              {/* Without `nodes_total` (the executor has not reported the graph
                  yet) the bar was simply absent, and a just-accepted run was
                  indistinguishable from a stuck one. The indeterminate strip
                  says "there is work, I don't know how much yet" without
                  making up a number. */}
              <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-muted">
                {j.nodes_total ? (
                  <div className="h-full rounded-full bg-primary transition-[width] duration-500"
                       style={{ width: `${Math.min(100, (j.nodes_done / j.nodes_total) * 100)}%` }} />
                ) : (
                  <div className="h-full w-1/3 rounded-full bg-primary/60 animate-progresso-indeterminado" />
                )}
              </div>
            </Card>
          ))}
        </section>
      )}

      {/* ── Summary ───────────────────────────────────────────────────────
          It was twelve label/value pairs in a flat grid — a wall where
          nothing indicated that "Reconexões" (reconnections) and "PID" answer
          different questions. Grouped by subject, with an icon marking each
          block, the eye finds the group first and the row afterwards. */}
      {snap && (
        <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Grupo icone={TbPlugConnected} titulo="Conexão">
            <Linha rotulo="Estado">
              {/* `pulsando` has existed in StatusBadge forever and was never
                  passed. Only in the TRANSIENT states: a pulse on "Conectado"
                  would be permanent motion with nothing to say, and it is
                  precisely while connecting or reconnecting that the person
                  needs to see something is still happening. */}
              <StatusBadge
                status={snap.conn_state}
                rotulo={CONNECTION[snap.conn_state] ?? snap.conn_state}
                pulsando={snap.conn_state === 'connecting' || snap.conn_state === 'reconnecting'}
              />
            </Linha>
            <Linha rotulo="Conectado há">{duracao(snap.conn_since_s)}</Linha>
            {/* When reconnecting, the time until the next attempt is the only
                information that keeps the user from repeatedly clicking
                Reconectar (reconnect). */}
            {snap.conn_state === 'reconnecting' && snap.next_retry_in_s != null && (
              <Linha rotulo="Nova tentativa">{Math.ceil(snap.next_retry_in_s)}s</Linha>
            )}
            <Linha rotulo="Reconexões">{snap.reconnects}</Linha>
          </Grupo>

          <Grupo icone={TbBolt} titulo="Trabalho">
            <Linha rotulo="No ar há">{duracao(snap.uptime_s)}</Linha>
            <Linha rotulo="Workers">{snap.max_concurrent}</Linha>
            <Linha rotulo="Nós executados">{snap.nodes_executed_total.toLocaleString('pt-BR')}</Linha>
            <Linha rotulo="A confirmar">{snap.result_queue_size + snap.outbox_pending}</Linha>
          </Grupo>

          <Grupo icone={TbServer} titulo="Sistema">
            <Linha rotulo="Servidor">
              <span className="truncate font-mono" title={SERVIDOR}>
                {SERVIDOR.replace(/^wss?:\/\//, '')}
              </span>
            </Linha>
            {estado.hello && <Linha rotulo="Python">{estado.hello.python}</Linha>}
            {estado.hello && <Linha rotulo="PID">{estado.hello.pid}</Linha>}
            {info && <Linha rotulo="Electron">{info.versaoElectron}</Linha>}
          </Grupo>
        </section>
      )}
    </div>
  )
}

/** Summary block: one subject, marked by an icon, with its rows. */
function Grupo({
  icone: Icone, titulo, children,
}: {
  icone: React.ComponentType<{ size?: number; className?: string }>
  titulo: string
  children: React.ReactNode
}) {
  return (
    // Card, and not a hand-repainted div: the copy had the same color and
    // curvature but lacked the `shadow-xs` that defines elevation Level 1 — a
    // level that system.md's table does not have. Card's tailwind-merge
    // resolves py-5→py-3 and gap-4→gap-2 on its own.
    <Card className="gap-2 px-4 py-3">
      <span className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        <Icone size={13} className="shrink-0" />{titulo}
      </span>
      <div className="flex flex-col gap-1 text-xs">{children}</div>
    </Card>
  )
}

function Linha({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3">
      <span className="shrink-0 text-muted-foreground">{rotulo}</span>
      <span className="min-w-0 truncate text-right tabular-nums">{children}</span>
    </div>
  )
}

// ── Shell pieces ─────────────────────────────────────────────────────────────

/**
 * Own title bar + content + status bar — the window has no system frame
 * (`frame: false` in windows.ts).
 *
 * The status bar is optional because on the loading and link screens there is
 * no executor to report anything about.
 */
function Frame({ children, barra }: { children: React.ReactNode; barra?: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TitleBar />
      {children}
      {barra}
    </div>
  )
}
