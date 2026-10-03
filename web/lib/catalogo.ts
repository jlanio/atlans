// web/lib/catalogo.ts
//
// The source catalog in NUMBERS and in NAMES, for the showcase the Home shows
// to those who have not signed in yet (the "No catálogo" group of `HomeSidebar`).
//
// Why a constant and not a GET: the Home's anonymous shell makes NO requests
// AT ALL — that is the decision that keeps the "Meu" group from even mounting
// without a session (`home-sidebar.tsx`), and a `/fontes/resumo` here would undo
// it for a number that changes with every new seed. The values come from
// `catalogo/geoservicos/`, the same folder the API imports at startup
// (`app/core/fontes_catalogo.py`).
//
// What keeps them from going stale is `tests/unit/test_vitrine_do_catalogo.py`:
// it recomputes everything from the folder and fails STATING the new number.
// Changing the seed and forgetting this file breaks the test — which is exactly
// the point. If the showcase ever needs the number from the database (learned
// sources, workspace sources), the way is for the server to pass it as a prop,
// never for the client to fetch it.

/**
 * A base cited by the showcase: `rotulo` is what the person reads; `pasta` is
 * what PROVES it exists — the name (or name prefix) of the folder in
 * `catalogo/geoservicos/`. Countries are prefixes: "Bolívia" appears in the
 * bar, but the folder is `Bolivia INRA`, without the accent. The test uses this
 * field to check that no name here has become fiction.
 */
export interface CitedBase {
  rotulo: string
  pasta: string
}

/**
 * The size of the catalog. `paises` counts Brazil plus the 10 abroad — and
 * "countries" is a deliberate approximation: French Guiana is French territory,
 * and "countries and territories" does not fit in the bar's label.
 */
export const CATALOGO = {
  camadas: 25_492,
  instituicoes: 76,
  paises: 11,
} as const

/** The first strip: the most recognizable federal agencies. */
export const ORGAOS_FEDERAIS: readonly CitedBase[] = [
  { rotulo: "IBGE", pasta: "IBGE" },
  { rotulo: "IBAMA", pasta: "IBAMA" },
  { rotulo: "FUNAI", pasta: "FUNAI" },
  { rotulo: "ICMBio", pasta: "ICMBio INDE" },
  { rotulo: "ANA", pasta: "ANA" },
  { rotulo: "Embrapa", pasta: "Embrapa" },
  { rotulo: "Marinha", pasta: "Marinha DHN" },
  { rotulo: "IPHAN", pasta: "IPHAN" },
]

/**
 * The second strip: states and agencies. It exists to undo the impression that
 * the catalog is only federal — INEA and Sisema alone are 22% of the layers.
 */
export const ORGAOS_REGIONAIS: readonly CitedBase[] = [
  { rotulo: "INEA (RJ)", pasta: "INEA RJ" },
  { rotulo: "Sisema (MG)", pasta: "Sisema MG" },
  { rotulo: "SEPLAN (TO)", pasta: "SEPLAN TO" },
  { rotulo: "GEOBASES (ES)", pasta: "GEOBASES ES" },
  { rotulo: "ANP", pasta: "ANP" },
  { rotulo: "ANM", pasta: "ANM" },
  { rotulo: "MAPA", pasta: "MAPA" },
  { rotulo: "SFB", pasta: "SFB" },
]

/**
 * The third strip: everything outside Brazil, in order of WEIGHT in the catalog
 * (Nicaragua and Ecuador together are more than the other eight combined). All
 * ten are there on purpose: picking six gave an arbitrary list, and Chile —
 * a single layer, the railway network — drops out of any honest cut by size,
 * but it is true that it is there.
 */
export const PAISES: readonly CitedBase[] = [
  { rotulo: "Equador", pasta: "Equador" },
  { rotulo: "Nicarágua", pasta: "Nicarágua" },
  { rotulo: "Guiana Francesa", pasta: "Guiana Francesa" },
  { rotulo: "Argentina", pasta: "Argentina" },
  { rotulo: "Bolívia", pasta: "Bolivia" },
  { rotulo: "México", pasta: "México" },
  { rotulo: "Canadá", pasta: "Canadá" },
  { rotulo: "Uruguai", pasta: "Uruguai" },
  { rotulo: "Peru", pasta: "Peru" },
  { rotulo: "Chile", pasta: "Chile" },
]
