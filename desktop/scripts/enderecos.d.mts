// Tipos de desktop/scripts/enderecos.mjs, para o vite.config.ts e o vitest.config.ts.
export interface Enderecos { servidor: string; ui: string }
export const DEV: Enderecos
export const TESTE: Enderecos
export function enderecosDoBuild(opts?: { dev?: boolean }): Enderecos
export function defineDosEnderecos(e: Enderecos): Record<string, string>
export interface MarcaDoBuild extends Enderecos { modo: 'dev' | 'producao' }
export function marcaDoBuild(opts: { dev?: boolean } & Enderecos): MarcaDoBuild
export function conferirMarcaDoBuild(marca: unknown): void
