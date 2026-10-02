// desktop/src/renderer/components/TitleBar.tsx
//
// Barra de título desenhada pelo app (a janela usa `frame: false`).
//
// Híbrido deliberado: a APARÊNCIA é a do macOS (círculos coloridos sólidos),
// mas a POSIÇÃO e a ORDEM são as do Windows — à direita, minimizar / maximizar
// / fechar, com o fechar na quina. É onde a mão do usuário de Windows já vai, e
// deixar o "fechar" em qualquer outro lugar do grupo criaria um híbrido que não
// corresponde a nenhum dos dois sistemas.
//
// A única reação ao mouse é o glifo da função aparecendo dentro do círculo sob
// o cursor — um de cada vez, só o que está sendo apontado.
//
// O `-webkit-app-region: drag` faz a barra arrastar a janela; os botões
// precisam de `no-drag` explícito, senão o clique vira início de arrasto e
// nunca dispara.
import { useState } from 'react'
import { cn } from '../lib/utils.js'

type Semaforo = 'fechar' | 'minimizar' | 'maximizar'

// Cores dos semáforos do macOS. São valores fixos de propósito, e não tokens do
// design system: o usuário reconhece este vermelho/amarelo/verde específicos
// como "controles de janela", e trocá-los pela paleta terracota do produto
// tiraria justamente a familiaridade que motiva usá-los.
const CORES: Record<Semaforo, string> = {
  fechar: 'bg-[#ff5f57]',
  minimizar: 'bg-[#febc2e]',
  maximizar: 'bg-[#28c840]',
}

// Tom escuro da própria cor do círculo, como no macOS: um glifo preto ou branco
// brigaria com o fundo colorido em vez de assentar nele.
const TINTA: Record<Semaforo, string> = {
  fechar: '#7a0a04',
  minimizar: '#8a5a00',
  maximizar: '#0a5c17',
}

function Glifo({ tipo, maximizada }: { tipo: Semaforo; maximizada: boolean }) {
  const comum = {
    // `group-hover/semaforo` casa com o `group/semaforo` do PROPRIO botao —
    // cada circulo e o seu grupo, entao so o que esta sob o cursor revela o
    // glifo. `pointer-events-none` no svg impede que ele roube o hover do
    // botao e o icone pisque ao mover o mouse dentro do circulo.
    className:
      'pointer-events-none absolute inset-0 m-auto opacity-0 transition-opacity duration-150 group-hover/semaforo:opacity-100 group-focus-visible/semaforo:opacity-100',
    stroke: TINTA[tipo],
    strokeWidth: 1.3,
    strokeLinecap: 'round' as const,
    fill: 'none',
    'aria-hidden': true,
  }

  if (tipo === 'fechar') {
    return <svg {...comum} width="6" height="6" viewBox="0 0 6 6"><path d="M1 1l4 4M5 1L1 5" /></svg>
  }
  if (tipo === 'minimizar') {
    return <svg {...comum} width="7" height="2" viewBox="0 0 7 2"><path d="M0.6 1h5.8" /></svg>
  }
  return (
    <svg {...comum} width="7" height="7" viewBox="0 0 7 7">
      {maximizada
        // Restaurar: setas apontando para dentro.
        ? <path d="M3.6 0.9v2.3H1.3M3.4 6.1V3.8h2.3" />
        // Maximizar: cantos opostos, apontando para fora.
        : <path d="M1 3.2V1h2.2M6 3.8V6H3.8" />}
    </svg>
  )
}

function Botao({
  tipo, rotulo, maximizada, aoClicar,
}: {
  tipo: Semaforo
  rotulo: string
  maximizada: boolean
  aoClicar: () => void
}) {
  return (
    <button
      type="button"
      onClick={aoClicar}
      aria-label={rotulo}
      title={rotulo}
      // `app-region: no-drag` é obrigatório: dentro de uma área de arrasto, o
      // clique seria consumido pelo gesto de mover a janela.
      style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
      // O CÍRCULO tem 12px, mas o alvo não precisa ter: `p-1.5 -m-1.5` cresce a
      // área clicável para 24px sem mover o desenho nem mudar a altura da
      // barra. Eram três alvos de 12px lado a lado — os primeiros tab stops do
      // app, e sem anel de foco.
      //
      // `focus-visible` (e não `focus`): quem clica não vê anel nenhum; quem
      // tabula vê. Sem ele, o teclado atravessava os três controles de janela
      // às cegas.
      className={cn(
        'group/semaforo relative -m-1.5 box-content size-3 rounded-full p-1.5 outline-none',
        'transition-transform active:scale-90',
        'focus-visible:ring-ring/70 focus-visible:ring-2',
        'bg-clip-content',
        CORES[tipo],
      )}
    >
      <Glifo tipo={tipo} maximizada={maximizada} />
    </button>
  )
}

export function TitleBar({ titulo }: { titulo?: string }) {
  // Só rastreia para escolher o rótulo entre "Maximizar" e "Restaurar" — o
  // botão não muda de aparência.
  const [maximizada, setMaximizada] = useState(false)

  const alternarMaximizar = () => {
    void window.atlas.janela('alternar-maximizar').then(setMaximizada)
  }

  return (
    <header
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
      // Duplo clique na barra alterna maximizar — comportamento esperado nos
      // dois sistemas.
      onDoubleClick={alternarMaximizar}
      className="relative flex h-9 shrink-0 items-center justify-end border-b border-border/60 bg-sidebar px-3 select-none"
    >
      {/* Título centralizado na JANELA, e não no espaço restante: `absolute`
          evita que a largura do grupo de botões o desloque para a esquerda. */}
      <span className="pointer-events-none absolute inset-x-0 text-center text-xs font-medium text-muted-foreground">
        {titulo ?? 'Atlans Executor'}
      </span>

      {/* Ordem do Windows: fechar por último, na quina da janela. O hover é de
          cada botão (`group/semaforo`), não deste contêiner. */}
      <div className="flex items-center gap-2">
        <Botao tipo="minimizar" rotulo="Minimizar" maximizada={maximizada}
               aoClicar={() => void window.atlas.janela('minimizar')} />
        <Botao tipo="maximizar" rotulo={maximizada ? 'Restaurar' : 'Maximizar'} maximizada={maximizada}
               aoClicar={alternarMaximizar} />
        <Botao tipo="fechar" rotulo="Fechar" maximizada={maximizada}
               aoClicar={() => void window.atlas.janela('fechar')} />
      </div>
    </header>
  )
}
