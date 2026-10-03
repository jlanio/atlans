// Tipos de desktop/scripts/enderecos.mjs, para o vite.config.ts e o vitest.config.ts.
export interface Addresses { servidor: string; ui: string }
export const DEV: Addresses
export const TEST: Addresses
export function buildAddresses(opts?: { dev?: boolean }): Addresses
export function addressDefines(e: Addresses): Record<string, string>
export interface BuildBrand extends Addresses { modo: 'dev' | 'producao' }
export function buildBrand(opts: { dev?: boolean } & Addresses): BuildBrand
export function conferirMarcaDoBuild(marca: unknown): void
