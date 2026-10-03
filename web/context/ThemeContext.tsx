// app/theme-provider.tsx
"use client";

import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useState } from "react";
import Cookies from "js-cookie";

// On the server there is no layout to measure and React warns on every render.
// The choice is constant per environment, so it does not break hook order.
const useEfeitoDeLayout = typeof window !== "undefined" ? useLayoutEffect : useEffect;

type Theme = "light" | "dark";

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
}>({
  // Dark is the platform default (see the cookie fallback in app/layout.tsx).
  theme: "dark",
  setTheme: () => { },
});

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  // Placeholder until the useLayoutEffect below reads the real class of <html>
  // (before paint). Dark because it is the platform default — see app/layout.tsx.
  const [theme, setThemeState] = useState<Theme>("dark");

  // The root layout has already resolved the theme from the cookie on the server
  // and stamped the `dark` class on <html> — the class is the answer, and
  // re-reading the cookie here would only duplicate the source of truth.
  //
  // useLayoutEffect, not useEffect: dark-theme users saw a flash of light
  // components after hydration, because the correction only arrived after the
  // first paint. Here it comes in BEFORE — the reconciliation still exists, but
  // nobody sees it. (Eliminating it altogether requires the layout to pass the
  // theme resolved on the server as a prop, which cannot be done from here
  // alone.)
  useEfeitoDeLayout(() => {
    const resolvido: Theme = document.documentElement.classList.contains("dark") ? "dark" : "light";
    setThemeState(resolvido);
  }, []);

  // Stable: without this, `value` would be a new object on every provider render
  // and every useTheme() consumer would reconcile because of the new identity.
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    Cookies.set("theme", newTheme, { expires: 365 });
    document.documentElement.classList.toggle("dark", newTheme === "dark");
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};
