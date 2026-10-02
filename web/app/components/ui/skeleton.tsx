import { cn } from "@/lib/utils"

// Shimmer contínuo: comunica "dado chegando" em vez de "tela congelada".
// Gradiente animado move-se horizontalmente com background-size 200%.
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn(
        "rounded-md bg-accent/60",
        "bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.15)_50%,transparent_100%)]",
        "bg-[length:200%_100%] animate-skeleton-shimmer",
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
