// app/theme-provider.tsx
"use client";

import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useState } from "react";
import Cookies from "js-cookie";

// No servidor não existe layout a medir e o React avisa em toda renderização.
// A escolha é constante por ambiente, então não quebra a ordem dos hooks.
const useEfeitoDeLayout = typeof window !== "undefined" ? useLayoutEffect : useEffect;

type Theme = "light" | "dark";

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (theme: Theme) => void;
}>({
  // Dark é o padrão da plataforma (ver o fallback do cookie em app/layout.tsx).
  theme: "dark",
  setTheme: () => { },
});

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  // Placeholder até o useLayoutEffect abaixo ler a classe real do <html> (antes
  // do paint). Dark por ser o padrão da plataforma — ver app/layout.tsx.
  const [theme, setThemeState] = useState<Theme>("dark");

  // O root layout já resolveu o tema pelo cookie no servidor e carimbou a classe
  // `dark` no <html> — a classe é a resposta, e reler o cookie aqui só duplicaria
  // a fonte da verdade.
  //
  // useLayoutEffect, e não useEffect: quem usa tema escuro via um lampejo de
  // componentes claros depois da hidratação, porque a correção só chegava depois
  // do primeiro paint. Aqui ela entra ANTES — o reconcílio continua existindo,
  // mas ninguém o enxerga. (Eliminá-lo de vez exige o layout passar o tema
  // resolvido no servidor como prop, o que não dá para fazer só daqui.)
  useEfeitoDeLayout(() => {
    const resolvido: Theme = document.documentElement.classList.contains("dark") ? "dark" : "light";
    setThemeState(resolvido);
  }, []);

  // Estável: sem isto, `value` seria um objeto novo a cada render do provider e
  // todo consumidor de useTheme() reconciliaria por identidade nova.
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
