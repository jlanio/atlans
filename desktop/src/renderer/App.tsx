// desktop/src/renderer/App.tsx
//
// Shell do app: barra de título própria, navegação lateral e a área da aba
// ativa — o mesmo esqueleto do Atlans Studio (.interface-design/system.md).
//
// A mudança em relação às abas no topo: o que vale em toda tela saiu do
// cabeçalho do Painel e virou chrome da janela — o controle iniciar/parar na
// sidebar, o estado da conexão na StatusBar do rodapé. Antes, trocar de aba
// escondia justamente o que se quer de olho enquanto se lê o log.
import { useCallback, useEffect, useState } from 'react'
import {
  TbActivity, TbBolt, TbChartBar, TbCircleOff, TbCpu, TbHandStop, TbKey, TbLoader,
  TbPlayerPlayFilled, TbPlugConnected, TbServer, TbTrendingUp,
} from 'react-icons/tb'
import type { EstadoApp } from '../main/state/store.js'
import type { EstadoConfiguracao } from '../main/state/config.js'
import type { InfoApp } from '../shared/ipc.js'
import { Ajustes } from './components/Ajustes.js'
import { Alerta } from './components/Alerta.js'
import { Copiavel } from './components/Copiavel.js'
import { Execucoes } from './components/Execucoes.js'
import { GeoSync } from './components/GeoSync.js'
import { Logs } from './components/Logs.js'
import { MetricCard } from './components/MetricCard.js'
import { Onboarding } from './components/Onboarding.js'
import { Sidebar, type Aba } from './components/Sidebar.js'
import { StatusBadge } from './components/StatusBadge.js'
import { StatusBar } from './components/StatusBar.js'
import { TitleBar } from './components/TitleBar.js'
import { Button } from './components/ui/button.js'
import { Card, CardContent } from './components/ui/card.js'
import { Skeleton } from './components/ui/skeleton.js'
import { SERVIDOR } from '../shared/servidor.js'
import { duracao } from './lib/formato.js'
import { ContextoSnapshot } from './lib/snapshot.js'
import { useLog } from './lib/useLog.js'

const CONEXAO: Record<string, string> = {
  offline: 'Offline',
  connecting: 'Conectando',
  connected: 'Conectado',
  reconnecting: 'Reconectando',
  terminal: 'Recusado pelo servidor',
}

/** Mensagem acionável por passo de falha — é o que o `state: failed` carrega. */
const REMEDIO: Record<string, string> = {
  config: 'Este computador ainda não foi vinculado a um executor. Gere um OTP no painel web, em Executores, e conclua o enrollment.',
  enrollment: 'O certificado mTLS não foi encontrado. Refaça o enrollment com um OTP novo.',
  server_key: 'Não foi possível obter a chave de assinatura do servidor. Verifique a conexão de rede e o endereço configurado.',
  // O KeywordDetector reage ao nome `private_key` e captura o literal ao lado —
  // que aqui é uma frase em português, não uma chave. O pragma precisa ficar na
  // MESMA linha do hit; acima dela o detector o ignora.
  private_key: 'A chave privada do executor está ausente ou ilegível. Refazer o enrollment gera um par novo.', // pragma: allowlist secret
  revoked: 'O servidor não reconhece mais este executor — ele foi removido ou revogado. O certificado guardado aqui continua válido localmente, mas é inútil: só um enrollment novo devolve o executor ao ar.',
}

/** Passos cuja solução é refazer o vínculo, e não tentar de novo. */
const PEDE_NOVO_ENROLLMENT = new Set(['revoked', 'enrollment', 'private_key'])

const TITULOS: Record<Aba, string> = {
  painel: 'Painel',
  execucoes: 'Execuções',
  geosync: 'GeoSync',
  ajustes: 'Ajustes',
}

/**
 * Janela dedicada ao log — aberta por `abrirJanelaDeLog` no main.
 *
 * A rota é o hash da URL, e não um router: são DUAS telas, e trazer um roteador
 * inteiro para isso custaria mais em dependência do que economiza em código.
 */
function ehJanelaDeLog(): boolean {
  return window.location.hash === '#log'
}

/** Só o log, em tela cheia, com a barra de título do app por cima. */
function JanelaDeLog() {
  // Nem assina o estado: esta janela só mostra log, e o canal do log é
  // independente do de estado. O `info` vem por ser estático — só o caminho da
  // pasta de logs, para o atalho do rodapé.
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
  // Antes de qualquer hook: as duas telas têm ciclos de vida diferentes, e
  // montar uma delas condicionalmente dentro de um componente só quebraria a
  // ordem dos hooks.
  return ehJanelaDeLog() ? <JanelaDeLog /> : <JanelaPrincipal />
}

function JanelaPrincipal() {
  const [estado, setEstado] = useState<EstadoApp | null>(null)
  const [info, setInfo] = useState<InfoApp | null>(null)
  const [config, setConfig] = useState<EstadoConfiguracao | null>(null)
  /**
   * Refazendo o vínculo — a única ação da janela que é MESMO bloqueante.
   *
   * O main precisa parar o executor antes de apagar os PEMs (eles podem estar
   * abertos), e só então devolve a configuração nova. As demais ações de ciclo
   * de vida voltam na hora e não desabilitam nada: um "ocupado" global preso à
   * promessa de `parar` deixava a janela inteira cinza durante a drenagem,
   * inclusive os botões "Forçar", que são a saída dela.
   */
  const [refazendo, setRefazendo] = useState(false)
  const [aba, setAba] = useState<Aba>('painel')
  /**
   * Telas com alterações não salvas.
   *
   * Não bloqueia a navegação — as duas telas de formulário ficam montadas e
   * nada se perde ao trocar de aba. O que isto alimenta é o MARCADOR na
   * barra lateral: um aviso permanente e discreto, que não interrompe.
   *
   * Um diálogo de confirmação a cada troca seria pior: interrompe sempre para
   * proteger de uma perda que já não acontece.
   */
  const [pendencias, setPendencias] = useState<Partial<Record<Aba, boolean>>>({})
  // Pasta SALVA do GeoSync, para o atalho do rodapé. Vem da própria tela, que é
  // quem sabe quando o `.env` mudou.
  const [pastaGeosync, setPastaGeosync] = useState<string | null>(null)

  const marcarPendencia = useCallback((tela: Aba, pendente: boolean) => {
    setPendencias((atual) => (
      Boolean(atual[tela]) === pendente ? atual : { ...atual, [tela]: pendente }
    ))
  }, [])

  // Estáveis de propósito: são props de telas memoizadas, e uma closure nova a
  // cada render (isto é, a cada segundo) atravessaria o `memo` e ainda faria o
  // `useEffect([sujo, aoMudarPendencia])` das duas reexecutar sem nada ter
  // mudado.
  const pendenciaGeosync = useCallback(
    (p: boolean) => marcarPendencia('geosync', p), [marcarPendencia],
  )
  const pendenciaAjustes = useCallback(
    (p: boolean) => marcarPendencia('ajustes', p), [marcarPendencia],
  )

  const recarregarConfig = useCallback(() => {
    void window.atlas.configuracao().then(setConfig)
  }, [])

  useEffect(() => {
    void window.atlas.estado().then(setEstado)
    void window.atlas.info().then(setInfo)
    recarregarConfig()
    // O cancelamento devolvido pelo preload precisa rodar no cleanup, senão
    // cada remontagem acumula um ouvinte de IPC.
    return window.atlas.aoAtualizarEstado(setEstado)
  }, [recarregarConfig])

  // Uma falha em `config`/`enrollment` significa que o `.env` ou os certificados
  // mudaram por fora (pasta apagada, cert expirado e removido). Reler devolve o
  // usuário ao formulário em vez de deixá-lo num painel que não funciona.
  useEffect(() => {
    if (estado?.passoFase === 'config' || estado?.passoFase === 'enrollment') {
      recarregarConfig()
    }
  }, [estado?.passoFase, recarregarConfig])

  const refazerEnrollment = useCallback(async () => {
    setRefazendo(true)
    try { setConfig(await window.atlas.refazerEnrollment()) }
    finally { setRefazendo(false) }
  }, [])

  // A barra de título é do app (a janela usa `frame: false`), então precisa
  // envolver TODOS os estados — inclusive o de carregamento, senão a janela
  // abre sem nenhum jeito de fechar.
  if (!estado || !config) {
    return (
      <Moldura>
        {/* Esqueleto no formato do que vem: a barra lateral e os quatro cartões
            do Painel. Uma frase centralizada não diz onde o conteúdo vai
            aparecer nem quanto dele vem — e some de repente, num salto. */}
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
      </Moldura>
    )
  }

  // Sem enrollment não há painel a mostrar, e nem sidebar: ela só navegaria
  // entre telas vazias. O vínculo ocupa a janela inteira.
  if (!config.configurado) {
    return (
      <Moldura>
        <Onboarding config={config} aoConcluir={recarregarConfig} />
      </Moldura>
    )
  }

  const snap = estado.snapshot

  return (
    // O snapshot desce por contexto: como prop, ele re-renderizava GeoSync e
    // Ajustes inteiras a cada segundo. Ver lib/snapshot.ts.
    <ContextoSnapshot.Provider value={snap}>
      <Moldura barra={<StatusBar estado={estado} info={info}
                            pastaGeosync={pastaGeosync}
                            aoAbrirAjustes={() => setAba('ajustes')} />}>
        <div className="flex min-h-0 flex-1">
          <Sidebar
            aba={aba}
            aoTrocar={setAba}
            pendencias={pendencias}
            estado={estado}
            aoIniciar={() => void window.atlas.iniciar()}
            aoParar={() => void window.atlas.parar()}
            aoForcar={() => void window.atlas.forcar()}
          />

          <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
            {/* `max-w-5xl` + `mx-auto`: maximizada num monitor largo, cada linha
                rótulo/valor do resumo abria ~730px e o par deixava de se ler
                como par — que é todo o trabalho que a linha faz. 1024px casa
                com a janela padrão de 980; o web usa `max-w-6xl` num layout
                menos denso (Layout > Page container, system.md). */}
            <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-6 py-5">

              {/* ── Cabeçalho da página ───────────────────────────────────
                  Só o título e o que é específico da tela: estado e ações de
                  ciclo de vida agora vivem na sidebar, e repeti-los aqui
                  custaria altura sem dizer nada de novo. */}
              <header className="flex min-h-8 items-center justify-between gap-4">
                <h1 className="text-lg font-semibold">{TITULOS[aba]}</h1>
                {aba === 'painel' && estado.hello && (
                  <div className="flex items-center gap-3">
                    <Copiavel
                      valor={estado.hello.executor_id}
                      rotulo="ID do executor"
                      exibir={`${estado.hello.executor_id.slice(0, 8)}…`}
                    />
                    {/* O `title` mora no SPAN, não no botão: a base do Button
                        traz `disabled:pointer-events-none`, e sem hit-test o
                        Chromium nunca mostra tooltip nativo — a explicação só
                        existia no estado em que não podia ser lida. */}
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

              {/* ── Avisos ────────────────────────────────────────────────
                  Valem em qualquer aba: uma falha de boot ou uma drenagem em
                  curso importam tanto olhando o log quanto o painel. */}
              {estado.supervisor === 'failed' && (
                <Alerta
                  tom="erro"
                  titulo="O executor não está rodando."
                  remedio={estado.passoFase ? REMEDIO[estado.passoFase] : undefined}
                  bruto={estado.detalheFase ?? estado.detalheSupervisor}
                >
                  {estado.passoFase && PEDE_NOVO_ENROLLMENT.has(estado.passoFase) && (
                    <Button size="sm" disabled={refazendo}
                            title="Descarta o certificado desta máquina. A configuração e os artefatos são mantidos."
                            onClick={() => void refazerEnrollment()}>
                      <TbKey size={15} /> Refazer enrollment
                    </Button>
                  )}
                </Alerta>
              )}

              {/* Durante a drenagem os snapshots continuam chegando: dá para
                  mostrar progresso real em vez de um spinner cego. */}
              {estado.fase === 'draining' && snap && (
                <Alerta
                  tom="aviso"
                  titulo={`Encerrando — ${snap.running_count} execução(ões) em andamento`}
                  remedio={`${snap.result_queue_size} resultado(s) ainda a confirmar. O executor espera os workflows terminarem para não perder trabalho.`}
                >
                  {/* NUNCA desabilitado: é a saída de uma espera que pode chegar
                      a 150 s, e desabilitá-lo durante ela deixava a janela sem
                      nenhuma ação possível. */}
                  <Button size="sm" variant="destructive"
                          onClick={() => void window.atlas.forcar()}>
                    <TbHandStop size={15} /> Forçar agora
                  </Button>
                </Alerta>
              )}

              {/* ── Conteúdo da aba ─────────────────────────────────────────
                  GeoSync e Ajustes ficam MONTADOS o tempo todo, apenas ocultos.
                  São as duas telas com formulário, e desmontá-las ao trocar de
                  aba jogaria fora as edições não salvas — sem aviso, sem desfazer.
                  Ocultas, o estado sobrevive: a pessoa vai ao Log conferir algo,
                  volta, e continua de onde parou.

                  As demais são só leitura e podem desmontar. Vale a pena manter a
                  distinção: `Logs` monta centenas de nós, e deixá-lo vivo em
                  segundo plano custaria caro à toa. */}
              {/* `key={aba}` nas telas montadas o tempo todo faria elas
                  remontarem (e perderem a edição). A entrada vai no wrapper,
                  que é recriado pelo React só quando `hidden` muda de valor —
                  o suficiente para a troca de aba deixar de ser um corte seco.
                  Ver o bloco prefers-reduced-motion no index.css. */}
              <div hidden={aba !== 'geosync'}
                   className={aba === 'geosync' ? 'animate-in fade-in-0 slide-in-from-bottom-1 duration-200' : undefined}>
                <GeoSync
                  rodando={estado.supervisor === 'running'}
                  visivel={aba === 'geosync'}
                  aoMudarPendencia={pendenciaGeosync}
                  aoMudarPasta={setPastaGeosync}
                />
              </div>
              <div hidden={aba !== 'ajustes'}
                   className={aba === 'ajustes' ? 'animate-in fade-in-0 slide-in-from-bottom-1 duration-200' : undefined}>
                <Ajustes
                  info={info} rodando={estado.supervisor === 'running'}
                  aoMudarPendencia={pendenciaAjustes}
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
      </Moldura>
    </ContextoSnapshot.Provider>
  )
}

// ── Painel ───────────────────────────────────────────────────────────────────

function Painel({
  estado, info, aoIniciar,
}: {
  estado: EstadoApp
  info: InfoApp | null
  aoIniciar: () => void
}) {
  const snap = estado.snapshot

  // Executor parado por decisão do usuário: métricas zeradas não informam
  // nada, e a ação óbvia precisa estar à vista.
  if (estado.supervisor === 'stopped') {
    return (
      <Card className="py-10">
        <CardContent className="flex flex-col items-center gap-4 px-6 text-center">
          {/* Um ícone grande e apagado ocupa o vazio que as métricas deixaram e
              diz o estado antes de qualquer texto ser lido. */}
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
      {/* `md` e não `lg`: os breakpoints do Tailwind medem a JANELA, e a janela
          padrão agora tem 980px — em `lg` (1024px) os quatro cartões nunca
          ficariam lado a lado no tamanho em que o app abre. */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricCard
          icone={TbChartBar} titulo="Execuções"
          valor={snap ? String(snap.total_ok + snap.total_error) : '—'}
          rodape={snap ? `${snap.total_ok} ok · ${snap.total_error} com erro` : undefined}
          // Vermelho só quando HÁ erro: um cartão permanentemente colorido
          // deixa de significar alguma coisa.
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

      {/* Único bloco que o Painel repete da aba Execuções — é o que justifica
          olhar o Painel enquanto algo roda. */}
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
              {/* Sem `nodes_total` (o executor ainda não reportou o grafo) a
                  barra ficava simplesmente ausente, e uma execução recém-aceita
                  era indistinguível de uma travada. A faixa indeterminada diz
                  "há trabalho, ainda não sei quanto" sem inventar um número. */}
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

      {/* ── Resumo ────────────────────────────────────────────────────────
          Eram doze pares rótulo/valor numa grade plana — uma parede em que
          nada indicava que "Reconexões" e "PID" respondem perguntas
          diferentes. Agrupados por assunto, com um ícone marcando cada bloco,
          o olho encontra o grupo primeiro e a linha depois. */}
      {snap && (
        <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Grupo icone={TbPlugConnected} titulo="Conexão">
            <Linha rotulo="Estado">
              {/* `pulsando` existe no StatusBadge desde sempre e nunca era
                  passado. Só nos estados TRANSITÓRIOS: um pulso em "Conectado"
                  seria movimento permanente sem nada a dizer, e é justamente
                  enquanto conecta ou reconecta que a pessoa precisa ver que
                  algo ainda está acontecendo. */}
              <StatusBadge
                status={snap.conn_state}
                rotulo={CONEXAO[snap.conn_state] ?? snap.conn_state}
                pulsando={snap.conn_state === 'connecting' || snap.conn_state === 'reconnecting'}
              />
            </Linha>
            <Linha rotulo="Conectado há">{duracao(snap.conn_since_s)}</Linha>
            {/* Quando reconectando, o tempo até a próxima tentativa é a única
                informação que evita o usuário ficar clicando em Reconectar. */}
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

/** Bloco do resumo: um assunto, marcado por ícone, com suas linhas. */
function Grupo({
  icone: Icone, titulo, children,
}: {
  icone: React.ComponentType<{ size?: number; className?: string }>
  titulo: string
  children: React.ReactNode
}) {
  return (
    // Card, e não um div repintado à mão: a cópia tinha a mesma cor e curvatura
    // mas ficava sem o `shadow-xs` que define o Nível 1 de elevação — um nível
    // que a tabela do system.md não tem. O tailwind-merge do Card resolve
    // py-5→py-3 e gap-4→gap-2 sozinho.
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

// ── Peças do shell ───────────────────────────────────────────────────────────

/**
 * Barra de título própria + conteúdo + barra de estado — a janela não tem
 * moldura do sistema (`frame: false` em windows.ts).
 *
 * A barra de estado é opcional porque nas telas de carregamento e de vínculo
 * não há executor sobre o qual reportar nada.
 */
function Moldura({ children, barra }: { children: React.ReactNode; barra?: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TitleBar />
      {children}
      {barra}
    </div>
  )
}
