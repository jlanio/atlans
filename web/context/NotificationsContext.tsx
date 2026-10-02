"use client"

import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from "react"

export interface AppNotification {
  id: string
  type: "success" | "error" | "info"
  title: string
  message?: string
  timestamp: Date
  read: boolean
}

interface NotificationsContextValue {
  notifications: AppNotification[]
  unreadCount: number
  addNotification: (n: Omit<AppNotification, "id" | "timestamp" | "read">) => void
  markAllRead: () => void
  clearAll: () => void
}

const NotificationsContext = createContext<NotificationsContextValue | null>(null)

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([])

  const addNotification = useCallback((n: Omit<AppNotification, "id" | "timestamp" | "read">) => {
    const notification: AppNotification = {
      ...n,
      id: crypto.randomUUID(),
      timestamp: new Date(),
      read: false,
    }
    setNotifications(prev => [notification, ...prev].slice(0, 50))
  }, [])

  const markAllRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }, [])

  const clearAll = useCallback(() => {
    setNotifications([])
  }, [])

  // Memo pelo mesmo motivo dos demais providers da raiz do dashboard: objeto
  // novo a cada render arrastava toda a árvore junto. `addNotification` entra
  // como dep do efeito de polling do ActiveRunsContext, então precisa ser
  // estável — e é, por já vir de useCallback sem deps.
  const value = useMemo<NotificationsContextValue>(() => ({
    notifications,
    unreadCount: notifications.filter(n => !n.read).length,
    addNotification,
    markAllRead,
    clearAll,
  }), [notifications, addNotification, markAllRead, clearAll])

  return (
    <NotificationsContext.Provider value={value}>
      {children}
    </NotificationsContext.Provider>
  )
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext)
  if (!ctx) throw new Error("useNotifications deve ser usado dentro de NotificationsProvider")
  return ctx
}
