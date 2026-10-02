# app/mcp/guia/__init__.py
"""
O guia de autoria, fatiado por tópico.

Uma fonte só para dois consumidores: a tool `get_authoring_guide(topic=…)` e o
resource `atlans://guide/authoring/{topic}`. Guardar o texto em arquivos `.md`
ao lado deste módulo (e não em constantes Python) é o que permite revisar o
conteúdo como texto, com diff legível — e o que garante que tool e resource
nunca divirjam, porque leem o mesmo arquivo.
"""
from __future__ import annotations

from pathlib import Path

# A ordem é a de leitura recomendada: o que é um fluxo, como ligar os nós, como
# referenciar credenciais, como escrever expressões, como receber entradas, de
# onde vêm as fontes externas (o catálogo), SQL, armadilhas conhecidas e, por
# fim, receitas prontas.
TOPICOS: tuple[str, ...] = (
    "overview",
    "edges",
    "credentials",
    "expressions",
    "inputs",
    "sources",
    "sql",
    "pitfalls",
    "recipes",
)


def ler_topico(topic: str) -> str:
    """O markdown de um tópico.

    Tópico fora da lista levanta `ValueError` — nunca um caminho de arquivo: o
    nome vem do cliente, e montar `Path` com texto arbitrário seria travessia de
    diretório.
    """
    if topic not in TOPICOS:
        raise ValueError(
            f"Tópico desconhecido: {topic!r}. Disponíveis: {', '.join(TOPICOS)}."
        )
    return (Path(__file__).parent / f"{topic}.md").read_text(encoding="utf-8")
