# app/services/fontes_vault.py
"""
The geoservice Vault parser — Obsidian markdown becomes records of the
source catalog, without touching the database or the network.

The versioned folder in `catalogo/geoservicos/` is a copy of the owner's Vault:
one subfolder per institution, and inside it three script-generated notes —

- the institution note (`<Nome — SIGLA>.md`, or `nota-base.md`): a list of
  `- **Campo:** valor` fields (Mantenedor, Finalidade, Endpoint WFS,
  GetCapabilities, Versão usada para os schemas, Última coleta de metadados…),
  a paragraph of remarks and, sometimes, a "Como consumir no Atlans" callout;
- `Camadas.md`: `## <Grupo> (n)` and, per layer, `- `ns:camada` — Título`;
- `Atributos.md`: `### `ns:camada`` followed by the DescribeFeatureType's
  `| Campo | Tipo XSD | Nulo | Ocorrência |` table.

The parser reads that format AS IS and, on top of it, three optional extensions
that Obsidian already knows how to edit (see `docs/sources.md`):

- **YAML frontmatter** in the institution note (`sigla`, `pais`, `uf`,
  `endpoint_wfs`, `versao_wfs`, `temas`, `prioridade`, `coletada_em`) — only the
  flat subset of YAML, with no new dependency;
- **inline tags** at the end of the layer line (`#terras-indígenas #preferida`),
  which leave the title and go into `temas`; `#preferida`/`#secundaria` become the
  priority;
- **`_sinonimos.md`** at the root, a `| termo | sinônimos |` table that search
  uses to expand the query.

Only what the `WFS` node can read gets in: a folder without `Endpoint WFS` (ArcGIS REST,
"em validação" placeholders) comes out as `Skipped`, with the reason, so the import
summary can say what was left out. Nothing here raises an exception over a badly
written note: the folder becomes `Skipped(motivo="nota_ilegivel")` and the import
moves on to the next one.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

LAYERS_FILE = "Camadas.md"
ATTRIBUTES_FILE = "Atributos.md"
SYNONYMS_FILE = "_sinonimos.md"
DEFAULT_VERSION = "2.0.0"

# The candidates for the sort column, in order of preference: GeoServer
# requires a SORTBY to paginate a layer without a primary key, and an id column is
# the bet that almost always pays off.
SORTBY_CANDIDATES = ("gid", "fid", "id", "objectid", "ogc_fid")

# Ceiling for the remarks that become `dicas`: the note's paragraph is short, but a
# multi-line callout would exceed `describe_source`'s context budget.
MAX_HINTS = 600

# `gml:<G>PropertyType` → geometry type, the same table owslib uses
# (`owslib/feature/schema.py`), copied because owslib is not a dependency of the
# server, nor should it be.
GEOMETRIES = {
    "PointPropertyType": "Point",
    "MultiPointPropertyType": "MultiPoint",
    "LineStringPropertyType": "LineString",
    "CurvePropertyType": "LineString",
    "MultiLineStringPropertyType": "MultiLineString",
    "MultiCurvePropertyType": "MultiLineString",
    "PolygonPropertyType": "Polygon",
    "SurfacePropertyType": "Polygon",
    "MultiPolygonPropertyType": "MultiPolygon",
    "MultiSurfacePropertyType": "MultiPolygon",
    "GeometryPropertyType": "Geometry",
    "MultiGeometryPropertyType": "GeometryCollection",
}

_FIELD = re.compile(r"^(?:-\s*)?\*\*(.+?):\*\*\s*(.*?)\s*$")
_URL_ANGULAR = re.compile(r"^<(.+)>$")
_VERSION = re.compile(r"(\d+\.\d+(?:\.\d+)?)")
_TITLE_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
_GROUP = re.compile(r"^##\s+(.+?)(?:\s+\((\d+)\))?\s*$")
_LAYER = re.compile(r"^-\s+`([^`]+)`\s*(?:[—–-]\s*(.*))?$")
_TAG = re.compile(r"(?:^|\s)#([^\s#]+)")
_ATTRIBUTE_H3 = re.compile(r"^###\s+`([^`]+)`\s*$")
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
_CREDENTIAL_IN_URL = re.compile(r"://[^/@\s]+:[^/@\s]+@")
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
_CALLOUT = re.compile(r"^>\s*\[![a-z]+\]\s*(.*)$", re.I)


# ── Registros ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Coluna:
    name: str
    type: str
    xsd: str
    nullable: bool = True


@dataclass(frozen=True)
class VaultSchema:
    columns: tuple[Coluna, ...]
    geometry_column: str | None
    geometry_type: str | None

    def as_dict(self) -> dict:
        return {
            "columns": [
                {"name": c.name, "type": c.type, "xsd": c.xsd, "nullable": c.nullable}
                for c in self.columns
            ],
            "geometry_column": self.geometry_column,
            "geometry_type": self.geometry_type,
            "columns_source": "vault",
        }


@dataclass(frozen=True)
class Camada:
    grupo: str | None
    type_name: str
    titulo: str
    tags: tuple[str, ...] = ()


@dataclass
class Institution:
    nome: str
    sigla: str | None = None
    mantenedor: str | None = None
    finalidade: str | None = None
    endpoint: str | None = None
    versao: str = DEFAULT_VERSION
    temas: list[str] = field(default_factory=list)
    prioridade: int | None = None
    pais: str | None = None
    uf: str | None = None
    coletada_em: str | None = None
    observacoes: str | None = None


@dataclass(frozen=True)
class RegistroDoVault:
    """A Vault layer, ready to become a catalog row."""

    instituicao: str
    grupo: str | None
    url: str
    type_name: str
    titulo: str
    descricao: str
    temas: tuple[str, ...]
    esquema: dict | None
    propriedades: dict
    dicas: str | None
    prioridade: int
    versao: str
    coletada_em: str | None

    @property
    def vault_hash(self) -> str:
        """sha256 of the canonical record — changes when ANY field changes."""
        canonical = {
            "instituicao": self.instituicao,
            "grupo": self.grupo,
            "url": self.url,
            "type_name": self.type_name,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "temas": list(self.temas),
            "esquema": self.esquema,
            "propriedades": self.propriedades,
            "dicas": self.dicas,
            "prioridade": self.prioridade,
            "versao": self.versao,
            "coletada_em": self.coletada_em,
        }
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class Skipped:
    """A folder that does not go into the catalog — and why."""

    pasta: str
    motivo: str
    detalhe: str | None = None


# ── Utilidades ────────────────────────────────────────────────────────────────


def nfc(texto: str) -> str:
    """Names coming from macOS arrive in NFD; the catalog compares in NFC."""
    return unicodedata.normalize("NFC", texto)


def _strip_angle_brackets(valor: str) -> str:
    achado = _URL_ANGULAR.match(valor.strip())
    return achado.group(1).strip() if achado else valor.strip()


def _strip_quotes(valor: str) -> str:
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1]
    return valor


def _yaml_list(valor: str) -> list[str]:
    valor = valor.strip()
    if valor.startswith("[") and valor.endswith("]"):
        return [_strip_quotes(v) for v in valor[1:-1].split(",") if _strip_quotes(v)]
    return [_strip_quotes(valor)] if valor else []


def read_frontmatter(texto: str) -> tuple[dict, str]:
    """The `---` block at the top as a flat dict, and the rest of the text.

    Only the YAML Obsidian writes in Properties: `chave: valor`, inline
    lists `[a, b]` and block lists (`- item`). No dependency: PyYAML is not
    on the server, and the subset is enough for what the catalog reads.
    """
    achado = _FRONTMATTER.match(texto)
    if not achado:
        return {}, texto
    campos: dict = {}
    list_key: str | None = None
    for linha in achado.group(1).splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s*-\s+(.*)$", linha)
        if item and list_key:
            campos[list_key].append(_strip_quotes(item.group(1)))
            continue
        par = re.match(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$", linha)
        if not par:
            continue
        chave, valor = par.group(1).strip().lower(), par.group(2).strip()
        if valor == "":
            campos[chave] = []
            list_key = chave
            continue
        list_key = None
        campos[chave] = _yaml_list(valor) if valor.startswith("[") else _strip_quotes(valor)
    return campos, texto[achado.end():]


def _version(valor: str | None) -> str:
    if not valor:
        return DEFAULT_VERSION
    achado = _VERSION.search(str(valor))
    if not achado:
        return DEFAULT_VERSION
    partes = achado.group(1).split(".")
    while len(partes) < 3:
        partes.append("0")
    return ".".join(partes)


def _priority(valor) -> int | None:
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    return n if n in (1, 2, 3) else None


def _tags(texto: str) -> tuple[str, tuple[str, ...]]:
    """Splits the `#x` tags off the end of a title; returns (clean title, tags)."""
    tags = tuple(t for t in _TAG.findall(texto))
    if not tags:
        return texto.strip(), ()
    limpo = _TAG.sub("", texto).strip()
    return limpo, tags


# ── The institution note ──────────────────────────────────────────────────────


def read_institution(texto: str, *, folder_name: str) -> Institution:
    """The note's fields, with the frontmatter (when present) taking precedence over the body."""
    frontmatter, corpo = read_frontmatter(texto)
    titulo = _TITLE_H1.search(corpo)
    inst = Institution(nome=nfc(titulo.group(1).strip()) if titulo else nfc(folder_name))

    campos: dict[str, str] = {}
    observacoes: list[str] = []
    in_navigation = False
    for linha in corpo.splitlines():
        if linha.startswith("## "):
            in_navigation = True  # from here on it is navigation/wikilinks
            continue
        if in_navigation or linha.startswith("# "):
            continue
        campo = _FIELD.match(linha.strip())
        if campo:
            campos[_normalize_key(campo.group(1))] = _strip_angle_brackets(campo.group(2))
            continue
        callout = _CALLOUT.match(linha.strip())
        if callout:
            if callout.group(1).strip():
                observacoes.append(callout.group(1).strip())
            continue
        if linha.strip().startswith(">"):
            observacoes.append(linha.strip().lstrip("> ").strip())
            continue
        if linha.strip():
            observacoes.append(linha.strip())

    inst.mantenedor = campos.get("mantenedor")
    inst.finalidade = campos.get("finalidade")
    inst.endpoint = campos.get("endpoint wfs")
    inst.versao = _version(campos.get("versao usada para os schemas"))
    inst.coletada_em = campos.get("ultima coleta de metadados")
    if "—" in inst.nome:
        inst.sigla = inst.nome.rsplit("—", 1)[1].strip() or None

    # The frontmatter beats the body: it is the explicit form, edited in Properties.
    if frontmatter.get("sigla"):
        inst.sigla = str(frontmatter["sigla"]).strip()
    if frontmatter.get("endpoint_wfs"):
        inst.endpoint = _strip_angle_brackets(str(frontmatter["endpoint_wfs"]))
    if frontmatter.get("versao_wfs"):
        inst.versao = _version(str(frontmatter["versao_wfs"]))
    if frontmatter.get("coletada_em"):
        inst.coletada_em = str(frontmatter["coletada_em"]).strip()
    for chave in ("pais", "uf"):
        if frontmatter.get(chave):
            setattr(inst, chave, str(frontmatter[chave]).strip().upper())
    temas = frontmatter.get("temas")
    if isinstance(temas, list):
        inst.temas = [str(t).strip() for t in temas if str(t).strip()]
    elif isinstance(temas, str) and temas.strip():
        inst.temas = [t.strip() for t in temas.split(",") if t.strip()]
    inst.prioridade = _priority(frontmatter.get("prioridade"))

    if observacoes:
        inst.observacoes = " ".join(observacoes)[:MAX_HINTS].strip()
    return inst


def _normalize_key(chave: str) -> str:
    unaccented = unicodedata.normalize("NFKD", chave)
    return "".join(c for c in unaccented if not unicodedata.combining(c)).casefold().strip()


# ── Camadas.md ────────────────────────────────────────────────────────────────


def read_layers(texto: str) -> list[Camada]:
    """The layers, with the group (`## Grupo (n)`) they appear in and the tags."""
    camadas: list[Camada] = []
    grupo: str | None = None
    for linha in texto.splitlines():
        cabecalho = _GROUP.match(linha)
        if cabecalho:
            grupo = nfc(cabecalho.group(1).strip())
            continue
        item = _LAYER.match(linha.strip())
        if not item:
            continue
        type_name = item.group(1).strip()
        titulo, tags = _tags(nfc(item.group(2) or ""))
        # ArcGIS bullet (`- \`Título\` — <url>`): the "name" is not a typeName
        # and the title is a URL. Left out — the WFS node does not read this.
        if titulo.startswith("<http") or titulo.startswith("http"):
            continue
        camadas.append(Camada(grupo=grupo, type_name=type_name, titulo=titulo or type_name, tags=tags))
    return camadas


# ── Atributos.md ──────────────────────────────────────────────────────────────


def _column(cells: list[str]) -> Coluna | None:
    if len(cells) < 2:
        return None
    nome = cells[0].strip().strip("`").strip()
    xsd = cells[1].strip().strip("`").strip()
    if not nome or not xsd or nome.lower() in ("campo", "---", ":---"):
        return None
    nulo = cells[2].strip().lower() if len(cells) > 2 else "true"
    if xsd.startswith("gml:"):
        tipo = GEOMETRIES.get(xsd[4:], "Geometry")
    else:
        tipo = xsd.split(":", 1)[1] if ":" in xsd else xsd
    return Coluna(name=nome, type=tipo, xsd=xsd, nullable=nulo not in ("false", "não", "nao", "n"))


def read_attributes(texto: str) -> dict[str, VaultSchema]:
    """`{type_name: esquema}` from the `Atributos.md` tables."""
    esquemas: dict[str, VaultSchema] = {}
    atual: str | None = None
    colunas: list[Coluna] = []

    def fechar() -> None:
        if atual is None:
            return
        geometria = next((c for c in colunas if c.xsd.startswith("gml:")), None)
        esquemas[atual] = VaultSchema(
            columns=tuple(colunas),
            geometry_column=geometria.name if geometria else None,
            geometry_type=geometria.type if geometria else None,
        )

    for linha in texto.splitlines():
        cabecalho = _ATTRIBUTE_H3.match(linha.strip())
        if cabecalho:
            fechar()
            atual, colunas = cabecalho.group(1).strip(), []
            continue
        if atual is None:
            continue
        tabela = _TABLE_ROW.match(linha.strip())
        if not tabela:
            continue
        cells = tabela.group(1).split("|")
        if all(c.strip().strip(":-") == "" for c in cells):
            continue  # a linha separadora |---|---|
        coluna = _column(cells)
        if coluna:
            colunas.append(coluna)
    fechar()
    return esquemas


# ── _sinonimos.md ─────────────────────────────────────────────────────────────


def read_synonyms(texto: str) -> dict[str, set[str]]:
    """`{termo: {sinônimos}}` from the table (or from `- termo: a, b` lines)."""
    saida: dict[str, set[str]] = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        termo = synonyms = None
        tabela = _TABLE_ROW.match(linha)
        if tabela:
            cells = [c.strip() for c in tabela.group(1).split("|")]
            if len(cells) >= 2 and cells[0].lower() not in ("termo", "") and not set(cells[0]) <= set(":-"):
                termo, synonyms = cells[0], cells[1]
        elif linha.startswith("- ") and ":" in linha:
            termo, synonyms = linha[2:].split(":", 1)
        if not termo or not synonyms:
            continue
        lista = {s.strip() for s in synonyms.split(",") if s.strip()}
        if lista:
            saida.setdefault(termo.strip(), set()).update(lista)
    return saida


# ── A pasta inteira ───────────────────────────────────────────────────────────


def _institution_notes(pasta: Path) -> list[Path]:
    """The candidate notes, `nota-base.md` last: the named note is the one that
    usually carries the endpoint."""
    notas = [
        p for p in sorted(pasta.iterdir())
        if p.is_file() and p.suffix.lower() == ".md"
        and p.name not in (LAYERS_FILE, ATTRIBUTES_FILE)
        and not p.name.startswith("_")
    ]
    return sorted(notas, key=lambda p: p.name == "nota-base.md")


def _sort_by(colunas: tuple[Coluna, ...]) -> str | None:
    nomes = {c.name.lower(): c.name for c in colunas}
    for candidato in SORTBY_CANDIDATES:
        if candidato in nomes:
            return nomes[candidato]
    return None


def read_institution_from_folder(pasta: Path) -> Iterator[RegistroDoVault | Skipped]:
    """The records of ONE institution folder (or the `Skipped` that sums it up)."""
    nome = nfc(pasta.name)
    try:
        inst: Institution | None = None
        for nota in _institution_notes(pasta):
            candidate = read_institution(nota.read_text(encoding="utf-8"), folder_name=nome)
            if candidate.endpoint:
                inst = candidate
                break
            inst = inst or candidate
        if inst is None or not inst.endpoint:
            yield Skipped(nome, "sem_endpoint_wfs")
            return
        if _CREDENTIAL_IN_URL.search(inst.endpoint):
            yield Skipped(nome, "url_com_credencial")
            return
        layers_md = pasta / LAYERS_FILE
        camadas = read_layers(layers_md.read_text(encoding="utf-8")) if layers_md.exists() else []
        if not camadas:
            yield Skipped(nome, "sem_camadas")
            return
        attributes_md = pasta / ATTRIBUTES_FILE
        esquemas = read_attributes(attributes_md.read_text(encoding="utf-8")) if attributes_md.exists() else {}
    except (OSError, UnicodeDecodeError) as exc:
        yield Skipped(nome, "nota_ilegivel", str(exc)[:200])
        return

    sigla = inst.sigla or nome
    descricao = inst.nome
    if inst.finalidade:
        descricao = f"{inst.nome.rstrip('.')}. {inst.finalidade}"
    base_themes = [sigla] + inst.temas
    if inst.pais:
        base_themes.append(inst.pais)
    if inst.uf:
        base_themes.append(inst.uf)

    for camada in camadas:
        esquema = esquemas.get(camada.type_name)
        propriedades: dict = {"url": inst.endpoint, "typeName": camada.type_name, "version": inst.versao}
        if esquema:
            sort_order = _sort_by(esquema.columns)
            if sort_order:
                propriedades["sortBy"] = sort_order
        temas: list[str] = list(base_themes)
        if camada.grupo:
            temas.append(camada.grupo)
        prioridade = inst.prioridade or 2
        for tag in camada.tags:
            clean_tag = _normalize_key(tag)
            if clean_tag == "preferida":
                prioridade = 1
            elif clean_tag in ("secundaria", "secundária"):
                prioridade = 3
            else:
                temas.append(tag.replace("-", " "))
        yield RegistroDoVault(
            instituicao=nome,
            grupo=camada.grupo,
            url=inst.endpoint,
            type_name=camada.type_name,
            titulo=camada.titulo,
            descricao=descricao,
            temas=tuple(dict.fromkeys(t for t in temas if t)),
            esquema=esquema.as_dict() if esquema else None,
            propriedades=propriedades,
            dicas=inst.observacoes,
            prioridade=prioridade,
            versao=inst.versao,
            coletada_em=inst.coletada_em,
        )


def read_folder(caminho: str | Path) -> Iterator[RegistroDoVault | Skipped]:
    """Walks `<caminho>/<INSTITUIÇÃO>/` and produces the records and the ignored ones.

    Loose files at the root (index, reports, scripts) are not sources and are
    skipped silently — only `_sinonimos.md` has a role, read by `synonyms_of`.
    """
    raiz = Path(caminho)
    if not raiz.is_dir():
        return
    for pasta in sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith(".")):
        yield from read_institution_from_folder(pasta)


def synonyms_of(caminho: str | Path) -> dict[str, set[str]]:
    """The synonyms from `_sinonimos.md` at the folder root, or `{}`."""
    arquivo = Path(caminho) / SYNONYMS_FILE
    if not arquivo.is_file():
        return {}
    try:
        return read_synonyms(arquivo.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}
