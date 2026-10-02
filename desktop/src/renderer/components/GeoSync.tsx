// desktop/src/renderer/components/GeoSync.tsx
//
// Configuração do GeoSync — sincronizar pastas locais com o Drive do workspace.
//
// Até aqui isso só existia como variáveis no `.env`, editadas à mão, com duas
// armadilhas que falham em SILÊNCIO:
//
//   1. `EXECUTOR_SYNC_DIRS` é separado por vírgula e o Python divide cegamente.
//      Uma pasta com vírgula no nome vira duas entradas inexistentes.
//   2. Com mais de um workspace acessível e `EXECUTOR_WORKSPACE_ID` vazio, o
//      executor DESABILITA o GeoSync com um `logger.warning` e segue rodando
//      normalmente (executor/main.py). Nada na interface indicava isso.
//
// Esta tela existe para tornar as duas visíveis antes de salvar.
import {
  memo, useCallback, useEffect, useMemo, useState,
  type ComponentType, type ReactNode,
} from 'react'
import {
  TbArrowsExchange, TbCloud, TbCloudCheck, TbCloudDownload, TbCloudUpload,
  TbCopy, TbDeviceDesktop, TbDownloadOff, TbFolder, TbFolderFilled, TbFolderOff,
  TbFolderOpen, TbRefresh, TbShieldLock, TbX,
} from 'react-icons/tb'
import { INTERVALO_SYNC, PADRAO_SYNC } from '../../shared/geosync.js'
import type { EstrategiaConflito, ModoSync } from '../../shared/geosync.js'
import type { ConfigGeoSync, PastaInvalida } from '../../main/state/config.js'
import type { ResultadoStatus, Workspace } from '../../main/python/status.js'
import { useSnapshot } from '../lib/snapshot.js'
import { BarraSalvar } from './BarraSalvar.js'
import { Alerta } from './Alerta.js'
import { Button } from './ui/button.js'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card.js'
import { cn } from '../lib/utils.js'

/**
 * Uma escolha da lista. `etiqueta` destaca o que muda de natureza, não de grau.
 *
 * `icone` guarda o COMPONENTE, e não um elemento pronto: a mesma opção é
 * desenhada em tamanhos diferentes pela lista completa (18px) e pelo controle
 * segmentado (14px), e um elemento com `size` embutido serviria só a um deles.
 */
interface Opcao<T extends string> {
  v: T
  r: string
  d: ReactNode
  icone: ComponentType<{ size?: number; className?: string }>
  etiqueta?: string
}

/**
 * Localidade: o conteúdo pode sair desta máquina?
 *
 * Esta escolha vivia como uma quarta opção de "Direção", e era erro de
 * categoria: as outras três respondem PARA ONDE os arquivos vão, e esta responde
 * SE eles saem. O sintoma dava para ver no próprio código — escolher "só
 * catalogar" precisava desabilitar o cartão de conflito, e uma opção que
 * invalida um cartão irmão não é da mesma natureza que suas vizinhas.
 *
 * Separada, a decisão com consequência legal vem primeiro e sozinha, e a
 * hierarquia da tela passa a espelhar a do código.
 */
type Localidade = 'sincronizar' | 'local'

const LOCALIDADES: Array<Opcao<Localidade>> = [
  {
    v: 'sincronizar',
    r: 'Sincronizar os arquivos',
    icone: TbCloud,
    d: 'O conteúdo vai e volta entre esta pasta e o Drive do workspace.',
  },
  {
    v: 'local',
    // Mesmo rótulo do campo `localidade` dos nós de saída — e agora a MESMA
    // decisão, não só o mesmo nome: `EXECUTOR_SYNC_MODE=catalog`, que esta opção
    // grava, é o que os nós leem para saber se podem enviar
    // (flow/utils/artifact_helpers.py::localidade_padrao).
    r: 'Manter apenas no executor',
    icone: TbShieldLock,
    etiqueta: 'LGPD',
    d: 'Nada sai desta máquina — nem esta pasta, nem o que os workflows gravarem. '
     + 'O servidor recebe só a ficha de cada arquivo.',
  },
]

/**
 * O que fica e o que sai, no modo escolhido.
 *
 * As descrições das opções eram um parágrafo de quatro linhas em cinza de 12px
 * — a informação mais importante da tela, no elemento menos visível dela. E
 * texto corrido é ruim justamente para a pergunta que as pessoas faziam ("mas
 * então o arquivo vai PARA ONDE?"): a resposta é uma correspondência entre
 * coisas e lugares, e correspondência se lê melhor em colunas que em prosa.
 *
 * ⚠️ No modo de sincronização o conteúdo depende da DIREÇÃO, que é escolhida no
 * cartão de baixo: em "Só baixar" nada sobe, e um quadro fixo estaria mentindo
 * metade do tempo. Por isso `direcao` entra aqui e o texto acompanha — inclusive
 * ao vivo, quando a pessoa troca a direção logo abaixo.
 *
 * Os dois quadros têm peso visual diferente de propósito: o local é realçado
 * porque descreve uma consequência (o dado não sai, o download não existe); o de
 * sincronização é neutro porque descreve o comportamento esperado.
 */
function QuadroDoModo({
  local, direcao, pasta,
}: {
  local: boolean
  direcao: Exclude<ModoSync, 'catalog'>
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
      // Sem margem própria: o espaçamento é do contêiner do cartão (gap-4).
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
          // Só no modo local: sem o realce, a leitura apressada é "sobe alguma
          // coisa, então sobe o arquivo". Na sincronização subir o arquivo é o
          // esperado, e destacar seria alarme falso.
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
 * Escolha exclusiva COMPACTA — uma faixa em vez de uma pilha de cartões.
 *
 * Direção e conflito usavam a mesma `Opcoes` da localidade e ocupavam seis
 * blocos altos, competindo em peso com a decisão que os governa. Aqui cada
 * grupo cabe numa linha, e a explicação aparece só para a opção ESCOLHIDA —
 * que é a única que descreve o que vai acontecer de fato. As demais continuam
 * alcançáveis pelo rótulo e pelo ícone.
 */
function Segmentado<T extends string>({
  valor, opcoes, aoMudar,
}: {
  valor: T
  opcoes: Array<Opcao<T>>
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
      {/* A descrição da escolhida fica embaixo, fora da faixa: dentro dela não
          caberia, e sem ela o controle viraria três rótulos sem consequência. */}
      <span className="text-xs leading-relaxed text-muted-foreground">{escolhida?.d}</span>
    </div>
  )
}

/**
 * Bloco subordinado dentro de um cartão.
 *
 * Título menor que o do cartão e separado por régua: a hierarquia precisa ficar
 * visível, senão o cartão vira uma lista plana de oito opções de rádio em que
 * nada indica quais pertencem a qual pergunta.
 */
function Subsecao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-t pt-3">
      {/* Rótulo em caixa alta e pequeno: precisa marcar a divisão sem competir
          com o título do cartão, que é a decisão principal. */}
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

/** Direções de transferência. Só se aplicam quando o conteúdo pode sair. */
const MODOS: Array<Opcao<Exclude<ModoSync, 'catalog'>>> = [
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

const CONFLITOS: Array<Opcao<EstrategiaConflito>> = [
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
 * Último segmento do caminho — como a pessoa chama a pasta.
 *
 * Separa por `\` E por `/`: o caminho vem de um diálogo do Windows, mas um
 * `.env` editado à mão pode ter barras normais, e nesse caso o "nome" seria o
 * caminho inteiro.
 */
function nomeDaPasta(caminho: string): string {
  const partes = caminho.split(/[\/]/).filter(Boolean)
  return partes[partes.length - 1] ?? caminho
}

/**
 * Onde a sincronização está agora.
 *
 * Os números vêm do MANIFESTO do executor, publicado ao fim de cada ciclo
 * (`sync_inventory`). Por isso "no executor", e não "no servidor": saber o total
 * do Drive exigiria listar o workspace a cada tick — chamada de rede que não
 * cabe num snapshot de 1 Hz. O que está aqui é o que esta máquina conhece.
 *
 * O botão existe porque a varredura é periódica: quem acabou de copiar um
 * arquivo para a pasta não deveria esperar o intervalo para ver o efeito.
 *
 * É o ÚNICO ponto desta tela que muda a cada segundo, e por isso lê o snapshot
 * do contexto em vez de recebê-lo por prop: assim o tick re-renderiza este
 * cartão, e não os dez da tela inteira. Ver lib/snapshot.ts.
 */
function Situacao() {
  const snapshot = useSnapshot()
  const [pedindo, setPedindo] = useState(false)
  const [retorno, setRetorno] = useState<string | null>(null)

  async function sincronizarAgora() {
    setPedindo(true)
    setRetorno(null)
    try {
      const ok = await window.atlas.comando('sync_now')
      setRetorno(ok ? 'Varredura solicitada.' : 'O executor não aceitou o comando.')
    } finally {
      setPedindo(false)
      // A mensagem some sozinha: é confirmação de um clique, não estado.
      setTimeout(() => setRetorno(null), 4000)
    }
  }

  // Executor parado ou ainda sem o primeiro tick: não há situação a relatar.
  if (!snapshot) return null

  const pendentes = snapshot.sync_pending
  const emTransito = snapshot.sync_current

  return (
    <Card>
      {/* `CardHeader` é grid: o `flex-row` de antes não o tornava flex, e o
          botão caía numa linha inteira abaixo do subtítulo. `CardAction` é o
          slot que o primitivo reserva à direita. */}
      <CardHeader className="px-6">
        <CardTitle className="text-base font-medium">Situação</CardTitle>
        <CardDescription className="text-xs">
          A varredura roda a cada {INTERVALO_SYNC}s, e também quando um arquivo muda.
        </CardDescription>
        <CardAction>
        <Button size="sm" variant="secondary" className="shrink-0"
                disabled={pedindo} onClick={sincronizarAgora}
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

        {/* O arquivo em trânsito. O sync é sequencial — é um por vez, não uma
            lista, e mostrar "N baixando" seria inventar paralelismo que não
            existe. */}
        {emTransito && (
          <div className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs">
            <TbRefresh size={13} className="shrink-0 animate-spin text-primary" />
            <span className="truncate font-mono select-text">{emTransito}</span>
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
 * Lista de escolha exclusiva.
 *
 * É um grupo de rádio de fato (`role="radiogroup"`, `aria-checked`), e não uma
 * pilha de botões: são opções mutuamente exclusivas, e o leitor de tela precisa
 * anunciar "1 de N selecionado", e não N botões independentes.
 *
 * A seleção é marcada em três lugares — borda, fundo e ícone colorido — porque
 * um realce só de cor de fundo, num tema escuro, some em monitor de brilho
 * baixo.
 */
function Opcoes<T extends string>({
  valor, opcoes, aoMudar,
}: {
  valor: T
  opcoes: Array<Opcao<T>>
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
 * `memo` porque esta tela fica MONTADA atrás de `hidden` enquanto o usuário está
 * em outra aba — é o que preserva a edição não salva. Sem a fronteira, o
 * snapshot de 1 Hz redesenhava a árvore inteira dela o tempo todo, mesmo com a
 * aba invisível. O que muda a cada segundo saiu das props e foi para o contexto,
 * então o que sobrou aqui é estável.
 */
export const GeoSync = memo(function GeoSync({
  rodando, visivel = true, aoMudarPendencia, aoMudarPasta,
}: {
  /** O executor está no ar — decide se a barra oferece "Reiniciar agora". */
  rodando: boolean
  /**
   * A aba está à mostra.
   *
   * Esta tela fica MONTADA mesmo escondida, para não perder edições ao trocar
   * de aba — mas a consulta de workspaces spawna um processo Python, e rodá-la
   * na abertura do app, para quem talvez nunca abra o GeoSync, é custo puro.
   * Ela espera a primeira exibição.
   */
  visivel?: boolean
  /** Avisa o shell que há alterações não salvas, para marcar a navegação. */
  aoMudarPendencia?: (pendente: boolean) => void
  /**
   * Avisa a pasta SALVA — a do `.env`, não a que está sendo editada.
   *
   * O atalho no rodapé abre um caminho pelo IPC, e o main só autoriza os que
   * ele conhece (ver a allowlist em index.ts). Um caminho ainda não salvo não
   * está lá, e o botão simplesmente não faria nada.
   */
  aoMudarPasta?: (pasta: string | null) => void
}) {
  const [cfg, setCfg] = useState<ConfigGeoSync | null>(null)
  const [original, setOriginal] = useState<string>('')
  const [status, setStatus] = useState<ResultadoStatus | null>(null)
  const [carregandoWs, setCarregandoWs] = useState(false)
  const [invalidas, setInvalidas] = useState<PastaInvalida[]>([])
  const [salvo, setSalvo] = useState(false)
  /**
   * Direção escolhida antes de trocar para "manter apenas no executor".
   *
   * `catalog` ocupa o MESMO campo `modo` que as direções no `.env`, então
   * alternar para ele e voltar perderia a escolha anterior — a pessoa cairia
   * num default que nunca pediu. Guardar aqui torna a troca reversível.
   * Sem direção anterior (o `.env` já vinha em `catalog`), vale a do executor.
   */
  const [direcaoLembrada, setDirecaoLembrada] = useState<Exclude<ModoSync, 'catalog'>>(PADRAO_SYNC.modo)

  useEffect(() => {
    void window.atlas.geosync().then((c) => {
      setCfg(c)
      setOriginal(JSON.stringify(c))
      if (c.modo !== 'catalog') setDirecaoLembrada(c.modo)
      aoMudarPasta?.(c.pasta)
    })
    // `aoMudarPasta` de fora não deve reexecutar a carga; o efeito é de montagem.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /**
   * `atualizar` é o clique explícito em "Atualizar"/"Tentar de novo".
   *
   * Sem ele o main responde do cache da sessão: a consulta spawna um segundo
   * interpretador Python e fala com o servidor por mTLS, e repetir isso a cada
   * abertura da aba era o esqueleto pulsando por segundos. Ver python/status.ts.
   */
  const buscarWorkspaces = useCallback((atualizar = false) => {
    setCarregandoWs(true)
    void window.atlas.workspaces(atualizar)
      .then(setStatus)
      .finally(() => setCarregandoWs(false))
  }, [])

  // Uma vez só, na primeira vez que a aba aparece. `buscarWorkspaces` continua
  // disponível no botão "Atualizar" para quem quiser reconsultar.
  const [jaConsultou, setJaConsultou] = useState(false)
  useEffect(() => {
    if (!visivel || jaConsultou) return
    setJaConsultou(true)
    buscarWorkspaces()
  }, [visivel, jaConsultou, buscarWorkspaces])

  // Reportado por efeito, e não dentro do `patch`: é derivado da comparação com
  // o original, e há caminhos que o zeram sem passar por lá (salvar, descartar,
  // recarregar). Um `useMemo` só, usado nos dois lugares que precisam dele — a
  // versão anterior serializava a configuração DUAS vezes por render.
  const sujo = useMemo(
    () => Boolean(cfg) && JSON.stringify(cfg) !== original, [cfg, original],
  )
  useEffect(() => { aoMudarPendencia?.(sujo) }, [sujo, aoMudarPendencia])

  if (!cfg) {
    return <p className="text-sm text-muted-foreground">Carregando…</p>
  }

  const patch = (p: Partial<ConfigGeoSync>) => { setCfg({ ...cfg, ...p }); setSalvo(false) }

  const soCatalogo = cfg.modo === 'catalog'

  // A direção que a UI mostra. No modo local o campo `modo` guarda 'catalog',
  // então a direção vigente é a lembrada. O `if` também é o que estreita o tipo
  // para o cartão de direção, que não conhece 'catalog'.
  const direcaoAtual: Exclude<ModoSync, 'catalog'> =
    cfg.modo === 'catalog' ? direcaoLembrada : cfg.modo

  /**
   * Alterna a localidade preservando a direção escolhida.
   *
   * Voltar de "manter apenas no executor" devolve a direção que estava valendo
   * antes, e não um default: quem escolheu "só enviar" e experimentou o modo
   * local não deveria voltar para "nos dois sentidos" sem ter pedido.
   */
  function trocarLocalidade(v: Localidade) {
    if (v === 'local') {
      if (cfg!.modo !== 'catalog') setDirecaoLembrada(cfg!.modo)
      patch({ modo: 'catalog' })
    } else {
      patch({ modo: direcaoLembrada })
    }
  }

  const workspaces: Workspace[] = status?.ok ? status.workspaces : []
  // A regra do executor: com >1 workspace e nenhum escolhido, o GeoSync é
  // silenciosamente desabilitado. É o alerta mais importante desta tela.
  const precisaEscolherWorkspace = workspaces.length > 1 && !cfg.workspaceId
  const semWorkspace = status?.ok === true && workspaces.length === 0

  async function escolherPasta() {
    const p = await window.atlas.escolherPasta(cfg!.pasta ?? undefined)
    if (p) patch({ pasta: p })
  }

  async function salvar() {
    const r = await window.atlas.salvarGeosync(cfg!)
    setInvalidas(r.invalidas)
    if (r.salvo) {
      const atual = await window.atlas.geosync()
      setCfg(atual)
      setOriginal(JSON.stringify(atual))
      setSalvo(true)
      aoMudarPasta?.(atual.pasta)
    }
  }

  return (
    // O `pb-16` abre espaço para a barra de ações não cobrir o último cartão, e
    // só existe quando ela existe — senão sobra um vão no fim da página.
    <div className={cn('flex flex-col gap-4', (sujo || salvo) && 'pb-16')}>
      {/* ── Alertas que só existiam no log ──────────────────────────── */}
      {/* Os dois usam o `Alerta` compartilhado: eram cartões remontados à mão,
          sem ícone (o tom só existia como matiz de borda a 40% de alfa) e sem
          `role` — e são exatamente os avisos que aparecem sozinhos, por conta
          de uma consulta ao servidor, enquanto a pessoa olha outra parte da
          tela. */}
      {semWorkspace && (
        <Alerta
          tom="aviso"
          titulo="Este executor não está em nenhum workspace."
          remedio="Sem workspace não há Drive de destino, e o GeoSync não tem para onde sincronizar. Atribua o executor a um workspace no Atlans Studio, em Executores, e volte aqui."
        />
      )}

      {precisaEscolherWorkspace && cfg.pasta && (
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

      {/* ── Localidade dos dados ──────────────────────────────────────
          PRIMEIRO cartão da tela. É a decisão com consequência legal, e ela
          governa tudo abaixo: define o título do cartão da pasta ("catalogada"
          ou "sincronizada") e se direção e conflito chegam a existir.

          Estava depois da pasta e do workspace, e a leitura de cima para baixo
          ficava fora de ordem — o título "Pasta catalogada" aparecia antes de
          qualquer coisa explicar o que é catalogar. */}
      <Card>
        <CardHeader className="px-6">
          <CardTitle className="text-base font-medium">Localidade dos dados</CardTitle>
          <span className="text-xs text-muted-foreground">
            O conteúdo pode sair desta máquina? Vale para esta pasta e para tudo
            que os workflows gravarem aqui.
          </span>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 px-6">
          <Opcoes
            valor={soCatalogo ? 'local' : 'sincronizar'}
            opcoes={LOCALIDADES}
            aoMudar={trocarLocalidade}
          />
          <QuadroDoModo local={soCatalogo} direcao={direcaoAtual} pasta={cfg.pasta} />

          {/* ── Direção e conflito ──────────────────────────────────────
              DENTRO deste cartão, e não ao lado dele: as duas só existem
              quando o conteúdo pode sair, e essa dependência é estrutural.
              Como cartões irmãos, ela ficava expressa só pela vizinhança — e
              some quando a janela é estreita ou a pessoa rola.

              Continuam sumindo no modo local: o quadro acima já diz que nada
              é transferido, e dois blocos apagados repetindo isso em cinza
              custariam meia janela para explicar a própria inutilidade. */}
          {!soCatalogo && (
            <>
              <Subsecao titulo="Direção">
                <Segmentado
                  valor={direcaoAtual}
                  opcoes={MODOS}
                  aoMudar={(modo) => { setDirecaoLembrada(modo); patch({ modo }) }}
                />
              </Subsecao>

              <Subsecao titulo="Em caso de conflito">
                <Segmentado
                  valor={cfg.conflito} opcoes={CONFLITOS}
                  aoMudar={(conflito) => patch({ conflito })}
                />
              </Subsecao>
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Pasta ───────────────────────────────────────────────────── */}
      <Card>
        {/* Título e ícone acompanham o MODO. No modo local nada é
            sincronizado, e chamar a pasta de "sincronizada" ali diz o oposto
            do que acontece; o ícone repete o da opção escolhida no cartão
            acima, que é o que amarra visualmente a decisão ao seu efeito.

            O ícone mora DENTRO de `CardTitle` e o botão em `CardAction`: o
            header é grid, e o `flex-row` de antes era inerte — os três blocos
            empilhavam em linhas próprias, esticados na largura do cartão. */}
        <CardHeader className="px-6">
          <CardTitle className="flex min-w-0 items-center gap-2 text-base font-medium">
            <span className={cn(
              'shrink-0 transition-colors',
              soCatalogo ? 'text-primary' : 'text-muted-foreground',
            )}>
              {soCatalogo ? <TbShieldLock size={18} /> : <TbCloud size={18} />}
            </span>
            <span className="min-w-0 truncate">
              {soCatalogo ? 'Pasta catalogada' : 'Pasta sincronizada'}
            </span>
          </CardTitle>
          <CardDescription className="text-xs">
            {soCatalogo
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
                  {/* Nome em cima, caminho completo embaixo. Um caminho longo
                      truncado no meio não identifica pasta nenhuma — e o nome,
                      que é como a pessoa a chama, ficava escondido no fim de
                      uma linha cortada. */}
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate text-sm font-medium select-text">
                      {nomeDaPasta(cfg.pasta)}
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

          {/* Sem nota explicativa aqui. O cartão de localidade acima já diz o
              que acontece com o conteúdo, e o subtítulo deste diz para que
              serve a pasta.

              A nota que existia explicava por que só se aceita UMA pasta. Ela
              fazia falta quando o botão dizia "Adicionar pasta" e a lista era
              plural — alguém tentaria a segunda e mereceria o motivo. Com um
              único lugar de pasta e um botão "Trocar", a restrição já está dita
              pela própria interface, e o parágrafo virava justificativa de algo
              que ninguém tentou fazer. */}

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
        {/* Fixado na quina do cartão, e não na linha do título: é um utilitário
            de recarregar, não uma ação de igual peso ao conteúdo. Solto no
            canto ele sai do caminho da leitura e continua sempre no mesmo
            ponto, independente de o subtítulo ter uma ou duas linhas.

            Ícone + rótulo FIXO: trocar o texto por "Consultando…" mudava a
            largura do botão e ele pulava sob o cursor. Quem gira é o ícone. */}
        <Button size="sm" variant="ghost"
                className="absolute top-2.5 right-2.5 h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
                disabled={carregandoWs} onClick={() => buscarWorkspaces(true)}
                title="Consultar o servidor de novo">
          <TbRefresh size={14} className={cn(carregandoWs && 'animate-spin')} />
          Atualizar
        </Button>

        <CardHeader className="px-6">
          <CardTitle className="text-base font-medium">Workspace de destino</CardTitle>
          <span className="text-xs text-muted-foreground">
            {carregandoWs
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
                      disabled={carregandoWs} onClick={() => buscarWorkspaces(true)}>
                <TbRefresh size={13} className={cn(carregandoWs && 'animate-spin')} />
                Tentar de novo
              </Button>
            </div>
          )}

          {/* Primeira consulta ainda em curso: sem isto o cartão fica vazio e
              parece quebrado nos segundos em que o Python sobe. */}
          {carregandoWs && workspaces.length === 0 && !status && (
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

      {/* ── Intervalo ─────────────────────────────────────────────────
          Fixo, e mostrado só para explicar o comportamento. Ver
          INTERVALO_SYNC em shared/geosync.ts. */}
      <Card>
        <CardHeader className="px-6"><CardTitle className="text-base font-medium">Intervalo de verificação</CardTitle></CardHeader>
        <CardContent className="flex items-baseline gap-3 px-6">
          <span className="font-mono text-sm tabular-nums">{INTERVALO_SYNC}s</span>
          <span className="text-sm text-muted-foreground">
            O que muda na pasta é detectado na hora, por evento do sistema de
            arquivos. Esta varredura periódica só recolhe o que escapou — pastas
            de rede e alterações feitas com o executor parado. Não é configurável.
          </span>
        </CardContent>
      </Card>

      {/* ── Situação ────────────────────────────────────────────────── */}
      {rodando && <Situacao />}

      <BarraSalvar
        mudou={sujo} salvo={salvo}
        rodando={rodando}
        aoSalvar={salvar}
        aoDescartar={() => { setCfg(JSON.parse(original)); setSalvo(false) }}
      />
    </div>
  )
})
