// desktop/src/renderer/components/Ajustes.tsx
//
// Configuração de execução — o que antes só existia como variáveis no `.env`.
//
// Os limites vêm de `shared/limites.ts`, o espelho dos de `executor/config.py`,
// e isso importa: o Python descarta em SILÊNCIO um valor fora da faixa e cai no
// default. Sem a validação aqui, a tela mostraria 500 workers e o executor
// rodaria com 4, sem nada explicando a diferença.
import { memo, useCallback, useEffect, useMemo, useState } from 'react'
import {
  TbAlertTriangle, TbBug, TbCertificate, TbFolder, TbFolderOpen, TbInfoCircle,
  TbLock, TbPower, TbRotate, TbServer,
} from 'react-icons/tb'
import type { ConfigExecucao, NivelLog } from '../../main/state/config.js'
import type { EstadoAutostart } from '../../main/ui/autostart.js'
import type { InfoApp } from '../../shared/ipc.js'
import { DISCO_BAIXO_GB, DISCO_CRITICO_GB, gb, nivelDoDisco } from '../../shared/disco.js'
import { LIMITES, dentroDaFaixa, type Faixa } from '../../shared/limites.js'
import { useSnapshot } from '../lib/snapshot.js'
import { BarraSalvar } from './BarraSalvar.js'
import { Alerta } from './Alerta.js'
import { Button } from './ui/button.js'
import { Input } from './ui/input.js'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card.js'
import { SERVIDOR } from '../../shared/servidor.js'
import { cn } from '../lib/utils.js'

const NIVEIS: Array<{ v: NivelLog; r: string; d: string }> = [
  { v: 'DEBUG', r: 'Depuração', d: 'Tudo, inclusive detalhe interno. O arquivo cresce rápido.' },
  { v: 'INFO', r: 'Normal', d: 'O que acontece de relevante. É o padrão.' },
  { v: 'WARNING', r: 'Só avisos', d: 'O que merece atenção, e mais nada.' },
  { v: 'ERROR', r: 'Só falhas', d: 'Silêncio até algo dar errado.' },
]

// ── Peças ────────────────────────────────────────────────────────────────────

function Secao({
  icone, titulo, descricao, children,
}: {
  icone: React.ReactNode
  titulo: string
  descricao: string
  children: React.ReactNode
}) {
  return (
    <Card>
      {/* `CardHeader` é grid: `flex-row` não o tornava flex, e o ícone caía
          numa linha inteira ACIMA do título — um glifo solto no canto. O que
          acompanha o título mora DENTRO de `CardTitle`. */}
      <CardHeader className="gap-1 px-6">
        <CardTitle className="flex min-w-0 items-center gap-2 text-base font-medium">
          <span className="shrink-0 text-muted-foreground">{icone}</span>
          <span className="min-w-0 truncate">{titulo}</span>
        </CardTitle>
        <CardDescription className="text-xs">{descricao}</CardDescription>
      </CardHeader>
      <CardContent className="px-6">{children}</CardContent>
    </Card>
  )
}

function Numero({
  rotulo, valor, min, max, padrao, sufixo, descricao, aoMudar,
}: Faixa & {
  rotulo: string
  valor: number
  sufixo?: string
  descricao: string
  aoMudar: (v: number) => void
}) {
  const invalido = !dentroDaFaixa(valor, { padrao, min, max })
  // Sem teto quando o executor não impõe um (o tempo limite): dizer "entre 1 e
  // 86400" seria inventar uma regra que ele não tem.
  const faixa = max === null ? `um valor a partir de ${min}` : `entre ${min} e ${max}`
  const alterado = Number.isFinite(valor) && valor !== padrao
  // `<label>` sem `htmlFor` ao lado de `<input>` sem `id` não associa nada: os
  // três campos numéricos desta tela chegavam ao leitor de tela como "caixa de
  // rotação, sem nome". O id vem do rótulo, que é estável e único na tela.
  const id = `ajuste-${rotulo.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium">{rotulo}</label>
        {/* "Voltar ao padrão" só aparece quando há o que voltar — um link
            permanente sugeriria que o valor atual é anormal. */}
        {/* O system.md proíbe botão ad-hoc por escrito, e a variante `link` do
            Button existe exatamente para isto — com o anel de foco de graça,
            que a versão à mão não tinha. */}
        {alterado && (
          <Button
            type="button" variant="link" size="sm"
            onClick={() => aoMudar(padrao)}
            className="h-auto p-0 text-xs font-normal text-muted-foreground hover:text-foreground"
          >
            padrão: {padrao}
          </Button>
        )}
      </div>
      <div className="flex items-center gap-2">
        {/* `ui/input.tsx`, e não mais uma cópia à mão das mesmas classes: a
            invalidez passa por `aria-invalid`, que o primitivo já pinta E que
            é o que um leitor de tela anuncia — antes o erro existia só como
            borda vermelha. */}
        <Input
          id={id}
          type="number" min={min} max={max ?? undefined} value={Number.isFinite(valor) ? valor : ''}
          onChange={(e) => aoMudar(Number.parseInt(e.target.value, 10))}
          aria-invalid={invalido || undefined}
          aria-describedby={`${id}-ajuda`}
          className={cn(
            'w-24 tabular-nums select-text',
          )}
        />
        {sufixo && <span className="text-sm text-muted-foreground">{sufixo}</span>}
      </div>
      {/* `id` casando com o `aria-describedby` do campo: a mensagem de faixa
          inválida passa a ser lida junto com o valor, em vez de existir só
          como um parágrafo vermelho abaixo. */}
      <span
        id={`${id}-ajuda`}
        className={cn('text-xs leading-relaxed', invalido ? 'text-destructive' : 'text-muted-foreground')}
      >
        {invalido
          ? `Fora da faixa. O executor ignoraria e usaria ${padrao} — informe ${faixa}.`
          : descricao}
      </span>
    </div>
  )
}

/** Campo de caminho com "Abrir" ao lado — abrir e editar no mesmo lugar. */
function Caminho({
  valor, aoMudar, aoAbrir, aoEscolher, motivoBloqueio,
}: {
  valor: string
  aoMudar?: (v: string) => void
  aoAbrir: () => void
  aoEscolher?: () => void
  /**
   * Quando presente, "Abrir" fica desabilitado com este motivo.
   *
   * O main só abre caminhos que ELE conhece (ver a allowlist em index.ts), e um
   * caminho digitado mas ainda não salvo não está lá — sem isto, o botão
   * simplesmente não faria nada, que é o pior desfecho possível.
   */
  motivoBloqueio?: string
}) {
  return (
    <div className="flex items-center gap-2">
      <Input
        value={valor}
        readOnly={!aoMudar}
        onChange={(e) => aoMudar?.(e.target.value)}
        spellCheck={false}
        title={valor}
        className={cn(
          'min-w-0 flex-1 font-mono text-xs select-text',
          aoMudar ? 'bg-transparent' : 'bg-muted/40 text-muted-foreground',
        )}
      />
      {aoEscolher && (
        <Button variant="secondary" size="sm" className="shrink-0" onClick={aoEscolher}>
          Escolher
        </Button>
      )}
      <Button variant="ghost" size="sm" className="shrink-0 px-2"
              disabled={Boolean(motivoBloqueio)} onClick={aoAbrir}
              title={motivoBloqueio ?? 'Abrir no Explorer'}>
        <TbFolderOpen size={15} />
      </Button>
    </div>
  )
}

// ── Iniciar com o Windows ────────────────────────────────────────────────────

/**
 * Interruptor do autostart.
 *
 * Mostra mais que um "ligado/desligado" porque o Windows tem mais que dois
 * estados aqui: a entrada pode existir no registro e ainda assim não executar,
 * se o usuário desativou o item em Gerenciador de Tarefas → Inicializar. Um
 * checkbox marcado nesse caso seria mentira. Ver `main/ui/autostart.ts`.
 */
function Autostart({ estado, aoAlternar }: {
  estado: EstadoAutostart | null
  aoAlternar: (v: boolean) => void
}) {
  if (!estado) return null
  const desativadoPeloWindows = estado.ativo && !estado.efetivo

  return (
    <div className="flex flex-col gap-3">
      <label className="flex cursor-pointer items-start gap-3">
        <input
          type="checkbox" checked={estado.ativo}
          onChange={(e) => aoAlternar(e.target.checked)}
          className="mt-0.5 size-4 accent-[var(--primary)]"
        />
        <span className="flex flex-col gap-0.5">
          <span className="text-sm font-medium">Iniciar com o Windows</span>
          <span className="text-xs text-muted-foreground">
            O app sobe junto com a sessão, direto na bandeja e sem abrir a
            janela, e o executor volta a receber execuções sem ninguém precisar
            lembrar de abri-lo.
          </span>
        </span>
      </label>

      {estado.erro && (
        <Aviso tom="erro">
          O Windows recusou a alteração: <span className="font-mono">{estado.erro}</span> Em
          máquina gerenciada, isso costuma ser política de grupo.
        </Aviso>
      )}

      {desativadoPeloWindows && (
        <Aviso tom="aviso">
          A entrada existe, mas está <strong>desativada</strong> em Gerenciador
          de Tarefas → Inicializar. Enquanto estiver assim, o app não sobe no
          logon — reative por lá, o app não consegue fazer isso sozinho.
        </Aviso>
      )}

      {estado.dev && (
        <Aviso tom="aviso">
          Em <span className="font-mono">npm run dev</span> a entrada aponta para
          o <span className="font-mono">electron.exe</span> do node_modules e
          continua valendo depois que o dev server é encerrado. Ligue só para
          testar, e desligue em seguida.
        </Aviso>
      )}

      {estado.ativo && (
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-medium text-muted-foreground uppercase">
            Comando registrado
          </span>
          <code className="rounded-md border bg-muted/40 px-2.5 py-1.5 font-mono text-[11px] break-all text-muted-foreground select-text">
            {estado.comando}
          </code>
        </div>
      )}
    </div>
  )
}

/**
 * Espaço livre do disco onde os artefatos são gravados.
 *
 * Não é o disco do sistema: a pasta é configurável e pode estar em outra
 * unidade. Vale a tela porque com localidade local (LGPD) o artefato tem uma
 * cópia só, e ela está aqui — disco cheio deixa de ser inconveniente e vira
 * perda de dado do cliente.
 *
 * Lê o snapshot do contexto: é o único trecho desta tela que muda a cada
 * segundo, e como prop ele arrastava a tela inteira junto. Ver lib/snapshot.ts.
 */
function Disco({ rodando }: { rodando: boolean }) {
  const snapshot = useSnapshot()
  const livre = snapshot?.artifacts_disk_free_gb
  const total = snapshot?.artifacts_disk_total_gb
  const nivel = nivelDoDisco(livre)

  // A métrica vem do executor, com o snapshot. Parado, não há o que mostrar —
  // e inventar um "—" com barra cinza sugeriria um problema de leitura.
  if (!rodando || nivel == null || typeof livre !== 'number') {
    return (
      <span className="mt-1 text-xs text-muted-foreground">
        {rodando
          ? 'Espaço em disco: aguardando a primeira medição do executor.'
          : 'Inicie o executor para ver o espaço livre neste disco.'}
      </span>
    )
  }

  const usadoPct = typeof total === 'number' && total > 0
    ? Math.min(100, Math.max(0, ((total - livre) / total) * 100))
    : null

  const cor = nivel === 'critico' ? 'bg-destructive'
    : nivel === 'baixo' ? 'bg-warning'
    : 'bg-primary'

  return (
    <div className="mt-1 flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3 text-xs">
        <span className="text-muted-foreground">Espaço livre neste disco</span>
        <span className={cn(
          'font-medium tabular-nums',
          nivel === 'critico' ? 'text-destructive'
            : nivel === 'baixo' ? 'text-warning' : 'text-foreground',
        )}>
          {gb(livre)}{typeof total === 'number' && ` de ${gb(total)}`}
        </span>
      </div>
      {usadoPct != null && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div className={cn('h-full rounded-full transition-[width] duration-500', cor)}
               style={{ width: `${usadoPct}%` }} />
        </div>
      )}
      {nivel !== 'ok' && (
        <Aviso tom={nivel === 'critico' ? 'erro' : 'aviso'}>
          {nivel === 'critico'
            ? <>Menos de {DISCO_CRITICO_GB} GB livres. Workflows já podem falhar ao
                gravar o resultado, e um artefato mantido só nesta máquina que não
                for gravado não existe em nenhum outro lugar.</>
            : <>Menos de {DISCO_BAIXO_GB} GB livres. Vale liberar espaço antes que
                comece a falhar — os artefatos locais não têm cópia no servidor.</>}
        </Aviso>
      )}
    </div>
  )
}

/**
 * Alias local do `Alerta` compartilhado, na forma densa.
 *
 * Esta tela tinha a própria cópia do padrão — mesmo desenho, outro padding e
 * outro tamanho de texto que os do App e do GeoSync. O mesmo tipo de evento
 * aparecia com peso visual diferente conforme a aba, e o `role="alert"` teria
 * de ser acrescentado três vezes.
 */
function Aviso({ tom, children }: { tom: 'erro' | 'aviso'; children: React.ReactNode }) {
  return <Alerta tom={tom} denso titulo={<span className="font-normal select-text">{children}</span>} />
}

// ── Tela ─────────────────────────────────────────────────────────────────────

/**
 * `memo` pelo mesmo motivo do GeoSync: a tela fica MONTADA atrás de `hidden`
 * para não perder edição não salva, e sem a fronteira o snapshot de 1 Hz
 * redesenhava todos os cartões dela mesmo com a aba invisível.
 */
export const Ajustes = memo(function Ajustes({
  info, rodando, aoMudarPendencia,
}: {
  info: InfoApp | null
  rodando: boolean
  /** Avisa o shell que há alterações não salvas, para marcar a navegação. */
  aoMudarPendencia?: (pendente: boolean) => void
}) {
  const [cfg, setCfg] = useState<ConfigExecucao | null>(null)
  const [original, setOriginal] = useState<ConfigExecucao | null>(null)
  const [autostart, setAutostart] = useState<EstadoAutostart | null>(null)
  const [salvo, setSalvo] = useState(false)

  const carregar = useCallback(() => {
    void window.atlas.execucao().then((c) => { setCfg(c); setOriginal(c) })
  }, [])

  useEffect(() => {
    carregar()
    void window.atlas.autostart().then(setAutostart)
  }, [carregar])

  // Ver a nota equivalente em GeoSync: derivado, e não avisado a cada edição, e
  // calculado UMA vez por render — antes eram quatro `JSON.stringify` por
  // render, num componente que renderizava uma vez por segundo.
  const sujo = useMemo(
    () => Boolean(cfg) && JSON.stringify(cfg) !== JSON.stringify(original),
    [cfg, original],
  )
  useEffect(() => { aoMudarPendencia?.(sujo) }, [sujo, aoMudarPendencia])

  if (!cfg || !original) return <p className="text-sm text-muted-foreground">Carregando…</p>

  const patch = (p: Partial<ConfigExecucao>) => { setCfg({ ...cfg, ...p }); setSalvo(false) }
  const valido =
    dentroDaFaixa(cfg.workers, LIMITES.workers) &&
    dentroDaFaixa(cfg.filaMax, LIMITES.filaMax) &&
    dentroDaFaixa(cfg.timeoutS, LIMITES.timeoutS) &&
    cfg.artifactsDir.trim().length > 0

  async function salvar() {
    const atual = await window.atlas.salvarExecucao(cfg!)
    setCfg(atual)
    setOriginal(atual)
    setSalvo(true)
  }

  return (
    // O `pb-16` abre espaço para a barra de ações não cobrir o último cartão, e
    // só existe quando ela existe — senão sobra um vão no fim da página.
    <div className={cn('flex flex-col gap-4', (sujo || salvo) && 'pb-16')}>
      <Secao
        icone={<TbPower size={18} />}
        titulo="Execução"
        descricao="Quanta carga esta máquina aceita de cada vez."
      >
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          <Numero
            rotulo="Execuções simultâneas" valor={cfg.workers} {...LIMITES.workers}
            descricao="Quantos workflows rodam ao mesmo tempo. Acima do número de núcleos, eles disputam CPU e todos ficam mais lentos."
            aoMudar={(workers) => patch({ workers })}
          />
          <Numero
            rotulo="Fila máxima" valor={cfg.filaMax} {...LIMITES.filaMax}
            descricao="Quantos podem esperar a vez. Com a fila cheia, o executor recusa novos e o servidor tenta outro."
            aoMudar={(filaMax) => patch({ filaMax })}
          />
          <Numero
            rotulo="Tempo limite" valor={cfg.timeoutS} {...LIMITES.timeoutS} sufixo="segundos"
            descricao="Um workflow que passar disso é interrompido e reportado como erro. Serve para nada travar um worker para sempre."
            aoMudar={(timeoutS) => patch({ timeoutS })}
          />
        </div>
      </Secao>

      <Secao
        icone={<TbFolder size={18} />}
        titulo="Pasta de artefatos"
        descricao="Onde os workflows gravam os arquivos que produzem."
      >
        <div className="flex flex-col gap-1.5">
          <Caminho
            valor={cfg.artifactsDir}
            aoMudar={(artifactsDir) => patch({ artifactsDir })}
            aoAbrir={() => window.atlas.abrirCaminho(cfg.artifactsDir)}
            motivoBloqueio={cfg.artifactsDir !== original.artifactsDir
              ? 'Salve a alteração antes de abrir esta pasta'
              : undefined}
            aoEscolher={async () => {
              const p = await window.atlas.escolherPasta(cfg.artifactsDir)
              if (p) patch({ artifactsDir: p })
            }}
          />
          <span className="text-xs leading-relaxed text-muted-foreground">
            Inclui os artefatos mantidos <strong className="font-medium text-foreground">só nesta
            máquina</strong> — os de workflows com saída local, que nunca sobem para o
            servidor. Trocar a pasta não move o que já existe na anterior.
          </span>
          <Disco rodando={rodando} />
        </div>
      </Secao>

      <Secao
        icone={<TbServer size={18} />}
        titulo="Servidor"
        descricao="A quem este executor obedece."
      >
        <div className="flex flex-col gap-1.5">
          <div className="flex h-9 items-center gap-2 rounded-md border border-input bg-muted/40 px-3">
            <TbLock size={13} className="shrink-0 text-muted-foreground" />
            <span className="truncate font-mono text-xs text-muted-foreground select-text">{SERVIDOR}</span>
          </div>
          <span className="text-xs leading-relaxed text-muted-foreground">
            Fixo nesta versão do app e não editável — apontar o executor para
            outro servidor faria esta máquina rodar workflows enviados por ele.
            O certificado guardado aqui também foi emitido por este servidor e
            não vale em nenhum outro.
          </span>
        </div>
      </Secao>

      <Secao
        icone={<TbBug size={18} />}
        titulo="Registro (log)"
        descricao="Quanto detalhe o executor grava enquanto trabalha."
      >
        <div role="radiogroup" className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          {NIVEIS.map((n) => {
            const ativo = cfg.nivelLog === n.v
            return (
              <button
                key={n.v} type="button" role="radio" aria-checked={ativo}
                onClick={() => patch({ nivelLog: n.v })}
                className={cn(
                  'flex flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left transition-colors',
                  'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none',
                  ativo ? 'border-primary bg-primary/5' : 'border-input hover:bg-accent',
                )}
              >
                <span className="flex items-center gap-2">
                  <span className="text-sm font-medium">{n.r}</span>
                  <span className={cn(
                    'font-mono text-[10px]',
                    ativo ? 'text-primary' : 'text-muted-foreground',
                  )}>
                    {n.v}
                  </span>
                </span>
                <span className="text-xs text-muted-foreground">{n.d}</span>
              </button>
            )
          })}
        </div>
      </Secao>

      <Secao
        icone={<TbRotate size={18} />}
        titulo="Sistema"
        descricao="Como o app se comporta fora da janela."
      >
        <Autostart
          estado={autostart}
          aoAlternar={async (v) => setAutostart(await window.atlas.autostart(v))}
        />
      </Secao>

      {info && (
        <Secao
          icone={<TbInfoCircle size={18} />}
          titulo="Arquivos desta instalação"
          descricao="Onde o app guarda o que é dele. Nada disso fica na pasta de instalação."
        >
          <div className="flex flex-col gap-3">
            <Linha rotulo="Configuração" caminho={info.envFile} />
            <Linha rotulo="Certificados" caminho={info.certDir} icone={<TbCertificate size={13} />} />
            <Linha rotulo="Logs" caminho={info.logDir} />
            <div className="flex flex-wrap gap-x-4 gap-y-1 border-t pt-3 text-xs text-muted-foreground">
              <span>Versão {info.versao}</span>
              <span>Electron {info.versaoElectron}</span>
              {info.dev && <span className="font-medium text-primary">dev</span>}
            </div>
          </div>
        </Secao>
      )}

      <BarraSalvar
        mudou={sujo} salvo={salvo}
        invalido={!valido}
        rodando={rodando}
        aoSalvar={salvar}
        aoDescartar={() => { setCfg(original); setSalvo(false) }}
      />
    </div>
  )
})

function Linha({ rotulo, caminho, icone }: { rotulo: string; caminho: string; icone?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="flex items-center gap-1.5 text-xs font-medium">
        {icone}{rotulo}
      </span>
      <Caminho valor={caminho} aoAbrir={() => window.atlas.abrirCaminho(caminho)} />
    </div>
  )
}
