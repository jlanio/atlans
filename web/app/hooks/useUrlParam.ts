import { useSearchParams, usePathname, useRouter } from "next/navigation"

// Base hook to manage a URL parameter
export function useUrlParam(key: string) {
  const searchParams = useSearchParams()
  const pathname     = usePathname()
  const router       = useRouter()

  const value = searchParams.get(key) as string | undefined

  function set(val: string) {
    const params = new URLSearchParams(searchParams.toString())
    params.set(key, val)
    // `replace`, not `push`: `cn`/`ndid`/`ndhid` are EPHEMERAL UI params (config
    // modal, connection drawer). `push` stacked a history entry on every
    // open/close, and the browser's Back reopened an already-closed modal.
    router.replace(`${pathname}/?${params.toString()}`)
  }

  function remove() {
    const params = new URLSearchParams(searchParams.toString())
    params.delete(key)
    // `replace`, not `push`: `cn`/`ndid`/`ndhid` are EPHEMERAL UI params (config
    // modal, connection drawer). `push` stacked a history entry on every
    // open/close, and the browser's Back reopened an already-closed modal.
    router.replace(`${pathname}/?${params.toString()}`)
  }

  return { value, set, remove }
}
