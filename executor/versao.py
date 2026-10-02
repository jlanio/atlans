"""
Versão do executor — a que o painel de executores mostra.

Ordem de escolha, em `versao_do_executor()`:

1. a gravada na imagem Docker no build (`ARQUIVO_DA_IMAGEM`, FORA da árvore
   do código: um checkout nunca a tem, então o desktop e a CLI não a herdam).
   Vence o ambiente de propósito: as instalações antigas têm
   `EXECUTOR_VERSION=1.0.0` no `executor/.env`, semeado do `.env.example`, e
   por isso todo executor Docker aparecia como "v1.0.0";
2. `EXECUTOR_VERSION` do ambiente — o app desktop define com a versão dele;
3. "1.0.0".

No build, `python -m executor.versao <pasta> <destino>` grava a versão do
produto — a do app desktop, `desktop/package.json`; o release passa a da tag em
`EXECUTOR_BASE` — mais o commit: `2.15.0+3f02f44`. O commit vem do próprio
checkout (o Dockerfile copia `.git/HEAD`, `packed-refs` e `refs` para a pasta;
o .dockerignore deixa entrar só isso) ou de `EXECUTOR_COMMIT`, que vale mais.
Sem nenhum dos dois (build de um tarball), sai só a versão do produto.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Mapping

ARQUIVO_DA_IMAGEM = Path("/usr/local/share/atlans-executor/VERSAO")
# O servidor descarta versões maiores que isso (`_EXECUTOR_VERSION_MAX` em
# app/api/routers/executor_ws/protocolo.py) e o painel ficaria sem nenhuma.
TAMANHO_MAXIMO = 20
PADRAO = "1.0.0"
_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")   # SHA-1 ou SHA-256


def _aceitavel(versao: str) -> bool:
    return 0 < len(versao) <= TAMANHO_MAXIMO and versao.isprintable()


def versao_do_executor(
    ambiente: Mapping[str, str] | None = None, arquivo: Path | None = None
) -> str:
    """A versão que o executor declara no handshake e no enroll (ver a ordem acima).

    Tolerante: um arquivo ilegível, grande demais ou com lixo é ignorado —
    isto roda na importação de `executor.config`, e um erro aqui impediria o
    executor de subir.

    O `EXECUTOR_VERSION` passa pela mesma régua do arquivo: o enroll valida o
    tamanho (`executor_version`, até 20 caracteres) e recusaria com 422 um
    `<versão>+<commit>` longo de um build local. Grande demais, o commit
    encurta como no build (`compor`); sem conserto, fica o padrão.
    """
    ambiente = os.environ if ambiente is None else ambiente
    arquivo = ARQUIVO_DA_IMAGEM if arquivo is None else arquivo
    try:
        gravada = arquivo.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        gravada = ""
    if _aceitavel(gravada):
        return gravada
    do_ambiente = (ambiente.get("EXECUTOR_VERSION") or "").strip()
    if _aceitavel(do_ambiente):
        return do_ambiente
    if do_ambiente:
        base, _, commit = do_ambiente.partition("+")
        encurtada = compor(base, commit or None)
        if encurtada:
            return encurtada
    return PADRAO


def commit_do_git(pasta: Path) -> str | None:
    """SHA do HEAD a partir das cópias de `.git/HEAD`, `.git/packed-refs` e do
    conteúdo de `.git/refs` (`heads/`, `tags/`...) numa pasta só — o layout que
    o `COPY` do Dockerfile produz. None se não der para saber."""
    try:
        head = (pasta / "HEAD").read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None
    if _SHA.match(head):                               # HEAD destacado
        return head
    if not head.startswith("ref: refs/"):
        return None
    ref = head[len("ref: "):]
    if ".." in ref.split("/"):
        return None
    try:
        # A ref solta vence a empacotada: o `git pull` atualiza só ela.
        solta = (pasta / ref[len("refs/"):]).read_text(encoding="utf-8").strip()
        if _SHA.match(solta):
            return solta
    except (OSError, ValueError):
        pass
    try:
        for linha in (pasta / "packed-refs").read_text(encoding="utf-8").splitlines():
            partes = linha.split()
            if len(partes) == 2 and partes[1] == ref and _SHA.match(partes[0]):
                return partes[0]
    except (OSError, ValueError):
        pass
    return None


def compor(versao_do_produto: str, commit: str | None) -> str:
    """`<versão>+<commit curto>` dentro do limite do servidor.

    O hash encurta (7 → 4 caracteres) antes de sair; se nem a versão do
    produto couber, fica só o commit, que é o que identifica o código.
    """
    base = versao_do_produto.strip()
    curto = "".join(c for c in (commit or "").strip() if c.isalnum())[:7]
    if base:
        for tamanho in range(len(curto), 3, -1):
            candidata = f"{base}+{curto[:tamanho]}"
            if _aceitavel(candidata):
                return candidata
        if _aceitavel(base):
            return base
    return curto if _aceitavel(curto) else ""


def gravar(
    pasta: Path, destino: Path, *, commit: str | None = None, base: str | None = None,
) -> str | None:
    """Build da imagem: grava a versão em `destino` e a devolve.

    Nunca derruba o build: sem versão aceitável, avisa e não grava — o
    executor cai no EXECUTOR_VERSION, como antes.
    """
    if not base:
        try:
            base = json.loads((pasta / "package.json").read_text(encoding="utf-8"))["version"]
        except (OSError, ValueError, KeyError, TypeError):
            base = ""
    # A tag do release é `executor/v1.2.3`; o painel já põe o "v" na frente.
    base = re.sub(r"^[vV](?=\d)", "", str(base).strip())
    versao = compor(base, commit or commit_do_git(pasta))
    if not versao:
        print(f"aviso: sem versão aceitável para o executor (base {base!r}); nada gravado.", file=sys.stderr)
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(versao, encoding="utf-8")
    return versao


if __name__ == "__main__":
    print(gravar(
        Path(sys.argv[1]), Path(sys.argv[2]),
        commit=os.environ.get("EXECUTOR_COMMIT") or None,
        base=os.environ.get("EXECUTOR_BASE") or None,
    ))
