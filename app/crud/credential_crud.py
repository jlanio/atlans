# app/crud/credential_crud.py
"""Data access operations for Credential — no business logic."""
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Credential


class CredentialCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, cred_id: UUID) -> Credential | None:
        result = await self.db.execute(select(Credential).where(Credential.id == cred_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        owner_id: str | None = None,
        type: str | None = None,
        workspace_ids: list[str] | None = None,
    ) -> list[Credential]:
        """Lists visible credentials: the owner's UNION those shared with
        their workspaces.

        `owner_id` and `workspace_ids` combine with OR — a credential shows up
        if it belongs to the user OR has a workspace_id in one of their
        workspaces. With neither, keeps the old behavior (no scope filter);
        that is why the router ALWAYS passes owner_id, so it never lists openly.
        """
        stmt = select(Credential)
        escopo = []
        if owner_id:
            escopo.append(Credential.owner_id == owner_id)
        if workspace_ids:
            escopo.append(Credential.workspace_id.in_(workspace_ids))
        if escopo:
            stmt = stmt.where(or_(*escopo))
        if type:
            stmt = stmt.where(Credential.type == type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
