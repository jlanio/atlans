// web/app/components/home/artefatos/normalizar.ts
//
// O acervo unificado da Home: artefatos de execução e arquivos do Drive na MESMA
// lista, distinguidos SÓ por ícone (decisão 8). Este módulo é PURO — junta as
// duas formas do backend (`IArtifactItem`, `IDriveFile`) num só `ItemDoAcervo` e
// decide o estado do item. Sem React, sem fetch: dá para testar a escada de
// estados e o "adicionável ao globo" sem montar nada.
//
// O motivo de um item não ir ao globo é decidido AQUI, como chave (`motivo`); a
// frase é do dicionário. A lista da Home traduz pela chave na hora de mostrar —
// o acervo fica guardado no hook, e trocar de idioma nas Preferências não pode
// deixar a frase no idioma velho.

import type { IArtifactItem, IDriveFile } from "@/service/types"
import { isLocalDoExecutor } from "@/app/components/local-badge"

export type FonteDoAcervo = "artefato" | "drive"

/** Por que um item NÃO vai ao globo — as chaves de `listas.artefatos.semPrevia`. */
export type MotivoSemPrevia =
  | "executor"
  | "cartaImagem"
  | "semCamadaNoPortal"
  | "formatoSemPrevia"
  | "drive"

/**
 * O estado que decide o ícone (decisão 8). Escada, nesta ordem:
 * - `local`: o conteúdo ficou no executor e nunca subiu à nuvem (sem download,
 *   sem prévia) — vale para artefato E arquivo do Drive.
 * - `efemero`: tem `expires_at` (só artefato; o Drive é permanente).
 * - `permanente`: o resto (Drive, ou artefato sem expiração).
 */
export type EstadoDoAcervo = "local" | "efemero" | "permanente"

export interface ItemDoAcervo {
  /** Chave única na lista (a fonte + o id — os dois espaços de id são disjuntos
   *  na prática, mas o prefixo garante). */
  chave: string
  id: string
  fonte: FonteDoAcervo
  nome: string
  /** geojson | json | csv | shapefile | ... (minúsculo). */
  formato: string
  estado: EstadoDoAcervo
  /** Só quando efêmero (o Drive nunca tem). */
  expiresAt: string | null
  executorId: string | null
  /**
   * A data que ORDENA a lista — no Drive é a última escrita de CONTEÚDO, não a
   * criação da linha. É o mesmo `coalesce` que o servidor usa para ordenar
   * /drive: um `.gpkg` de oito meses sobrescrito hoje pelo GeoSync precisa subir
   * ao topo, e por `created_at` ele afundava entre os arquivos antigos — em duas
   * telas com ordens diferentes para os mesmos arquivos.
   */
  ordenadoEm: string | null
  workspaceId: string | null
  /** Pode ir ao globo: só artefato geojson ou com camada de portal viva, e nunca
   *  local (o `camadaDoGlobo` é endpoint de ARTEFATO — arquivo do Drive não
   *  entra na v1). */
  adicionavel: boolean
  /** Por que NÃO vai ao globo — `null` quando vai. É pela chave que a lista diz
   *  a frase no idioma em uso. O motivo é o único texto que a linha inerte tem
   *  para oferecer, e "sem prévia no globo" sozinho descrevia mal o caso mais
   *  comum (conteúdo parado no executor). */
  motivo: MotivoSemPrevia | null
  driveFile?: IDriveFile
}

/** A escada de estados, isolada para teste direto. */
export function estadoDoAcervo(
  item: { content_location?: string | null; expires_at?: string | null },
): EstadoDoAcervo {
  if (isLocalDoExecutor(item)) return "local"
  if (item.expires_at) return "efemero"
  return "permanente"
}

/**
 * Um artefato pode ir ao globo quando é geojson OU tem camada de portal viva
 * (vira MVT), e nunca quando é local (sem bytes na nuvem para buscar).
 *
 * `is_published` sozinho NÃO basta: o endpoint da camada casa o artefato a uma
 * `PortalLayer` daquela execução e devolve "indisponível" quando não acha
 * (agente_camadas_router). `is_portal_active` é exatamente esse casamento, já
 * feito no servidor (`is_published` E o run tem camada) — oferecer "Exibir no
 * globo" por `is_published` prometia uma prévia que o backend ia recusar.
 *
 * Devolve junto a chave do motivo da recusa: a frase dela é o texto que a
 * linha inerte exibe.
 */
const FORMATOS_DE_IMAGEM = new Set(["png", "jpg", "jpeg", "pdf"])

function previaDoArtefato(a: IArtifactItem): { adicionavel: boolean; motivo: MotivoSemPrevia | null } {
  if (isLocalDoExecutor(a)) return { adicionavel: false, motivo: "executor" }
  const formato = (a.format ?? "").toLowerCase()
  if (formato === "geojson") return { adicionavel: true, motivo: null }
  if (FORMATOS_DE_IMAGEM.has(formato)) {
    // A carta imagem (nó CartaImagem) é um arquivo para baixar: nem publicar
    // no portal a poria no globo, então a frase genérica ("publique o mapa")
    // mentiria.
    return { adicionavel: false, motivo: "cartaImagem" }
  }
  if (a.is_portal_active) return { adicionavel: true, motivo: null }
  if (a.is_published) return { adicionavel: false, motivo: "semCamadaNoPortal" }
  return { adicionavel: false, motivo: "formatoSemPrevia" }
}

export function normalizarArtefato(a: IArtifactItem): ItemDoAcervo {
  const previa = previaDoArtefato(a)
  return {
    chave: `art:${a.id_hash}`,
    id: a.id_hash,
    fonte: "artefato",
    nome: a.filename,
    formato: (a.format ?? "").toLowerCase(),
    estado: estadoDoAcervo(a),
    expiresAt: a.expires_at,
    executorId: a.executor_id,
    // Artefato de execução não é sobrescrito: criação e ordenação coincidem.
    ordenadoEm: a.created_at,
    workspaceId: a.workspace_id,
    adicionavel: previa.adicionavel,
    motivo: previa.motivo,
  }
}

export function normalizarArquivoDoDrive(f: IDriveFile): ItemDoAcervo {
  return {
    chave: `drv:${f.id_hash}`,
    id: f.id_hash,
    fonte: "drive",
    nome: f.original_name,
    formato: (f.extension ?? "").toLowerCase(),
    estado: estadoDoAcervo(f), // Drive não tem expires_at → local ou permanente
    expiresAt: null,
    executorId: f.content_executor_id ?? null,
    // Ordena pela última escrita de conteúdo, como o servidor ordena /drive.
    ordenadoEm: f.content_written_at ?? f.created_at,
    workspaceId: f.workspace_id,
    adicionavel: false, // arquivo do Drive nunca vai ao globo na v1
    motivo: "drive",
    driveFile: f,
  }
}
