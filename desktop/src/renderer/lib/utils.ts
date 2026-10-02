// Copiado de web/lib/utils.ts — mesmo utilitario, para que os primitivos
// shadcn portados funcionem sem alteracao.
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
