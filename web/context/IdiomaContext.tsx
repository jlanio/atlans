"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import Cookies from "js-cookie";
import { LANGUAGE_COOKIE, DEFAULT_LANGUAGE, type Idioma, type ResolvedLanguage } from "@/lib/idioma";

interface LanguageState extends ResolvedLanguage {
  /** Stores the choice (365-day cookie, like the theme); `null` goes back to automatic. */
  escolher: (idioma: Idioma | null) => void;
}

// Without a provider (component tests, the /share portal) Portuguese applies:
// it is the language the Home was written in, and the tests that check text
// keep checking the same text.
const IdiomaContext = createContext<LanguageState>({
  idioma: DEFAULT_LANGUAGE,
  detectado: DEFAULT_LANGUAGE,
  escolhido: null,
  escolher: () => {},
});

export const useLanguage = () => useContext(IdiomaContext);

/**
 * Starts with the language the server resolved (`resolverIdioma` in the
 * dashboard layout) — the first paint already comes out in the right language.
 * Changing it in Preferences re-renders right away, without reloading: the
 * cookie is for the NEXT request, the state is for this screen.
 */
export function LanguageProvider({
  inicial,
  children,
}: {
  inicial: ResolvedLanguage;
  children: React.ReactNode;
}) {
  const [escolhido, setChosen] = useState<Idioma | null>(inicial.escolhido);
  // The layout resolves again on every `router.refresh()`, and the cookie may
  // have changed in another tab. Without this, the provider (which does not
  // remount) kept the old choice while `detectado` was already new: the screen,
  // the cookie and Preferences disagreed until the next F5. A choice made in
  // THIS tab is not lost: the refresh returns the same value it stored.
  const [serverChoice, setServerChoice] = useState(inicial.escolhido);
  if (serverChoice !== inicial.escolhido) {
    setServerChoice(inicial.escolhido);
    setChosen(inicial.escolhido);
  }

  const escolher = useCallback((idioma: Idioma | null) => {
    setChosen(idioma);
    if (idioma) Cookies.set(LANGUAGE_COOKIE, idioma, { expires: 365, sameSite: "lax" });
    else Cookies.remove(LANGUAGE_COOKIE);
  }, []);

  const value = useMemo(
    () => ({ idioma: escolhido ?? inicial.detectado, detectado: inicial.detectado, escolhido, escolher }),
    [escolhido, inicial.detectado, escolher],
  );

  return <IdiomaContext.Provider value={value}>{children}</IdiomaContext.Provider>;
}

// ── Where the screen follows the language ─────────────────────────────────────
// Only the HOME is translated; the administration (editor, projects, admin)
// stays in Portuguese. Without this scope, a shared component — the account
// menu, the editor's assistant conversation — would switch language inside the
// administration area and leave it half in each language. The default is
// `true` because component tests mount pieces of the Home without a layout;
// what really decides is the dashboard layout's `EscopoPelaRota`.
const NaHome = createContext(true);

export const useNaHome = () => useContext(NaHome);

/** The same criterion as `ShellSidebar`: the Home is the exact `/` route. */
export function ScopeByRoute({ children }: { children: React.ReactNode }) {
  const naHome = usePathname() === "/";
  return <NaHome.Provider value={naHome}>{children}</NaHome.Provider>;
}
