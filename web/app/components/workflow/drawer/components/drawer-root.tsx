import { ReactNode } from "react"

interface DrawerRootProps {
  children: ReactNode
}

const DrawerRoot = ({ children }: DrawerRootProps) => {
  return (
    // 26rem is 416px — wider than a phone's entire screen (360-390px), so there
    // the drawer takes the full width. The `min-w` only comes back from `sm`
    // up, where it actually shares space with the canvas.
    <div className="flex flex-col w-full sm:w-[26rem] sm:min-w-[26rem] overflow-y-hidden bg-card h-full">
      {children}
    </div>
  )
}

export default DrawerRoot