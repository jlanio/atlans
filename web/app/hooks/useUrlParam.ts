import { useSearchParams, usePathname, useRouter } from "next/navigation"

// Hook base para gerenciar um parâmetro de URL
export function useUrlParam(key: string) {
  const searchParams = useSearchParams()
  const pathname     = usePathname()
  const router       = useRouter()

  const value = searchParams.get(key) as string | undefined

  function set(val: string) {
    const params = new URLSearchParams(searchParams.toString())
    params.set(key, val)
    // `replace`, nao `push`: `cn`/`ndid`/`ndhid` sao params EFEMEROS de UI (modal
    // de config, drawer de conexao). `push` empilhava uma entrada de historico a
    // cada abrir/fechar, e o Voltar do navegador reabria um modal ja fechado.
    router.replace(`${pathname}/?${params.toString()}`)
  }

  function remove() {
    const params = new URLSearchParams(searchParams.toString())
    params.delete(key)
    // `replace`, nao `push`: `cn`/`ndid`/`ndhid` sao params EFEMEROS de UI (modal
    // de config, drawer de conexao). `push` empilhava uma entrada de historico a
    // cada abrir/fechar, e o Voltar do navegador reabria um modal ja fechado.
    router.replace(`${pathname}/?${params.toString()}`)
  }

  return { value, set, remove }
}
