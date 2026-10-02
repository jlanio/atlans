# tests/unit/test_locks_python.py
"""
Os locks Python — o que a imagem, o CI, o app desktop e a instalação pela CLI
instalam — têm de estar em dia com as fontes, trazer hash em toda linha e dar a
mesma versão para o mesmo pacote em todo lugar.

Por que isso é teste, e não só convenção:

- O CI instala o LOCK. Um `.in` editado sem regerar o `.txt` passaria verde e a
  mudança simplesmente não aconteceria — um pacote novo não entraria, um que
  saiu continuaria instalado; um pino mexido à mão no lock divergiria da fonte
  em silêncio.
- Sem hash, o pip não confere nada: um lock regerado sem `--generate-hashes`
  instalaria o que o PyPI entregasse, e é essa conferência que impede um
  arquivo trocado lá de instalar. (Com hash em parte das linhas, o pip recusa o
  arquivo inteiro; o risco real é o lock inteiro sair sem.)
- Mesma versão em todo lugar é o que mantém a API, o executor do Docker e o do
  app desktop rodando as mesmas bibliotecas — o bug que só aparece num deles é
  o mais caro de achar.
- Os flags `--require-hashes`/`--only-binary=:all:` nos Dockerfiles e no CI são
  uma linha cada; sumir com um deles desliga a proteção sem quebrar nada.
- Um `-c` dentro de um `.in` faz o Dependabot falhar ao regenerar o lock (ver
  PARES em scripts/travar_python.py): a restrição vai pela linha de comando.

Regerar: `python scripts/travar_python.py`. Estático e sem rede, no espírito de
`test_ci_workflow.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

# (fonte, lock, restrições) — os PARES de scripts/travar_python.py.
TRIOS = [
    ("requirements.in", "requirements.txt", []),
    ("requirements-dev.in", "requirements-dev.txt", ["requirements.txt"]),
    ("executor/requirements-full.in", "executor/requirements-full.txt", []),
    ("executor/requirements.in", "executor/requirements.txt", ["executor/requirements-full.txt"]),
]
PARES = [(entrada, saida) for entrada, saida, _ in TRIOS]
LOCKS = [saida for _, saida in PARES]

_PINO = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s\\;#]+)")
_NOME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalizar(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def _blocos(caminho: str) -> dict[str, tuple[str, int]]:
    """`nome -> (versão, quantos hashes)` de um requirements com hash."""
    blocos: dict[str, tuple[str, int]] = {}
    atual = None
    for linha in (RAIZ / caminho).read_text(encoding="utf-8").splitlines():
        m = _PINO.match(linha)
        if m:
            atual = _normalizar(m.group(1))
            blocos[atual] = (m.group(2), 0)
        elif atual and linha.strip().startswith("--hash="):
            versao, n = blocos[atual]
            blocos[atual] = (versao, n + 1)
        elif linha.strip() and not linha.startswith((" ", "\t", "#")):
            # Linha de requisito que não é `nome==versão`: um lock não tem isso.
            pytest.fail(f"{caminho}: linha fora do formato de lock: {linha!r}")
        else:
            atual = None
    return blocos


def _pedidos_por(caminho: str) -> dict[str, set[str]]:
    """`nome -> de onde veio`, pelas anotações `# via` do pip-compile (numa
    linha, `# via X`, ou em várias, `# via` seguido de `#   X`)."""
    via: dict[str, set[str]] = {}
    atual, lendo = None, False
    for linha in (RAIZ / caminho).read_text(encoding="utf-8").splitlines():
        m = _PINO.match(linha)
        if m:
            atual, lendo = _normalizar(m.group(1)), False
            via[atual] = set()
            continue
        uma = re.match(r"^\s+# via\s+(\S.*)$", linha)
        if atual and uma:
            via[atual].add(uma.group(1).strip())
        elif atual and re.match(r"^\s+# via\s*$", linha):
            lendo = True
        elif atual and lendo and (item := re.match(r"^\s+#\s{3}(\S.*)$", linha)):
            via[atual].add(item.group(1).strip())
        elif not linha.lstrip().startswith("--hash="):
            lendo = False
    return via


def _fonte(caminho: str) -> tuple[dict[str, str], set[str]]:
    """Os pinos `==` e todos os nomes pedidos por um `.in`."""
    pinos, nomes = {}, set()
    for linha in (RAIZ / caminho).read_text(encoding="utf-8").splitlines():
        if not linha.strip() or linha.lstrip().startswith(("#", "-")):
            continue
        m = _PINO.match(linha.strip())
        if m:
            pinos[_normalizar(m.group(1))] = m.group(2)
        nome = _NOME.match(linha.strip())
        if nome:
            nomes.add(_normalizar(nome.group(1)))
    return pinos, nomes


@pytest.mark.parametrize("entrada,saida", PARES, ids=[s for _, s in PARES])
def test_cada_lock_bate_com_a_sua_fonte(entrada, saida):
    pinos, nomes = _fonte(entrada)
    travados = _blocos(saida)

    faltando = sorted(nomes - set(travados))
    assert faltando == [], f"{entrada} pede {faltando}, que não estão em {saida} — regere o lock"

    divergentes = {n: (v, travados[n][0]) for n, v in pinos.items() if travados[n][0] != v}
    assert divergentes == {}, f"{entrada} x {saida} (fonte, lock): {divergentes} — regere o lock"

    # E o contrário: o que o lock diz ter vindo do `.in` e já saiu de lá
    # continuaria sendo instalado.
    sobrando = sorted(n for n, fontes in _pedidos_por(saida).items() if f"-r {entrada}" in fontes and n not in nomes)
    assert sobrando == [], f"{saida} ainda traz {sobrando}, que saíram de {entrada} — regere o lock"


@pytest.mark.parametrize("entrada", [e for e, _ in PARES])
def test_as_fontes_nao_embutem_restricao(entrada):
    embutidas = [
        linha for linha in (RAIZ / entrada).read_text(encoding="utf-8").splitlines()
        if re.match(r"^\s*(-c|--constraint)\b", linha)
    ]
    assert embutidas == [], (
        f"{entrada}: {embutidas} — o Dependabot compila cada .in sozinho e esbarra no lock "
        "velho da restrição; ela vai em PARES, em scripts/travar_python.py"
    )


@pytest.mark.parametrize("lock", LOCKS)
def test_toda_linha_dos_locks_tem_hash(lock):
    sem_hash = sorted(n for n, (_, hashes) in _blocos(lock).items() if hashes == 0)
    assert sem_hash == [], f"{lock}: pacotes sem hash {sem_hash}"


@pytest.mark.parametrize("entrada,saida,restricoes", TRIOS, ids=[s for _, s, _ in TRIOS])
def test_os_locks_saem_do_pip_compile_com_hash(entrada, saida, restricoes):
    """O cabeçalho é o comando que regera o lock, e é por ele (`--output-file`)
    que o Dependabot acha o lock de cada `.in`. Quem o reexecutar tem de obter o
    mesmo arquivo: com hash, com as restrições e sem o `--no-index` que o
    pip-tools 7.6.1 escreve por engano (resolveria sem índice nenhum)."""
    comando = next(
        (l for l in (RAIZ / saida).read_text(encoding="utf-8").splitlines() if re.match(r"^#\s+pip-compile\s", l)),
        "",
    )
    assert "--generate-hashes" in comando, f"{saida}: cabeçalho sem o comando do pip-compile com hash"
    assert f"--output-file={saida}" in comando, f"{saida}: o cabeçalho não aponta para o próprio lock"
    assert comando.rstrip().endswith(entrada), f"{saida}: o cabeçalho não compila {entrada}"
    assert "--no-index" not in comando.split(), f"{saida}: o cabeçalho traz o --no-index espúrio"
    for restricao in restricoes:
        assert f"--constraint={restricao}" in comando, f"{saida}: compilado sem a restrição {restricao}"


def test_mesma_versao_em_todos_os_locks():
    visto: dict[str, dict[str, str]] = {}
    for lock in LOCKS:
        for nome, (versao, _) in _blocos(lock).items():
            visto.setdefault(nome, {})[lock] = versao
    divergentes = {n: v for n, v in visto.items() if len(set(v.values())) > 1}
    assert divergentes == {}, f"o mesmo pacote em versões diferentes: {divergentes}"


@pytest.mark.parametrize(
    "arquivo,trecho",
    [
        ("Dockerfile.api", "--require-hashes --only-binary=:all: --prefix=/install -r requirements.txt"),
        ("Dockerfile.executor", "--require-hashes --only-binary=:all: -r requirements-full.txt"),
        (".github/workflows/ci.yml",
         "pip install --require-hashes --only-binary=:all: -r requirements.txt -r requirements-dev.txt"),
        (".github/workflows/ci.yml", "pip install --require-hashes --only-binary=:all: -r requirements-dev.txt"),
        # O desktop instala o lock do executor, e com hash (e confere no Windows).
        ("desktop/scripts/lib.mjs", "export const LOCK     = path.join(REPO, 'executor', 'requirements-full.txt')"),
        ("desktop/scripts/build-python-runtime.mjs", "'--require-hashes',"),
        ("desktop/scripts/check-lock.mjs", "'--require-hashes', '--only-binary=:all:'"),
    ],
)
def test_quem_instala_os_locks_confere_o_hash(arquivo, trecho):
    assert trecho in (RAIZ / arquivo).read_text(encoding="utf-8"), f"{arquivo} deixou de instalar com hash"


def test_o_lock_de_dev_instala_no_windows():
    """Quem commita do Windows instala o requirements-dev.txt (o pre-commit vem
    dele). O lock sai do Linux, que não vê o colorama que o `build` (do
    pip-tools) pede no Windows; sem ele no `.in`, o --require-hashes recusa o
    lock inteiro lá — e ninguém no Linux percebe."""
    assert "colorama" in _blocos("requirements-dev.txt"), "o requirements-dev.in perdeu o colorama (Windows)"
