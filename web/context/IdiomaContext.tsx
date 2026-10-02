"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import Cookies from "js-cookie";
import { COOKIE_DO_IDIOMA, IDIOMA_PADRAO, type Idioma, type IdiomaResolvido } from "@/lib/idioma";

interface EstadoDoIdioma extends IdiomaResolvido {
  /** Grava a escolha (cookie de 365 dias, como o tema); `null` volta ao automático. */
  escolher: (idioma: Idioma | null) => void;
}

// Sem provider (testes de componente, o portal /share) vale o português: é o
// idioma em que a Home foi escrita, e os testes que conferem texto continuam
// conferindo o mesmo texto.
const IdiomaContext = createContext<EstadoDoIdioma>({
  idioma: IDIOMA_PADRAO,
  detectado: IDIOMA_PADRAO,
  escolhido: null,
  escolher: () => {},
});

export const useIdioma = () => useContext(IdiomaContext);

/**
 * Nasce com o idioma que o servidor resolveu (`resolverIdioma` no layout do
 * dashboard) — a primeira pintura já sai no idioma certo. Trocar nas
 * Preferências re-renderiza na hora, sem recarregar: o cookie é para a PRÓXIMA
 * requisição, o estado é para esta tela.
 */
export function IdiomaProvider({
  inicial,
  children,
}: {
  inicial: IdiomaResolvido;
  children: React.ReactNode;
}) {
  const [escolhido, setEscolhido] = useState<Idioma | null>(inicial.escolhido);
  // O layout resolve de novo a cada `router.refresh()`, e o cookie pode ter
  // mudado noutra aba. Sem isto, o provider (que não remonta) ficava com a
  // escolha velha enquanto o `detectado` já vinha novo: a tela, o cookie e as
  // Preferências discordavam até o próximo F5. Uma escolha feita NESTA aba
  // não se perde: o refresh devolve o mesmo valor que ela gravou.
  const [escolhidoDoServidor, setEscolhidoDoServidor] = useState(inicial.escolhido);
  if (escolhidoDoServidor !== inicial.escolhido) {
    setEscolhidoDoServidor(inicial.escolhido);
    setEscolhido(inicial.escolhido);
  }

  const escolher = useCallback((idioma: Idioma | null) => {
    setEscolhido(idioma);
    if (idioma) Cookies.set(COOKIE_DO_IDIOMA, idioma, { expires: 365, sameSite: "lax" });
    else Cookies.remove(COOKIE_DO_IDIOMA);
  }, []);

  const value = useMemo(
    () => ({ idioma: escolhido ?? inicial.detectado, detectado: inicial.detectado, escolhido, escolher }),
    [escolhido, inicial.detectado, escolher],
  );

  return <IdiomaContext.Provider value={value}>{children}</IdiomaContext.Provider>;
}

// ── Onde a tela segue o idioma ────────────────────────────────────────────────
// Só a HOME é traduzida; a administração (editor, projetos, admin) continua em
// português. Sem este escopo, um componente compartilhado — o menu da conta, a
// conversa do assistente do editor — trocaria de idioma dentro da área de
// administração e a deixaria metade em cada língua. O padrão é `true` porque os
// testes de componente montam pedaços da Home sem layout; quem decide de
// verdade é o `EscopoPelaRota` do layout do dashboard.
const NaHome = createContext(true);

export const useNaHome = () => useContext(NaHome);

/** O mesmo critério do `ShellSidebar`: a Home é a rota `/` exata. */
export function EscopoPelaRota({ children }: { children: React.ReactNode }) {
  const naHome = usePathname() === "/";
  return <NaHome.Provider value={naHome}>{children}</NaHome.Provider>;
}
