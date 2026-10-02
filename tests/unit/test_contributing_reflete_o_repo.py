# tests/unit/test_contributing_reflete_o_repo.py
"""
A arvore de arquivos do CONTRIBUTING descreve o repositorio de verdade.

A renomeacao `worker -> agent -> executor` parou no meio: o codigo virou
`executor_*`, e o CONTRIBUTING continuou documentando arquivos `agent_*` que nao
existem mais. Alem disso, a arvore chegou a citar `flow/executor.py` — um arquivo
que nao existe (o motor virou o pacote `flow/executor/`).

Isso nao e cosmetico. O CONTRIBUTING e o primeiro lugar onde alguem novo procura
"onde fica o dispatch de jobs"; um mapa que aponta para arquivos inexistentes
custa a essa pessoa a confianca no resto do documento.

O teste reconstroi o CAMINHO de cada `.py` a partir da indentacao do desenho
ASCII e exige que ele exista naquele caminho. A versao anterior so comparava o
basename com um glob `**/nome.py`, entao `flow/executor.py` (inexistente) passava
porque `app/models/executor.py` tem o mesmo basename — um falso positivo que
mascarava justamente o tipo de erro que o teste deveria pegar. Nao valida o
inverso (arquivo sem mencao): a arvore e um resumo curado, nao um `ls`.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "CONTRIBUTING.md"

# Marcadores de galho do desenho de arvore; cada nivel de indentacao antes deles
# ocupa 4 colunas ("│   " ou "    ").
_GALHO = re.compile(r"[├└]── ")


def _arquivos_com_caminho() -> list[tuple[int, str]]:
    """(linha, caminho relativo a raiz) de cada `.py` citado nas arvores.

    Reconstroi o diretorio empilhando os nos-diretorio (que terminam em `/`) por
    profundidade de indentacao, para que o caminho completo — nao so o basename —
    seja verificado. O CONTRIBUTING tem mais de uma arvore: a principal (raiz
    `atlans/`, = raiz do repo) e a de testes (raiz `tests/`). Uma linha `nome/`
    sem galho e sem indentacao e a raiz de uma arvore e define o prefixo dos
    caminhos seguintes: uma pasta que existe na raiz do repo (`tests/`) vira o
    prefixo; outro nome (`atlans/`) e o proprio repo. Nao pelo nome da pasta do
    clone: o CI clona na pasta com o nome do repositorio, e um repositorio com
    outro nome (um fork, a copia publica) quebraria o teste.
    """
    achados: list[tuple[int, str]] = []
    pilha: dict[int, str] = {}  # profundidade -> nome do diretorio naquele nivel
    base = ""                   # prefixo da (sub)arvore atual
    for i, linha in enumerate(DOC.read_text(encoding="utf-8").splitlines(), 1):
        m = _GALHO.search(linha)
        if not m:
            # Raiz de uma (sub)arvore: `nome/` puro, sem galho e sem indentacao.
            token = re.split(r"\s{2,}|#", linha, maxsplit=1)[0]
            if re.fullmatch(r"[A-Za-z0-9_]+/", token):
                nome_raiz = token.rstrip("/")
                base = nome_raiz if (RAIZ / nome_raiz).is_dir() else ""
                pilha = {}
            continue
        profundidade = m.start() // 4
        # nome do item: primeiro token apos o galho, antes de qualquer comentario
        # (o desenho usa espacos duplos ou `#` para os comentarios de cada linha).
        nome = re.split(r"\s{2,}|#", linha[m.end():], maxsplit=1)[0].strip()
        if nome.endswith("/"):
            pilha[profundidade] = nome.rstrip("/")
            for d in [d for d in pilha if d > profundidade]:
                del pilha[d]
        elif nome.endswith(".py"):
            partes = ([base] if base else []) + [pilha[d] for d in sorted(pilha) if d < profundidade] + [nome]
            achados.append((i, "/".join(partes)))
    return achados


def test_todo_arquivo_py_citado_na_arvore_existe():
    arquivos = _arquivos_com_caminho()
    assert arquivos, "a arvore de diretorios do CONTRIBUTING sumiu — ajuste este teste"

    faltando = [
        f"CONTRIBUTING.md:{linha} cita {caminho}, que nao existe"
        for linha, caminho in arquivos
        if not (RAIZ / caminho).exists()
    ]

    assert not faltando, (
        "o mapa do CONTRIBUTING aponta para arquivos inexistentes:\n  "
        + "\n  ".join(faltando)
    )


def test_o_vocabulario_agent_nao_voltou_ao_documento():
    """`agent` foi o nome do meio numa renomeacao ja concluida no codigo.

    Mantê-lo no documento faz o leitor procurar por um vocabulario que o
    repositorio abandonou.
    """
    problemas = [
        f"CONTRIBUTING.md:{i} — {linha.strip()}"
        for i, linha in enumerate(DOC.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\bagents?_[a-z]+\.py\b", linha)
    ]
    assert not problemas, (
        "nome de arquivo com o prefixo `agent_` de volta ao CONTRIBUTING; "
        "o codigo usa `executor_`:\n  " + "\n  ".join(problemas)
    )
