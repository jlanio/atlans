import { cn } from "@/lib/utils"

// Continuous shimmer: conveys "data arriving" instead of "frozen screen".
// An animated gradient moves horizontally with background-size 200%.
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
