// web/lib/respostas.ts
//
// O que uma tela faz com a `IResponse` que o `GisFlowService` devolve.
//
// O transporte (service/http.ts) NUNCA rejeita: a queda de rede, o 4xx e o 5xx
// voltam resolvidos, com `error` preenchido e `data` indefinido. Um `try/catch`
// em volta da chamada é código morto — e quem lê só o `data` transforma a falha
// numa afirmação falsa. Foi o que aconteceu no editor: o log de uma execução
// "expirou" quando a rede caiu, e as execuções recentes e os seletores de
// artefato e de arquivo do Drive diziam "nenhum" quando nem tinham perguntado.
//
// O padrão é o das telas vizinhas do editor (histórico de versões, pins,
// cancelar execução): um toast com o título da tela e a mensagem do servidor.

import type { IResponse } from "@/service/types"
import { createToast } from "@/utils/createToast"

/**
 * O dado da resposta — ou `null`, depois de avisar a falha num toast.
 *
 * `null` quer dizer "não sei", e não "vazio": a lista que o recebe não pode
 * cair no estado de "nenhum item", que é o que a pessoa leria como resposta.
 * Uma resposta sem corpo também volta `null`; é para leituras, que sempre têm.
 */
export function dadoOuAviso<T>(res: IResponse<T>, titulo: string): T | null {
  if (res.error) {
    createToast.error(titulo, res.error.message)
    return null
  }
  return res.data ?? null
}
