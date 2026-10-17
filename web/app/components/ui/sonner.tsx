"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner, ToasterProps } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      style={
        {
          // sonner injects `font-family: ui-sans-serif, system-ui…` on the
          // toaster, outside any layer — a utility can't beat it. Inline,
          // the toast inherits the app font (Inter) like the rest of the page.
          fontFamily: "inherit",
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
        } as React.CSSProperties
      }
      // Beside an assistant panel on screen, or above its field on the phone
      // (`useToastsForaDoPainel`, `globals.css`); sonner's own 24px and 16px
      // otherwise. `min()`: on a narrow screen, or with the panel dragged wide,
      // beside it would push the toast off the left edge — it stops 16px short.
      offset={{
        right: "min(calc(24px + var(--toasts-recuo-direita, 0px)), calc(100vw - var(--width) - 16px))",
        bottom: "calc(24px + var(--toasts-recuo-baixo, 0px))",
      }}
      mobileOffset={{ bottom: "calc(16px + var(--toasts-recuo-baixo, 0px))" }}
      {...props}
    />
  )
}

export { Toaster }
