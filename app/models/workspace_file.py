# app/models/workspace_file.py
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Index, JSON, func, text
from uuid import uuid4
from app.models.base import Base


class WorkspaceFile(Base):
    """Arquivo vinculado a um workspace, armazenado no MinIO."""
    __tablename__ = "workspace_files"
    __table_args__ = (
        Index("ix_workspace_file_workspace_created", "workspace_id", "created_at"),
        Index("ix_workspace_file_workspace_written", "workspace_id", "content_written_at"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    id_hash       = Column(String(36), unique=True, nullable=False, index=True,
                           default=lambda: str(uuid4()))

    workspace_id  = Column(String(36), nullable=False, index=True)
    # NULL quando `content_location='executor'`: nao ha objeto no storage.
    s3_key        = Column(String(1024), nullable=True)            # key no MinIO
    original_name = Column(String(512), nullable=False)            # nome original do usuario
    extension     = Column(String(20),  nullable=False)
    mime_type     = Column(String(120), nullable=True)
    size          = Column(BigInteger,  nullable=True)             # bytes (preenchido apos confirm)
    content_md5   = Column(String(32), nullable=True, index=True)  # MD5 do conteudo
    uploaded_by   = Column(String(36), nullable=True)              # user.id_hash ou executor_id
    status        = Column(String(16), nullable=False, server_default="confirmed")  # pending | confirmed

    created_at    = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at    = Column(DateTime, nullable=True, onupdate=func.now())
    # Ultima vez que o CONTEUDO foi escrito. Distinta de `updated_at`, que
    # qualquer update da linha (renomear, por exemplo) dispara — e que NAO
    # dispara quando uma sobrescrita nao muda nenhum campo. Gravada
    # explicitamente no confirm_upload; e por ela que a listagem ordena.
    content_written_at = Column(DateTime, nullable=True)

    # ── Localidade do conteudo (LGPD) ─────────────────────────────────────────
    # 'minio'    — objeto no storage; s3_key preenchida (o caso de sempre).
    # 'executor' — GeoSync em modo catalogo: o arquivo esta na pasta sincronizada
    #              do executor e NUNCA foi enviado. O servidor guarda apenas o
    #              catalogo (nome, tipo, tamanho, CRS, bbox, contagem).
    #
    # Nao ha coluna de caminho aqui, diferente de `artifacts.local_path`, e isso e
    # deliberado: o executor reencontra o arquivo pelo PROPRIO manifesto de sync
    # (`.atlans-sync.json`, que mapeia remote_id_hash -> dataset). Nenhum caminho
    # de sistema de arquivos trafega pela rede nem fica guardado no servidor.
    content_location  = Column(String(16), nullable=False, server_default=text("'minio'"))
    content_executor_id = Column(String(36), nullable=True)   # qual executor tem os bytes
    spatial_metadata  = Column(JSON, nullable=True)           # CRS, bbox, feature_count, columns
