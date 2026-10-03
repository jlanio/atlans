import { useSearchParams, usePathname, useRouter } from "next/navigation"
import { useUrlParam } from "@/app/hooks/useUrlParam"

export const useLinkNodeParams = () => {
  const { value: linkNodeIdParam }   = useUrlParam('ndid')
  const { value: linkHandleIdParam } = useUrlParam('ndhid')
  const searchParams = useSearchParams()
  const pathname     = usePathname()
  const router       = useRouter()

  const setLinkNodeParam = (nodeId: string, handleNodeId?: string) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('ndid', nodeId)
    if (handleNodeId) params.set('ndhid', handleNodeId)
    // `replace`, not `push`: ephemeral UI param (connection drawer). See useUrlParam.
    router.replace(`${pathname}/?${params.toString()}`)
  }

  const removeLinkNodeParam = () => {
    const params = new URLSearchParams(searchParams.toString())
    params.delete('ndid')
    params.delete('ndhid')
    // `replace`, not `push`: ephemeral UI param (connection drawer). See useUrlParam.
    router.replace(`${pathname}/?${params.toString()}`)
  }

  return { linkNodeIdParam, linkHandleIdParam, setLinkNodeParam, removeLinkNodeParam }
}

