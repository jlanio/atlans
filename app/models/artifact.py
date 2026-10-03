# app/models/artifact.py
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean, Index, func, JSON, text
from uuid import uuid4
from app.models.base import Base


class Artifact(Base):
    """Artifact produced by a DataOutput node during a workflow run."""
    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifact_workspace_created", "workspace_id", "created_at"),
        Index("ix_artifact_run_id", "run_id"),
        # One pin cache per (workflow, node). The duplicate was born in
        # `_upsert_pin_artifact` when two runs of the same workflow finished
        # together, and from then on every read found two rows.
        #
        # Partial because only the PINNED row is unique: the same node produces
        # a regular artifact per run, and those may repeat freely.
        # A null `node_id` is left out on its own — `NULL <> NULL` in the index.
        Index(
            "uq_artifact_pin_por_no",
            "workflow_hash",
            "node_id",
            unique=True,
            postgresql_where=text("is_pinned"),
            sqlite_where=text("is_pinned"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False, index=True,
                     default=lambda: str(uuid4()))

    # Escopo
    workspace_id  = Column(String(36), nullable=False, index=True)
    workflow_hash = Column(String(36), nullable=True, index=True)
    run_id        = Column(String(36), nullable=True)   # run id
    node_id       = Column(String(255), nullable=True)

    # Artifact metadata
    output_key    = Column(String(255), nullable=False)   # label defined on the node
    filename      = Column(String(512), nullable=False)
    format        = Column(String(32), nullable=True)     # geojson, json, csv, …
    size_bytes    = Column(BigInteger, nullable=True)
    features      = Column(Integer, nullable=True)        # number of features (GeoDataFrame)
    s3_key           = Column(String(1024), nullable=True)   # key in MinIO
    # Nome SQL "executor_id" (renomeada em 20260716_0001); atributo Python
    # mantido como executor_id ate R2.3.
    executor_id         = Column("executor_id", String(36), nullable=True)     # id_hash of the executor that produced it

    # ── Content locality (LGPD) ───────────────────────────────────────────────
    # 'minio'    — the object is in storage; s3_key filled in (the usual case).
    # 'executor' — the bytes NEVER left the executor's machine. s3_key is NULL
    #              and `local_path` says where the file is, relative to that
    #              executor's EXECUTOR_ARTIFACTS_DIR. Download through the
    #              platform does not exist: serving the file would require
    #              bringing the content to the server, which is exactly what
    #              the marker forbids. `executor_id` (derived from run.host, a
    #              trusted source) identifies which machine has it.
    content_location = Column(String(16), nullable=False, server_default=text("'minio'"))
    local_path       = Column(String(1024), nullable=True)

    # Download access control
    credential_id = Column(String(36), nullable=True)     # if set → download requires a token

    # Sharing portal
    is_published   = Column(Boolean, nullable=False, server_default=text("false"))
    publish_config = Column(JSON, nullable=True)

    # Pin cache
    is_pinned = Column(Boolean, nullable=False, server_default=text("false"))

    # Retention
    created_at  = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    expires_at  = Column(DateTime, nullable=True)         # null = does not expire
