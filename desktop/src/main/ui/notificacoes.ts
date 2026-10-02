// desktop/src/main/ui/notificacoes.ts
//
// Notificações do Windows.
//
// Um agente de background que falha em silêncio é o modo de falha clássico: o
// app vive na bandeja, a janela costuma estar fechada, e a pessoa só descobre
// que o executor parou pelo trabalho que não rodou.
//
// ## O que NÃO notifica
//
// Nada de "workflow concluído". Numa máquina que roda dezenas por dia, isso
// vira ruído, e a pessoa desliga as notificações do app inteiro — inclusive as
// três que importam. A régua aqui é: **notifica só o que exige uma ação humana
// e não se resolve sozinho.**
//
// Falha de conexão também fica de fora: o executor reconecta com backoff, e uma
// oscilação de rede de trinta segundos não é assunto de ninguém.
//
// ## Por que uma função pura
//
// `avaliarNotificacao` decide sem tocar no Electron. O que faz um sistema de
// notificação virar spam é a duplicação — notificar a cada tick do snapshot, ou
// re-notificar a mesma condição — e isso é exatamente o que dá para travar com
// teste quando a decisão está separada do efeito.
import { Notification } from 'electron'
import { ICONE_APP } from '../paths.js'
import type { EstadoApp } from '../state/store.js'
// Os limiares moram em `shared/` porque a TELA também precisa deles e não pode
// importar valor daqui (este módulo puxa `electron`). Uma barra verde enquanto
// a notificação já avisou seria pior que compartilhar dois números.
import { DISCO_BAIXO_GB, DISCO_CRITICO_GB } from '../../shared/disco.js'

export { DISCO_BAIXO_GB, DISCO_CRITICO_GB }

export interface Aviso {
  /**
   * Identidade da condição, não da mensagem.
   *
   * Duas leituras seguidas com a mesma chave são a MESMA situação, e a segunda
   * não vira notificação. É o que separa "avisar" de "martelar": o snapshot
   * chega a cada segundo.
   */
  chave: string
  titulo: string
  corpo: string
  urgente: boolean
}

/**
 * Decide o que merece notificação no estado atual. `null` = nada a dizer.
 *
 * Uma condição por vez, por prioridade: o executor parado por erro torna o
 * espaço em disco irrelevante, e duas toasts empilhadas competem entre si.
 */
export function avaliarNotificacao(estado: EstadoApp): Aviso | null {
  // ── 1. Revogado ────────────────────────────────────────────────────────────
  // O caso mais grave: não é uma falha que passa. O executor está fora do ar
  // até alguém refazer o vínculo, e nada no sistema vai consertar isso sozinho.
  if (estado.supervisor === 'failed' && estado.passoFase === 'revoked') {
    return {
      chave: 'revoked',
      titulo: 'Executor removido do servidor',
      corpo: 'Esta máquina não é mais reconhecida e parou de receber execuções. '
           + 'Abra o painel e refaça o vínculo com um OTP novo.',
      urgente: true,
    }
  }

  // ── 2. Parado por erro ─────────────────────────────────────────────────────
  if (estado.supervisor === 'failed') {
    return {
      // O passo entra na chave: um erro de certificado depois de um erro de
      // configuração são problemas diferentes, e o segundo merece ser dito.
      chave: `failed:${estado.passoFase ?? '?'}`,
      titulo: 'O executor parou',
      corpo: estado.detalheFase ?? estado.detalheSupervisor
           ?? 'Abra o painel para ver o motivo.',
      urgente: true,
    }
  }

  // ── 3. Disco ───────────────────────────────────────────────────────────────
  // Só com o executor rodando: avisar sobre disco de um executor parado é
  // ruído sobre um problema que ainda não existe.
  const livre = estado.snapshot?.artifacts_disk_free_gb
  if (estado.supervisor === 'running' && typeof livre === 'number') {
    if (livre < DISCO_CRITICO_GB) {
      return {
        chave: 'disco:critico',
        titulo: 'Disco quase cheio',
        corpo: `Restam ${livre.toFixed(1)} GB na pasta de artefatos. Workflows `
             + 'já podem falhar ao gravar o resultado.',
        urgente: true,
      }
    }
    if (livre < DISCO_BAIXO_GB) {
      return {
        chave: 'disco:baixo',
        titulo: 'Pouco espaço em disco',
        corpo: `Restam ${livre.toFixed(1)} GB na pasta de artefatos. Os arquivos `
             + 'mantidos apenas nesta máquina não têm cópia em outro lugar.',
        urgente: false,
      }
    }
  }

  return null
}

// ── Efeito ───────────────────────────────────────────────────────────────────

let ultimaChave: string | null = null

/**
 * Notifica quando a condição MUDA.
 *
 * Chamada a cada atualização do store — uma vez por segundo com o executor
 * rodando. Sem a comparação com a chave anterior, um executor parado por erro
 * geraria uma toast por segundo até alguém intervir.
 *
 * `aoClicar` leva ao painel: uma notificação que diz "abra o painel" e não abre
 * nada ao ser clicada é pior que não existir.
 */
export function notificarSeMudou(estado: EstadoApp, aoClicar: () => void): void {
  const aviso = avaliarNotificacao(estado)
  const chave = aviso?.chave ?? null

  // Voltar ao normal REARMA: se o problema retornar depois de resolvido, ele é
  // dito de novo. Sem isto, um executor que falha, é reiniciado e falha outra
  // vez ficaria mudo na segunda.
  if (chave === ultimaChave) return
  ultimaChave = chave
  if (!aviso) return

  if (!Notification.isSupported()) return
  try {
    const n = new Notification({
      title: aviso.titulo,
      body: aviso.corpo,
      icon: ICONE_APP,
      // `urgency` só tem efeito no Linux; no Windows o Electron o ignora.
      // Fica pela portabilidade, não porque muda algo aqui.
      urgency: aviso.urgente ? 'critical' : 'normal',
    })
    n.on('click', aoClicar)
    n.show()
  } catch {
    // Notificação é conveniência. Um Windows com toasts desativadas por
    // política não pode derrubar o loop de estado do app.
  }
}

/** Para os testes: descarta a memória da última condição. */
export function _resetarMemoria(): void {
  ultimaChave = null
}
