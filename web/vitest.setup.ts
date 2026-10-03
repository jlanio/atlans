import "@testing-library/jest-dom/vitest"

// jsdom does not implement ResizeObserver, and the Radix components that
// measure their own size (tooltip, popover, select) break with "ResizeObserver
// is not defined" on mount — before any assertion, so the error says nothing
// about what the test wanted to check.
//
// An inert polyfill on purpose: nothing here resizes, so the callback never
// needs to fire. It only serves to let the component mount.
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}

// Same story as ResizeObserver: jsdom does not implement `scrollIntoView`, and
// any component that pins the scroll to the end of a list (the assistant's
// conversation) breaks on mount, before any assertion.
// The `typeof Element` guard is not overcaution: some tests declare
// `@vitest-environment node` (the SessionSync SSR), and there is no DOM there at all.
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function () {}
}

// jsdom 30.1.0 fires `blur` on `window` when an element gains focus after the
// previously focused element has left the DOM (Testing Library's cleanup
// removes everything at the end of each test). The browser does not do this:
// there, the `window` `blur` is the window losing focus, and it comes without
// `relatedTarget`. This fake `blur` carries the element that gained focus, and
// that is how it can be told apart from the real one. Radix's DropdownMenu and
// Select close when they hear the `window` `blur`: from the second test of a
// file on, the menu opened and closed at once. jsdom 30.1.1 no longer fires
// this `blur` (it follows the spec when moving focus), and then this can go.
if (typeof window !== "undefined") {
  window.addEventListener(
    "blur",
    (evento) => {
      // The elements' `blur` events also pass through the capture phase (they do
      // not bubble up, but they travel down through `window`): only the one
      // targeting `window` itself matters. `evento.target === window` does not
      // work in Vitest: the global `window` is not the same object jsdom puts
      // in `target`.
      if (evento.eventPhase === Event.AT_TARGET && evento.relatedTarget !== null) {
        evento.stopImmediatePropagation()
      }
    },
    { capture: true },
  )
}
