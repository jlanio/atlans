# tests/unit/test_npm_sem_scripts.py
"""
Nenhum pacote npm roda código na instalação — no CI, no build da imagem do web
ou na máquina de quem desenvolve.

É a porta dos worms do npm de 2025: a versão maliciosa de um pacote rodava
no `npm install` (preinstall/postinstall), roubava tokens (npm, GitHub,
nuvem) e se republicava. O `web/.npmrc` e o `desktop/.npmrc` ligam
`ignore-scripts=true`; estes testes seguram as pontas que desligariam a
proteção sem quebrar nada visível:

- o `.npmrc` deixar de valer `true` (linha removida, ou um `false` depois);
- o Dockerfile do web instalar sem o `.npmrc` no estágio (o build da imagem
  voltaria a rodar os scripts), ou reverter o valor por variável/flag;
- um workflow reverter o valor por variável ou flag;
- um script de ciclo de vida no package.json. Com `ignore-scripts` o npm
  também deixa de rodar os do próprio projeto — `postinstall`, `prepare`,
  e os ganchos `pre`/`post` do `npm run` — e o passo sumiria em silêncio. Foi
  o caso do `prebuild` que copia o Monaco, que virou chamada explícita no
  próprio `build`.
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

# Os scripts que o npm roda sozinho no `npm install`/`npm ci` do próprio
# projeto — e que o ignore-scripts cala.
CICLO_DE_VIDA = {
    "preinstall", "install", "postinstall", "prepublish",
    "preprepare", "prepare", "postprepare", "dependencies",
}
# Subcomandos do npm que instalam pacotes (com os apelidos que o npm aceita).
_NPM_INSTALA = re.compile(
    r"\bnpm\s+(?:-\S+\s+)*(?:ci|clean-install|ic|install-clean|isntall-clean"
    r"|i|in|ins|inst|insta|instal|install|isnt|isnta|isntal|isntall|add)\b"
)
# O que reverteria o .npmrc: a flag na linha de comando ou a variável.
_REVERTE = re.compile(r"--ignore-scripts[= ]false|--no-ignore-scripts|npm_config_ignore_scripts", re.I)


def _valor_efetivo(npmrc: Path, chave: str) -> str | None:
    """Como o npm lê: `chave = valor`, com ou sem espaços; vale a última."""
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
    """(INSTRUÇÃO, argumentos) de um Dockerfile: a barra no fim da linha junta
    a seguinte, comentário cai fora, instrução em qualquer caixa."""
    texto = re.sub(r"\\\n", " ", dockerfile.read_text(encoding="utf-8"))
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        instrucao, _, argumentos = linha.partition(" ")
        yield instrucao.upper(), argumentos


def test_a_imagem_do_web_instala_com_o_npmrc():
    # `COPY . .` também leva o .npmrc — desde que o .dockerignore não o tire.
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
    """Nem o Dockerfile do web nem um workflow podem desligar a proteção por
    fora do .npmrc (`--ignore-scripts=false`, `NPM_CONFIG_IGNORE_SCRIPTS`)."""
    revertidos = [
        f"{arquivo.relative_to(RAIZ)}: {linha.strip()}"
        for arquivo in [DOCKERFILE_WEB, *WORKFLOWS]
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if _REVERTE.search(linha)
    ]
    assert revertidos == [], revertidos
