// desktop/src/renderer/components/GeoSync.tsx
//
// GeoSync settings — syncing local folders with the workspace Drive.
//
// Until now this existed only as variables in `.env`, edited by hand, with two
// pitfalls that fail SILENTLY:
//
//   1. `EXECUTOR_SYNC_DIRS` is comma-separated and Python splits it blindly.
//      A folder with a comma in its name becomes two nonexistent entries.
//   2. With more than one accessible workspace and `EXECUTOR_WORKSPACE_ID`
//      empty, the executor DISABLES GeoSync with a `logger.warning` and keeps
//      running normally (executor/main.py). Nothing in the UI indicated this.
//
// This screen exists to make both visible before saving.
import {
  memo, useCallback, useEffect, useMemo, useState,
  type ComponentType, type ReactNode,
} from 'react'
import {
  TbArrowsExchange, TbCloud, TbCloudCheck, TbCloudDownload, TbCloudUpload,
  TbCopy, TbDeviceDesktop, TbDownloadOff, TbFolder, TbFolderFilled, TbFolderOff,
  TbFolderOpen, TbRefresh, TbShieldLock, TbX,
} from 'react-icons/tb'
import { SYNC_INTERVAL, SYNC_DEFAULTS } from '../../shared/geosync.js'
import type { ConflictStrategy, SyncMode } from '../../shared/geosync.js'
import type { ConfigGeoSync, InvalidFolder } from '../../main/state/config.js'
import type { StatusResult, Workspace } from '../../main/python/status.js'
import { useSnapshot } from '../lib/snapshot.js'
import { BarraSalvar } from './BarraSalvar.js'
import { Alerta } from './Alerta.js'
import { Button } from './ui/button.js'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card.js'
import { cn } from '../lib/utils.js'

/**
 * One choice from the list. `etiqueta` highlights what changes in kind, not in
 * degree.
 *
 * `icone` holds the COMPONENT, not a ready-made element: the same option is
 * drawn at different sizes by the full list (18px) and by the segmented control
 * (14px), and an element with a built-in `size` would serve only one of them.
 */
interface Choice<T extends string> {
  v: T
  r: string
  d: ReactNode
  icone: ComponentType<{ size?: number; className?: string }>
  etiqueta?: string
}

/**
 * Locality: can the content leave this machine?
 *
 * This choice lived as a fourth option of "Direção" (direction), and that was a
 * category error: the other three answer WHERE the files go, and this one
 * answers WHETHER they leave. The symptom was visible in the code itself —
 * choosing "só catalogar" (catalog only) had to disable the conflict card, and
 * an option that invalidates a sibling card is not of the same nature as its
 * neighbors.
 *
 * Separated, the decision with legal consequences comes first and alone, and
 * the hierarchy of the screen now mirrors that of the code.
 */
type Localidade = 'sincronizar' | 'local'

const LOCALITIES: Array<Choice<Localidade>> = [
  {
    v: 'sincronizar',
    r: 'Sincronizar os arquivos',
    icone: TbCloud,
    d: 'O conteúdo vai e volta entre esta pasta e o Drive do workspace.',
  },
  {
    v: 'local',
    // Same label as the `localidade` field of the output nodes — and now the SAME
    // decision, not just the same name: `EXECUTOR_SYNC_MODE=catalog`, which this
    // option writes, is what the nodes read to know whether they may upload
    // (flow/utils/artifact_helpers.py::localidade_padrao).
    r: 'Manter apenas no executor',
    icone: TbShieldLock,
    etiqueta: 'LGPD',
    d: 'Nada sai desta máquina — nem esta pasta, nem o que os workflows gravarem. '
     + 'O servidor recebe só a ficha de cada arquivo.',
  },
]

/**
 * What stays and what leaves, in the chosen mode.
 *
 * The option descriptions were a four-line paragraph in 12px gray — the most
 * important information on the screen, in its least visible element. And
 * running text is bad precisely for the question people asked ("but then the
 * file goes WHERE?"): the answer is a mapping between things and places, and a
 * mapping reads better in columns than in prose.
 *
 * ⚠️ In sync mode the content depends on the DIRECTION, which is chosen in the
 * card below: in "Só baixar" (download only) nothing goes up, and a fixed panel
 * would be lying half the time. That is why `direcao` comes in here and the
 * text follows it — live, too, when the person changes the direction just
 * below.
 *
 * The two panels have different visual weight on purpose: the local one is
 * highlighted because it describes a consequence (the data does not leave, the
 * download does not exist); the sync one is neutral because it describes the
 * expected behavior.
 */
function ModePanel({
  local, direcao, pasta,
}: {
  local: boolean
  direcao: Exclude<SyncMode, 'catalog'>
  pasta: string | null
}) {
  const conteudo = local
    ? {
        fica: ['O arquivo inteiro', 'Na pasta configurada abaixo', 'Nada é movido nem copiado'],
        sai: ['Nome e formato', 'CRS e número de feições', 'Extensão geográfica'],
        alerta: 'sai' as const,
        nota: (
          <>
            <TbDownloadOff size={14} className="mt-px shrink-0" />
            <span>
              Sem download pelo Studio. Só workflows que rodarem{' '}
              <strong className="font-medium text-foreground">neste</strong> executor
              conseguem abrir estes arquivos. Nós que só funcionam enviando —{' '}
              <em>Publicar no Mapa</em> e o anexo automático do{' '}
              <em>Enviar E-mail</em> — passam a{' '}
              <strong className="font-medium text-foreground">falhar</strong>, com a
              explicação no log da execução.
            </span>
          </>
        ),
      }
    : direcao === 'upload'
      ? {
          fica: ['Os arquivos originais, na pasta', 'Nada é apagado daqui'],
          sai: ['O arquivo inteiro', 'Nome, formato e metadados'],
          alerta: undefined,
          nota: (
            <>
              <TbCloudDownload size={14} className="mt-px shrink-0" />
              <span>O que a equipe publicar no Drive <strong className="font-medium text-foreground">não</strong> desce para esta pasta.</span>
            </>
          ),
        }
      : direcao === 'download'
        ? {
            fica: ['Uma cópia do que está no Drive'],
            sai: ['Nada — esta máquina só recebe'],
            alerta: undefined,
            nota: (
              <>
                <TbCloudUpload size={14} className="mt-px shrink-0" />
                <span>O que você criar nesta pasta <strong className="font-medium text-foreground">não</strong> sobe para o Drive.</span>
              </>
            ),
          }
        : {
            fica: ['Os arquivos, espelhados com o Drive'],
            sai: ['O arquivo inteiro', 'Nome, formato e metadados'],
            alerta: undefined,
            nota: (
              <>
                <TbArrowsExchange size={14} className="mt-px shrink-0" />
                <span>Mudou dos dois lados? A regra de conflito, mais abaixo, decide qual versão fica.</span>
              </>
            ),
          }

  return (
    <div className={cn(
      // No margin of its own: the spacing belongs to the card container (gap-4).
      'flex flex-col gap-2.5 rounded-md border p-3',
      local ? 'border-primary/30 bg-primary/[0.04]' : 'bg-muted/30',
    )}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Coluna
          icone={<TbDeviceDesktop size={15} />}
          titulo="Fica nesta máquina"
          itens={conteudo.fica}
        />
        <Coluna
          icone={<TbCloudUpload size={15} />}
          titulo="Vai para o servidor"
          itens={conteudo.sai}
          // Only in local mode: without the highlight, the hasty reading is "something
          // goes up, so the file goes up". In sync, uploading the file is the
          // expected behavior, and highlighting it would be a false alarm.
          tom={conteudo.alerta === 'sai' ? 'atencao' : undefined}
        />
      </div>

      <div className={cn(
        'flex items-start gap-2 border-t pt-2.5 text-xs text-muted-foreground',
        local && 'border-primary/20',
      )}>
        {conteudo.nota}
      </div>

      {pasta && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <TbFolder size={14} className="shrink-0" />
          <span className="truncate font-mono select-text" title={pasta}>{pasta}</span>
        </div>
      )}
    </div>
  )
}

/**
 * COMPACT exclusive choice — a strip instead of a stack of cards.
 *
 * Direction and conflict used the same `Choices` as locality and took up six
 * tall blocks, competing in weight with the decision that governs them. Here
 * each group fits on one line, and the explanation appears only for the CHOSEN
 * option — which is the only one that describes what will actually happen. The
 * others remain reachable through the label and the icon.
 */
function Segmented<T extends string>({
  valor, opcoes, aoMudar,
}: {
  valor: T
  opcoes: Array<Choice<T>>
  aoMudar: (v: T) => void
}) {
  const escolhida = opcoes.find((o) => o.v === valor)

  return (
    <div className="flex flex-col gap-1.5">
      <div role="radiogroup" className="grid grid-cols-3 gap-1 rounded-md border bg-muted/40 p-1">
        {opcoes.map((o) => {
          const ativo = valor === o.v
          return (
            <button
              key={o.v}
              type="button"
              role="radio"
              aria-checked={ativo}
              onClick={() => aoMudar(o.v)}
              className={cn(
                'flex items-center justify-center gap-1.5 rounded px-2 py-1.5 text-xs transition-colors',
                'focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none',
                ativo
                  ? 'bg-background font-medium text-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <o.icone size={14} className={cn('shrink-0', ativo && 'text-primary')} />
              <span className="truncate">{o.r}</span>
            </button>
          )
        })}
      </div>
      {/* The description of the chosen one sits below, outside the strip: it
          would not fit inside, and without it the control would become three
          labels with no consequence. */}
      <span className="text-xs leading-relaxed text-muted-foreground">{escolhida?.d}</span>
    </div>
  )
}

/**
 * Subordinate block inside a card.
 *
 * Title smaller than the card's and separated by a rule: the hierarchy needs
 * to be visible, otherwise the card becomes a flat list of eight radio options
 * where nothing indicates which belong to which question.
 */
function Subsecao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-t pt-3">
      {/* Small uppercase label: it needs to mark the division without competing
          with the card title, which is the main decision. */}
      <span className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
        {titulo}
      </span>
      {children}
    </div>
  )
}

function Coluna({
  icone, titulo, itens, tom,
}: {
  icone: ReactNode
  titulo: string
  itens: string[]
  tom?: 'atencao'
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className={cn(
        'flex items-center gap-1.5 text-xs font-semibold',
        tom === 'atencao' ? 'text-warning' : 'text-foreground',
      )}>
        {icone}{titulo}
      </span>
      <ul className="flex flex-col gap-0.5">
        {itens.map((i) => (
          <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
            <span className="mt-1.5 size-1 shrink-0 rounded-full bg-muted-foreground/50" />
            {i}
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Transfer directions. Only apply when the content may leave. */
const MODES: Array<Choice<Exclude<SyncMode, 'catalog'>>> = [
  {
    v: 'upload',
    r: 'Só enviar',
    icone: TbCloudUpload,
    d: 'Esta máquina alimenta o Drive. O que você criar ou alterar na pasta '
     + 'sobe; o que a equipe publicar no Drive não desce.',
  },
  {
    v: 'download',
    r: 'Só baixar',
    icone: TbCloudDownload,
    d: 'O Drive alimenta esta máquina. O que a equipe publica desce para a '
     + 'pasta; o que você criar aqui fica só aqui.',
  },
  {
    v: 'bidirectional',
    r: 'Nos dois sentidos',
    icone: TbArrowsExchange,
    d: 'Pasta e Drive são mantidos iguais. É o modo usual quando os mesmos '
     + 'arquivos são editados aqui e no Studio.',
  },
]

const CONFLICTS: Array<Choice<ConflictStrategy>> = [
  {
    v: 'remote-wins',
    r: 'O Drive vence',
    icone: TbCloudCheck,
    d: 'A versão do servidor substitui a local, e a alteração feita aqui é '
     + 'perdida. Use quando o Studio é a fonte da verdade.',
  },
  {
    v: 'local-wins',
    r: 'Esta máquina vence',
    icone: TbDeviceDesktop,
    d: 'A versão daqui substitui a do Drive, e a alteração feita lá é perdida. '
     + 'Use quando é esta máquina que produz o dado.',
  },
  {
    v: 'keep-both',
    r: 'Manter as duas',
    icone: TbCopy,
    d: 'Nada é sobrescrito: a segunda versão entra com um sufixo no nome. '
     + 'Acumula duplicatas, mas nunca descarta trabalho.',
  },
]

/**
 * Last segment of the path — what the person calls the folder.
 *
 * Splits on `\` AND on `/`: the path comes from a Windows dialog, but a
 * hand-edited `.env` may have forward slashes, and in that case the "name"
 * would be the whole path.
 */
function folderName(caminho: string): string {
  const partes = caminho.split(/[\/]/).filter(Boolean)
  return partes[partes.length - 1] ?? caminho
}

/**
 * Where the sync stands now.
 *
 * The numbers come from the executor's MANIFEST, published at the end of each
 * cycle (`sync_inventory`). Hence "no executor" (on the executor), and not "no
 * servidor" (on the server): knowing the Drive total would require listing the
 * workspace on every tick — a network call that does not fit in a 1 Hz
 * snapshot. What is here is what this machine knows.
 *
 * The button exists because the scan is periodic: someone who just copied a
 * file into the folder should not have to wait for the interval to see the
 * effect.
 *
 * It is the ONLY part of this screen that changes every second, and that is
 * why it reads the snapshot from the context instead of receiving it as a
 * prop: that way the tick re-renders this card, and not the ten of the whole
 * screen. See lib/snapshot.ts.
 */
function SyncStatusCard() {
  const snapshot = useSnapshot()
  const [pedindo, setRequesting] = useState(false)
  const [retorno, setFeedback] = useState<string | null>(null)

  async function syncNow() {
    setRequesting(true)
    setFeedback(null)
    try {
      const ok = await window.atlas.comando('sync_now')
      setFeedback(ok ? 'Varredura solicitada.' : 'O executor não aceitou o comando.')
    } finally {
      setRequesting(false)
      // The message disappears on its own: it confirms a click, it is not state.
      setTimeout(() => setFeedback(null), 4000)
    }
  }

  // Executor stopped or still without the first tick: there is no status to report.
  if (!snapshot) return null

  const pendentes = snapshot.sync_pending
  const inTransit = snapshot.sync_current

  return (
    <Card>
      {/* `CardHeader` is a grid: the old `flex-row` did not make it flex, and
          the button dropped onto a whole row below the subtitle. `CardAction`
          is the slot the primitive reserves on the right. */}
      <CardHeader className="px-6">
        <CardTitle className="text-base font-medium">Situação</CardTitle>
        <CardDescription className="text-xs">
          A varredura roda a cada {SYNC_INTERVAL}s, e também quando um arquivo muda.
        </CardDescription>
        <CardAction>
        <Button size="sm" variant="secondary" className="shrink-0"
                disabled={pedindo} onClick={syncNow}
                title="Acorda o ciclo agora, sem esperar o intervalo">
          <TbRefresh size={14} className={cn(pedindo && 'animate-spin')} />
          Sincronizar agora
        </Button>
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 px-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Numero rotulo="No executor" valor={snapshot.sync_total} />
          <Numero rotulo="Em dia" valor={snapshot.sync_synced} />
          <Numero rotulo="Na fila" valor={pendentes}
                  tom={pendentes > 0 ? 'atencao' : undefined} />
          <Numero rotulo="Com erro" valor={snapshot.sync_errors}
                  tom={snapshot.sync_errors > 0 ? 'erro' : undefined} />
        </div>

        {/* The file in transit. The sync is sequential — it is one at a time,
            not a list, and showing "N downloading" would invent parallelism
            that does not exist. */}
        {inTransit && (
          <div className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs">
            <TbRefresh size={13} className="shrink-0 animate-spin text-primary" />
            <span className="truncate font-mono select-text">{inTransit}</span>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t pt-2.5 text-xs text-muted-foreground">
          <span>↑ {snapshot.sync_files_up} enviado(s) · {bytes(snapshot.sync_bytes_up)}</span>
          <span>↓ {snapshot.sync_files_down} recebido(s) · {bytes(snapshot.sync_bytes_down)}</span>
          {snapshot.sync_conflicts > 0 && (
            <span className="text-warning">{snapshot.sync_conflicts} conflito(s)</span>
          )}
          {retorno && <span className="text-foreground">{retorno}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

function Numero({ rotulo, valor, tom }: {
  rotulo: string
  valor: number
  tom?: 'atencao' | 'erro'
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className={cn(
        'text-xl font-semibold tabular-nums',
        tom === 'erro' ? 'text-destructive' : tom === 'atencao' ? 'text-warning' : undefined,
      )}>
        {valor}
      </span>
      <span className="text-xs text-muted-foreground">{rotulo}</span>
    </div>
  )
}

function bytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1073741824) return `${(n / 1048576).toFixed(1)} MB`
  return `${(n / 1073741824).toFixed(2)} GB`
}

/**
 * Exclusive choice list.
 *
 * It is an actual radio group (`role="radiogroup"`, `aria-checked`), not a
 * stack of buttons: they are mutually exclusive options, and the screen reader
 * needs to announce "1 of N selected", not N independent buttons.
 *
 * The selection is marked in three places — border, background and colored
 * icon — because a highlight in background color only, on a dark theme,
 * vanishes on a low-brightness monitor.
 */
function Choices<T extends string>({
  valor, opcoes, aoMudar,
}: {
  valor: T
  opcoes: Array<Choice<T>>
  aoMudar: (v: T) => void
}) {
  return (
    <div role="radiogroup" className="flex flex-col gap-1.5">
      {opcoes.map((o) => {
        const ativo = valor === o.v
        return (
          <button
            key={o.v}
            type="button"
            role="radio"
            aria-checked={ativo}
            onClick={() => aoMudar(o.v)}
            className={cn(
              'flex items-start gap-3 rounded-md border px-3 py-2.5 text-left transition-colors',
              'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none',
              ativo
                ? 'border-primary bg-primary/5'
                : 'border-input hover:border-input hover:bg-accent',
            )}
          >
            <span className={cn(
              'mt-px shrink-0 transition-colors',
              ativo ? 'text-primary' : 'text-muted-foreground',
            )}>
              <o.icone size={18} />
            </span>
            <span className="flex min-w-0 flex-col gap-0.5">
              <span className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">{o.r}</span>
                {o.etiqueta && (
                  <span className="rounded bg-primary/15 px-1.5 py-px text-[10px] font-semibold tracking-wide text-primary uppercase">
                    {o.etiqueta}
                  </span>
                )}
              </span>
              <span className="text-xs leading-relaxed text-muted-foreground">{o.d}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}

/**
 * `memo` because this screen stays MOUNTED behind `hidden` while the user is on
 * another tab — that is what preserves the unsaved edits. Without the boundary,
 * the 1 Hz snapshot redrew its whole tree all the time, even with the tab
 * invisible. What changes every second moved out of the props and into the
 * context, so what is left here is stable.
 */
export const GeoSync = memo(function GeoSync({
  rodando, visivel = true, aoMudarPendencia, aoMudarPasta,
}: {
  /** The executor is up — decides whether the bar offers "Reiniciar agora" (restart now). */
  rodando: boolean
  /**
   * The tab is showing.
   *
   * This screen stays MOUNTED even when hidden, so edits are not lost when
   * switching tabs — but the workspace query spawns a Python process, and
   * running it when the app opens, for someone who may never open GeoSync, is
   * pure cost. It waits for the first display.
   */
  visivel?: boolean
  /** Tells the shell there are unsaved changes, so it can mark the navigation. */
  aoMudarPendencia?: (pendente: boolean) => void
  /**
   * Reports the SAVED folder — the one in `.env`, not the one being edited.
   *
   * The shortcut in the footer opens a path over IPC, and the main process only
   * authorizes the ones it knows (see the allowlist in index.ts). A path not yet
   * saved is not there, and the button would simply do nothing.
   */
  aoMudarPasta?: (pasta: string | null) => void
}) {
  const [cfg, setCfg] = useState<ConfigGeoSync | null>(null)
  const [original, setOriginal] = useState<string>('')
  const [status, setStatus] = useState<StatusResult | null>(null)
  const [loadingWs, setLoadingWs] = useState(false)
  const [invalidas, setInvalidFolders] = useState<InvalidFolder[]>([])
  const [salvo, setSaved] = useState(false)
  /**
   * Direction chosen before switching to "manter apenas no executor" (keep
   * only on the executor).
   *
   * `catalog` occupies the SAME `modo` field as the directions in `.env`, so
   * switching to it and back would lose the previous choice — the person would
   * land on a default they never asked for. Keeping it here makes the switch
   * reversible. Without a previous direction (the `.env` already came with
   * `catalog`), the executor's applies.
   */
  const [rememberedDirection, setRememberedDirection] = useState<Exclude<SyncMode, 'catalog'>>(SYNC_DEFAULTS.modo)

  useEffect(() => {
    void window.atlas.geosync().then((c) => {
      setCfg(c)
      setOriginal(JSON.stringify(c))
      if (c.modo !== 'catalog') setRememberedDirection(c.modo)
      aoMudarPasta?.(c.pasta)
    })
    // An outside `aoMudarPasta` must not re-run the load; the effect is mount-only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /**
   * `atualizar` is the explicit click on "Atualizar"/"Tentar de novo"
   * (refresh/try again).
   *
   * Without it the main process answers from the session cache: the query
   * spawns a second Python interpreter and talks to the server over mTLS, and
   * repeating that every time the tab opened meant the skeleton pulsing for
   * seconds. See python/status.ts.
   */
  const fetchWorkspaces = useCallback((atualizar = false) => {
    setLoadingWs(true)
    void window.atlas.workspaces(atualizar)
      .then(setStatus)
      .finally(() => setLoadingWs(false))
  }, [])

  // Only once, the first time the tab appears. `fetchWorkspaces` remains
  // available through the "Atualizar" button for anyone who wants to re-query.
  const [alreadyQueried, setAlreadyQueried] = useState(false)
  useEffect(() => {
    if (!visivel || alreadyQueried) return
    setAlreadyQueried(true)
    fetchWorkspaces()
  }, [visivel, alreadyQueried, fetchWorkspaces])

  // Reported through an effect, not inside `patch`: it is derived from the
  // comparison with the original, and there are paths that reset it without
  // going through there (save, discard, reload). A single `useMemo`, used in the
  // two places that need it — the previous version serialized the
  // configuration TWICE per render.
  const sujo = useMemo(
    () => Boolean(cfg) && JSON.stringify(cfg) !== original, [cfg, original],
  )
  useEffect(() => { aoMudarPendencia?.(sujo) }, [sujo, aoMudarPendencia])

  if (!cfg) {
    return <p className="text-sm text-muted-foreground">Carregando…</p>
  }

  const patch = (p: Partial<ConfigGeoSync>) => { setCfg({ ...cfg, ...p }); setSaved(false) }

  const catalogOnly = cfg.modo === 'catalog'

  // The direction the UI shows. In local mode the `modo` field holds 'catalog',
  // so the effective direction is the remembered one. The `if` is also what
  // narrows the type for the direction card, which does not know 'catalog'.
  const currentDirection: Exclude<SyncMode, 'catalog'> =
    cfg.modo === 'catalog' ? rememberedDirection : cfg.modo

  /**
   * Toggles the locality while preserving the chosen direction.
   *
   * Coming back from "manter apenas no executor" (keep only on the executor)
   * restores the direction that was in effect before, not a default: someone
   * who chose "só enviar" (upload only) and tried the local mode should not
   * return to "nos dois sentidos" (both ways) without having asked.
   */
  function changeLocality(v: Localidade) {
    if (v === 'local') {
      if (cfg!.modo !== 'catalog') setRememberedDirection(cfg!.modo)
      patch({ modo: 'catalog' })
    } else {
      patch({ modo: rememberedDirection })
    }
  }

  const workspaces: Workspace[] = status?.ok ? status.workspaces : []
  // The executor's rule: with >1 workspace and none chosen, GeoSync is silently
  // disabled. It is the most important alert on this screen.
  const mustPickWorkspace = workspaces.length > 1 && !cfg.workspaceId
  const semWorkspace = status?.ok === true && workspaces.length === 0

  async function escolherPasta() {
    const p = await window.atlas.escolherPasta(cfg!.pasta ?? undefined)
    if (p) patch({ pasta: p })
  }

  async function salvar() {
    const r = await window.atlas.salvarGeosync(cfg!)
    setInvalidFolders(r.invalidas)
    if (r.salvo) {
      const atual = await window.atlas.geosync()
      setCfg(atual)
      setOriginal(JSON.stringify(atual))
      setSaved(true)
      aoMudarPasta?.(atual.pasta)
    }
  }

  return (
    // The `pb-16` makes room so the action bar does not cover the last card, and
    // only exists when the bar exists — otherwise a gap is left at the end of
    // the page.
    <div className={cn('flex flex-col gap-4', (sujo || salvo) && 'pb-16')}>
      {/* ── Alerts that only existed in the log ─────────────────────── */}
      {/* Both use the shared `Alerta`: they were cards rebuilt by hand,
          without an icon (the tone existed only as a border hue at 40% alpha)
          and without `role` — and they are exactly the warnings that show up
          on their own, because of a server query, while the person is looking
          at another part of the screen. */}
      {semWorkspace && (
        <Alerta
          tom="aviso"
          titulo="Este executor não está em nenhum workspace."
          remedio="Sem workspace não há Drive de destino, e o GeoSync não tem para onde sincronizar. Atribua o executor a um workspace no Atlans Studio, em Executores, e volte aqui."
        />
      )}

      {mustPickWorkspace && cfg.pasta && (
        <Alerta
          tom="aviso"
          titulo="Escolha o workspace de destino."
          remedio={
            <>
              Este executor alcança {workspaces.length} workspaces, e a detecção
              automática só funciona quando há um. Com a escolha em aberto, o
              executor sobe normalmente e desliga <em>só</em> o GeoSync, deixando
              um aviso no log — a pasta simplesmente nunca sincroniza.
            </>
          }
        />
      )}

      {/* ── Data locality ─────────────────────────────────────────────
          FIRST card on the screen. It is the decision with legal consequences,
          and it governs everything below: it defines the title of the folder
          card ("catalogada" or "sincronizada" — cataloged or synced) and
          whether direction and conflict exist at all.

          It used to come after the folder and the workspace, and the
          top-to-bottom reading was out of order — the title "Pasta catalogada"
          appeared before anything explained what cataloging is. */}
      <Card>
        <CardHeader className="px-6">
          <CardTitle className="text-base font-medium">Localidade dos dados</CardTitle>
          <span className="text-xs text-muted-foreground">
            O conteúdo pode sair desta máquina? Vale para esta pasta e para tudo
            que os workflows gravarem aqui.
          </span>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 px-6">
          <Choices
            valor={catalogOnly ? 'local' : 'sincronizar'}
            opcoes={LOCALITIES}
            aoMudar={changeLocality}
          />
          <ModePanel local={catalogOnly} direcao={currentDirection} pasta={cfg.pasta} />

          {/* ── Direction and conflict ──────────────────────────────────
              INSIDE this card, not next to it: both only exist when the
              content may leave, and that dependency is structural. As
              sibling cards, it was expressed only by proximity — and it
              vanishes when the window is narrow or the person scrolls.

              They still disappear in local mode: the panel above already says
              nothing is transferred, and two dimmed blocks repeating that in
              gray would cost half a window to explain their own uselessness. */}
          {!catalogOnly && (
            <>
              <Subsecao titulo="Direção">
                <Segmented
                  valor={currentDirection}
                  opcoes={MODES}
                  aoMudar={(modo) => { setRememberedDirection(modo); patch({ modo }) }}
                />
              </Subsecao>

              <Subsecao titulo="Em caso de conflito">
                <Segmented
                  valor={cfg.conflito} opcoes={CONFLICTS}
                  aoMudar={(conflito) => patch({ conflito })}
                />
              </Subsecao>
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Pasta ───────────────────────────────────────────────────── */}
      <Card>
        {/* Title and icon follow the MODE. In local mode nothing is synced,
            and calling the folder "sincronizada" (synced) there says the
            opposite of what happens; the icon repeats that of the option
            chosen in the card above, which is what visually ties the decision
            to its effect.

            The icon lives INSIDE `CardTitle` and the button in `CardAction`:
            the header is a grid, and the old `flex-row` was inert — the three
            blocks stacked on rows of their own, stretched to the card width. */}
        <CardHeader className="px-6">
          <CardTitle className="flex min-w-0 items-center gap-2 text-base font-medium">
            <span className={cn(
              'shrink-0 transition-colors',
              catalogOnly ? 'text-primary' : 'text-muted-foreground',
            )}>
              {catalogOnly ? <TbShieldLock size={18} /> : <TbCloud size={18} />}
            </span>
            <span className="min-w-0 truncate">
              {catalogOnly ? 'Pasta catalogada' : 'Pasta sincronizada'}
            </span>
          </CardTitle>
          <CardDescription className="text-xs">
            {catalogOnly
              ? 'Onde moram os arquivos que o executor vai catalogar.'
              : 'Onde moram os arquivos espelhados com o Drive.'}
          </CardDescription>
          <CardAction>
            <Button size="sm" variant="secondary" className="shrink-0" onClick={escolherPasta}>
              <TbFolderOpen size={14} />
              {cfg.pasta ? 'Trocar' : 'Escolher pasta'}
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 px-6">
          {cfg.pasta
            ? (
              <div className="flex items-center justify-between gap-3 rounded-md border bg-muted/30 px-3 py-2.5">
                <div className="flex min-w-0 items-center gap-2.5">
                  <TbFolderFilled size={17} className="shrink-0 text-muted-foreground" />
                  {/* Name on top, full path below. A long path truncated in the
                      middle identifies no folder at all — and the name, which
                      is what the person calls it, was hidden at the end of a
                      cut-off line. */}
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate text-sm font-medium select-text">
                      {folderName(cfg.pasta)}
                    </span>
                    <span className="truncate font-mono text-xs text-muted-foreground select-text"
                          title={cfg.pasta}>
                      {cfg.pasta}
                    </span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs"
                          onClick={() => window.atlas.abrirCaminho(cfg.pasta!)}>
                    <TbFolderOpen size={14} /> Abrir
                  </Button>
                  <Button variant="ghost" size="sm"
                          className="h-8 px-2 text-muted-foreground hover:text-destructive"
                          title="Remover a pasta — o GeoSync fica desligado"
                          onClick={() => patch({ pasta: null })}>
                    <TbX size={15} />
                  </Button>
                </div>
              </div>
            )
            : (
              <div className="flex items-start gap-2.5 rounded-md border border-dashed px-3 py-2.5">
                <TbFolderOff size={16} className="mt-0.5 shrink-0 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                  <strong className="font-medium text-foreground">Nenhuma pasta escolhida.</strong>{' '}
                  O GeoSync fica desligado até que haja uma — o resto do executor
                  funciona normalmente sem isto.
                </span>
              </div>
            )}

          {/* No explanatory note here. The locality card above already says
              what happens to the content, and this card's subtitle says what
              the folder is for.

              The note that existed explained why only ONE folder is accepted.
              It was needed when the button said "Adicionar pasta" (add folder)
              and the list was plural — someone would try a second one and
              deserve the reason. With a single folder slot and a "Trocar"
              (change) button, the restriction is already stated by the
              interface itself, and the paragraph became a justification for
              something nobody tried to do. */}

          {invalidas.length > 0 && (
            <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2">
              <p className="text-sm font-medium">A pasta não foi salva:</p>
              <ul className="mt-1 flex flex-col gap-0.5">
                {invalidas.map((i) => (
                  <li key={i.caminho} className="text-xs text-muted-foreground">
                    <span className="font-mono">{i.caminho}</span> — {i.motivo}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Workspace ───────────────────────────────────────────────── */}
      <Card className="relative">
        {/* Pinned to the card's corner, not on the title line: it is a reload
            utility, not an action of equal weight to the content. Loose in the
            corner it gets out of the way of reading and always stays in the
            same spot, regardless of whether the subtitle has one or two lines.

            Icon + FIXED label: swapping the text for "Consultando…" changed
            the button width and it jumped under the cursor. The icon is what
            spins. */}
        <Button size="sm" variant="ghost"
                className="absolute top-2.5 right-2.5 h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
                disabled={loadingWs} onClick={() => fetchWorkspaces(true)}
                title="Consultar o servidor de novo">
          <TbRefresh size={14} className={cn(loadingWs && 'animate-spin')} />
          Atualizar
        </Button>

        <CardHeader className="px-6">
          <CardTitle className="text-base font-medium">Workspace de destino</CardTitle>
          <span className="text-xs text-muted-foreground">
            {loadingWs
              ? 'Consultando o servidor…'
              : workspaces.length > 0
                ? `${workspaces.length} workspace(s) ao alcance deste executor.`
                : 'A lista vem do servidor, autenticada com o certificado desta máquina.'}
          </span>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 px-6">
          {status && !status.ok && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2">
              <p className="text-sm text-muted-foreground select-text">
                Não foi possível listar os workspaces. Isso não impede salvar os
                ajustes, mas impede escolher o destino. {status.erro}
              </p>
              <Button size="sm" variant="secondary" className="h-7 shrink-0 text-xs"
                      disabled={loadingWs} onClick={() => fetchWorkspaces(true)}>
                <TbRefresh size={13} className={cn(loadingWs && 'animate-spin')} />
                Tentar de novo
              </Button>
            </div>
          )}

          {/* First query still in progress: without this the card stays empty and
              looks broken during the seconds Python takes to start. */}
          {loadingWs && workspaces.length === 0 && !status && (
            <div className="flex flex-col gap-2" aria-hidden>
              {[0, 1].map((i) => (
                <div key={i} className="h-[52px] animate-pulse rounded-md border border-input bg-muted/40" />
              ))}
            </div>
          )}

          {workspaces.length > 0 && (
            <>
              <button
                type="button"
                onClick={() => patch({ workspaceId: null })}
                className={cn(
                  'flex flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left transition-colors',
                  !cfg.workspaceId ? 'border-primary bg-primary/5' : 'border-input hover:bg-accent',
                )}
              >
                <span className="text-sm font-medium">Detectar automaticamente</span>
                <span className="text-xs text-muted-foreground">
                  {workspaces.length === 1
                    ? 'Só há um workspace acessível, então o executor acerta sozinho.'
                    : `Não serve aqui: com ${workspaces.length} workspaces o executor não tem como escolher, e desliga o GeoSync.`}
                </span>
              </button>
              {workspaces.map((w) => (
                <button
                  key={w.id_hash}
                  type="button"
                  onClick={() => patch({ workspaceId: w.id_hash })}
                  className={cn(
                    'flex flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left transition-colors',
                    cfg.workspaceId === w.id_hash ? 'border-primary bg-primary/5' : 'border-input hover:bg-accent',
                  )}
                >
                  <span className="text-sm font-medium">{w.name || 'Sem nome'}</span>
                  <span className="font-mono text-xs text-muted-foreground">{w.id_hash}</span>
                </button>
              ))}
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Interval ──────────────────────────────────────────────────
          Fixed, and shown only to explain the behavior. See
          SYNC_INTERVAL in shared/geosync.ts. */}
      <Card>
        <CardHeader className="px-6"><CardTitle className="text-base font-medium">Intervalo de verificação</CardTitle></CardHeader>
        <CardContent className="flex items-baseline gap-3 px-6">
          <span className="font-mono text-sm tabular-nums">{SYNC_INTERVAL}s</span>
          <span className="text-sm text-muted-foreground">
            O que muda na pasta é detectado na hora, por evento do sistema de
            arquivos. Esta varredura periódica só recolhe o que escapou — pastas
            de rede e alterações feitas com o executor parado. Não é configurável.
          </span>
        </CardContent>
      </Card>

      {/* ── Status ──────────────────────────────────────────────────── */}
      {rodando && <SyncStatusCard />}

      <BarraSalvar
        mudou={sujo} salvo={salvo}
        rodando={rodando}
        aoSalvar={salvar}
        aoDescartar={() => { setCfg(JSON.parse(original)); setSaved(false) }}
      />
    </div>
  )
})
