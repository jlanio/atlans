"""
app/services/situacao_instalacao.py

`python -m app.cli status`: the state of an installation in one JSON line, for
scripts/up.sh to read instead of guessing from logs. Read-only.

    {"schema": true, "revisao": "9ed006ca1660", "admins": 1,
     "executores": [{"id": "...", "nome": "Executor local (dev)",
                     "status": "active", "online": true}]}

Without the schema (`alembic upgrade head` still pending) the other fields are
empty: `schema` false says what to do. A database that does not answer is an
error (exit 1), with the explanation of check-db.
"""
from __future__ import annotations


async def situacao() -> dict:
    from sqlalchemy import func, inspect, select, text

    from app.core.db import get_session_async
    from app.models.executor import Executor
    from app.models.user import User

    async with get_session_async() as db:
        migrado = await db.run_sync(lambda s: inspect(s.connection()).has_table("alembic_version"))
        if not migrado:
            return {"schema": False, "revisao": None, "admins": 0, "executores": []}
        revisao = (await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))).scalar_one_or_none()
        admins = (await db.execute(
            select(func.count()).select_from(User).where(User.role == "admin", User.status == "active")
        )).scalar_one()
        # Read inside the session: on leaving it the objects expire, and reading
        # them afterwards is a DetachedInstanceError.
        executores = [
            {"id": e.id_hash, "nome": e.name, "status": e.status}
            for e in (await db.execute(
                select(Executor).where(Executor.deleted_at.is_(None)).order_by(Executor.created_at)
            )).scalars()
        ]

    online = await _presenca([e["id"] for e in executores])
    for e in executores:
        e["online"] = bool(online.get(e["id"]))
    return {"schema": True, "revisao": revisao, "admins": int(admins), "executores": executores}


async def _presenca(ids: list[str]) -> dict[str, bool]:
    """Who is connected, from the same Redis snapshot as the Executors screen.
    Without Redis nobody is online, which is what the screen would say too."""
    if not ids:
        return {}
    try:
        from app.core.executor_connections import executor_registry

        online, _ = await executor_registry.read_presence_and_capacities(ids)
        return online
    except Exception:  # noqa: BLE001 — presence is a hint, not the point of the command
        return {}
