from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.models.base import Base


class PlatformFileSettings(Base):
    """Configurações globais de upload — singleton (sempre id=1)."""
    __tablename__ = "platform_file_settings"

    id          = Column(Integer, primary_key=True, default=1)
    max_size_mb = Column(Integer, default=200, nullable=False)
    updated_at  = Column(DateTime, onupdate=func.now(), nullable=True)


class AllowedFileExtension(Base):
    """Extensões de arquivo aceitas pela plataforma."""
    __tablename__ = "allowed_file_extensions"

    id         = Column(Integer, primary_key=True, index=True)
    extension  = Column(String(20), unique=True, nullable=False, index=True)
    enabled    = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
