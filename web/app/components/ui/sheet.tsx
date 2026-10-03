"use client"

import * as React from "react"
import * as SheetPrimitive from "@radix-ui/react-dialog"
import { XIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  useResizablePanel,
  type ResizablePanelOptions,
} from "@/app/hooks/useResizablePanel"

function Sheet({ ...props }: React.ComponentProps<typeof SheetPrimitive.Root>) {
  return <SheetPrimitive.Root data-slot="sheet" {...props} />
}

function SheetTrigger({
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Trigger>) {
  return <SheetPrimitive.Trigger data-slot="sheet-trigger" {...props} />
}

function SheetPortal({
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Portal>) {
  return <SheetPrimitive.Portal data-slot="sheet-portal" {...props} />
}

function SheetOverlay({
  className,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Overlay>) {
  return (
    <SheetPrimitive.Overlay
      data-slot="sheet-overlay"
      className={cn(
        "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50",
        className
      )}
      {...props}
    />
  )
}

function SheetContent({
  className,
  children,
  side = "right",
  hideCloseButton = false,
  resizable,
  style,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Content> & {
  side?: "top" | "right" | "bottom" | "left"
  hideCloseButton?: boolean
  /**
   * Makes the panel's inner edge draggable. Only for the vertical sides —
   * `top`/`bottom` would be height, and no panel needs that today.
   */
  resizable?: boolean | ResizablePanelOptions
}) {
  const vertical = side === "left" || side === "right"
  const canResize = !!resizable && vertical
  const { width, isResizing, resizeHandleProps } = useResizablePanel({
    ...(typeof resizable === "object" ? resizable : {}),
    side: side === "left" ? "left" : "right",
    enabled: canResize,
  })

  return (
    <SheetPortal>
      <SheetOverlay />
      <SheetPrimitive.Content
        data-slot="sheet-content"
        style={
          canResize
            ? { ...style, "--sheet-width": `${width}px` } as React.CSSProperties
            : style
        }
        className={cn(
          "bg-background data-[state=open]:animate-in data-[state=closed]:animate-out fixed z-50 flex flex-col gap-4 shadow-lg transition ease-in-out data-[state=closed]:duration-300 data-[state=open]:duration-500",
          side === "right" &&
            "data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right inset-y-0 right-0 h-full w-3/4 border-l sm:max-w-sm",
          side === "left" &&
            "data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left inset-y-0 left-0 h-full w-3/4 border-r sm:max-w-sm",
          side === "top" &&
            "data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top inset-x-0 top-0 h-auto border-b",
          side === "bottom" &&
            "data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom inset-x-0 bottom-0 h-auto border-t",
          className,
          // After `className` on purpose: the dragged size has to
          // beat any `w-*`/`max-w-*` the consumer may have passed.
          // Below `sm` the panel takes up the screen and there's nothing to drag.
          canResize && "sm:w-[var(--sheet-width)] sm:max-w-none",
          isResizing && "select-none"
        )}
        {...props}
      >
        {canResize && (
          <div
            {...resizeHandleProps}
            data-slot="sheet-resize-handle"
            data-resizing={isResizing || undefined}
            className={cn(
              "group absolute inset-y-0 z-10 hidden w-3 cursor-col-resize touch-none sm:block",
              "focus-visible:outline-hidden",
              side === "right" ? "-left-1.5" : "-right-1.5"
            )}
          >
            <span
              className={cn(
                "pointer-events-none absolute inset-y-0 left-1/2 w-px -translate-x-1/2 transition-colors",
                "group-hover:bg-primary/60 group-focus-visible:bg-ring",
                isResizing && "bg-primary"
              )}
            />
            <span
              className={cn(
                "bg-border pointer-events-none absolute top-1/2 left-1/2 h-8 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full opacity-0 transition-opacity",
                "group-hover:opacity-100 group-focus-visible:opacity-100",
                isResizing && "bg-primary opacity-100"
              )}
            />
          </div>
        )}
        {children}
        {!hideCloseButton && (
          <SheetPrimitive.Close className="ring-offset-background focus:ring-ring data-[state=open]:bg-secondary absolute top-4 right-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden disabled:pointer-events-none">
            <XIcon className="size-4" />
            <span className="sr-only">Fechar</span>
          </SheetPrimitive.Close>
        )}
      </SheetPrimitive.Content>
    </SheetPortal>
  )
}

function SheetHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-header"
      className={cn("flex flex-col gap-1.5 p-4", className)}
      {...props}
    />
  )
}

function SheetTitle({
  className,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Title>) {
  return (
    <SheetPrimitive.Title
      data-slot="sheet-title"
      className={cn("text-foreground font-semibold", className)}
      {...props}
    />
  )
}

function SheetDescription({
  className,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Description>) {
  return (
    <SheetPrimitive.Description
      data-slot="sheet-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

export {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
}
