# app/crud/credential_crud.py
"""Operações de acesso a dados para Credential — sem lógica de negócio."""
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
        """Lista credenciais visíveis: as do dono UNIÃO as compartilhadas com
        seus workspaces.

        `owner_id` e `workspace_ids` combinam por OR — uma credencial aparece se
        pertence ao usuário OU tem workspace_id em um workspace dele. Sem nenhum
        dos dois, mantém o comportamento antigo (sem filtro de escopo); por isso
        o router SEMPRE passa owner_id, para nunca listar aberto.
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
