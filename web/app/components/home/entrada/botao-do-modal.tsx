"use client"

import { TbLoader2 } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * The button for the sign-in modal's actions: the Home's `Button` (terracotta,
 * via the `home-portal` tokens) with the spinner and the loading label. `submit`
 * by default, as befits a form button.
 */
export function ModalButton({
  loading = false,
  loadingLabel,
  disabled,
  className,
  children,
  type = "submit",
  ...props
}: React.ComponentProps<typeof Button> & { loading?: boolean; loadingLabel?: string }) {
  return (
    <Button
      type={type}
      disabled={loading || disabled}
      className={cn("h-11 w-full gap-2 text-sm font-semibold", className)}
      {...props}
    >
      {loading ? (
        <>
          <TbLoader2 size={16} className="motion-safe:animate-spin" aria-hidden="true" />
          {loadingLabel}
        </>
      ) : (
        children
      )}
    </Button>
  )
}

/** The footer link that switches panels (Entrar ↔ Criar conta) — a button, because it does not navigate. */
export function LinkDoModal({ className, ...props }: React.ComponentProps<"button">) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex min-h-10 items-center rounded-sm text-primary underline underline-offset-4 transition-colors hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  )
}
