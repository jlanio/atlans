from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Schedule


class ScheduleCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, job_id: str) -> Schedule | None:
        stmt = select(Schedule).where(Schedule.job_id == job_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, **data) -> Schedule:
        """
        Cria um novo agendamento.
        """
        sch = Schedule(**data)
        self.db.add(sch)
        await self.db.commit()
        await self.db.refresh(sch)
        return sch

    async def update(
        self,
        sch: Schedule,
        updates: dict
    ) -> Schedule:
        """
        Atualiza campos de um agendamento existente.
        """
        for key, value in updates.items():
            setattr(sch, key, value)
        await self.db.commit()
        await self.db.refresh(sch)
        return sch

    async def update_by_id(
        self,
        schedule_id: int,
        updates: dict
    ) -> Schedule:
        """
        Busca um agendamento pelo ID e aplica updates.
        Lança ValueError se não encontrado.
        """
        sch = await self.get(schedule_id)
        if not sch:
            raise ValueError(f"Schedule {schedule_id} não encontrado.")
        return await self.update(sch, updates)

    async def delete(self, job_id: str | Schedule) -> None:
        """
        Remove um agendamento por ID ou instância.
        """
        if isinstance(job_id, Schedule):
            sch = job_id
        else:
            sch = await self.get(job_id)
        if sch:
            await self.db.delete(sch)
            await self.db.commit()

    async def get_by_workflow_hash(self, id_hash: str, active_only: bool = False) -> list[Schedule]:
        stmt = select(Schedule).where(Schedule.workflow_hash == id_hash)
        if active_only:
            stmt = stmt.where(Schedule.active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalars().all()
