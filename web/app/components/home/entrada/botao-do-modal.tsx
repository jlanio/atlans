"use client"

import { TbLoader2 } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * O botão das ações do modal de entrada: o `Button` da Home (terracota, pelos
 * tokens do `home-portal`) com o spinner e o rótulo de carregamento. `submit`
 * por padrão, como convém a um botão de formulário.
 */
export function BotaoDoModal({
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

/** O link de rodapé que troca de painel (Entrar ↔ Criar conta) — um botão, porque não navega. */
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
