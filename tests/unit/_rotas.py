# tests/unit/_rotas.py
"""
As rotas efetivas de um app FastAPI, para os testes que conferem o que existe.

O nome começa com `_` de propósito: o pytest não coleta este arquivo.

Até o FastAPI 0.140, o `include_router` copiava as rotas do roteador incluído
para o `app.routes`, já com o prefixo: a lista era plana, e cada item tinha
`path` e `endpoint`. Desde o 0.141 o `app.routes` guarda um nó por roteador
incluído (`_IncludedRouter`), sem `path` nem `endpoint`. Quem varre o
`app.routes` direto passa a não ver rota nenhuma dos roteadores: um teste que
procura uma rota falha, e um que procura rota *proibida* passa sem conferir
nada. O `iter_route_contexts` (novo no 0.141) devolve cada rota com o caminho
efetivo, e é o que o próprio FastAPI usa para montar o OpenAPI.
"""
from __future__ import annotations


def rotas_efetivas(app) -> list:
    """Cada rota do app com `path` e `endpoint`, também as dos roteadores incluídos."""
    try:
        from fastapi.routing import iter_route_contexts
    except ImportError:  # FastAPI < 0.141: o app.routes já é a lista plana
        rotas = list(app.routes)
    else:
        # Rota WebSocket de roteador incluído: o contexto devolve path "", e o
        # caminho efetivo fica na rota que o FastAPI monta para casar a conexão.
        rotas = [
            getattr(contexto, "starlette_route", None) or contexto
            for contexto in iter_route_contexts(app.routes)
        ]
    # Sem isto, uma próxima mudança de formato voltaria a esvaziar os caminhos
    # em silêncio, e um `assert "/x" not in caminhos` passaria sem conferir nada.
    sem_caminho = [rota for rota in rotas if not getattr(rota, "path", None)]
    assert not sem_caminho, f"rota sem caminho no app (o FastAPI mudou o app.routes?): {sem_caminho[:3]}"
    return rotas
