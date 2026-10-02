// web/lib/consultas.ts
//
// O cliente do @tanstack/react-query, com os padrões das telas de HOJE.
//
// A camada de dados migra tela a tela (docs/specs/padrao-telas.md §10). Cada
// padrão abaixo reproduz o que os hooks feitos à mão já fazem, para que migrar
// uma tela não mude o que ela mostra: repetir, reler no foco ou guardar cache é
// decisão de cada consulta, declarada nela — nunca herança silenciosa daqui.

import { QueryClient } from "@tanstack/react-query"

export function criarClienteDeConsultas(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Nenhuma tela repete uma leitura que falhou: a falha vira, na hora, o
        // cartão de erro (1ª carga) ou o aviso da recarga. O padrão da
        // biblioteca (três novas tentativas, 1 s + 2 s + 4 s) seguraria o
        // skeleton por uns 7 s antes de mostrar o erro.
        retry: false,
        // Nenhuma tela relê ao voltar o foco nem ao reconectar. Quem faz
        // polling liga os dois na própria consulta (ver §10).
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        // Sem cache: toda montagem e toda troca de filtro buscam de novo, com
        // o skeleton — é o que as telas fazem hoje. Quem quer cache (o TTL do
        // Histórico) declara `staleTime` e `gcTime` na própria consulta.
        staleTime: 0,
        gcTime: 0,
        // A requisição sai mesmo com `navigator.onLine` falso, como hoje, e a
        // queda vira erro. No modo padrão ("online") a consulta ficaria
        // pausada: skeleton sem fim, sem cartão de erro.
        networkMode: "always",
      },
      mutations: {
        networkMode: "always",
      },
    },
  })
}
