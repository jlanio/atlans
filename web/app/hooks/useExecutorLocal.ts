// web/app/hooks/useExecutorLocal.ts
//
// Status do executor DESTA máquina, quando a UI roda dentro do app desktop.
//
// Fora do desktop (navegador comum) a ponte não existe e o hook devolve `null`
// para sempre — quem consome deve tratar `null` como "não mostrar nada".
'use client'
import { useEffect, useState } from 'react'
import { ponteDesktop, type StatusExecutorLocal } from '@/lib/desktop'

export function useExecutorLocal(): StatusExecutorLocal | null {
  const [status, setStatus] = useState<StatusExecutorLocal | null>(null)

  useEffect(() => {
    const ponte = ponteDesktop()
    if (!ponte) return

    let vivo = true
    // Primeiro render vem do pull; as mudanças chegam pelo push.
    ponte.obterStatus().then((s) => { if (vivo) setStatus(s) }).catch(() => { /* ignora */ })
    const cancelar = ponte.aoMudarStatus((s) => setStatus(s))

    return () => { vivo = false; cancelar() }
  }, [])

  return status
}
