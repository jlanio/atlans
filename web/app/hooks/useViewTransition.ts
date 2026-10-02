"use client"

import { useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"

type TransicaoDeVisao = {
  skipTransition: () => void
  ready?: Promise<void>
}

type DocumentoComTransicao = Document & {
  startViewTransition?: (cb: () => void | Promise<void>) => TransicaoDeVisao
}

// Teto de espera pelo comite da rota. Rotas já em cache comitam em poucos
// frames; a do editor (`/workflow/[id]`) baixa React Flow e Monaco e leva
// segundos — segurar a transição por todo esse tempo deixaria a tela congelada
// num retrato estático, que é pior que não ter transição alguma.
const TETO_DE_ESPERA_MS = 200
// Sondagem por `setTimeout`, e NÃO por `requestAnimationFrame`: enquanto o
// callback do `startViewTransition` não resolve, o navegador suspende a
// renderização do documento e os callbacks de rAF param de rodar. Timers não.
const INTERVALO_DA_SONDA_MS = 16

function documentoComTransicao(): DocumentoComTransicao | null {
  if (typeof document === "undefined") return null
  const doc = document as DocumentoComTransicao
  return typeof doc.startViewTransition === "function" ? doc : null
}

/**
 * Navega envolvendo a troca de rota em `document.startViewTransition`.
 *
 * O callback devolve uma PROMESSA que só resolve quando a rota comitou de fato.
 * Sem isso — que era o caso — `router.push` do App Router retorna com o DOM
 * ainda inalterado: o navegador tirava o retrato "novo" da MESMA tela e cruzava
 * dois retratos idênticos. O resultado era o efeito exatamente invertido do
 * pretendido: a página inteira piscava e deslizava os 4px do `vt-fade-in` sem
 * trocar de rota, e a troca real, segundos depois, acontecia sem transição
 * nenhuma. Era a "mexida" da listagem de projetos ao abrir um workflow.
 *
 * Se a rota não comitar dentro do teto, `skipTransition()` descarta a animação:
 * sem mudança de DOM não há o que animar, e animar assim mesmo é o bug.
 */
function navegarComTransicao(navegar: () => void, href: string) {
  const doc = documentoComTransicao()
  if (!doc) {
    navegar()
    return
  }

  // `location.pathname` é o sinal de comite observável de fora do Next: o App
  // Router sincroniza o histórico num `useInsertionEffect`, ou seja, na fase de
  // commit da nova rota e antes do paint.
  const destino = new URL(href, window.location.href).pathname
  // Objeto-portador em vez de `let`: o callback abaixo lê a transição que o
  // próprio `startViewTransition` devolve. Ele só é chamado depois que a
  // atribuição aconteceu, mas escrever a referência direta dentro do
  // inicializador da própria variável não passa no TS.
  const transicao: { atual?: TransicaoDeVisao } = {}

  transicao.atual = doc.startViewTransition(
    () =>
      new Promise<void>(resolve => {
        navegar()

        let pendente = true
        let sonda: ReturnType<typeof setTimeout> | null = null
        const inicio = Date.now()

        const encerrar = (comitou: boolean) => {
          if (!pendente) return
          pendente = false
          if (sonda) clearTimeout(sonda)
          if (!comitou) transicao.atual?.skipTransition()
          resolve()
        }

        const verificar = () => {
          if (window.location.pathname === destino) return encerrar(true)
          if (Date.now() - inicio >= TETO_DE_ESPERA_MS) return encerrar(false)
          sonda = setTimeout(verificar, INTERVALO_DA_SONDA_MS)
        }

        sonda = setTimeout(verificar, INTERVALO_DA_SONDA_MS)
      }),
  )

  // `ready` rejeita com AbortError quando a transição é pulada — sem este
  // `catch` o descarte deliberado aparece no console como erro não tratado.
  transicao.atual?.ready?.catch(() => {})
}

// Wrapper do `useRouter` do Next.js. Em navegadores sem View Transitions
// (Firefox, Safari <18) cai no comportamento padrão.
//
// Uso:
//   const router = useViewTransitionRouter()
//   router.push("/projects")
export function useViewTransitionRouter() {
  const router = useRouter()

  const push = useCallback(
    (href: string) => navegarComTransicao(() => router.push(href), href),
    [router],
  )

  // `useMemo`: quem consome isto deriva callbacks com `[router]` na dependência
  // e os entrega a listas memoizadas. Um objeto novo a cada render invalidava
  // essas dependências sempre, e o `React.memo` dos cards de /projects nunca
  // acertava — a lista inteira re-renderizava a cada tecla da busca, que é
  // exatamente o que a memoização de lá diz estar evitando. O `useRouter` do
  // App Router já devolve instância estável, então só `push` entra.
  return useMemo(
    () => ({ push, prefetch: router.prefetch }),
    [push, router],
  )
}
