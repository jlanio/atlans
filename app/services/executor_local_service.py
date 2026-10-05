"""
app/services/executor_local_service.py

The executor that `make up-dev` brings up on its own, for local tests.

Two containers share a folder (the executor's `/data/matricula`, see
docker-compose.yml) and talk through two small JSON files in it:

  pedido.json      written HERE: the executor id and a fresh enrollment OTP.
                   The executor's entrypoint (scripts/executor-local/) reads it,
                   enrolls through the dev Traefik, exactly as an operator would
                   with `python -m executor enroll`, and deletes it.
  cadastrado.json  written by the executor after the enrollment worked: the id
                   it holds a certificate for.

Each pass of `provisionar` compares the database with those two files and does
the least it can: nothing when the executor is active and enrolled; a new OTP
when it still needs one; a new executor when the old one was revoked or
removed (or the database was recreated). `vigiar` repeats the pass, so the
executor also comes back after `alembic upgrade head` on a fresh database,
after a revocation in the UI and after a `down -v`.

The executor goes into the default pool (`executor_type="default"`): every
workspace can route to it, with no assignment by hand.

Development only: the compose file runs it in the `executor-local` profile,
never in `prod`.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.core.utils.logger import get_logger

logger = get_logger(__name__)

NOME = "Executor local (dev)"
DESCRICAO = "Criado pelo make up-dev para testes locais. Volta sozinho se for removido."
# Who the OTP says created it (the column has no FK; there is no user behind it).
CRIADO_POR = "executor-local"

PEDIDO = "pedido.json"
CADASTRADO = "cadastrado.json"

Situacao = Literal["pronto", "pedido", "aguardando"]


def _ler_json(caminho: Path) -> dict:
    """The file's object, or {} when it is missing or unreadable (half written, edited by hand)."""
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def _gravar_json(caminho: Path, dados: dict) -> None:
    """Writes atomically and born 600: the OTP is a credential, and the reader
    must never see half a file."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=caminho.parent, prefix=f".{caminho.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f)
        os.chmod(tmp, 0o600)
        os.replace(tmp, caminho)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _pedido_vale(pedido: dict, executor_id: str) -> bool:
    """A request the executor can still use: for this executor and not expired."""
    if pedido.get("executor_id") != executor_id or not pedido.get("otp"):
        return False
    try:
        expira = datetime.fromisoformat(pedido["expira_em"])
    except (KeyError, TypeError, ValueError):
        return False
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    return expira > datetime.now(timezone.utc)


async def provisionar(pasta: Path) -> Situacao:
    """One pass: makes sure the local executor exists and, when it still needs a
    certificate, leaves an enrollment request in `pasta`.

    Returns what it found: `pronto` (active and enrolled), `aguardando` (a
    request is there, the executor has not used it yet) or `pedido` (wrote a new
    request). A database without the schema raises: the caller decides whether
    to retry.
    """
    from sqlalchemy import select

    from app.core.db import get_session_async
    from app.models.executor import Executor
    from app.services import executor_enrollment_service, executor_service

    cadastrado = _ler_json(pasta / CADASTRADO)
    pedido = _ler_json(pasta / PEDIDO)

    async with get_session_async() as db:
        executor = None
        # The id the executor holds a certificate for comes first: the name can
        # be edited in the UI, the id cannot.
        if cadastrado.get("executor_id"):
            executor = await executor_service.get_agent(db, cadastrado["executor_id"])
        if executor is None:
            executor = (
                await db.execute(
                    select(Executor)
                    .where(Executor.name == NOME, Executor.deleted_at.is_(None))
                    .order_by(Executor.created_at.desc())
                )
            ).scalars().first()
        # Revoked (or any other final state): a new one, instead of fighting
        # whoever revoked it. Enrolling a revoked executor again would also work,
        # but it would bring back the certificate history of the old one.
        if executor is not None and executor.status not in ("pending", "active"):
            executor = None
        if executor is None:
            executor = await executor_service.create_executor(
                db,
                name=NOME,
                created_by=None,
                description=DESCRICAO,
                executor_type="default",
            )
            logger.info("Executor local criado: %s.", executor.id_hash)

        # Read while the session is open: leaving it rolls back, which expires
        # the instance.
        executor_id = executor.id_hash
        if executor.status == "active" and cadastrado.get("executor_id") == executor_id:
            return "pronto"
        # A request already waiting for this executor: generating another OTP now
        # would invalidate it while the executor may be using it.
        if _pedido_vale(pedido, executor_id):
            return "aguardando"

        otp, expira_em = await executor_enrollment_service.create_enrollment_otp(
            db, executor_id, created_by=CRIADO_POR,
        )

    _gravar_json(pasta / PEDIDO, {
        "executor_id": executor_id,
        "otp": otp,
        "expira_em": expira_em.isoformat(),
    })
    return "pedido"


MENSAGENS: dict[str, str] = {
    "pronto": "Executor local cadastrado e ativo.",
    "pedido": "Executor local: pedido de cadastro gravado; o container do executor faz o resto.",
    "aguardando": "Executor local: aguardando o container do executor usar o pedido de cadastro.",
}


def explicar_erro(exc: BaseException) -> str:
    """What to do about a failed pass, in one line. The usual one on a fresh
    database is the schema that `alembic upgrade head` has not created yet."""
    texto = str(exc)
    # asyncpg's UndefinedTableError, as SQLAlchemy wraps it: 'relation "executors" does not exist'.
    if "relation" in texto and "does not exist" in texto:
        return (
            "Executor local: o banco ainda nao tem o schema. "
            "Rode `docker compose exec api alembic upgrade head`; o executor sobe em seguida."
        )
    return f"Executor local: sem acesso ao banco ainda ({type(exc).__name__}). Tentando de novo."


async def vigiar(pasta: Path, intervalo: float = 15.0) -> None:
    """Repeats `provisionar` forever, printing only when the situation changes."""
    ultima = None
    while True:
        try:
            mensagem = MENSAGENS[await provisionar(pasta)]
        except Exception as exc:  # noqa: BLE001 — the loop is the retry
            mensagem = explicar_erro(exc)
        if mensagem != ultima:
            print(mensagem, flush=True)
            ultima = mensagem
        await asyncio.sleep(intervalo)
