#!/usr/bin/env python3
"""scripts/idade_dos_locks.py — a idade de cada versão travada nos locks Python.

A quarentena de 14 dias vale para o que o Dependabot e o scripts/travar_python.py
escolhem sozinhos. Duas coisas entram nos locks sem ela:

- no PR do Dependabot, as transitivas que o pip-compile resolve junto com o
  pacote atualizado: o cooldown só filtra o pacote-alvo;
- uma atualização de segurança, que por definição não espera.

Este script pergunta ao PyPI quando cada `nome==versão` dos locks foi publicado,
pelos arquivos cujo hash está no lock, e lista o que tem menos de 14 dias ou foi
retirado (yanked) depois de travado. É a parte do PR que merece a revisão mais
atenta (roteiro em CONTRIBUTING.md, "PRs do Dependabot"). No GitHub Actions, cada
achado vira um aviso no PR e a tabela vai para o resumo da execução.

Informativo: sai com 0 mesmo com achados, a menos que receba `--estrito`. Só
biblioteca padrão; roda em qualquer sistema.

    python scripts/idade_dos_locks.py
    python scripts/idade_dos_locks.py --estrito
"""
from __future__ import annotations

import argparse
import datetime as dt
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

# Os locks gerados por scripts/travar_python.py — o mesmo conjunto dos PARES de lá.
LOCKS = [
    "requirements.txt",
    "requirements-dev.txt",
    "executor/requirements-full.txt",
    "executor/requirements.txt",
]

# A espera do Dependabot (.github/dependabot.yml, `cooldown.default-days`) e do
# scripts/travar_python.py, que importa daqui.
QUARENTENA_DIAS = 14

PYPI = "https://pypi.org/pypi"

_PINO = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s\\;#]+)")
_HASH = re.compile(r"--hash=sha256:([0-9a-f]{64})")


def normalizar(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def travados(caminho: Path) -> dict[tuple[str, str], set[str]]:
    """`(nome, versão) -> hashes sha256` de um lock com hash."""
    blocos: dict[tuple[str, str], set[str]] = {}
    atual = None
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        m = _PINO.match(linha)
        if m:
            atual = (normalizar(m.group(1)), m.group(2))
            blocos.setdefault(atual, set())
        if atual:
            blocos[atual].update(_HASH.findall(linha))
    return blocos


class Consulta:
    """O que o PyPI diz de uma versão: quando os arquivos dela (os do lock)
    foram publicados, e se ela foi retirada."""

    def __init__(self, publicado: dt.datetime, retirada: str | None):
        self.publicado = publicado
        self.retirada = retirada  # o motivo do yank ("" se não deram), ou None


def consultar(nome: str, versao: str, hashes: set[str] | None = None, tentativas: int = 3) -> Consulta:
    """Pergunta ao PyPI pela versão. `publicado` é o upload MAIS RECENTE entre os
    arquivos dela que estão no lock: um wheel acrescentado depois a uma versão
    antiga também é arquivo novo. Sem `hashes`, conta todos os arquivos."""
    url = f"{PYPI}/{nome}/{versao}/json"
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=30) as resposta:
                dados = json.load(resposta)
            break
        except urllib.error.HTTPError as erro:
            if erro.code not in (429, 500, 502, 503, 504) or tentativa == tentativas - 1:
                raise
        except urllib.error.URLError:
            if tentativa == tentativas - 1:
                raise
        time.sleep(2 ** tentativa)

    arquivos = dados.get("urls") or []
    if hashes:
        arquivos = [a for a in arquivos if a.get("digests", {}).get("sha256") in hashes]
        if not arquivos:
            # O pip recusaria instalar: nenhum arquivo do PyPI bate com o lock.
            raise ValueError(f"{nome}=={versao}: nenhum arquivo do PyPI tem os hashes do lock")
    if not arquivos:
        raise ValueError(f"{nome}=={versao}: o PyPI não lista arquivos para esta versão")
    publicado = max(
        dt.datetime.fromisoformat(a["upload_time_iso_8601"].replace("Z", "+00:00")) for a in arquivos
    )
    retirados = [a for a in arquivos if a.get("yanked")]
    retirada = (retirados[0].get("yanked_reason") or "") if retirados else None
    return Consulta(publicado, retirada)


def consultar_varios(
    pedidos: dict[tuple[str, str], set[str] | None],
) -> dict[tuple[str, str], Consulta | Exception]:
    """`consultar` em paralelo; o erro de cada um volta no lugar da resposta."""

    def uma(chave: tuple[str, str]) -> Consulta | Exception:
        try:
            return consultar(chave[0], chave[1], pedidos[chave])
        except Exception as erro:  # noqa: BLE001 — cada erro é relatado com o pacote
            return erro

    with ThreadPoolExecutor(max_workers=16) as pool:
        return dict(zip(pedidos, pool.map(uma, pedidos)))


def _dias(delta: dt.timedelta) -> str:
    return f"{delta.total_seconds() / 86400:.1f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--estrito", action="store_true",
        help="sai com 1 se houver versão recente ou retirada (e com 2 se o PyPI não responder)",
    )
    args = parser.parse_args()

    agora = dt.datetime.now(dt.timezone.utc)
    corte = agora - dt.timedelta(days=QUARENTENA_DIAS)

    onde: dict[tuple[str, str], list[str]] = {}
    hashes: dict[tuple[str, str], set[str]] = {}
    for lock in LOCKS:
        for chave, hs in travados(RAIZ / lock).items():
            onde.setdefault(chave, []).append(lock)
            hashes.setdefault(chave, set()).update(hs)

    respostas = consultar_varios({c: hashes[c] or None for c in onde})
    recentes = sorted(
        ((c, r) for c, r in respostas.items() if isinstance(r, Consulta) and r.publicado > corte),
        key=lambda cr: cr[1].publicado,
        reverse=True,
    )
    retiradas = sorted((c, r) for c, r in respostas.items() if isinstance(r, Consulta) and r.retirada is not None)
    erros = sorted((c, r) for c, r in respostas.items() if isinstance(r, Exception))

    no_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    resumo = [f"### Versões recentes nos locks Python (menos de {QUARENTENA_DIAS} dias)", ""]

    print(f"{len(onde)} versões em {len(LOCKS)} locks; corte da quarentena: {corte:%Y-%m-%d %H:%M} UTC")
    if recentes:
        print(f"\nPublicadas há menos de {QUARENTENA_DIAS} dias — revise antes do merge:")
        resumo += ["| Pacote | Publicado (UTC) | Dias | Locks |", "|---|---|---|---|"]
        for (nome, versao), r in recentes:
            locks = ", ".join(onde[(nome, versao)])
            dias = _dias(agora - r.publicado)
            print(f"  {nome}=={versao}  {r.publicado:%Y-%m-%d %H:%M}  ({dias} dias)  {locks}")
            resumo.append(f"| `{nome}=={versao}` | {r.publicado:%Y-%m-%d %H:%M} | {dias} | {locks} |")
            if no_actions:
                print(
                    f"::warning title=Versão recente — {nome}::{nome}=={versao} foi publicada há {dias} dias "
                    f"(quarentena: {QUARENTENA_DIAS}). Em: {locks}"
                )
    else:
        print(f"\nNenhuma versão com menos de {QUARENTENA_DIAS} dias.")
        resumo.append(f"Nenhuma versão com menos de {QUARENTENA_DIAS} dias.")

    for (nome, versao), r in retiradas:
        motivo = r.retirada or "sem motivo informado"
        print(f"  RETIRADA do PyPI (yanked): {nome}=={versao} — {motivo}")
        resumo.append(f"\n**Retirada do PyPI (yanked):** `{nome}=={versao}` — {motivo}")
        if no_actions:
            print(f"::warning title=Versão retirada — {nome}::{nome}=={versao} foi retirada do PyPI: {motivo}")

    for (nome, versao), erro in erros:
        print(f"  não consegui consultar {nome}=={versao}: {erro}")
        resumo.append(f"\nNão consegui consultar `{nome}=={versao}`: {erro}")
        if no_actions:
            print(f"::warning title=Idade dos locks::não consegui consultar {nome}=={versao} no PyPI: {erro}")

    if no_actions and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as saida:
            saida.write("\n".join(resumo) + "\n")

    if args.estrito:
        if erros:
            return 2
        if recentes or retiradas:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
