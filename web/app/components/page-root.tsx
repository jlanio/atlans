import { ReactNode } from "react"

// Entrance fade in pure CSS (tw-animate-css, imported in globals.css).
// This used to be a motion.div: the 12 routes that use PageRoot downloaded and
// parsed the whole framer-motion before the first paint just to animate the
// container's opacity/translateY. Without motion, the component also no longer
// needs "use client" and renders on the server.
const PageRoot = ({ children }: { children: ReactNode }) => {
  return (
    // Smaller padding on the phone: a fixed `px-8` ate 64px of the 360px of the
    // narrowest screen we support, leaving less than 300px for the content.
    // `px-safe` covers the notch in landscape, where the cutout is on the side.
    <main className="flex justify-center w-full px-safe">
      <div className="flex flex-col gap-4 px-4 py-6 sm:gap-6 sm:px-8 sm:py-8 max-w-6xl w-full animate-in fade-in slide-in-from-bottom-2 duration-350 ease-out">
        {children}
      </div>
    </main>
  )
}

export default PageRoot
