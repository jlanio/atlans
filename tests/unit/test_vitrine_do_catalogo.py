# tests/unit/test_vitrine_do_catalogo.py
"""The numbers and names of the Home showcase against the catalog seed.

`web/lib/catalogo.ts` holds CONSTANTS — the Home's anonymous sidebar cannot make
requests (see the header of that file and of `home-sidebar.tsx`), so what it
shows is written by hand. The price of that is aging silently: someone adds an
institution under `catalogo/geoservicos/` and the Home keeps announcing the old
number, which is worse than announcing nothing.

This test is what collects the price. It recomputes everything from the folder
and, when it diverges, states the new number in the message — updating the
showcase means copying it back.

The set that counts is the SAME one the import takes seriously: a folder with
`Camadas.md`, `Atributos.md` and an institution note that declares a WFS
endpoint. The others (ArcGIS REST, "metadados em validação") are left out with
the reason `sem_endpoint_wfs` — see `docs/sources.md`.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SEED_DIR = RAIZ / "catalogo" / "geoservicos"
VITRINE = RAIZ / "web" / "lib" / "catalogo.ts"

# The CMR belongs to FUNAI: two folders, one institution. That is the difference
# between the 77 folders with WFS and the 76 institutions `docs/sources.md` announces.
SAME_INSTITUTION_FOLDERS = {"FUNAI CMR": "FUNAI"}

# The seed's country vocabulary (the prefix used to name the folders from
# outside Brazil). It lives here, and not in the TypeScript, because it lets the
# test detect the case the showcase has no way to notice on its own: a NEW
# country gaining WFS and staying out of the strip.
COUNTRY_PREFIXES = (
    "Antígua e Barbuda", "Argentina", "Barbados", "Bolivia", "Canadá", "Chile",
    "Colombia", "Costa Rica", "Dominica", "EUA", "Equador", "Granada",
    "Guatemala", "Guiana Francesa", "Haiti", "México", "Nicarágua", "Panamá",
    "Paraguai", "Peru", "República Dominicana", "Santa Lúcia", "Uruguai",
)


def _has_wfs_endpoint(pasta: Path) -> bool:
    """The institution note declares a WFS endpoint."""
    for nota in pasta.glob("*.md"):
        if nota.name in ("Camadas.md", "Atributos.md"):
            continue
        if "endpoint wfs" in nota.read_text(encoding="utf-8").lower():
            return True
    return False


@pytest.fixture(scope="module")
def folders_with_wfs() -> dict[str, int]:
    """`{nome da pasta: camadas}` for what the import actually takes."""
    if not SEED_DIR.is_dir():
        pytest.skip("a semente do catálogo não está neste checkout")
    found: dict[str, int] = {}
    for pasta in sorted(p for p in SEED_DIR.iterdir() if p.is_dir()):
        camadas = pasta / "Camadas.md"
        if not camadas.exists() or not (pasta / "Atributos.md").exists():
            continue
        if not _has_wfs_endpoint(pasta):
            continue
        total = re.search(r"Total: \*\*(\d+)\*\*", camadas.read_text(encoding="utf-8"))
        if total:
            found[pasta.name] = int(total.group(1))
    assert found, "nenhuma pasta com WFS: o parser deste teste saiu do lugar"
    return found


@pytest.fixture(scope="module")
def vitrine() -> str:
    return VITRINE.read_text(encoding="utf-8")


def _number_field(vitrine: str, campo: str) -> int:
    achado = re.search(rf"{campo}:\s*([\d_]+)", vitrine)
    assert achado, f"`{campo}` sumiu de web/lib/catalogo.ts"
    return int(achado.group(1).replace("_", ""))


def _bases(vitrine: str, constante: str) -> list[tuple[str, str]]:
    bloco = re.search(rf"export const {constante}[^=]*=\s*\[(.*?)\n\]", vitrine, re.S)
    assert bloco, f"`{constante}` sumiu de web/lib/catalogo.ts"
    pares = re.findall(r'rotulo:\s*"([^"]+)",\s*pasta:\s*"([^"]+)"', bloco.group(1))
    assert pares, f"`{constante}` está vazia"
    return pares


def test_layers(vitrine, folders_with_wfs):
    soma = sum(folders_with_wfs.values())
    assert _number_field(vitrine, "camadas") == soma, (
        f"a semente agora tem {soma} camadas com WFS — atualize `camadas` em web/lib/catalogo.ts"
    )


def test_institutions(vitrine, folders_with_wfs):
    distintas = {SAME_INSTITUTION_FOLDERS.get(nome, nome) for nome in folders_with_wfs}
    assert _number_field(vitrine, "instituicoes") == len(distintas), (
        f"a semente agora tem {len(distintas)} instituições com WFS ({len(folders_with_wfs)} pastas) — "
        "atualize `instituicoes` em web/lib/catalogo.ts"
    )


def test_countries(vitrine, folders_with_wfs):
    """Brazil plus the countries outside it — and the strip has to name all of them."""
    from_outside = {
        prefixo
        for prefixo in COUNTRY_PREFIXES
        for nome in folders_with_wfs
        if nome == prefixo or nome.startswith(prefixo + " ")
    }
    assert _number_field(vitrine, "paises") == len(from_outside) + 1, (
        f"a semente agora tem {len(from_outside)} países com WFS além do Brasil — "
        "atualize `paises` em web/lib/catalogo.ts"
    )
    in_strip = {pasta for _, pasta in _bases(vitrine, "PAISES")}
    assert in_strip == from_outside, (
        f"a fita de países não bate com a semente: falta {sorted(from_outside - in_strip)}, "
        f"sobra {sorted(in_strip - from_outside)}"
    )


@pytest.mark.parametrize("constante", ["ORGAOS_FEDERAIS", "ORGAOS_REGIONAIS", "PAISES"])
def test_each_cited_name_exists_in_the_seed(constante, vitrine, folders_with_wfs):
    """No showcase label is fiction: each one has a folder with WFS behind it."""
    for rotulo, pasta in _bases(vitrine, constante):
        casa = [n for n in folders_with_wfs if n == pasta or n.startswith(pasta + " ")]
        assert casa, (
            f'a vitrine mostra "{rotulo}", mas nenhuma pasta com WFS começa por "{pasta}"'
        )
