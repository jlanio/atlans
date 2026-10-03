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
    # NULL when `content_location='executor'`: there is no object in storage.
    s3_key        = Column(String(1024), nullable=True)            # key in MinIO
    original_name = Column(String(512), nullable=False)            # user's original name
    extension     = Column(String(20),  nullable=False)
    mime_type     = Column(String(120), nullable=True)
    size          = Column(BigInteger,  nullable=True)             # bytes (preenchido apos confirm)
    content_md5   = Column(String(32), nullable=True, index=True)  # MD5 of the content
    uploaded_by   = Column(String(36), nullable=True)              # user.id_hash ou executor_id
    status        = Column(String(16), nullable=False, server_default="confirmed")  # pending | confirmed

    created_at    = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at    = Column(DateTime, nullable=True, onupdate=func.now())
    # Last time the CONTENT was written. Distinct from `updated_at`, which any
    # update of the row (renaming, for example) triggers — and which is NOT
    # triggered when an overwrite changes no field. Written explicitly in
    # confirm_upload; it is what the listing sorts by.
    content_written_at = Column(DateTime, nullable=True)

    # ── Content locality (LGPD) ───────────────────────────────────────────────
    # 'minio'    — object in storage; s3_key filled in (the usual case).
    # 'executor' — GeoSync in catalog mode: the file is in the executor's synced
    #              folder and was NEVER uploaded. The server keeps only the
    #              catalog (name, type, size, CRS, bbox, count).
    #
    # There is no path column here, unlike `artifacts.local_path`, and that is
    # deliberate: the executor finds the file again through its OWN sync manifest
    # (`.atlans-sync.json`, which maps remote_id_hash -> dataset). No file system
    # path travels over the network or is stored on the server.
    content_location  = Column(String(16), nullable=False, server_default=text("'minio'"))
    content_executor_id = Column(String(36), nullable=True)   # which executor has the bytes
    spatial_metadata  = Column(JSON, nullable=True)           # CRS, bbox, feature_count, columns
