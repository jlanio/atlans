"""
Taxonomia de erro.

Classifica uma falha numa CATEGORIA estável para o servidor decidir o que fazer
com ela (mostrar ao usuário, reentregar a outro executor, mandar para a
dead-letter) — em vez de tratar toda falha como uma string opaca.

Vive em `flow/` porque é usada nos dois níveis: o job inteiro (executor/) e cada
nó individual (flow/executor/core.py, que publica a categoria no evento para o
painel de execução dizer "não adianta repetir, corrija a entrada").

Categorias e semântica de retry:

  user       — input/configuração inválidos (ex.: coluna ausente, CRS faltando);
               o usuário precisa corrigir.            → NÃO retryable
  validation — reprovado na validação de segurança do job.   → NÃO retryable
  timeout    — excedeu o tempo limite.                → retryable (pode ser transitório)
  resource   — sem recursos (memória).                → NÃO retryable como está
               (precisa de dado menor ou executor maior)
  transient  — falha operacional/infra (rede, conexão).      → retryable
  internal   — inesperado/desconhecido.               → terminal (não reentregar às cegas)

`retryable` é derivado da categoria — é a dica que a futura lógica de reentrega
usa para decidir re-despachar vs. dead-letter.
"""
import asyncio

# categoria → retryable
_RETRYABLE = {
    "user": False,
    "validation": False,
    "timeout": True,
    "resource": False,
    "transient": True,
    "internal": False,
}


def is_retryable(category: str) -> bool:
    return _RETRYABLE.get(category, False)


def _chain(exc: BaseException):
    """Percorre a exceção e sua cadeia (__cause__/__context__) sem repetir.

    Os nós envolvem o erro original num RuntimeError (`raise RuntimeError(...)
    from e`), então a causa raiz (ex.: MemoryError da interseção) fica no
    __cause__ — precisa olhar a cadeia, não só o topo."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        yield cur
        cur = cur.__cause__ or cur.__context__


def classify_error(exc: BaseException) -> str:
    """Retorna a categoria (string) da falha, olhando a cadeia de exceções."""
    types = tuple(type(e) for e in _chain(exc))

    def has(*cls: type) -> bool:
        return any(issubclass(t, cls) for t in types)

    # Ordem importa: do mais específico/informativo para o genérico.
    if has(MemoryError):
        return "resource"
    # asyncio.TimeoutError é alias de TimeoutError no 3.11+ (o executor roda 3.12).
    if has(asyncio.TimeoutError, TimeoutError):
        return "timeout"
    if has(ConnectionError):
        return "transient"
    if has(ValueError, TypeError, KeyError, IndexError):
        return "user"
    return "internal"
