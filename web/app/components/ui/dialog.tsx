"use client"

import * as React from "react"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { XIcon } from "lucide-react"

import { cn } from "@/lib/utils"

function Dialog({
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Root>) {
  return <DialogPrimitive.Root data-slot="dialog" {...props} />
}

function DialogTrigger({
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Trigger>) {
  return <DialogPrimitive.Trigger data-slot="dialog-trigger" {...props} />
}

function DialogPortal({
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Portal>) {
  return <DialogPrimitive.Portal data-slot="dialog-portal" {...props} />
}

function DialogClose({
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Close>) {
  return <DialogPrimitive.Close data-slot="dialog-close" {...props} />
}

function DialogOverlay({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      data-slot="dialog-overlay"
      className={cn(
        "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50",
        className
      )}
      {...props}
    />
  )
}

function DialogContent({
  className,
  children,
  showCloseButton = true,
  closeDisabled = false,
  bloqueado = false,
  closeLabel = "Fechar",
  overlayClassName,
  onEscapeKeyDown,
  onInteractOutside,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Content> & {
  showCloseButton?: boolean
  /** The screen-reader name of the `X` — the translated Home passes its language's. */
  closeLabel?: string
  /**
   * Classes of the scrim behind the dialog. Without the prop, the usual
   * `bg-black/50`; the Home's sign-in modal passes a lighter scrim, so the globe
   * stays visible behind it.
   */
  overlayClassName?: string
  /**
   * Disables ONLY the `X`, without hiding it. For the "operation in flight" case,
   * prefer `bloqueado`, which locks all three exits at once.
   *
   * `false` by default — no existing dialog changes behavior.
   */
  closeDisabled?: boolean
  /**
   * Operation in flight: locks the dialog's THREE exits — Esc, click outside and
   * the `X` (disabled, not hidden). Closing in the middle of a submit leaves the
   * person not knowing whether it happened. Before, each dialog copied the trio
   * `onEscapeKeyDown` + `onInteractOutside` + `closeDisabled`, and whoever forgot
   * one of the three left an exit open. Cancel belongs to the dialog: whoever
   * passes `bloqueado` disables theirs along with it.
   *
   * The caller's `onEscapeKeyDown`/`onInteractOutside` keep running.
   * `false` by default — no existing dialog changes behavior.
   */
  bloqueado?: boolean
}) {
  return (
    <DialogPortal data-slot="dialog-portal">
      <DialogOverlay className={overlayClassName} />
      <DialogPrimitive.Content
        data-slot="dialog-content"
        onEscapeKeyDown={e => { onEscapeKeyDown?.(e); if (bloqueado) e.preventDefault() }}
        onInteractOutside={e => { onInteractOutside?.(e); if (bloqueado) e.preventDefault() }}
        className={cn(
          "bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border p-6 shadow-lg duration-200 sm:max-w-lg",
          // Height ceiling + its own scrolling. Without this tall content (a
          // postgresql credential form has 5 fields + descriptions +
          // test result + footer) spilled out of the viewport WITHOUT
          // scroll: Radix locks the body scroll and the content didn't scroll, so
          // title and buttons became unreachable on a short screen.
          //
          // 100dvh (not vh) because of the mobile address bar, which changes the
          // visible height while scrolling.
          "max-h-[calc(100dvh-2rem)] overflow-y-auto",
          className
        )}
        {...props}
      >
        {children}
        {showCloseButton && (
          <DialogPrimitive.Close
            data-slot="dialog-close"
            disabled={closeDisabled || bloqueado}
            className="text-foreground ring-offset-background focus:ring-ring data-[state=open]:bg-accent data-[state=open]:text-muted-foreground absolute top-4 right-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4"
          >
            <XIcon />
            <span className="sr-only">{closeLabel}</span>
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </DialogPortal>
  )
}

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex flex-col gap-2 text-center sm:text-left", className)}
      {...props}
    />
  )
}

function DialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "flex flex-col-reverse gap-2 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    />
  )
}

function DialogTitle({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn("text-foreground text-lg leading-none font-semibold", className)}
      {...props}
    />
  )
}

function DialogDescription({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}
