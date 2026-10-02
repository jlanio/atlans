#!/usr/bin/env python3
"""scripts/travar_python.py — os locks Python, com hash e quarentena.

Cada par `.in` -> `.txt` de PARES é compilado pelo pip-compile (pip-tools) com
o hash de cada arquivo. O `.in` é a fonte, o que se edita; o `.txt` é o que a
imagem, o CI, o app desktop e a instalação pela CLI instalam, com
`--require-hashes`. É também o formato que o Dependabot sabe regenerar nos PRs
dele.

Quarentena: o que o resolvedor escolhe sozinho (as transitivas) só entra se
foi publicado há QUARENTENA_DIAS dias ou mais — a mesma espera do Dependabot.
Versão maliciosa costuma ser descoberta e retirada em horas ou poucos dias, e
um lock regerado à mão não pode ser a porta que o Dependabot fecha. O
pip-compile não filtra por data; o uv filtra (`--exclude-newer`). Então:

  1. o uv resolve com a data de corte, semeado pelo lock atual (nada muda sem
     motivo). Sem corte fica só o que alguém decidiu: o pinado com `==` no
     `.in` e o travado num lock de restrição. Uma versão já travada e mais nova
     que o corte (veio de um PR do Dependabot ou de segurança, revisado) segue
     valendo, mas só ela: nada mais novo que ela entra, e ela não é rebaixada;
  2. o resultado semeia o `.txt`;
  3. o pip-compile, que respeita os pinos que encontra no arquivo, gera o lock
     final: mesmas versões, agora com hash, anotações e o cabeçalho;
  4. toda versão que mudou, fora as pinadas no `.in`, tem a data conferida no
     PyPI. Uma que fure o corte desfaz tudo.

    python scripts/travar_python.py             # regenera, mantendo o que já está travado
    python scripts/travar_python.py --renovar   # re-resolve as transitivas (ainda com a quarentena)

Se um par falhar, ou o script for interrompido (Ctrl-C, SIGTERM, SIGHUP), todos
os locks voltam ao que eram.

Roda em Linux x86_64 com Python 3.12 — a plataforma da imagem e do CI, para a
qual o lock é resolvido. Precisa do requirements-dev.txt instalado (pip-tools e
uv) e de acesso ao PyPI. Fora do Linux, pelo Docker (num Mac com Apple Silicon
também: o `--platform` roda o x86_64 emulado):

    docker run --rm --platform linux/amd64 -v "$PWD":/w -w /w python:3.12-slim-bookworm sh -c \\
      'pip install -q --require-hashes -r requirements-dev.txt && python scripts/travar_python.py'
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import platform
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from idade_dos_locks import QUARENTENA_DIAS, consultar_varios

RAIZ = Path(__file__).resolve().parents[1]

# (fonte, lock, restrições). Em ordem: um lock usado como restrição por outro
# compila antes dele. A restrição dá ao pacote que os dois têm em comum a mesma
# versão: o CI instala o lock da API e o de dev juntos, e o executor mínimo é um
# pedaço do completo.
#
# Ela vai na linha de comando (e fica no cabeçalho do lock), não num `-c` dentro
# do `.in`. O Dependabot compila cada `.in` sozinho, na ordem em que os acha, sem
# atualizar antes o lock referenciado: com o `-c` no `.in`, o pip-compile dele
# esbarra na versão velha e o PR nem sai (ResolutionImpossible). Sem o `-c`, ele
# sobe o pacote em cada lock com o mesmo `-P nome==versão`, e o
# tests/unit/test_locks_python.py confere que as versões continuam iguais.
PARES = [
    ("requirements.in", "requirements.txt", []),
    ("requirements-dev.in", "requirements-dev.txt", ["requirements.txt"]),
    ("executor/requirements-full.in", "executor/requirements-full.txt", []),
    ("executor/requirements.in", "executor/requirements.txt", ["executor/requirements-full.txt"]),
]

# Estas opções vão para o cabeçalho do `.txt`: é o comando que regera o lock. O
# Dependabot preserva o cabeçalho, mas não o relê: deduz as opções do conteúdo
# (as linhas `--hash=` viram `--generate-hashes`; pip/setuptools travados,
# `--allow-unsafe`; `--strip-extras` escrito no cabeçalho). O que importa para
# ele é o lock continuar com hash em toda linha.
# `--no-emit-index-url`/`--no-emit-trusted-host`: um índice configurado na
# máquina (proxy, espelho) não pode vazar para o arquivo versionado.
OPCOES_PIP_COMPILE = [
    "--generate-hashes",
    "--allow-unsafe",
    "--strip-extras",
    "--no-emit-index-url",
    "--no-emit-trusted-host",
]

_PINO = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([^\s;\\#]+)")
_HASH = re.compile(r"--hash=sha256:([0-9a-f]{64})")
# O pip-tools 7.6.1 com o click 8.5 (o que o lock da API pina) escreve
# `--no-index` no comando do cabeçalho sem que ninguém o tenha passado: para
# flag sem forma negativa, ele compara o valor com o default, e o default do
# click 8.5 virou uma sentinela, então `False` também "difere" e é escrito. A
# resolução usou o PyPI normalmente (o flag real é False); só o cabeçalho
# mente. E quem reexecutasse aquele comando resolveria SEM índice nenhum. O
# pip-tools 7.5 nem roda com o click 8.5.
_NO_INDEX_ESPURIO = re.compile(r"^(#\s+pip-compile\b.*?) --no-index\b", re.M)


class Falha(Exception):
    """Um par não pôde ser travado; a mensagem diz por quê."""


def normalizar(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def pinos(caminho: Path) -> dict[str, str]:
    """`nome -> versão` de cada linha `nome==versão` (continuações de hash e
    comentários ficam de fora)."""
    if not caminho.exists():
        return {}
    achados = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        m = _PINO.match(linha)
        if m:
            achados[normalizar(m.group(1))] = m.group(2)
    return achados


def hashes_por_pino(caminho: Path) -> dict[str, set[str]]:
    """`nome -> hashes sha256` de um lock com hash."""
    blocos: dict[str, set[str]] = {}
    atual = None
    if not caminho.exists():
        return blocos
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        m = _PINO.match(linha)
        if m:
            atual = normalizar(m.group(1))
            blocos[atual] = set()
        if atual:
            blocos[atual].update(_HASH.findall(linha))
    return blocos


def conferir_plataforma() -> None:
    if (sys.platform, platform.machine(), sys.version_info[:2]) != ("linux", "x86_64", (3, 12)):
        sys.exit(
            f"travar_python: o lock é da plataforma da imagem e do CI (Linux x86_64, Python 3.12);\n"
            f"  aqui é {sys.platform} {platform.machine()} Python {platform.python_version()}.\n"
            f"  Rode pelo Docker (ver a docstring de scripts/travar_python.py)."
        )
    # Como módulos DESTE interpretador, e não pelo PATH: um pip-compile de outro
    # ambiente (outra versão, outro Python) geraria outro lock.
    for modulo, pacote in (("uv", "uv"), ("piptools", "pip-tools")):
        if importlib.util.find_spec(modulo) is None:
            sys.exit(
                f"travar_python: '{pacote}' não está instalado neste Python — "
                f"pip install --require-hashes -r requirements-dev.txt"
            )


def _instante(momento: dt.datetime) -> str:
    return momento.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def isencoes(
    atual: dict[str, str], hashes: dict[str, set[str]], fixos: set[str], corte: dt.datetime,
) -> dict[str, str]:
    """`nome -> instante` para o `--exclude-newer-package` do uv.

    - Pinado com `==` no `.in` ou travado num lock de restrição: sem corte. A
      versão é aquela, e alguém a escolheu.
    - Travado no lock atual numa versão mais nova que o corte: liberado até o
      upload DAQUELA versão, nunca além. Isentar o nome inteiro deixaria entrar
      a versão de ontem sempre que outra mudança obrigasse o pacote a subir (um
      boto3 novo puxando o botocore). E sem isenção nenhuma o uv não veria a
      versão travada e a rebaixaria em silêncio — inclusive uma correção de
      segurança.
    """
    amanha = _instante(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1))
    livres = {nome: amanha for nome in fixos}
    pendentes = {(n, v): hashes.get(n) or None for n, v in atual.items() if n not in fixos}
    for (nome, versao), resposta in consultar_varios(pendentes).items():
        if isinstance(resposta, Exception):
            # Sem a data não dá para provar que ela é recente: fica com o corte
            # comum. Se ela for mesmo mais nova, o uv não a verá; a conferência
            # do fim pega qualquer troca que isso cause.
            print(f"  aviso: sem a data de {nome}=={versao} no PyPI ({resposta}); vale o corte comum")
            continue
        if resposta.publicado > corte:
            livres[nome] = _instante(resposta.publicado + dt.timedelta(seconds=1))
    return livres


def resolver_em_quarentena(
    entrada_rel: str, restricoes_rel: list[str], atual: dict[str, str], livres: dict[str, str],
    renovar: bool, corte: dt.datetime,
) -> dict[str, str]:
    """Passo 1: a resolução do uv com a data de corte."""
    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "quarentena.txt"
        if not renovar and atual:
            # O uv lê o arquivo de saída que já existe como preferência.
            saida.write_text("".join(f"{n}=={v}\n" for n, v in sorted(atual.items())))
        cmd = [
            sys.executable, "-m", "uv", "pip", "compile", entrada_rel,
            "--output-file", str(saida),
            "--python", sys.executable,
            "--exclude-newer", _instante(corte),
            "--no-header", "--no-annotate", "--quiet",
        ]
        for restricao in restricoes_rel:
            cmd += ["--constraint", restricao]
        for nome, instante in sorted(livres.items()):
            cmd += ["--exclude-newer-package", f"{nome}={instante}"]
        feito = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
        if feito.returncode != 0:
            raise Falha(f"o uv não resolveu {entrada_rel} com a quarentena:\n{feito.stderr}")
        return pinos(saida)


def _rebaixou(antes: str | None, depois: str) -> bool:
    if not antes:
        return False
    try:
        from packaging.version import Version  # vem com o pip-tools
        return Version(depois) < Version(antes)
    except Exception:  # noqa: BLE001 — versão fora do padrão: só não marca
        return False


def travar(entrada_rel: str, saida_rel: str, restricoes_rel: list[str], renovar: bool, corte: dt.datetime) -> None:
    entrada, saida = RAIZ / entrada_rel, RAIZ / saida_rel
    atual = pinos(saida)
    no_in = pinos(entrada)
    # O que vem de um lock de restrição já passou pela conferência quando ele
    # foi gerado.
    das_restricoes: dict[str, str] = {}
    for restricao in restricoes_rel:
        das_restricoes.update(pinos(RAIZ / restricao))
    fixos = set(no_in) | set(das_restricoes)

    livres = isencoes(atual, hashes_por_pino(saida), fixos, corte)
    semente = resolver_em_quarentena(entrada_rel, restricoes_rel, atual, livres, renovar, corte)

    # Passo 2: a semente no lugar do lock. Passo 3: o pip-compile a respeita.
    # (Se algo falhar daqui em diante, o main devolve o lock original.)
    saida.write_text("".join(f"{n}=={v}\n" for n, v in sorted(semente.items())), encoding="utf-8")
    cmd = [sys.executable, "-m", "piptools", "compile", *OPCOES_PIP_COMPILE, "--quiet"]
    for restricao in restricoes_rel:
        cmd.append(f"--constraint={restricao}")
    cmd += [f"--output-file={saida_rel}", entrada_rel]
    feito = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
    if feito.returncode != 0:
        raise Falha(f"o pip-compile falhou em {entrada_rel}:\n{feito.stderr}")
    texto = saida.read_text(encoding="utf-8")
    saida.write_text(_NO_INDEX_ESPURIO.sub(r"\1", texto, count=1), encoding="utf-8")

    final = pinos(saida)
    mudou = {n: (atual.get(n), v) for n, v in final.items() if atual.get(n) != v}

    # Passo 4: o que mudou sem ter sido pinado no `.in` tem de ter passado pelo
    # corte — inclusive o que o pip-compile escolheu diferente do uv.
    hashes = hashes_por_pino(saida)
    conferir = {
        (n, v): hashes.get(n) or None
        for n, (_, v) in mudou.items()
        if n not in no_in and das_restricoes.get(n) != v
    }
    furos = []
    for (nome, versao), resposta in sorted(consultar_varios(conferir).items()):
        if isinstance(resposta, Exception):
            furos.append(f"{nome}=={versao}: não consegui a data no PyPI ({resposta})")
        elif resposta.publicado > corte:
            furos.append(f"{nome}=={versao}: publicado em {_instante(resposta.publicado)}, depois do corte")
        elif resposta.retirada is not None:
            furos.append(f"{nome}=={versao}: retirado do PyPI (yanked): {resposta.retirada or 'sem motivo'}")
    if furos:
        raise Falha(
            f"{saida_rel}: versões fora da quarentena de {QUARENTENA_DIAS} dias:\n"
            + "\n".join(f"    {f}" for f in furos)
            + "\n  Se uma delas é mesmo necessária (correção de segurança), pine-a com `==` no "
            f"{entrada_rel} — é uma decisão, e fica registrada."
        )

    saiu = sorted(set(atual) - set(final))
    fora_da_semente = sorted(n for n, v in final.items() if semente.get(n) != v)
    print(f"{saida_rel}: {len(final)} pacotes travados com hash")
    for nome, (antes, depois) in sorted(mudou.items()):
        marca = "  (REBAIXOU — confira por quê)" if _rebaixou(antes, depois) else ""
        print(f"    {nome}: {antes or '(novo)'} -> {depois}{marca}")
    for nome in saiu:
        print(f"    {nome}: {atual[nome]} -> (saiu)")
    if fora_da_semente:
        # O pip-compile escolheu diferente do uv. A data já foi conferida acima;
        # fica o registro de que a resolução dos dois divergiu.
        print(f"  nota: o pip-compile divergiu da resolução do uv em: {', '.join(fora_da_semente)}")


def _interromper(sinal: int, _quadro) -> None:
    # SIGTERM e SIGHUP matam o processo sem passar pelo `finally`: o lock ficaria
    # com a semente sem hash, e o pip-compile órfão ainda o reescreveria depois.
    # Como exceção, o `subprocess.run` mata o filho e o main restaura os locks.
    raise KeyboardInterrupt(signal.Signals(sinal).name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--renovar", action="store_true",
        help="re-resolve as transitivas em vez de manter as travadas (ainda com a quarentena)",
    )
    args = parser.parse_args()
    conferir_plataforma()
    for sinal in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sinal, _interromper)

    # Instante exato, não data: com só a data, o uv aceita o dia de corte
    # inteiro, e algo publicado nele entraria com menos de 14 dias.
    corte = dt.datetime.now(dt.timezone.utc).replace(microsecond=0) - dt.timedelta(days=QUARENTENA_DIAS)
    print(f"quarentena: só entra o que foi publicado até {_instante(corte)} ({QUARENTENA_DIAS} dias)")

    originais = {
        saida_rel: (RAIZ / saida_rel).read_text(encoding="utf-8") if (RAIZ / saida_rel).exists() else None
        for _, saida_rel, _ in PARES
    }
    try:
        for entrada_rel, saida_rel, restricoes_rel in PARES:
            travar(entrada_rel, saida_rel, restricoes_rel, args.renovar, corte)
    except BaseException as erro:
        # Um par pela metade, ou só os primeiros regerados, deixaria locks que
        # não batem entre si: volta tudo — sem deixar um segundo Ctrl-C cortar
        # a volta no meio.
        for sinal in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sinal, signal.SIG_IGN)
        for saida_rel, texto in originais.items():
            if texto is None:
                (RAIZ / saida_rel).unlink(missing_ok=True)
            else:
                (RAIZ / saida_rel).write_text(texto, encoding="utf-8")
        if isinstance(erro, Falha):
            sys.exit(f"travar_python: {erro}\n  Os locks voltaram ao que eram.")
        if isinstance(erro, KeyboardInterrupt):
            sys.exit(f"travar_python: interrompido ({str(erro) or 'Ctrl-C'}); os locks voltaram ao que eram.")
        raise


if __name__ == "__main__":
    main()
