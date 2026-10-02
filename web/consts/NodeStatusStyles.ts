// Cores e labels de status de execução de nodes — fonte única de verdade.
// Usado pelo InputInspector, OutputPreview, RunLogs e outros componentes.

export const STATUS_COLOR_MAP: Record<string, string> = {
  idle: "bg-muted text-muted-foreground",
  started: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  completed: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
}

export const STATUS_LABEL: Record<string, string> = {
  idle: "Aguardando",
  started: "Executando",
  completed: "Concluído",
  failed: "Falhou",
}
