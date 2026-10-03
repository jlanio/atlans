// web/app/hooks/useExecutorLocal.ts
//
// Status of THIS machine's executor, when the UI runs inside the desktop app.
//
// Outside the desktop (a regular browser) the bridge does not exist and the hook
// returns `null` forever — consumers must treat `null` as "show nothing".
'use client'
import { useEffect, useState } from 'react'
import { ponteDesktop, type StatusExecutorLocal } from '@/lib/desktop'

export function useExecutorLocal(): StatusExecutorLocal | null {
  const [status, setStatus] = useState<StatusExecutorLocal | null>(null)

  useEffect(() => {
    const ponte = ponteDesktop()
    if (!ponte) return

    let vivo = true
    // The first render comes from the pull; changes arrive through the push.
    ponte.obterStatus().then((s) => { if (vivo) setStatus(s) }).catch(() => { /* ignora */ })
    const cancelar = ponte.aoMudarStatus((s) => setStatus(s))

    return () => { vivo = false; cancelar() }
  }, [])

  return status
}
