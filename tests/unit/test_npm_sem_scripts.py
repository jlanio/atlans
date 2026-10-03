# tests/unit/test_npm_sem_scripts.py
"""
No npm package runs code on install — in CI, in the web image build or on a
developer's machine.

It is the door the 2025 npm worms came through: a package's malicious version
ran on `npm install` (preinstall/postinstall), stole tokens (npm, GitHub,
cloud) and republished itself. `web/.npmrc` and `desktop/.npmrc` turn on
`ignore-scripts=true`; these tests hold down the loose ends that would turn
the protection off without breaking anything visible:

- the `.npmrc` no longer being `true` (line removed, or a `false` after it);
- the web Dockerfile installing without the `.npmrc` in the stage (the image
  build would go back to running the scripts), or reverting the value via
  variable/flag;
- a workflow reverting the value via variable or flag;
- a lifecycle script in package.json. With `ignore-scripts` npm also stops
  running the project's own ones — `postinstall`, `prepare`, and the
  `pre`/`post` hooks of `npm run` — and the step would silently vanish. That
  was the case of the `prebuild` that copies Monaco, which became an explicit
  call in `build` itself.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PROJETOS = ["web", "desktop"]
DOCKERFILE_WEB = RAIZ / "web" / "Dockerfile.ui"
WORKFLOWS = sorted((RAIZ / ".github" / "workflows").glob("*.y*ml"))

# The scripts npm runs on its own on the project's own `npm install`/`npm ci`
# — and that ignore-scripts silences.
CICLO_DE_VIDA = {
    "preinstall", "install", "postinstall", "prepublish",
    "preprepare", "prepare", "postprepare", "dependencies",
}
# npm subcommands that install packages (with the aliases npm accepts).
_NPM_INSTALA = re.compile(
    r"\bnpm\s+(?:-\S+\s+)*(?:ci|clean-install|ic|install-clean|isntall-clean"
    r"|i|in|ins|inst|insta|instal|install|isnt|isnta|isntal|isntall|add)\b"
)
# What would revert the .npmrc: the command-line flag or the variable.
_REVERTE = re.compile(r"--ignore-scripts[= ]false|--no-ignore-scripts|npm_config_ignore_scripts", re.I)


def _valor_efetivo(npmrc: Path, chave: str) -> str | None:
    """As npm reads it: `chave = valor`, with or without spaces; the last one wins."""
    valor = None
    for linha in npmrc.read_text(encoding="utf-8").splitlines():
        m = re.match(rf"^\s*{re.escape(chave)}\s*=\s*(\S*)\s*$", linha)
        if m:
            valor = m.group(1).lower()
    return valor


@pytest.mark.parametrize("projeto", PROJETOS)
def test_npmrc_desliga_os_scripts_de_instalacao(projeto):
    valor = _valor_efetivo(RAIZ / projeto / ".npmrc", "ignore-scripts")
    assert valor == "true", f"{projeto}/.npmrc: ignore-scripts vale {valor!r}, não 'true'"


@pytest.mark.parametrize("projeto", PROJETOS)
def test_sem_scripts_de_ciclo_de_vida_no_package_json(projeto):
    scripts = json.loads((RAIZ / projeto / "package.json").read_text(encoding="utf-8"))["scripts"]
    nomes = set(scripts)
    calados = sorted(
        nome for nome in nomes
        if nome in CICLO_DE_VIDA
        or (nome.startswith("pre") and nome[3:] in nomes)
        or (nome.startswith("post") and nome[4:] in nomes)
    )
    assert calados == [], f"{projeto}: scripts que o ignore-scripts nunca vai rodar: {calados}"


def test_o_build_do_web_copia_o_monaco_explicitamente():
    scripts = json.loads((RAIZ / "web" / "package.json").read_text(encoding="utf-8"))["scripts"]
    for nome in ("build", "dev"):
        assert "scripts/copiar-monaco.mjs" in scripts[nome], f"`npm run {nome}` deixou de copiar o Monaco"


def _instrucoes(dockerfile: Path):
    """(INSTRUCTION, arguments) of a Dockerfile: a backslash at the end of the line
    joins the next one, comments are dropped, instructions in any case."""
    texto = re.sub(r"\\\n", " ", dockerfile.read_text(encoding="utf-8"))
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        instrucao, _, argumentos = linha.partition(" ")
        yield instrucao.upper(), argumentos


def test_a_imagem_do_web_instala_com_o_npmrc():
    # `COPY . .` also takes the .npmrc — as long as .dockerignore doesn't exclude it.
    ignorados = (RAIZ / "web" / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert not any(re.fullmatch(r"\s*/?\.npmrc\s*", linha) for linha in ignorados), \
        "web/.dockerignore tira o .npmrc do contexto do build"

    copiado = False
    for instrucao, argumentos in _instrucoes(DOCKERFILE_WEB):
        if instrucao == "FROM":
            copiado = False
        elif instrucao in ("COPY", "ADD"):
            fontes = [t for t in argumentos.split()[:-1] if not t.startswith("--")]
            copiado = copiado or any(f in (".npmrc", ".", "./") for f in fontes)
        elif instrucao == "RUN":
            # Forma exec (`RUN ["npm", "ci"]`) vira texto comum para a busca.
            comando = " ".join(re.findall(r'"([^"]*)"', argumentos)) if argumentos.lstrip().startswith("[") else argumentos
            if _NPM_INSTALA.search(comando):
                assert copiado, f"web/Dockerfile.ui instala sem o .npmrc no estágio: RUN {argumentos.strip()}"


def test_nada_reverte_o_ignore_scripts():
    """Neither the web Dockerfile nor a workflow may turn off the protection
    outside the .npmrc (`--ignore-scripts=false`, `NPM_CONFIG_IGNORE_SCRIPTS`)."""
    revertidos = [
        f"{arquivo.relative_to(RAIZ)}: {linha.strip()}"
        for arquivo in [DOCKERFILE_WEB, *WORKFLOWS]
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if _REVERTE.search(linha)
    ]
    assert revertidos == [], revertidos
