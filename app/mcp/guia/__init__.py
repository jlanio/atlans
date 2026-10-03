# app/mcp/guia/__init__.py
"""
The authoring guide, sliced by topic.

A single source for two consumers: the `get_authoring_guide(topic=…)` tool and
the `atlans://guide/authoring/{topic}` resource. Keeping the text in `.md` files
next to this module (and not in Python constants) is what lets the content be
reviewed as text, with a readable diff — and what guarantees that tool and
resource never diverge, because they read the same file.
"""
from __future__ import annotations

from pathlib import Path

# The order is the recommended reading order: what a workflow is, how to wire
# nodes, how to reference credentials, how to write expressions, how to receive
# inputs, where external sources come from (the catalog), SQL, known pitfalls
# and, finally, ready-made recipes.
TOPICS: tuple[str, ...] = (
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
    """The markdown of a topic.

    A topic outside the list raises `ValueError` — never a file path: the name
    comes from the client, and building a `Path` from arbitrary text would be
    directory traversal.
    """
    if topic not in TOPICS:
        raise ValueError(
            f"Tópico desconhecido: {topic!r}. Disponíveis: {', '.join(TOPICS)}."
        )
    return (Path(__file__).parent / f"{topic}.md").read_text(encoding="utf-8")
