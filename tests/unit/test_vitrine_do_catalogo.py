# tests/unit/test_vitrine_do_catalogo.py
"""Os números e os nomes da vitrine da Home contra a semente do catálogo.

`web/lib/catalogo.ts` guarda CONSTANTES — a barra anônima da Home não pode fazer
requisição (ver o cabeçalho daquele arquivo e o do `home-sidebar.tsx`), então o
que ela mostra é escrito à mão. O preço disso é envelhecer em silêncio: alguém
acrescenta uma instituição em `catalogo/geoservicos/` e a Home segue anunciando
o número velho, que é pior do que não anunciar nada.

Este teste é o que cobra o preço. Ele recalcula tudo a partir da pasta e, quando
diverge, diz o número novo na mensagem — atualizar a vitrine é copiar de volta.

O conjunto que conta é o MESMO que a importação leva a sério: pasta com
`Camadas.md`, `Atributos.md` e uma nota de instituição que declara endpoint WFS.
As outras (ArcGIS REST, "metadados em validação") ficam de fora com o motivo
`sem_endpoint_wfs` — ver `docs/fontes.md`.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SEMENTE = RAIZ / "catalogo" / "geoservicos"
VITRINE = RAIZ / "web" / "lib" / "catalogo.ts"

# O CMR é da FUNAI: duas pastas, uma instituição. É a diferença entre as 77
# pastas com WFS e as 76 instituições que `docs/fontes.md` anuncia.
PASTAS_DA_MESMA_INSTITUICAO = {"FUNAI CMR": "FUNAI"}

# O vocabulário de países da semente (o prefixo com que as pastas de fora do
# Brasil são nomeadas). Está aqui, e não no TypeScript, porque serve para o
# teste detectar o caso que a vitrine não tem como perceber sozinha: um país
# NOVO ganhar WFS e continuar de fora da fita.
PREFIXOS_DE_PAIS = (
    "Antígua e Barbuda", "Argentina", "Barbados", "Bolivia", "Canadá", "Chile",
    "Colombia", "Costa Rica", "Dominica", "EUA", "Equador", "Granada",
    "Guatemala", "Guiana Francesa", "Haiti", "México", "Nicarágua", "Panamá",
    "Paraguai", "Peru", "República Dominicana", "Santa Lúcia", "Uruguai",
)


def _tem_endpoint_wfs(pasta: Path) -> bool:
    """A nota da instituição declara um endpoint WFS."""
    for nota in pasta.glob("*.md"):
        if nota.name in ("Camadas.md", "Atributos.md"):
            continue
        if "endpoint wfs" in nota.read_text(encoding="utf-8").lower():
            return True
    return False


@pytest.fixture(scope="module")
def pastas_com_wfs() -> dict[str, int]:
    """`{nome da pasta: camadas}` para o que a importação de fato leva."""
    if not SEMENTE.is_dir():
        pytest.skip("a semente do catálogo não está neste checkout")
    achadas: dict[str, int] = {}
    for pasta in sorted(p for p in SEMENTE.iterdir() if p.is_dir()):
        camadas = pasta / "Camadas.md"
        if not camadas.exists() or not (pasta / "Atributos.md").exists():
            continue
        if not _tem_endpoint_wfs(pasta):
            continue
        total = re.search(r"Total: \*\*(\d+)\*\*", camadas.read_text(encoding="utf-8"))
        if total:
            achadas[pasta.name] = int(total.group(1))
    assert achadas, "nenhuma pasta com WFS: o parser deste teste saiu do lugar"
    return achadas


@pytest.fixture(scope="module")
def vitrine() -> str:
    return VITRINE.read_text(encoding="utf-8")


def _numero(vitrine: str, campo: str) -> int:
    achado = re.search(rf"{campo}:\s*([\d_]+)", vitrine)
    assert achado, f"`{campo}` sumiu de web/lib/catalogo.ts"
    return int(achado.group(1).replace("_", ""))


def _bases(vitrine: str, constante: str) -> list[tuple[str, str]]:
    bloco = re.search(rf"export const {constante}[^=]*=\s*\[(.*?)\n\]", vitrine, re.S)
    assert bloco, f"`{constante}` sumiu de web/lib/catalogo.ts"
    pares = re.findall(r'rotulo:\s*"([^"]+)",\s*pasta:\s*"([^"]+)"', bloco.group(1))
    assert pares, f"`{constante}` está vazia"
    return pares


def test_camadas(vitrine, pastas_com_wfs):
    soma = sum(pastas_com_wfs.values())
    assert _numero(vitrine, "camadas") == soma, (
        f"a semente agora tem {soma} camadas com WFS — atualize `camadas` em web/lib/catalogo.ts"
    )


def test_instituicoes(vitrine, pastas_com_wfs):
    distintas = {PASTAS_DA_MESMA_INSTITUICAO.get(nome, nome) for nome in pastas_com_wfs}
    assert _numero(vitrine, "instituicoes") == len(distintas), (
        f"a semente agora tem {len(distintas)} instituições com WFS ({len(pastas_com_wfs)} pastas) — "
        "atualize `instituicoes` em web/lib/catalogo.ts"
    )


def test_paises(vitrine, pastas_com_wfs):
    """O Brasil mais os países de fora — e a fita tem de nomear todos eles."""
    de_fora = {
        prefixo
        for prefixo in PREFIXOS_DE_PAIS
        for nome in pastas_com_wfs
        if nome == prefixo or nome.startswith(prefixo + " ")
    }
    assert _numero(vitrine, "paises") == len(de_fora) + 1, (
        f"a semente agora tem {len(de_fora)} países com WFS além do Brasil — "
        "atualize `paises` em web/lib/catalogo.ts"
    )
    na_fita = {pasta for _, pasta in _bases(vitrine, "PAISES")}
    assert na_fita == de_fora, (
        f"a fita de países não bate com a semente: falta {sorted(de_fora - na_fita)}, "
        f"sobra {sorted(na_fita - de_fora)}"
    )


@pytest.mark.parametrize("constante", ["ORGAOS_FEDERAIS", "ORGAOS_REGIONAIS", "PAISES"])
def test_cada_nome_citado_existe_na_semente(constante, vitrine, pastas_com_wfs):
    """Nenhum rótulo da vitrine é ficção: cada um tem pasta com WFS por trás."""
    for rotulo, pasta in _bases(vitrine, constante):
        casa = [n for n in pastas_com_wfs if n == pasta or n.startswith(pasta + " ")]
        assert casa, (
            f'a vitrine mostra "{rotulo}", mas nenhuma pasta com WFS começa por "{pasta}"'
        )
