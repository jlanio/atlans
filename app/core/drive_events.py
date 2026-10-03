# app/core/drive_events.py
"""Shared module for emitting Drive events via Redis pub/sub."""
import json
from app.core.utils.logger import get_logger

from sqlalchemy import select

logger = get_logger(__name__)


async def emit_drive_event(
    workspace_id: str,
    action: str,
    file_info: dict,
    exclude_agent_id: str | None = None,
) -> None:
    """
    Publishes a Drive event on Redis for the workspace's active executors.

    file_info must contain at least: id_hash, original_name.
    Optional fields: extension, size, content_md5, source.
    """
    from app.models.workspace import Workspace
    from app.core.db import AsyncSessionLocal

    # Envelope signed with APP_SECRET — _drive_event_listener refuses any
    # message without a valid HMAC before forwarding it to the executor's WebSocket.
    from app.core.executor_connections import build_signed_envelope

    payload = build_signed_envelope(
        json.dumps({"type": "drive_event", "action": action, "file": file_info})
    )

    from app.core.redis import get_redis_pool
    rc = get_redis_pool()
    try:
        async with AsyncSessionLocal() as db:
            # Executors that serve this workspace: the legacy pointer AND the policy's
            # tier members — all of them may receive its jobs, so
            # all of them need to know the Drive changed.
            vivo = await db.execute(
                select(Workspace.id_hash).where(
                    Workspace.id_hash == workspace_id,
                    Workspace.deleted_at.is_(None),
                )
            )
            agent_ids: set[str] = set()
            if vivo.scalar_one_or_none():
                from app.services.workspace_executor_service import executor_ids_for_workspaces
                agent_ids |= await executor_ids_for_workspaces(db, [workspace_id])

            # Also looks up the default executor
            from app.services.user_executor_service import get_default_agent
            default_ag = await get_default_agent(db)
            if default_ag:
                agent_ids.add(default_ag.id_hash)

        for aid in agent_ids:
            if aid == exclude_agent_id:
                continue
            is_online = await rc.exists(f"executor:presence:{aid}")
            if is_online:
                await rc.publish(f"executor:{aid}:drive_events", payload)
    except Exception as exc:
        logger.warning("Erro ao emitir drive_event (%s): %s", action, exc)
