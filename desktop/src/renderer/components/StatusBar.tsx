// desktop/src/renderer/components/StatusBar.tsx
//
// Barra de estado no rodapé da JANELA — largura inteira, abaixo da sidebar e do
// conteúdo.
//
// O estado do executor não pertence a nenhuma tela: ele vale em todas. Enquanto
// morava no rodapé da sidebar, disputava espaço com a navegação e ficava
// espremido em 192px; e enquanto morava no cabeçalho do Painel, sumia ao trocar
// de aba. Aqui ele é chrome da janela, como a barra de status de um editor —
// sempre no mesmo lugar, sempre legível, sem custar altura do conteúdo.
//
// O que entra: o que se consulta de relance e não se clica com frequência.
// Ações de ciclo de vida continuam na sidebar, onde o alvo é grande.
import {
  TbAlertTriangle, TbCircleX, TbFolder, TbFolderSymlink, TbList,
} from 'react-icons/tb'
import type { EstadoApp } from '../../main/state/store.js'
import type { InfoApp } from '../../shared/ipc.js'
import { gb, nivelDoDisco } from '../../shared/disco.js'
import { cn } from '../lib/utils.js'

/** Ponto colorido de status. A cor é a mesma linguagem do ícone da bandeja. */
export function Ponto({ estado }: { estado: EstadoApp }) {
  const snap = estado.snapshot
  const conectado = estado.supervisor === 'running' && snap?.conn_state === 'connected'
  const ocupado = conectado && snap.running_count > 0
  const erro = estado.supervisor === 'failed'

  const cor = erro ? 'bg-destructive'
    : ocupado ? 'bg-blue-400'
    : conectado ? 'bg-green-400'
    : 'bg-muted-foreground'

  return (
    <span
      className="relative flex size-2 shrink-0"
      // A cor é a única pista do estado da conexão nesta faixa; sem rótulo
      // acessível, o LED não existe para quem usa leitor de tela.
      role="img"
      aria-label={`Estado: ${rotuloStatus(estado)}`}
    >
      {/* Respiração, não `animate-ping`.
          O anel que se expande a cada segundo mora na ÚNICA chrome permanente
          da janela — um app que fica aberto o dia inteiro em segundo plano — e
          movimento periférico contínuo cansa sem dizer nada de novo. A
          respiração comunica "vivo" com a mesma clareza e sem estroboscopia.
          Ver o bloco prefers-reduced-motion no index.css: sob ele o LED fica
          aceso, e não apagado. */}
      <span className={cn(
        'relative inline-flex size-2 rounded-full transition-colors duration-500',
        ocupado && 'animate-pulso-vivo',
        cor,
      )} />
    </span>
  )
}

export function rotuloStatus(estado: EstadoApp): string {
  const snap = estado.snapshot
  switch (estado.supervisor) {
    case 'stopped': return 'Parado'
    case 'starting': return 'Iniciando…'
    case 'draining': return 'Encerrando…'
    case 'restarting': return 'Reiniciando…'
    case 'failed': return 'Parado por erro'
    case 'running':
      if (!snap) return 'Conectando…'
      if (snap.conn_state === 'connected') {
        return snap.running_count > 0 ? `${snap.running_count} em execução` : 'Conectado'
      }
      return snap.conn_state === 'reconnecting' ? 'Reconectando…' : 'Sem conexão'
  }
}

/** Detalhe que só faz sentido em alguns estados — vazio nos demais. */
function detalhe(estado: EstadoApp): string | null {
  const snap = estado.snapshot
  if (!snap) return null
  // Sem isto, o usuário fica clicando em Reconectar sem saber que já há uma
  // tentativa agendada.
  if (snap.conn_state === 'reconnecting' && snap.next_retry_in_s != null) {
    return `nova tentativa em ${Math.ceil(snap.next_retry_in_s)}s`
  }
  if (estado.supervisor === 'draining') {
    return `${snap.running_count} em andamento, ${snap.result_queue_size} a confirmar`
  }
  if (snap.queued > 0) return `${snap.queued} na fila`
  return null
}

/**
 * Atalho da barra de estado.
 *
 * Cinco `<button>` ad-hoc dividiam a mesma aparência e nenhum tinha anel de
 * foco: a barra inteira era invisível para quem navega por teclado. O alvo
 * também era só o texto — `px-1.5 py-0.5` dá área de clique sem mudar a
 * altura da faixa, que é fixa.
 */
const ATALHO = [
  'flex shrink-0 items-center gap-1 rounded-sm px-1.5 py-0.5 outline-none',
  'transition-colors underline-offset-4 hover:underline',
  'focus-visible:ring-ring/50 focus-visible:ring-2',
].join(' ')

export function StatusBar({
  estado, info, pastaGeosync, aoAbrirAjustes,
}: {
  estado: EstadoApp
  info: InfoApp | null
  /** Pasta do GeoSync, quando há uma configurada. */
  pastaGeosync: string | null
  aoAbrirAjustes: () => void
}) {
  // Contado no main, incrementalmente. Varrer o log inteiro aqui exigiria
  // que ele viajasse no estado — que é exatamente o custo que o canal
  // incremental tirou (ver main/state/store.ts).
  const erros = estado.errosNoLog
  const extra = detalhe(estado)
  // Só com o executor rodando: a métrica vem do snapshot dele.
  const disco = estado.supervisor === 'running'
    ? nivelDoDisco(estado.snapshot?.artifacts_disk_free_gb)
    : null

  return (
    <footer className="flex h-7 shrink-0 items-center gap-3 border-t border-sidebar-border bg-sidebar px-3 text-xs text-muted-foreground">
      {/* Atalhos e versão à ESQUERDA; o estado fica na quina direita, que é
          onde a barra de status de um app de desktop o coloca — e onde ele não
          é empurrado de lugar quando um atalho aparece ou some. */}
      {/* O LOG saiu da navegação lateral e abre em JANELA PRÓPRIA. Ler log é
          quase sempre comparar com outra coisa — o painel, o Studio, um editor
          — e uma aba obriga a escolher entre os dois. A janela também não
          precisa de estado de "ativo" aqui: quem manda nela é o gerenciador de
          janelas, e um realce nosso descolaria da realidade assim que a pessoa
          a fechasse. */}
      <button type="button" onClick={() => window.atlas.abrirJanelaLog()}
              title="Abrir o log em uma janela separada"
              className={cn(ATALHO, 'hover:text-foreground')}>
        <TbList size={13} /> Log
      </button>

      {info && (
        <button type="button" onClick={() => window.atlas.abrirCaminho(info.artifactsDir)}
                title={`Abrir no Explorer: ${info.artifactsDir}`}
                className={cn(ATALHO, 'hover:text-foreground')}>
          <TbFolder size={13} /> Artefatos
        </button>
      )}
      {/* Só quando há uma configurada. Um atalho para pasta inexistente seria
          um botão que não faz nada — e a pasta do GeoSync é opcional. A pasta
          de logs saiu daqui: ela está em Ajustes, junto das outras da
          instalação, e duas coisas chamadas "Log" na mesma barra confundiam. */}
      {pastaGeosync && (
        <button type="button" onClick={() => window.atlas.abrirCaminho(pastaGeosync)}
                title={`Abrir no Explorer: ${pastaGeosync}`}
                className={cn(ATALHO, 'hover:text-foreground')}>
          <TbFolderSymlink size={13} /> GeoSync
        </button>
      )}
      {info && <span>v{info.versao}</span>}
      {info?.dev && <span className="font-medium text-primary">dev</span>}

      <span className="flex-1" />

      {/* Disco só aparece quando está apertado. Um indicador permanente de
          "487 GB livres" ocupa a barra para não dizer nada. */}
      {disco && disco !== 'ok' && (
        <button type="button" onClick={aoAbrirAjustes}
                title="Ver detalhes em Ajustes"
                className={cn(
                  ATALHO,
                  'animate-in fade-in-0 slide-in-from-right-2 duration-300',
                  disco === 'critico' ? 'text-destructive' : 'text-warning',
                )}>
          {/* Glifo de alerta, não o de armazenamento: este item só existe
              quando o disco está apertado, e um ícone neutro de "banco de
              dados" fazia dele mais uma informação da barra. */}
          <TbAlertTriangle size={13} />
          {gb(estado.snapshot?.artifacts_disk_free_gb)} livres
        </button>
      )}
      {erros > 0 && (
        <button type="button" onClick={() => window.atlas.abrirJanelaLog()}
                title="Abrir o log para ver os erros"
                className={cn(ATALHO, 'text-destructive animate-in fade-in-0 slide-in-from-right-2 duration-300')}>
          <TbCircleX size={13} />
          {/* "1 erro(s)" era o único plural entre parênteses do arquivo. */}
          {erros > 99 ? '99+ erros' : `${erros} ${erros === 1 ? 'erro' : 'erros'}`}
        </button>
      )}
      {extra && <span className="truncate">{extra}</span>}
      <span className="flex items-center gap-2 border-l border-sidebar-border pl-3">
        <Ponto estado={estado} />
        <span className="text-foreground">{rotuloStatus(estado)}</span>
      </span>
    </footer>
  )
}
