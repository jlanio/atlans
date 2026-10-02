// desktop/src/main/ui/tray.ts
//
// Ícone de bandeja: é a presença do app quando a janela está fechada.
//
// O ícone comunica o estado de relance — conectado, ocupado, offline. Sem isso
// o usuário não tem como saber se o executor está recebendo jobs sem abrir a
// janela.
//
// ⚠️ Este módulo é notificado a CADA atualização do store, ou seja, uma vez por
// segundo enquanto o executor roda. Tudo aqui é guardado por comparação com o
// estado anterior: reconstruir o menu a 1 Hz fecha o menu na cara de quem
// acabou de abri-lo, e recarregar o ícone do disco a 1 Hz é I/O puro em vão.
import { Menu, Tray, app, nativeImage, type NativeImage } from 'electron'
import fs from 'node:fs'
import { arquivoDoApp } from '../paths.js'
import type { EstadoApp } from '../state/store.js'
import { abrirJanela } from './windows.js'
import { abrirJanelaWeb } from './janela-web.js'
import { autostartAtivo, definirAutostart } from './autostart.js'

let tray: Tray | null = null

export type IconeEstado = 'online' | 'busy' | 'offline'

const ARQUIVO_ICONE: Record<IconeEstado, string> = {
  online: 'icon.ico',
  busy: 'icon-busy.ico',
  offline: 'icon-offline.ico',
}

/** Ícones carregados uma vez. Ver a nota do cabeçalho sobre I/O a 1 Hz. */
const cacheIcones = new Map<IconeEstado, NativeImage>()

function carregarIcone(estado: IconeEstado): NativeImage {
  const emCache = cacheIcones.get(estado)
  if (emCache) return emCache

  const caminho = arquivoDoApp('build', ARQUIVO_ICONE[estado])
  // `createFromPath` num arquivo ausente devolve uma imagem VAZIA em vez de
  // lançar, e o resultado é um tray invisível — o app parece não ter aberto.
  // Melhor um ícone genérico visível que nenhum.
  let img = nativeImage.createEmpty()
  if (fs.existsSync(caminho)) {
    const carregada = nativeImage.createFromPath(caminho)
    if (!carregada.isEmpty()) img = carregada
  }
  cacheIcones.set(estado, img)
  return img
}

// ── Funções puras (testáveis sem Electron) ───────────────────────────────────

export function estadoDoIcone(estado: EstadoApp | null): IconeEstado {
  if (!estado || estado.supervisor !== 'running') return 'offline'
  const snap = estado.snapshot
  if (!snap || snap.conn_state !== 'connected') return 'offline'
  return snap.running_count > 0 ? 'busy' : 'online'
}

export function resumo(estado: EstadoApp | null): string {
  if (!estado) return 'Iniciando…'
  switch (estado.supervisor) {
    case 'stopped': return estado.detalheSupervisor ?? 'Parado'
    case 'starting': return 'Iniciando…'
    case 'draining': {
      const n = estado.snapshot?.running_count ?? 0
      return n > 0 ? `Encerrando — ${n} execução(ões) em andamento` : 'Encerrando…'
    }
    case 'restarting': return estado.detalheSupervisor ?? 'Reiniciando…'
    case 'failed': return `Parado por erro — ${estado.detalheSupervisor ?? 'ver detalhes'}`
    case 'running': {
      const snap = estado.snapshot
      if (!snap) return 'Conectando…'
      if (snap.conn_state !== 'connected') return `Sem conexão (${snap.conn_state})`
      return snap.running_count > 0
        ? `${snap.running_count} execução(ões) em andamento`
        : 'Conectado, ocioso'
    }
  }
}

/**
 * Recorte do estado que o tray de fato exibe.
 *
 * É por esta string que se decide reconstruir o menu. Comparar o `EstadoApp`
 * inteiro seria inútil: ele muda a cada snapshot (uptime, CPU, memória), e nada
 * disso aparece na bandeja.
 *
 * `autostartAtivo()` responde do cache do módulo (ver autostart.ts): ele lia o
 * registro do Windows de forma síncrona, aqui dentro, a cada atualização de
 * estado — o único ponto do arquivo que escapava da blindagem contra 1 Hz.
 */
export function assinaturaDoTray(estado: EstadoApp | null): string {
  return [
    estadoDoIcone(estado),
    resumo(estado),
    estado?.supervisor ?? '',
    autostartAtivo() ? '1' : '0',
  ].join('|')
}

// ── Ciclo de vida ────────────────────────────────────────────────────────────

export interface AcoesTray {
  iniciar: () => void
  parar: () => void
  sair: () => void
}

let ultimaAssinatura = ''

export function criarTray(acoes: AcoesTray): Tray {
  tray = new Tray(carregarIcone('offline'))

  // Clique simples abre o app — a janela web, que é a cara do produto. É o
  // gesto que o usuário tenta primeiro, e não responder passa impressão de app
  // travado. Sem `double-click`: no Windows um duplo clique dispara `click`
  // duas vezes E `double-click`, o que abriria a janela três vezes.
  tray.on('click', () => abrirJanelaWeb())

  ultimaAssinatura = ''
  atualizarTray(null, acoes)
  return tray
}

export function atualizarTray(estado: EstadoApp | null, acoes: AcoesTray): void {
  if (!tray) return

  const assinatura = assinaturaDoTray(estado)
  if (assinatura === ultimaAssinatura) return    // nada que o tray mostre mudou
  ultimaAssinatura = assinatura

  const texto = resumo(estado)
  tray.setImage(carregarIcone(estadoDoIcone(estado)))
  // O tooltip do Windows corta em 127 caracteres; um detalhe de erro longo
  // encheria o limite e esconderia o começo, que é a parte útil.
  tray.setToolTip(`Atlans Executor — ${texto}`.slice(0, 127))

  const rodando = estado?.supervisor === 'running' || estado?.supervisor === 'starting'
  const encerrando = estado?.supervisor === 'draining'

  tray.setContextMenu(Menu.buildFromTemplate([
    { label: texto, enabled: false },
    { type: 'separator' },
    { label: 'Abrir Atlans', click: () => abrirJanelaWeb() },
    { label: 'Painel do executor', click: () => abrirJanela() },
    { type: 'separator' },
    { label: 'Iniciar executor', enabled: !rodando && !encerrando, click: acoes.iniciar },
    { label: 'Parar executor', enabled: rodando, click: acoes.parar },
    { type: 'separator' },
    {
      label: 'Iniciar com o Windows',
      type: 'checkbox',
      checked: autostartAtivo(),
      click: (item) => {
        definirAutostart(item.checked)
        // O menu guarda o próprio estado do checkbox; forçar a reconstrução
        // faz a marcação refletir o que o sistema DE FATO gravou, e não o que
        // o clique pediu — `definirAutostart` pode falhar em silêncio.
        ultimaAssinatura = ''
        atualizarTray(estado, acoes)
      },
    },
    { type: 'separator' },
    { label: `Versão ${app.getVersion()}`, enabled: false },
    { label: 'Sair', click: acoes.sair },
  ]))
}

export function destruirTray(): void {
  tray?.destroy()
  tray = null
  cacheIcones.clear()
  ultimaAssinatura = ''
}
