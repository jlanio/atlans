"use client"

// The extensions' layers (`web/extensoes`): modals and global effects that an
// extension hangs on the shell. A separate client component because
// `SidebarRoot` is rendered on the server, and the extension registry is a
// client concern. A layer that breaks drops out alone: the shell and the others stay.

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
