"use client"

// As camadas das extensões (`web/extensoes`): modais e efeitos globais que uma
// extensão pendura na casca. Componente de cliente à parte porque o
// `SidebarRoot` é renderizado no servidor, e o registro das extensões é coisa
// do cliente. Uma camada que quebra sai sozinha: a casca e as outras ficam.

import { EXTENSOES, LimiteDaExtensao } from "@/extensoes"

export function CamadasDasExtensoes() {
  return (
    <>
      {EXTENSOES.flatMap(extensao =>
        (extensao.camadas ?? []).map((Camada, i) => (
          <LimiteDaExtensao key={`${extensao.nome}:${i}`} nome={extensao.nome}>
            <Camada />
          </LimiteDaExtensao>
        )),
      )}
    </>
  )
}
