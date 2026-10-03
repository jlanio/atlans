// Copied from web/lib/utils.ts — same utility, so that the ported shadcn
// primitives work without changes.
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
