# app/services/fontes_vault.py
"""
O parser do Vault de geoserviços — o markdown do Obsidian vira registros do
catálogo de fontes, sem tocar em banco nem em rede.

A pasta versionada em `catalogo/geoservicos/` é uma cópia do Vault do dono:
uma subpasta por instituição, e dentro dela três notas geradas por script —

- a nota da instituição (`<Nome — SIGLA>.md`, ou `nota-base.md`): uma lista de
  campos `- **Campo:** valor` (Mantenedor, Finalidade, Endpoint WFS,
  GetCapabilities, Versão usada para os schemas, Última coleta de metadados…),
  um parágrafo de observações e, às vezes, um callout "Como consumir no Atlans";
- `Camadas.md`: `## <Grupo> (n)` e, por camada, `- `ns:camada` — Título`;
- `Atributos.md`: `### `ns:camada`` seguido da tabela
  `| Campo | Tipo XSD | Nulo | Ocorrência |` do DescribeFeatureType.

O parser lê esse formato COMO ESTÁ e, por cima dele, três extensões opcionais
que o Obsidian já sabe editar (ver `docs/sources.md`):

- **frontmatter YAML** na nota da instituição (`sigla`, `pais`, `uf`,
  `endpoint_wfs`, `versao_wfs`, `temas`, `prioridade`, `coletada_em`) — só o
  subconjunto plano do YAML, sem dependência nova;
- **tags inline** no fim da linha da camada (`#terras-indígenas #preferida`),
  que saem do título e entram em `temas`; `#preferida`/`#secundaria` viram a
  prioridade;
- **`_sinonimos.md`** na raiz, uma tabela `| termo | sinônimos |` que a busca
  usa para expandir a consulta.

Só entra o que o nó `WFS` consegue ler: pasta sem `Endpoint WFS` (ArcGIS REST,
placeholders "em validação") sai como `Ignorada`, com o motivo, para o resumo da
importação dizer o que ficou de fora. Nada aqui levanta exceção por uma nota
mal escrita: a pasta vira `Ignorada(motivo="nota_ilegivel")` e a importação
segue para a próxima.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

ARQUIVO_DE_CAMADAS = "Camadas.md"
ARQUIVO_DE_ATRIBUTOS = "Atributos.md"
ARQUIVO_DE_SINONIMOS = "_sinonimos.md"
VERSAO_PADRAO = "2.0.0"

# Os candidatos a coluna de ordenação, na ordem de preferência: o GeoServer
# exige um SORTBY para paginar camada sem chave primária, e uma coluna de id é
# a aposta que quase sempre acerta.
CANDIDATOS_A_SORTBY = ("gid", "fid", "id", "objectid", "ogc_fid")

# Teto das observações que viram `dicas`: o parágrafo da nota é curto, mas um
# callout de várias linhas passaria o orçamento de contexto de `describe_source`.
MAX_DICAS = 600

# `gml:<G>PropertyType` → tipo de geometria, a mesma tabela que o owslib usa
# (`owslib/feature/schema.py`), copiada porque o owslib não é dependência do
# servidor nem deve ser.
GEOMETRIAS = {
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

_CAMPO = re.compile(r"^(?:-\s*)?\*\*(.+?):\*\*\s*(.*?)\s*$")
_URL_ANGULAR = re.compile(r"^<(.+)>$")
_VERSAO = re.compile(r"(\d+\.\d+(?:\.\d+)?)")
_TITULO_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
_GRUPO = re.compile(r"^##\s+(.+?)(?:\s+\((\d+)\))?\s*$")
_CAMADA = re.compile(r"^-\s+`([^`]+)`\s*(?:[—–-]\s*(.*))?$")
_TAG = re.compile(r"(?:^|\s)#([^\s#]+)")
_ATRIBUTO_H3 = re.compile(r"^###\s+`([^`]+)`\s*$")
_LINHA_DE_TABELA = re.compile(r"^\|(.+)\|\s*$")
_CREDENCIAL_NA_URL = re.compile(r"://[^/@\s]+:[^/@\s]+@")
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
class EsquemaDoVault:
    columns: tuple[Coluna, ...]
    geometry_column: str | None
    geometry_type: str | None

    def como_dict(self) -> dict:
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
class Instituicao:
    nome: str
    sigla: str | None = None
    mantenedor: str | None = None
    finalidade: str | None = None
    endpoint: str | None = None
    versao: str = VERSAO_PADRAO
    temas: list[str] = field(default_factory=list)
    prioridade: int | None = None
    pais: str | None = None
    uf: str | None = None
    coletada_em: str | None = None
    observacoes: str | None = None


@dataclass(frozen=True)
class RegistroDoVault:
    """Uma camada do Vault, pronta para virar linha do catálogo."""

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
        """sha256 do registro canônico — muda quando QUALQUER campo muda."""
        canonico = {
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
            json.dumps(canonico, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class Ignorada:
    """Uma pasta que não entra no catálogo — e por quê."""

    pasta: str
    motivo: str
    detalhe: str | None = None


# ── Utilidades ────────────────────────────────────────────────────────────────


def nfc(texto: str) -> str:
    """Nomes vindos do macOS chegam em NFD; o catálogo compara em NFC."""
    return unicodedata.normalize("NFC", texto)


def _sem_angulares(valor: str) -> str:
    achado = _URL_ANGULAR.match(valor.strip())
    return achado.group(1).strip() if achado else valor.strip()


def _sem_aspas(valor: str) -> str:
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1]
    return valor


def _lista_yaml(valor: str) -> list[str]:
    valor = valor.strip()
    if valor.startswith("[") and valor.endswith("]"):
        return [_sem_aspas(v) for v in valor[1:-1].split(",") if _sem_aspas(v)]
    return [_sem_aspas(valor)] if valor else []


def ler_frontmatter(texto: str) -> tuple[dict, str]:
    """O bloco `---` do topo como dict plano, e o resto do texto.

    Só o YAML que o Obsidian escreve nas Propriedades: `chave: valor`, listas
    inline `[a, b]` e listas em bloco (`- item`). Sem dependência: PyYAML não
    está no servidor, e o subconjunto basta para o que o catálogo lê.
    """
    achado = _FRONTMATTER.match(texto)
    if not achado:
        return {}, texto
    campos: dict = {}
    chave_de_lista: str | None = None
    for linha in achado.group(1).splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s*-\s+(.*)$", linha)
        if item and chave_de_lista:
            campos[chave_de_lista].append(_sem_aspas(item.group(1)))
            continue
        par = re.match(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$", linha)
        if not par:
            continue
        chave, valor = par.group(1).strip().lower(), par.group(2).strip()
        if valor == "":
            campos[chave] = []
            chave_de_lista = chave
            continue
        chave_de_lista = None
        campos[chave] = _lista_yaml(valor) if valor.startswith("[") else _sem_aspas(valor)
    return campos, texto[achado.end():]


def _versao(valor: str | None) -> str:
    if not valor:
        return VERSAO_PADRAO
    achado = _VERSAO.search(str(valor))
    if not achado:
        return VERSAO_PADRAO
    partes = achado.group(1).split(".")
    while len(partes) < 3:
        partes.append("0")
    return ".".join(partes)


def _prioridade(valor) -> int | None:
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    return n if n in (1, 2, 3) else None


def _tags(texto: str) -> tuple[str, tuple[str, ...]]:
    """Separa as tags `#x` do fim de um título; devolve (título limpo, tags)."""
    tags = tuple(t for t in _TAG.findall(texto))
    if not tags:
        return texto.strip(), ()
    limpo = _TAG.sub("", texto).strip()
    return limpo, tags


# ── A nota da instituição ─────────────────────────────────────────────────────


def ler_instituicao(texto: str, *, nome_da_pasta: str) -> Instituicao:
    """Os campos da nota, com o frontmatter (quando há) valendo mais que o corpo."""
    frontmatter, corpo = ler_frontmatter(texto)
    titulo = _TITULO_H1.search(corpo)
    inst = Instituicao(nome=nfc(titulo.group(1).strip()) if titulo else nfc(nome_da_pasta))

    campos: dict[str, str] = {}
    observacoes: list[str] = []
    em_navegacao = False
    for linha in corpo.splitlines():
        if linha.startswith("## "):
            em_navegacao = True  # daqui em diante é navegação/wikilinks
            continue
        if em_navegacao or linha.startswith("# "):
            continue
        campo = _CAMPO.match(linha.strip())
        if campo:
            campos[_normalizar_chave(campo.group(1))] = _sem_angulares(campo.group(2))
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
    inst.versao = _versao(campos.get("versao usada para os schemas"))
    inst.coletada_em = campos.get("ultima coleta de metadados")
    if "—" in inst.nome:
        inst.sigla = inst.nome.rsplit("—", 1)[1].strip() or None

    # O frontmatter vence o corpo: é a forma explícita, editada nas Propriedades.
    if frontmatter.get("sigla"):
        inst.sigla = str(frontmatter["sigla"]).strip()
    if frontmatter.get("endpoint_wfs"):
        inst.endpoint = _sem_angulares(str(frontmatter["endpoint_wfs"]))
    if frontmatter.get("versao_wfs"):
        inst.versao = _versao(str(frontmatter["versao_wfs"]))
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
    inst.prioridade = _prioridade(frontmatter.get("prioridade"))

    if observacoes:
        inst.observacoes = " ".join(observacoes)[:MAX_DICAS].strip()
    return inst


def _normalizar_chave(chave: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", chave)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold().strip()


# ── Camadas.md ────────────────────────────────────────────────────────────────


def ler_camadas(texto: str) -> list[Camada]:
    """As camadas, com o grupo (`## Grupo (n)`) em que aparecem e as tags."""
    camadas: list[Camada] = []
    grupo: str | None = None
    for linha in texto.splitlines():
        cabecalho = _GRUPO.match(linha)
        if cabecalho:
            grupo = nfc(cabecalho.group(1).strip())
            continue
        item = _CAMADA.match(linha.strip())
        if not item:
            continue
        type_name = item.group(1).strip()
        titulo, tags = _tags(nfc(item.group(2) or ""))
        # Bullet de ArcGIS (`- \`Título\` — <url>`): o "nome" não é um typeName
        # e o título é uma URL. Fica de fora — o nó WFS não lê isso.
        if titulo.startswith("<http") or titulo.startswith("http"):
            continue
        camadas.append(Camada(grupo=grupo, type_name=type_name, titulo=titulo or type_name, tags=tags))
    return camadas


# ── Atributos.md ──────────────────────────────────────────────────────────────


def _coluna(celulas: list[str]) -> Coluna | None:
    if len(celulas) < 2:
        return None
    nome = celulas[0].strip().strip("`").strip()
    xsd = celulas[1].strip().strip("`").strip()
    if not nome or not xsd or nome.lower() in ("campo", "---", ":---"):
        return None
    nulo = celulas[2].strip().lower() if len(celulas) > 2 else "true"
    if xsd.startswith("gml:"):
        tipo = GEOMETRIAS.get(xsd[4:], "Geometry")
    else:
        tipo = xsd.split(":", 1)[1] if ":" in xsd else xsd
    return Coluna(name=nome, type=tipo, xsd=xsd, nullable=nulo not in ("false", "não", "nao", "n"))


def ler_atributos(texto: str) -> dict[str, EsquemaDoVault]:
    """`{type_name: esquema}` das tabelas de `Atributos.md`."""
    esquemas: dict[str, EsquemaDoVault] = {}
    atual: str | None = None
    colunas: list[Coluna] = []

    def fechar() -> None:
        if atual is None:
            return
        geometria = next((c for c in colunas if c.xsd.startswith("gml:")), None)
        esquemas[atual] = EsquemaDoVault(
            columns=tuple(colunas),
            geometry_column=geometria.name if geometria else None,
            geometry_type=geometria.type if geometria else None,
        )

    for linha in texto.splitlines():
        cabecalho = _ATRIBUTO_H3.match(linha.strip())
        if cabecalho:
            fechar()
            atual, colunas = cabecalho.group(1).strip(), []
            continue
        if atual is None:
            continue
        tabela = _LINHA_DE_TABELA.match(linha.strip())
        if not tabela:
            continue
        celulas = tabela.group(1).split("|")
        if all(c.strip().strip(":-") == "" for c in celulas):
            continue  # a linha separadora |---|---|
        coluna = _coluna(celulas)
        if coluna:
            colunas.append(coluna)
    fechar()
    return esquemas


# ── _sinonimos.md ─────────────────────────────────────────────────────────────


def ler_sinonimos(texto: str) -> dict[str, set[str]]:
    """`{termo: {sinônimos}}` da tabela (ou das linhas `- termo: a, b`)."""
    saida: dict[str, set[str]] = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        termo = sinonimos = None
        tabela = _LINHA_DE_TABELA.match(linha)
        if tabela:
            celulas = [c.strip() for c in tabela.group(1).split("|")]
            if len(celulas) >= 2 and celulas[0].lower() not in ("termo", "") and not set(celulas[0]) <= set(":-"):
                termo, sinonimos = celulas[0], celulas[1]
        elif linha.startswith("- ") and ":" in linha:
            termo, sinonimos = linha[2:].split(":", 1)
        if not termo or not sinonimos:
            continue
        lista = {s.strip() for s in sinonimos.split(",") if s.strip()}
        if lista:
            saida.setdefault(termo.strip(), set()).update(lista)
    return saida


# ── A pasta inteira ───────────────────────────────────────────────────────────


def _notas_da_instituicao(pasta: Path) -> list[Path]:
    """As notas candidatas, `nota-base.md` por último: a nota nomeada é a que
    costuma trazer o endpoint."""
    notas = [
        p for p in sorted(pasta.iterdir())
        if p.is_file() and p.suffix.lower() == ".md"
        and p.name not in (ARQUIVO_DE_CAMADAS, ARQUIVO_DE_ATRIBUTOS)
        and not p.name.startswith("_")
    ]
    return sorted(notas, key=lambda p: p.name == "nota-base.md")


def _sort_by(colunas: tuple[Coluna, ...]) -> str | None:
    nomes = {c.name.lower(): c.name for c in colunas}
    for candidato in CANDIDATOS_A_SORTBY:
        if candidato in nomes:
            return nomes[candidato]
    return None


def ler_instituicao_da_pasta(pasta: Path) -> Iterator[RegistroDoVault | Ignorada]:
    """Os registros de UMA pasta de instituição (ou a `Ignorada` que a resume)."""
    nome = nfc(pasta.name)
    try:
        inst: Instituicao | None = None
        for nota in _notas_da_instituicao(pasta):
            candidata = ler_instituicao(nota.read_text(encoding="utf-8"), nome_da_pasta=nome)
            if candidata.endpoint:
                inst = candidata
                break
            inst = inst or candidata
        if inst is None or not inst.endpoint:
            yield Ignorada(nome, "sem_endpoint_wfs")
            return
        if _CREDENCIAL_NA_URL.search(inst.endpoint):
            yield Ignorada(nome, "url_com_credencial")
            return
        camadas_md = pasta / ARQUIVO_DE_CAMADAS
        camadas = ler_camadas(camadas_md.read_text(encoding="utf-8")) if camadas_md.exists() else []
        if not camadas:
            yield Ignorada(nome, "sem_camadas")
            return
        atributos_md = pasta / ARQUIVO_DE_ATRIBUTOS
        esquemas = ler_atributos(atributos_md.read_text(encoding="utf-8")) if atributos_md.exists() else {}
    except (OSError, UnicodeDecodeError) as exc:
        yield Ignorada(nome, "nota_ilegivel", str(exc)[:200])
        return

    sigla = inst.sigla or nome
    descricao = inst.nome
    if inst.finalidade:
        descricao = f"{inst.nome.rstrip('.')}. {inst.finalidade}"
    base_de_temas = [sigla] + inst.temas
    if inst.pais:
        base_de_temas.append(inst.pais)
    if inst.uf:
        base_de_temas.append(inst.uf)

    for camada in camadas:
        esquema = esquemas.get(camada.type_name)
        propriedades: dict = {"url": inst.endpoint, "typeName": camada.type_name, "version": inst.versao}
        if esquema:
            ordenacao = _sort_by(esquema.columns)
            if ordenacao:
                propriedades["sortBy"] = ordenacao
        temas: list[str] = list(base_de_temas)
        if camada.grupo:
            temas.append(camada.grupo)
        prioridade = inst.prioridade or 2
        for tag in camada.tags:
            tag_limpa = _normalizar_chave(tag)
            if tag_limpa == "preferida":
                prioridade = 1
            elif tag_limpa in ("secundaria", "secundária"):
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
            esquema=esquema.como_dict() if esquema else None,
            propriedades=propriedades,
            dicas=inst.observacoes,
            prioridade=prioridade,
            versao=inst.versao,
            coletada_em=inst.coletada_em,
        )


def ler_pasta(caminho: str | Path) -> Iterator[RegistroDoVault | Ignorada]:
    """Percorre `<caminho>/<INSTITUIÇÃO>/` e gera os registros e as ignoradas.

    Arquivos soltos na raiz (índice, relatórios, scripts) não são fontes e são
    pulados sem aviso — só `_sinonimos.md` tem papel, lido por `sinonimos_de`.
    """
    raiz = Path(caminho)
    if not raiz.is_dir():
        return
    for pasta in sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith(".")):
        yield from ler_instituicao_da_pasta(pasta)


def sinonimos_de(caminho: str | Path) -> dict[str, set[str]]:
    """Os sinônimos de `_sinonimos.md` na raiz da pasta, ou `{}`."""
    arquivo = Path(caminho) / ARQUIVO_DE_SINONIMOS
    if not arquivo.is_file():
        return {}
    try:
        return ler_sinonimos(arquivo.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}
