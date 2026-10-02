import { ReactNode } from "react"

// Fade de entrada em CSS puro (tw-animate-css, importado no globals.css).
// Antes isto era um motion.div: as 12 rotas que usam PageRoot baixavam e
// parseavam o framer-motion inteiro antes do primeiro paint só para animar
// opacity/translateY do contêiner. Sem o motion, o componente também deixa de
// precisar de "use client" e passa a renderizar no servidor.
const PageRoot = ({ children }: { children: ReactNode }) => {
  return (
    // Padding menor no telefone: `px-8` fixo comia 64px dos 360px da tela mais
    // estreita que suportamos, e sobrava menos de 300px para o conteúdo. O
    // `px-safe` cobre o notch em paisagem, onde o recorte fica na lateral.
    <main className="flex justify-center w-full px-safe">
      <div className="flex flex-col gap-4 px-4 py-6 sm:gap-6 sm:px-8 sm:py-8 max-w-6xl w-full animate-in fade-in slide-in-from-bottom-2 duration-350 ease-out">
        {children}
      </div>
    </main>
  )
}

export default PageRoot
