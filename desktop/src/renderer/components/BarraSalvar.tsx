// desktop/src/renderer/components/BarraSalvar.tsx
//
// Barra de ações das telas de configuração (Ajustes e GeoSync).
//
// Fica FIXA no rodapé da área de conteúdo, e não no fim da página: as duas telas
// rolam bastante, e um Salvar lá embaixo obriga a percorrer tudo para confirmar
// uma mudança feita no primeiro cartão.
//
// ## O aviso virou botão
//
// A versão anterior dizia "Reinicie o executor para que passe a valer" — o app
// instruindo a pessoa a executar à mão uma sequência (Parar, esperar drenar,
// Iniciar) que ele próprio sabe fazer. Instrução é o que sobra quando falta um
// botão. Agora o mesmo texto vem com "Reiniciar agora" ao lado.
//
// Não é um "salvar e reiniciar" único de propósito: reiniciar DRENA as execuções
// em andamento e pode levar bem mais que um instante, então continua sendo uma
// decisão à parte, tomada depois de o salvamento já estar garantido.
import { useState } from 'react'
import { TbRotate } from 'react-icons/tb'
import { Button } from './ui/button.js'
import { useSnapshot } from '../lib/snapshot.js'

export function BarraSalvar({
  mudou, salvo, invalido, motivoInvalido, rodando, aoSalvar, aoDescartar,
}: {
  mudou: boolean
  salvo: boolean
  /** Bloqueia o salvamento — há valor fora da faixa aceita. */
  invalido?: boolean
  motivoInvalido?: string
  /** O executor está no ar; só então faz sentido oferecer o reinício. */
  rodando: boolean
  aoSalvar: () => Promise<void> | void
  aoDescartar: () => void
}) {
  const [ocupado, setOcupado] = useState(false)
  const [reiniciado, setReiniciado] = useState(false)
  // Execuções em andamento — a drenagem espera por elas. Vem do contexto, e não
  // de prop: assim o tick de 1 Hz do snapshot re-renderiza esta barra, e não as
  // telas de configuração inteiras que a contêm.
  const execucoes = useSnapshot()?.running_count

  if (!mudou && !salvo) return null

  async function reiniciar() {
    setOcupado(true)
    try {
      // Um canal só: o main faz `stop()` e depois `start()`, nesta ordem. Aqui
      // não dá mais para sequenciar com dois invokes — `parar` volta na hora, e
      // o `iniciar` seguinte chegaria com o processo antigo ainda drenando.
      await window.atlas.reiniciar()
      setReiniciado(true)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="sticky bottom-0 -mx-6 -mb-16 flex flex-wrap items-center gap-3 border-t bg-background/95 px-6 py-3 backdrop-blur">
      {mudou ? (
        <>
          <Button disabled={invalido || ocupado} onClick={() => { setReiniciado(false); void aoSalvar() }}>
            Salvar alterações
          </Button>
          <Button variant="ghost" disabled={ocupado} onClick={aoDescartar}>Descartar</Button>
          <span className="text-xs text-muted-foreground">
            {invalido
              ? (motivoInvalido ?? 'Há um valor fora da faixa aceita.')
              : rodando
                ? 'O executor lê estes ajustes ao iniciar — dá para reiniciá-lo aqui depois de salvar.'
                : 'Será aplicado quando o executor iniciar.'}
          </span>
        </>
      ) : reiniciado ? (
        <span className="text-xs text-muted-foreground">
          Executor reiniciado — os ajustes estão valendo.
        </span>
      ) : rodando ? (
        <>
          <Button size="sm" variant="secondary" disabled={ocupado} onClick={reiniciar}>
            <TbRotate size={15} className={ocupado ? 'animate-spin' : undefined} />
            {ocupado ? 'Reiniciando…' : 'Reiniciar agora'}
          </Button>
          <span className="text-xs text-muted-foreground">
            Salvo. O executor precisa reiniciar para aplicar
            {/* A drenagem espera os workflows terminarem — pode não ser
                instantâneo, e a pessoa merece saber ANTES de clicar. */}
            {typeof execucoes === 'number' && execucoes > 0
              ? ` — ${execucoes} execução(ões) em andamento terminam antes.`
              : '.'}
          </span>
        </>
      ) : (
        <span className="text-xs text-muted-foreground">
          Salvo. Vale a partir do próximo início do executor.
        </span>
      )}
    </div>
  )
}
