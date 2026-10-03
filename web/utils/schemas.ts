import { z } from "zod"

// Creates a name field with standardized validation
export function nameField({ min = 2, max, label }: { min?: number; max: number; label: string }) {
  const minMsg =
    min <= 1
      ? `O nome ${label} é obrigatório`
      : `O nome ${label} não pode ter menos de ${min} caracteres`
  return z
    .string()
    .min(min, minMsg)
    .max(max, `O nome ${label} não pode ter mais de ${max} caracteres`)
}
