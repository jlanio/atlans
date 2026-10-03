# tests/unit/test_locks_python.py
"""
The Python locks — what the image, the CI, the desktop app and the CLI install
install — must be up to date with the sources, carry a hash on every line and give
the same version for the same package everywhere.

Why this is a test, and not just a convention:

- The CI installs the LOCK. A `.in` edited without regenerating the `.txt` would pass
  green and the change simply would not happen — a new package would not get in, one
  that was removed would stay installed; a pin changed by hand in the lock would
  silently diverge from the source.
- Without a hash, pip checks nothing: a lock regenerated without `--generate-hashes`
  would install whatever PyPI delivered, and that check is what keeps a file swapped
  there from being installed. (With hashes on only some lines, pip rejects the whole
  file; the real risk is the whole lock coming out without them.)
- The same version everywhere is what keeps the API, the Docker executor and the
  desktop app's executor running the same libraries — the bug that only shows up in
  one of them is the most expensive to find.
- The `--require-hashes`/`--only-binary=:all:` flags in the Dockerfiles and in the CI
  are one line each; dropping one of them turns off the protection without breaking anything.
- A `-c` inside a `.in` makes Dependabot fail when regenerating the lock (see
  PARES in scripts/travar_python.py): the constraint goes on the command line.

Regenerate: `python scripts/travar_python.py`. Static and offline, in the spirit of
`test_ci_workflow.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

# (source, lock, constraints) — the PARES of scripts/travar_python.py.
TRIOS = [
    ("requirements.in", "requirements.txt", []),
    ("requirements-dev.in", "requirements-dev.txt", ["requirements.txt"]),
    ("executor/requirements-full.in", "executor/requirements-full.txt", []),
    ("executor/requirements.in", "executor/requirements.txt", ["executor/requirements-full.txt"]),
]
PARES = [(entrada, saida) for entrada, saida, _ in TRIOS]
LOCKS = [saida for _, saida in PARES]

_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s\\;#]+)")
_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalize(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def _blocos(caminho: str) -> dict[str, tuple[str, int]]:
    """`name -> (version, how many hashes)` from a hashed requirements file."""
    blocos: dict[str, tuple[str, int]] = {}
    atual = None
    for linha in (RAIZ / caminho).read_text(encoding="utf-8").splitlines():
        m = _PIN.match(linha)
        if m:
            atual = _normalize(m.group(1))
            blocos[atual] = (m.group(2), 0)
        elif atual and linha.strip().startswith("--hash="):
            versao, n = blocos[atual]
            blocos[atual] = (versao, n + 1)
        elif linha.strip() and not linha.startswith((" ", "\t", "#")):
            # A requirement line that is not `name==version`: a lock does not have that.
            pytest.fail(f"{caminho}: linha fora do formato de lock: {linha!r}")
        else:
            atual = None
    return blocos


def _requirements_by(caminho: str) -> dict[str, set[str]]:
    """`name -> where it came from`, from pip-compile's `# via` annotations (on one
    line, `# via X`, or on several, `# via` followed by `#   X`)."""
    via: dict[str, set[str]] = {}
    atual, lendo = None, False
    for linha in (RAIZ / caminho).read_text(encoding="utf-8").splitlines():
        m = _PIN.match(linha)
        if m:
            atual, lendo = _normalize(m.group(1)), False
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


def _source(caminho: str) -> tuple[dict[str, str], set[str]]:
    """The `==` pins and all the names requested by a `.in`."""
    pins, nomes = {}, set()
    for linha in (RAIZ / caminho).read_text(encoding="utf-8").splitlines():
        if not linha.strip() or linha.lstrip().startswith(("#", "-")):
            continue
        m = _PIN.match(linha.strip())
        if m:
            pins[_normalize(m.group(1))] = m.group(2)
        nome = _NAME.match(linha.strip())
        if nome:
            nomes.add(_normalize(nome.group(1)))
    return pins, nomes


@pytest.mark.parametrize("entrada,saida", PARES, ids=[s for _, s in PARES])
def test_each_lock_matches_its_source(entrada, saida):
    pins, nomes = _source(entrada)
    travados = _blocos(saida)

    faltando = sorted(nomes - set(travados))
    assert faltando == [], f"{entrada} pede {faltando}, que não estão em {saida} — regere o lock"

    mismatched = {n: (v, travados[n][0]) for n, v in pins.items() if travados[n][0] != v}
    assert mismatched == {}, f"{entrada} x {saida} (fonte, lock): {mismatched} — regere o lock"

    # And the reverse: what the lock says came from the `.in` and has already left it
    # would still be installed.
    sobrando = sorted(n for n, fontes in _requirements_by(saida).items() if f"-r {entrada}" in fontes and n not in nomes)
    assert sobrando == [], f"{saida} ainda traz {sobrando}, que saíram de {entrada} — regere o lock"


@pytest.mark.parametrize("entrada", [e for e, _ in PARES])
def test_sources_do_not_embed_constraints(entrada):
    embedded = [
        linha for linha in (RAIZ / entrada).read_text(encoding="utf-8").splitlines()
        if re.match(r"^\s*(-c|--constraint)\b", linha)
    ]
    assert embedded == [], (
        f"{entrada}: {embedded} — o Dependabot compila cada .in sozinho e esbarra no lock "
        "velho da restrição; ela vai em PARES, em scripts/travar_python.py"
    )


@pytest.mark.parametrize("lock", LOCKS)
def test_every_lock_line_has_hash(lock):
    without_hash = sorted(n for n, (_, hashes) in _blocos(lock).items() if hashes == 0)
    assert without_hash == [], f"{lock}: pacotes sem hash {without_hash}"


@pytest.mark.parametrize("entrada,saida,restricoes", TRIOS, ids=[s for _, s, _ in TRIOS])
def test_locks_come_from_pip_compile_with_hash(entrada, saida, restricoes):
    """The header is the command that regenerates the lock, and it is through it
    (`--output-file`) that Dependabot finds the lock of each `.in`. Whoever reruns it
    must get the same file: with hashes, with the constraints and without the
    `--no-index` that pip-tools 7.6.1 writes by mistake (it would resolve with no index at all)."""
    comando = next(
        (l for l in (RAIZ / saida).read_text(encoding="utf-8").splitlines() if re.match(r"^#\s+pip-compile\s", l)),
        "",
    )
    assert "--generate-hashes" in comando, f"{saida}: cabeçalho sem o comando do pip-compile com hash"
    assert f"--output-file={saida}" in comando, f"{saida}: o cabeçalho não aponta para o próprio lock"
    assert comando.rstrip().endswith(entrada), f"{saida}: o cabeçalho não compila {entrada}"
    assert "--no-index" not in comando.split(), f"{saida}: o cabeçalho traz o --no-index espúrio"
    for constraint in restricoes:
        assert f"--constraint={constraint}" in comando, f"{saida}: compilado sem a restrição {constraint}"


def test_same_version_in_all_locks():
    visto: dict[str, dict[str, str]] = {}
    for lock in LOCKS:
        for nome, (versao, _) in _blocos(lock).items():
            visto.setdefault(nome, {})[lock] = versao
    mismatched = {n: v for n, v in visto.items() if len(set(v.values())) > 1}
    assert mismatched == {}, f"o mesmo pacote em versões diferentes: {mismatched}"


@pytest.mark.parametrize(
    "arquivo,trecho",
    [
        ("Dockerfile.api", "--require-hashes --only-binary=:all: --prefix=/install -r requirements.txt"),
        ("Dockerfile.executor", "--require-hashes --only-binary=:all: -r requirements-full.txt"),
        (".github/workflows/ci.yml",
         "pip install --require-hashes --only-binary=:all: -r requirements.txt -r requirements-dev.txt"),
        (".github/workflows/ci.yml", "pip install --require-hashes --only-binary=:all: -r requirements-dev.txt"),
        # The desktop installs the executor's lock, with hashes (and checks it on Windows).
        ("desktop/scripts/lib.mjs", "export const LOCK     = path.join(REPO, 'executor', 'requirements-full.txt')"),
        ("desktop/scripts/build-python-runtime.mjs", "'--require-hashes',"),
        ("desktop/scripts/check-lock.mjs", "'--require-hashes', '--only-binary=:all:'"),
    ],
)
def test_lock_installers_verify_the_hash(arquivo, trecho):
    assert trecho in (RAIZ / arquivo).read_text(encoding="utf-8"), f"{arquivo} deixou de instalar com hash"


def test_dev_lock_installs_on_windows():
    """Whoever commits from Windows installs requirements-dev.txt (pre-commit comes
    from it). The lock is produced on Linux, which does not see the colorama that `build`
    (from pip-tools) requires on Windows; without it in the `.in`, --require-hashes rejects
    the whole lock there — and nobody on Linux notices."""
    assert "colorama" in _blocos("requirements-dev.txt"), "o requirements-dev.in perdeu o colorama (Windows)"
