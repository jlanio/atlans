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
    // No handle id is an anonymous output, and then the previous `ndhid` has to
    // GO: a "+" on a named port followed by a "+" on an anonymous output kept the
    // old one, and the new edge left from a handle its source does not have —
    // React Flow does not draw it, and it was saved like that.
    if (handleNodeId) params.set('ndhid', handleNodeId)
    else params.delete('ndhid')
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

