#!/usr/bin/env python3
"""scripts/avisos_de_terceiros.py — o THIRD-PARTY-NOTICES.md, a partir dos locks.

O Atlans é AGPL-3.0-only (LICENSE). O que ele instala de terceiros vem travado
nos locks: os pacotes do npm do web e do app desktop, e os do PyPI da API e do
executor. Este script lê os locks e escreve o THIRD-PARTY-NOTICES.md: cada
pacote, a versão, a licença e quem o usa; os conjuntos de ícones do
react-icons que os fontes importam; as bibliotecas nativas que algumas wheels
trazem; e, à parte, toda licença que não está em COMPATIVEIS, para alguém ler
antes de distribuir.

A licença de um pacote do npm vem no próprio package-lock.json. A de um pacote
do PyPI não está no lock: o script pergunta ao PyPI, pela versão travada, e
usa a expressão SPDX que o pacote declara (`License-Expression`). Sem ela, o
campo de licença curto ou o classificador; quando os dois são vagos («BSD»,
um texto inteiro), vale o que está em LIDAS_NO_PACOTE, lido no arquivo de
licença do próprio pacote. O que nada disso resolve sai como «desconhecida»
e vai para a revisão.

    python scripts/avisos_de_terceiros.py           # reescreve o THIRD-PARTY-NOTICES.md
    python scripts/avisos_de_terceiros.py --saida -  # só imprime

Os locks mudam a cada PR do Dependabot, e o arquivo não precisa acompanhar
cada um: ele é gerado de novo a cada versão publicada. Rodar aqui é para ver o
resultado, ou depois de somar uma dependência. Precisa de acesso ao PyPI; só
biblioteca padrão.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "THIRD-PARTY-NOTICES.md"

# (quem usa, lock). O primeiro campo é o que a coluna «Usado por» mostra.
LOCKS_NPM = [
    ("web", "web/package-lock.json"),
    ("desktop", "desktop/package-lock.json"),
]
LOCKS_PYPI = [
    ("API", "requirements.txt"),
    ("executor", "executor/requirements-full.txt"),
    ("executor mínimo", "executor/requirements.txt"),
]

# Pacotes `dev` do npm cujo código vai, mesmo assim, no que a instalação serve:
# o CSS do web e do app desktop os importa (`@import`), e o build os junta na
# folha de estilo. O teste confere a lista contra os `@import` dos fontes.
DEV_QUE_VAI_NO_BUILD = frozenset({"tailwindcss", "tw-animate-css"})

# Licenças que podem entrar numa obra AGPL-3.0: as livres que a FSF lista como
# compatíveis com a GPLv3 (https://www.gnu.org/licenses/license-list.html).
# Uma expressão com OR precisa de uma alternativa daqui; com AND, de todas.
COMPATIVEIS = frozenset({
    "0BSD", "AGPL-3.0-only", "AGPL-3.0-or-later", "Apache-2.0", "BlueOak-1.0.0",
    "BSD-2-Clause", "BSD-3-Clause", "BSL-1.0", "CC-BY-4.0", "CC0-1.0",
    "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later", "HPND", "ISC",
    "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0-only", "LGPL-3.0-or-later",
    "MIT", "MIT-0", "MIT-CMU", "MPL-2.0", "PSF-2.0", "Python-2.0",
    "Unlicense", "Zlib",
})

# Licenças que não entram no programa, mas convivem com ele como arquivo à
# parte (uma fonte servida ao navegador): valem só para uma obra de
# NO_REPOSITORIO marcada como agregada, e não para um pacote do npm ou do PyPI,
# cujo código é compilado junto. A OFL-1.1 é copyleft fraco para fontes; a FSF
# não a lista como compatível com a GPL, e aqui ela não precisa ser.
AGREGAVEIS = frozenset({"OFL-1.1"})

# Pacotes do PyPI sem `License-Expression` e com um campo de licença vago (um
# texto inteiro, ou «BSD» sem dizer qual): a licença lida no arquivo LICENSE
# do pacote, na versão travada. Só vale enquanto o pacote não declarar a
# expressão dele — a declarada ganha, e esta linha fica sobrando.
LIDAS_NO_PACOTE = {
    "cycler": "BSD-3-Clause",
    "jinja2": "BSD-3-Clause",
    "kiwisolver": "BSD-3-Clause",
    # A da PSF, com o nome do matplotlib no lugar.
    "matplotlib": "PSF-2.0",
    "pandas": "BSD-3-Clause",
    # Com uma exceção que permite ligar ao OpenSSL.
    "psycopg2-binary": "LGPL-3.0-or-later",
    # Apache-2.0 o que entrou a partir de 2017-12; o código anterior, BSD.
    "python-dateutil": "Apache-2.0 AND BSD-3-Clause",
}

# O campo `License` do PyPI, quando é um nome curto, e o SPDX dele.
_NOMES = {
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "bsd 3-clause": "BSD-3-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "isc license": "ISC",
    "mit license": "MIT",
}

# O classificador `License :: …` e o SPDX dele; os vagos («BSD License»,
# «LGPL» sem versão) ficam de fora de propósito.
_CLASSIFICADORES = {
    "Apache Software License": "Apache-2.0",
    "ISC License (ISCL)": "ISC",
    "MIT License": "MIT",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Python Software Foundation License": "PSF-2.0",
    "The Unlicense (Unlicense)": "Unlicense",
}

# O que mora DENTRO do repositório e é de terceiros: (obra, onde, licença,
# texto da licença), com os lugares e os textos em tuplas. Um arquivo copiado
# para cá entra nesta lista, com a licença ao lado dele. A licença é compatível
# com a AGPL-3.0 (COMPATIVEIS) ou, para um arquivo que só é servido à parte,
# uma de AGREGAVEIS.
NO_REPOSITORIO = [
    ("Inter, a fonte do web (The Inter Project Authors), servida como arquivo à parte", ("web/app/fonts/inter/",), "OFL-1.1", ("web/app/fonts/inter/OFL.txt",)),
    (
        "shadcn/ui, os componentes de base da interface (shadcn), adaptados",
        ("web/app/components/ui/", "web/hooks/use-mobile.ts", "desktop/src/renderer/components/ui/"),
        "MIT",
        ("web/app/components/ui/LICENSE.shadcn-ui.txt", "desktop/src/renderer/components/ui/LICENSE.shadcn-ui.txt"),
    ),
    (
        "Monokai, o tema do editor de código, portado do monaco-themes (Brijesh Bittu)",
        ("web/app/components/workflow/nodes-configuration/fields/monaco-code-editor.tsx",),
        "MIT",
        ("web/app/components/workflow/nodes-configuration/fields/LICENSE.monaco-themes.txt",),
    ),
]

# Os conjuntos do react-icons: o pacote é MIT, mas cada conjunto de ícones
# mantém a licença do projeto de onde veio (o LICENSE do react-icons lista
# todos). O gerador procura nos fontes do web e do app desktop os conjuntos
# importados (`react-icons/<conjunto>`); um que não está aqui sai como
# «desconhecida» e vai para a revisão.
CONJUNTOS_DO_REACT_ICONS = {
    "ai": ("Ant Design Icons", "MIT"),
    "bi": ("BoxIcons", "MIT"),
    "bs": ("Bootstrap Icons", "MIT"),
    "cg": ("css.gg", "MIT"),
    "ci": ("Circum Icons", "MPL-2.0"),
    "di": ("Devicons", "MIT"),
    "fa": ("Font Awesome 5 Free (Fonticons, Inc., https://fontawesome.com)", "CC-BY-4.0"),
    "fa6": ("Font Awesome 6 Free (Fonticons, Inc., https://fontawesome.com)", "CC-BY-4.0"),
    "fc": ("Flat Color Icons (Icons8)", "MIT"),
    "fi": ("Feather", "MIT"),
    "gi": ("Game Icons", "CC-BY-3.0"),
    "go": ("GitHub Octicons", "MIT"),
    "gr": ("Grommet Icons", "Apache-2.0"),
    "hi": ("Heroicons", "MIT"),
    "hi2": ("Heroicons 2", "MIT"),
    "im": ("IcoMoon Free", "CC-BY-4.0"),
    "io": ("Ionicons 4", "MIT"),
    "io5": ("Ionicons 5", "MIT"),
    "lia": ("Icons8 Line Awesome", "MIT"),
    "lu": ("Lucide", "ISC"),
    "md": ("Material Design icons (Google)", "Apache-2.0"),
    "pi": ("Phosphor Icons", "MIT"),
    "ri": ("Remix Icon", "Apache-2.0"),
    "rx": ("Radix Icons", "MIT"),
    "si": ("Simple Icons", "CC0-1.0"),
    "sl": ("Simple Line Icons", "MIT"),
    "tb": ("Tabler Icons", "MIT"),
    "tfi": ("Themify Icons", "MIT"),
    "ti": ("Typicons", "CC-BY-SA-3.0"),
    "vsc": ("VS Code Codicons (Microsoft)", "CC-BY-4.0"),
    "wi": ("Weather Icons", "OFL-1.1"),
}
# Onde procurar os imports, e o que pular: dependências, builds e testes.
FONTES_DOS_ICONES = ("web", "desktop/src")
_PULAR_PASTAS = frozenset({"node_modules", ".next", "dist", "out", "public", "coverage", "__tests__"})
_FONTE = re.compile(r"\.(?:ts|tsx|js|jsx|mjs|cjs)$")
_TESTE = re.compile(r"\.(?:test|spec)\.")
_IMPORT_DE_ICONE = re.compile(r"""['"]react-icons/([a-z0-9]+)['"]""")

# Wheels do PyPI que trazem bibliotecas nativas compiladas, com licença
# própria, junto do código do pacote: (pacote, o que vai dentro, licenças,
# onde está o texto). A coluna «Licença» das tabelas é a do pacote Python.
NATIVAS_NAS_WHEELS = [
    ("shapely", "GEOS", "LGPL-2.1", "`shapely-*.dist-info/licenses/LICENSE_GEOS`"),
    ("pyogrio", "GDAL, com as bibliotecas que ele usa", "MIT, com partes sob outras licenças livres", "https://gdal.org/en/stable/license.html"),
    ("pyproj", "PROJ, com as bibliotecas que ele usa (SQLite, libcurl, libtiff)", "MIT; as outras, as delas", "`pyproj-*.dist-info/licenses/LICENSE_proj` (o PROJ)"),
    ("numpy", "OpenBLAS e LAPACK; o runtime do GCC (libgfortran)", "BSD-3-Clause; GPL-3.0-or-later WITH GCC-exception-3.1", "`numpy-*.dist-info/licenses/LICENSE.txt`"),
    ("pillow", "as bibliotecas de imagem (libjpeg, libpng, libtiff, libwebp, FreeType, HarfBuzz e outras)", "as de cada uma", "`pillow-*.dist-info/licenses/LICENSE`"),
    ("psycopg2-binary", "libpq e OpenSSL, e o que o libpq usa: krb5, OpenLDAP, Cyrus SASL, PCRE, libselinux, libxcrypt", "PostgreSQL; Apache-2.0; MIT (krb5), OpenLDAP Public License, BSD (SASL, PCRE), domínio público (libselinux), LGPL-2.1 (libxcrypt)", "https://www.postgresql.org/about/licence/ e https://openssl-library.org/source/license/; as demais, nos projetos de cada uma"),
    ("cryptography", "OpenSSL, ligado estaticamente ao módulo Rust", "Apache-2.0", "https://openssl-library.org/source/license/"),
    ("uvloop", "libuv, ligado estaticamente", "MIT", "https://github.com/libuv/libuv/blob/v1.x/LICENSE"),
    ("pyarrow", "Arrow C++ e as bibliotecas que ele embute (zstd, lz4, snappy, brotli, re2, thrift e outras)", "Apache-2.0; as outras, as delas", "`pyarrow-*.dist-info/licenses/LICENSE.txt` e `NOTICE.txt`"),
    ("lxml", "libxml2 e libxslt", "MIT", "`lxml-*.dist-info/licenses/LICENSES.txt`"),
]

DESCONHECIDA = "desconhecida"

PYPI = "https://pypi.org/pypi"

_PINO = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s\\;#]+)")
_ID_SPDX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")


def normalizar(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


# ── Os locks ─────────────────────────────────────────────────────────────────

def pacotes_npm(lock: Path) -> dict[tuple[str, str], str]:
    """`(nome, versão) -> licença` dos pacotes de produção de um package-lock.json.

    Fica de fora o que é `dev`, menos o que o build junta assim mesmo
    (DEV_QUE_VAI_NO_BUILD): um `optional` (o binário do sharp de outra
    plataforma, por exemplo) é instalado onde serve, e vai junto.
    """
    pacotes = {}
    for caminho, dados in json.loads(lock.read_text(encoding="utf-8"))["packages"].items():
        if not caminho or dados.get("link"):
            continue
        nome = dados.get("name") or caminho.rsplit("node_modules/", 1)[-1]
        if dados.get("dev") and nome not in DEV_QUE_VAI_NO_BUILD:
            continue
        pacotes[(nome, dados["version"])] = _licenca_do_npm(dados.get("license"))
    return pacotes


def _licenca_do_npm(declarada) -> str:
    # Pacotes antigos declaram um objeto ({type, url}) ou uma lista deles.
    if isinstance(declarada, dict):
        declarada = declarada.get("type")
    if isinstance(declarada, list):
        tipos = [_licenca_do_npm(d) for d in declarada]
        declarada = " OR ".join(tipos) if tipos else None
    return declarada.strip() if isinstance(declarada, str) and declarada.strip() else DESCONHECIDA


def pinos_pypi(lock: Path) -> set[tuple[str, str]]:
    """`(nome, versão)` de cada pacote de um lock do pip-compile."""
    pinos = set()
    for linha in lock.read_text(encoding="utf-8").splitlines():
        m = _PINO.match(linha)
        if m:
            pinos.add((normalizar(m.group(1)), m.group(2)))
    return pinos


# ── A licença de um pacote do PyPI ───────────────────────────────────────────

def licenca_do_pypi(nome: str, info: dict) -> str:
    """A licença SPDX de um pacote, pelo `info` do JSON do PyPI daquela versão."""
    expressao = (info.get("license_expression") or "").strip()
    if expressao:
        return expressao
    if nome in LIDAS_NO_PACOTE:
        return LIDAS_NO_PACOTE[nome]
    # Mais de um classificador é a escolha entre eles; um vago, ou um que não
    # está no mapa, deixa a licença desconhecida.
    classificadores = {
        _CLASSIFICADORES.get(c.split(" :: ")[-1])
        for c in info.get("classifiers") or []
        if c.startswith("License :: ") and c != "License :: OSI Approved"
    }
    escolha = " OR ".join(sorted(classificadores)) if classificadores and None not in classificadores else None
    campo = (info.get("license") or "").strip()
    # Um campo de uma linha só é um nome; o de várias é o texto inteiro.
    if campo and "\n" not in campo and len(campo) <= 60:
        curta = _NOMES.get(campo.lower()) or (campo if _avaliar(campo) is not None else None)
        if curta:
            # O campo que diz uma das licenças de um pacote duplo («MIT», com
            # os classificadores do MIT e do Apache) não apaga a outra.
            if escolha and len(classificadores) > 1 and curta in classificadores:
                return escolha
            return curta
    return escolha or DESCONHECIDA


def consultar_pypi(pinos: set[tuple[str, str]]) -> dict[tuple[str, str], str]:
    """`(nome, versão) -> licença`, perguntando ao PyPI em paralelo."""
    def uma(pino):
        nome, versao = pino
        return pino, licenca_do_pypi(nome, _info(nome, versao))

    with ThreadPoolExecutor(max_workers=8) as executor:
        return dict(executor.map(uma, sorted(pinos)))


def _info(nome: str, versao: str) -> dict:
    url = f"{PYPI}/{nome}/{versao}/json"
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resposta:
                return json.load(resposta)["info"]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if tentativa == 2:
                raise SystemExit(f"Não deu para ler {url}: {exc}") from exc
            time.sleep(2 ** tentativa)
    raise AssertionError("inalcançável")


# ── Compatível ou não ────────────────────────────────────────────────────────

def compativel(licenca: str) -> bool:
    """Se a expressão SPDX pode entrar numa obra AGPL-3.0 (ver COMPATIVEIS)."""
    return bool(_avaliar(licenca))


def _avaliar(expressao: str) -> bool | None:
    """True/False pela regra de COMPATIVEIS; None se não é uma expressão SPDX."""
    fichas = re.findall(r"\(|\)|[^\s()]+", expressao)
    if not fichas:
        return None
    posicao = 0

    def proxima() -> str | None:
        return fichas[posicao] if posicao < len(fichas) else None

    def ou() -> bool | None:
        nonlocal posicao
        valor = e()
        while proxima() == "OR":
            posicao += 1
            outro = e()
            if valor is None or outro is None:
                return None
            valor = valor or outro
        return valor

    def e() -> bool | None:
        nonlocal posicao
        valor = termo()
        while proxima() == "AND":
            posicao += 1
            outro = termo()
            if valor is None or outro is None:
                return None
            valor = valor and outro
        return valor

    def termo() -> bool | None:
        nonlocal posicao
        ficha = proxima()
        if ficha == "(":
            posicao += 1
            valor = ou()
            if proxima() != ")":
                return None
            posicao += 1
            return valor
        if ficha is None or ficha in {")", "AND", "OR", "WITH"} or not _ID_SPDX.match(ficha):
            return None
        posicao += 1
        # Uma exceção (`X WITH Y`) só dá permissões a mais: vale a licença X.
        if proxima() == "WITH":
            posicao += 1
            if proxima() is None:
                return None
            posicao += 1
        return ficha in COMPATIVEIS

    valor = ou()
    return valor if posicao == len(fichas) else None


# ── O arquivo ────────────────────────────────────────────────────────────────

CABECALHO = """\
# Avisos de terceiros

O Atlans é software livre, sob a GNU Affero General Public License, versão 3
(AGPL-3.0-only); o texto está em [LICENSE](LICENSE). Ele usa obras de
terceiros, cada uma sob a licença que os autores dela escolheram. Esta página
diz quais são e sob que licença; o texto completo de cada licença vai junto com
a obra.

<!-- Gerado por scripts/avisos_de_terceiros.py a partir dos locks; não edite à
     mão, rode o script. -->

## Neste repositório

| Obra | Onde | Licença | Texto da licença |
|---|---|---|---|
{no_repositorio}

## Dados de terceiros no repositório

`catalogo/geoservicos/` reúne metadados de serviços WFS públicos de muitas
instituições (nomes, títulos e esquemas de camadas, colhidos do GetCapabilities
e do DescribeFeatureType de cada um). Esse conteúdo é de cada instituição e
segue os termos do serviço de origem; a organização em notas, as finalidades e
as dicas são do Atlans. Ver `catalogo/README.md`.

## Nos artefatos montados

Quem monta e distribui um artefato distribui, junto com o Atlans, o que vai
dentro dele, e com isso as licenças dessas obras. O que cada um leva:

- **As imagens da API e do executor** (`Dockerfile.api`, `Dockerfile.executor`)
  levam a imagem base (o Debian do `python:3.12-slim`, com a licença de cada
  pacote do sistema em `/usr/share/doc/`), o Python, a [LICENSE](LICENSE) e
  este arquivo, e os pacotes do PyPI das listas abaixo, inteiros: a licença de
  cada um fica em `site-packages/<pacote>.dist-info/`.
- **A imagem do web** (`web/Dockerfile.ui`) leva o Alpine do `node:24-alpine`,
  o Node.js, a [LICENSE](LICENSE) e este arquivo (em `/app/`), e o que o build
  do Next junta (a pasta `standalone`): o código dos pacotes do npm, mas não os
  arquivos de licença deles. Quem distribui essa imagem entrega junto os textos
  das licenças dos pacotes do npm. O editor de código serve o Monaco da própria
  origem, com a `LICENSE` e o `ThirdPartyNotices.txt` dele em `/monaco/`; o
  worker do MapLibre vai com a `LICENSE.txt` dele em `/maplibre/`.
- **O app desktop** (`desktop/`) leva o Electron, que o instalador acompanha de
  `LICENSE.electron.txt` e `LICENSES.chromium.html`; o Python do
  python-build-standalone (PSF-2.0, com as bibliotecas que ele embute e o
  `LICENSE.txt` dele); os pacotes do executor, com as licenças; e, em
  `resources/`, a LICENSE e este arquivo. O que o build junta do npm vai sem os
  arquivos de licença, como no web.
- **Os serviços que o `docker-compose.yml` sobe** (Valkey, MinIO, step-ca e
  Traefik) vêm das imagens oficiais de cada projeto, baixadas na instalação,
  com as licenças delas. O PostgreSQL fica fora do compose.

## Pacotes

Os pacotes abaixo não moram neste repositório: a instalação os baixa do npm e
do PyPI, nas versões travadas nos locks. A licença é a que o pacote declara, e
o texto completo vem com ele, em `node_modules/<pacote>/` ou em
`site-packages/<pacote>.dist-info/`. Do npm, entra o que vai para a produção,
e também o que o build junta mesmo sendo de desenvolvimento (`tailwindcss` e
`tw-animate-css`, no CSS).
"""


def gerar() -> tuple[str, list[tuple[str, str, str, str]]]:
    """O texto do arquivo e o que vai para a revisão: `(origem, pacote, versão, licença)`."""
    npm: dict[tuple[str, str], dict] = {}
    for quem, lock in LOCKS_NPM:
        for pino, licenca in pacotes_npm(RAIZ / lock).items():
            npm.setdefault(pino, {"licenca": licenca, "quem": []})["quem"].append(quem)

    usos_pypi: dict[tuple[str, str], list[str]] = {}
    for quem, lock in LOCKS_PYPI:
        for pino in pinos_pypi(RAIZ / lock):
            usos_pypi.setdefault(pino, []).append(quem)
    licencas_pypi = consultar_pypi(set(usos_pypi))
    pypi = {pino: {"licenca": licencas_pypi[pino], "quem": quem} for pino, quem in usos_pypi.items()}

    fora = [
        (origem, nome, versao, dados["licenca"])
        for origem, pacotes in (("npm", npm), ("PyPI", pypi))
        for (nome, versao), dados in sorted(pacotes.items())
        if not compativel(dados["licenca"])
    ]
    icones = conjuntos_de_icones()
    fora += [
        ("react-icons", f"react-icons/{conjunto}", "—", licenca)
        for conjunto, (_projeto, licenca) in sorted(icones.items())
        if not compativel(licenca)
    ]
    no_repositorio = "\n".join(
        f"| {obra} | {_caminhos(onde)} | {licenca} | {_caminhos(texto)} |"
        for obra, onde, licenca, texto in NO_REPOSITORIO
    )
    partes = [
        CABECALHO.format(no_repositorio=no_repositorio),
        _resumo(npm, pypi),
        _revisao(fora),
        _tabela("npm", LOCKS_NPM, npm),
        _icones(icones),
        _tabela("PyPI", LOCKS_PYPI, pypi),
        _nativas(),
    ]
    return "\n".join(partes), fora


def conjuntos_de_icones() -> dict[str, tuple[str, str]]:
    """`conjunto -> (projeto, licença)` de cada conjunto do react-icons que os fontes importam."""
    usados = set()
    for base in FONTES_DOS_ICONES:
        for pasta, subpastas, arquivos in os.walk(RAIZ / base):
            subpastas[:] = sorted(s for s in subpastas if s not in _PULAR_PASTAS)
            for nome in arquivos:
                if _FONTE.search(nome) and not _TESTE.search(nome):
                    texto = (Path(pasta) / nome).read_text(encoding="utf-8", errors="replace")
                    usados.update(_IMPORT_DE_ICONE.findall(texto))
    return {c: CONJUNTOS_DO_REACT_ICONS.get(c, (f"react-icons/{c}", DESCONHECIDA)) for c in sorted(usados)}


def _caminhos(caminhos: tuple[str, ...]) -> str:
    return ", ".join(f"`{c}`" for c in caminhos)


def _icones(icones: dict[str, tuple[str, str]]) -> str:
    linhas = [
        "### Os ícones do react-icons",
        "",
        "O `react-icons` é MIT, mas cada conjunto de ícones mantém a licença do projeto de onde veio. "
        "Os conjuntos que o web e o app desktop usam:",
        "",
        "| Conjunto | Projeto | Licença |",
        "|---|---|---|",
    ]
    linhas += [f"| `react-icons/{c}` | {projeto} | {_celula(licenca)} |" for c, (projeto, licenca) in icones.items()]
    linhas += [
        "",
        "Os ícones do Font Awesome Free são de Fonticons, Inc. (https://fontawesome.com), sob a "
        "Creative Commons Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/). "
        "Os logos de outros produtos (do Simple Icons, como o do PostgreSQL e o do MySQL) só "
        "identificam esses produtos: as marcas são dos donos delas.",
    ]
    return "\n".join(linhas) + "\n"


def _nativas() -> str:
    linhas = [
        "### Bibliotecas nativas dentro das wheels",
        "",
        "Algumas wheels do PyPI trazem bibliotecas compiladas, com licença própria, junto do código "
        "do pacote. A coluna «Licença» acima é a do pacote Python; o que mais vai dentro:",
        "",
        "| Pacote | Bibliotecas | Licença | Texto |",
        "|---|---|---|---|",
    ]
    linhas += [f"| `{pacote}` | {libs} | {_celula(licenca)} | {texto} |" for pacote, libs, licenca, texto in NATIVAS_NAS_WHEELS]
    return "\n".join(linhas) + "\n"


def _resumo(npm: dict, pypi: dict) -> str:
    contagem: dict[str, list[int]] = {}
    for coluna, pacotes in enumerate((npm, pypi)):
        for dados in pacotes.values():
            contagem.setdefault(dados["licenca"], [0, 0])[coluna] += 1
    linhas = ["### Resumo", "", "| Licença | npm | PyPI |", "|---|--:|--:|"]
    for licenca, (n, p) in sorted(contagem.items(), key=lambda item: (-sum(item[1]), item[0].lower())):
        linhas.append(f"| {_celula(licenca)} | {n or '—'} | {p or '—'} |")
    linhas.append(f"| **Total** | **{len(npm)}** | **{len(pypi)}** |")
    return "\n".join(linhas) + "\n"


def _revisao(fora: list[tuple[str, str, str, str]]) -> str:
    linhas = ["### Para revisar", ""]
    if not fora:
        linhas.append(
            "Nada: cada licença acima está entre as compatíveis com a AGPL-3.0 "
            "(`COMPATIVEIS`, em `scripts/avisos_de_terceiros.py`)."
        )
        return "\n".join(linhas) + "\n"
    linhas += [
        "Licenças fora de `COMPATIVEIS` (em `scripts/avisos_de_terceiros.py`), ou "
        "que o pacote não declara direito. Cada uma precisa ser lida antes de "
        "distribuir:",
        "",
        "| Origem | Pacote | Versão | Licença |",
        "|---|---|---|---|",
    ]
    linhas += [f"| {origem} | `{nome}` | {versao} | {_celula(licenca)} |" for origem, nome, versao, licenca in fora]
    return "\n".join(linhas) + "\n"


def _tabela(titulo: str, locks: list[tuple[str, str]], pacotes: dict) -> str:
    legenda = "Dos locks " + ", ".join(f"`{lock}` ({quem})" for quem, lock in locks) + "."
    linhas = [f"### {titulo}", "", legenda, "", "| Pacote | Versão | Licença | Usado por |", "|---|---|---|---|"]
    for (nome, versao), dados in sorted(pacotes.items(), key=lambda item: (item[0][0].lower(), item[0][1])):
        linhas.append(f"| `{nome}` | {versao} | {_celula(dados['licenca'])} | {', '.join(dados['quem'])} |")
    return "\n".join(linhas) + "\n"


def _celula(texto: str) -> str:
    return texto.replace("|", "\\|")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", default=str(SAIDA), help="onde escrever; «-» imprime (padrão: o THIRD-PARTY-NOTICES.md da raiz)")
    args = parser.parse_args()

    texto, fora = gerar()
    if args.saida == "-":
        sys.stdout.write(texto)
    else:
        Path(args.saida).write_text(texto, encoding="utf-8")
    for origem, nome, versao, licenca in fora:
        print(f"para revisar: {origem} {nome} {versao} — {licenca}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
