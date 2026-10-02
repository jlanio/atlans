# app/models/system_config.py
from sqlalchemy import Column, String, JSON, DateTime, func
from app.models.base import Base


class SystemConfig(Base):
    """Configurações globais do sistema armazenadas no banco de dados."""
    __tablename__ = "system_config"

    key = Column(String, primary_key=True, nullable=False)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
