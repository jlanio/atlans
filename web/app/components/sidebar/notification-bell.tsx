"use client"

import { useState } from "react"
import { TbBell, TbBellRinging, TbCheck, TbX, TbCircleCheck, TbAlertCircle } from "react-icons/tb"
import { useNotifications, AppNotification } from "@/context/NotificationsContext"
import { formatarQuando } from "@/lib/formatos"
import { cn } from "@/lib/utils"
import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { SidebarMenuButton } from "../ui/sidebar"

function NotificationItem({ n }: { n: AppNotification }) {
  // Tempo relativo pela mesma régua das outras telas (grão grosso "há N min/h",
  // depois calendário) em vez do cálculo caseiro — o timestamp é um Date local,
  // então normalizamos para ISO antes de passar ao formatador do contrato.
  const quando = formatarQuando(n.timestamp.toISOString())

  return (
    <div className={cn(
      "flex gap-2.5 px-3 py-2.5 border-b border-border last:border-0",
      !n.read && "bg-muted/40"
    )}>
      {/* Ícone de estado nos pares de status canônicos, com o par dark: — sucesso
          em verde, falha no token destrutivo (§6 do contrato). */}
      <div className="mt-0.5 shrink-0">
        {n.type === "success"
          ? (
            <span className="flex size-5 items-center justify-center rounded-full bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400">
              <TbCircleCheck size={13} aria-hidden="true" />
            </span>
          )
          : (
            <span className="flex size-5 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <TbAlertCircle size={13} aria-hidden="true" />
            </span>
          )
        }
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium leading-tight">{n.title}</p>
        {n.message && (
          <p className="text-[11px] text-muted-foreground mt-0.5 leading-tight line-clamp-2">{n.message}</p>
        )}
      </div>
      <span className="text-[10px] text-muted-foreground shrink-0 mt-0.5 tabular-nums">{quando}</span>
    </div>
  )
}

const NotificationBell = () => {
  const { notifications, unreadCount, markAllRead, clearAll } = useNotifications()
  const [open, setOpen] = useState(false)

  function handleOpen(v: boolean) {
    setOpen(v)
    if (v && unreadCount > 0) markAllRead()
  }

  const BellIcon = unreadCount > 0 ? TbBellRinging : TbBell

  return (
    <DropdownMenu open={open} onOpenChange={handleOpen}>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton tooltip="Notificações" className="relative">
          <div className="relative">
            <BellIcon className={cn("size-4", unreadCount > 0 && "text-primary")} />
            {unreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-primary text-[8px] font-bold text-primary-foreground ring-2 ring-sidebar">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </div>
          <span>Notificações</span>
        </SidebarMenuButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="right"
        align="end"
        sideOffset={8}
        className="z-50 w-72 rounded-lg border border-border bg-popover shadow-lg overflow-hidden p-0"
      >
        <div className="flex items-center justify-between px-3 py-2 border-b border-border">
          <p className="text-xs font-semibold">Notificações</p>
          {notifications.length > 0 && (
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={clearAll} title="Limpar tudo">
              <TbX size={13} />
            </Button>
          )}
        </div>

        <div className="max-h-72 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 gap-2 text-muted-foreground">
              <TbCheck size={22} />
              <p className="text-xs">Nenhuma notificação</p>
            </div>
          ) : (
            notifications.map(n => <NotificationItem key={n.id} n={n} />)
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default NotificationBell
