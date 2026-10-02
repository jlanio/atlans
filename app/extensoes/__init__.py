# app/extensoes/__init__.py
"""
Extensões: o que uma instalação pode ter além do núcleo.

Cada subpacote de `app/extensoes/` é uma extensão — os planos pagos, na
instalação que vende assinaturas, são uma. O núcleo NUNCA importa uma extensão
pelo nome: na primeira chamada a `registro()`, cada subpacote é importado e a
função `registrar(registro)` dele pendura no `Registro` o que a extensão traz.
Sem extensão nenhuma — a distribuição livre —, cada ponto de encaixe tem um
padrão no núcleo, e nada falta.

  rotas              APIRouters incluídos depois dos do núcleo
  tarefas_de_fundo   (nome, fábrica) somadas às do lifespan (`app/main.py`)
  plano_e_teto       o plano e o teto de tokens do assistente de uma pessoa
                     (padrão: nenhum plano, e o teto de `app/mcp/cotas.py`)
  assinaturas_ativas se a tela oferece contratar um plano (padrão: não)
  templates          pastas de modelos de e-mail, consultadas depois da do núcleo
  painel_do_modelo   campos a mais no painel de admin do modelo do assistente

Os modelos SQLAlchemy de uma extensão moram em `<extensão>/modelos`, e entram no
`Base.metadata` por `importar_modelos()` (chamada em `app/models/__init__.py`).
As tabelas deles, em `<extensão>/schema.sql` (DROP + CREATE, como o
`scripts/init_schema.sql` do núcleo): a base zero do alembic roda cada um,
depois do script do núcleo (`esquemas()`).

ATLANS_SEM_EXTENSOES=1 ignora as extensões presentes: é como os testes provam
que o núcleo anda sozinho. Uma extensão presente que não importa derruba o
arranque — sumir em silêncio com a cobrança seria pior.

Só a biblioteca padrão aqui: `app/models/__init__.py` importa este módulo.
"""
from __future__ import annotations

import importlib
import os
import pkgutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# (plano | None, teto) de uma pessoa. Recebe `user_id` e, por nome, `db` e `redis`.
PlanoETeto = Callable[..., Awaitable[tuple[str | None, int]]]
# Campos a mais no painel do modelo. Recebe `db` e, por nome, `atual`, `catalogo`,
# `simular` e `consulta` (os parâmetros da URL); devolve o que somar ao painel.
ContribuicaoAoPainel = Callable[..., Awaitable[dict[str, Any]]]
TarefaDeFundo = tuple[str, Callable[[], Awaitable[object]]]


def _nenhuma() -> bool:
    return False


@dataclass
class Registro:
    nomes: list[str] = field(default_factory=list)
    rotas: list[Any] = field(default_factory=list)
    tarefas_de_fundo: list[TarefaDeFundo] = field(default_factory=list)
    plano_e_teto: PlanoETeto | None = None
    # Uma função, e não um booleano: o valor depende da configuração da
    # extensão, lida quando a tela pergunta.
    assinaturas_ativas: Callable[[], bool] = field(default=_nenhuma)
    templates: list[Path] = field(default_factory=list)
    painel_do_modelo: list[ContribuicaoAoPainel] = field(default_factory=list)


_registro: Registro | None = None


def desligadas() -> bool:
    """ATLANS_SEM_EXTENSOES: o núcleo sozinho, mesmo com extensões no disco."""
    return os.getenv("ATLANS_SEM_EXTENSOES", "").strip().lower() in ("1", "true", "sim", "yes", "on")


def _nomes() -> list[str]:
    if desligadas():
        return []
    return sorted(
        m.name for m in pkgutil.iter_modules(__path__)
        if m.ispkg and not m.name.startswith("_")
    )


def registro() -> Registro:
    """O registro das extensões presentes, montado na primeira chamada."""
    global _registro
    if _registro is None:
        novo = Registro()
        for nome in _nomes():
            modulo = importlib.import_module(f"{__name__}.{nome}")
            registrar = getattr(modulo, "registrar", None)
            if registrar is None:
                raise RuntimeError(f"A extensão {nome!r} não tem registrar(registro).")
            registrar(novo)
            novo.nomes.append(nome)
        _registro = novo
    return _registro


def importar_modelos() -> None:
    """Importa `<extensão>/modelos` de cada extensão que o tiver."""
    for nome in _nomes():
        alvo = f"{__name__}.{nome}.modelos"
        try:
            importlib.import_module(alvo)
        except ModuleNotFoundError as exc:
            # Só a ausência do PRÓPRIO `modelos` é normal (extensão sem tabelas).
            if exc.name != alvo:
                raise


def esquemas() -> list[Path]:
    """O `schema.sql` de cada extensão presente que tem tabelas, em ordem de nome.

    Sem importar a extensão: a base zero do alembic roda isto, e o que ela
    precisa é o arquivo, não o código.
    """
    achados = []
    for nome in _nomes():
        for raiz in __path__:
            alvo = Path(raiz) / nome / "schema.sql"
            if alvo.is_file():
                achados.append(alvo)
                break
    return achados
