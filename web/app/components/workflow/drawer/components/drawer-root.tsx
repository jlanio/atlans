import { ReactNode } from "react"

interface DrawerRootProps {
  children: ReactNode
}

const DrawerRoot = ({ children }: DrawerRootProps) => {
  return (
    // 26rem são 416px — mais largo que a tela inteira de um telefone (360-390px),
    // então lá o drawer ocupa a largura toda. O `min-w` só volta a partir de
    // `sm`, onde ele de fato divide espaço com o canvas.
    <div className="flex flex-col w-full sm:w-[26rem] sm:min-w-[26rem] overflow-y-hidden bg-card h-full">
      {children}
    </div>
  )
}

export default DrawerRoot