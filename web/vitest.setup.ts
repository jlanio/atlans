import "@testing-library/jest-dom/vitest"

// O jsdom não implementa ResizeObserver, e os componentes do Radix que medem o
// próprio tamanho (tooltip, popover, select) quebram com "ResizeObserver is not
// defined" ao montar — antes de qualquer asserção, então o erro não diz nada
// sobre o que o teste queria verificar.
//
// Polyfill inerte de propósito: nada aqui redimensiona, então o callback nunca
// precisa disparar. Serve só para o componente montar.
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}

// Mesma história do ResizeObserver: o jsdom não implementa `scrollIntoView`, e
// qualquer componente que gruda a rolagem no fim de uma lista (a conversa do
// assistente) quebra ao montar, antes de qualquer asserção.
// A guarda de `typeof Element` não é zelo: alguns testes declaram
// `@vitest-environment node` (o SSR do SessionSync), e lá não existe DOM nenhum.
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function () {}
}

// O jsdom 30.1.0 dispara `blur` no `window` quando um elemento ganha o foco
// depois que o elemento focado antes saiu do DOM (o cleanup do Testing Library
// tira tudo ao fim de cada teste). O navegador não faz isso: lá, o `blur` do
// `window` é a janela perdendo o foco, e vem sem `relatedTarget`. Este `blur`
// falso traz o elemento que ganhou o foco, e assim dá para separá-lo do
// verdadeiro. O DropdownMenu e o Select do Radix fecham ao ouvir o `blur` do
// `window`: do segundo teste de um arquivo em diante, o menu abria e fechava na
// mesma hora. O jsdom 30.1.1 já não dispara esse `blur` (ele segue a
// especificação ao mover o foco), e aí isto pode sair.
if (typeof window !== "undefined") {
  window.addEventListener(
    "blur",
    (evento) => {
      // Na fase de captura passam também os `blur` dos elementos (não sobem,
      // mas descem pelo `window`): só o que tem o próprio `window` como alvo
      // interessa. `evento.target === window` não serve no Vitest: o `window`
      // global não é o mesmo objeto que o jsdom põe no `target`.
      if (evento.eventPhase === Event.AT_TARGET && evento.relatedTarget !== null) {
        evento.stopImmediatePropagation()
      }
    },
    { capture: true },
  )
}
