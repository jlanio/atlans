# app/crud/executor_crud.py
"""Operações de acesso a dados para Executor — sem lógica de negócio."""
from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.datetime_utils import utc_now_naive
from app.models.executor import Executor


class ExecutorCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, executor_id: str, include_deleted: bool = False) -> Executor | None:
        """Busca executor por id_hash."""
        q = select(Executor).where(Executor.id_hash == executor_id)
        if not include_deleted:
            q = q.where(Executor.deleted_at.is_(None))
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list(self) -> list[Executor]:
        """Lista executores ativos (não deletados), do mais recente para o mais antigo."""
        q = select(Executor).where(Executor.deleted_at.is_(None)).order_by(Executor.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_any(self, executor_id: str) -> Executor | None:
        """Busca executor por id_hash incluindo deletados (para delete/revoke)."""
        result = await self.db.execute(select(Executor).where(Executor.id_hash == executor_id))
        return result.scalar_one_or_none()

    async def touch_last_seen(self, executor_id: str) -> None:
        result = await self.db.execute(select(Executor).where(Executor.id_hash == executor_id))
        ag = result.scalar_one_or_none()
        if ag:
            ag.last_seen_at = utc_now_naive()
            await self.db.commit()

    async def touch_last_seen_if_later(self, executor_id: str, visto_em: datetime) -> None:
        """Grava `visto_em` só se for posterior ao `last_seen_at` atual, num
        UPDATE só (a condição e a escrita são atômicas)."""
        await self.db.execute(
            update(Executor)
            .where(Executor.id_hash == executor_id)
            .where(or_(Executor.last_seen_at.is_(None), Executor.last_seen_at < visto_em))
            .values(last_seen_at=visto_em)
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()
