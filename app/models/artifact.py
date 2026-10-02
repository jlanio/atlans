# app/models/artifact.py
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean, Index, func, JSON, text
from uuid import uuid4
from app.models.base import Base


class Artifact(Base):
    """Artefato produzido por um nó DataOutput durante a execução de um workflow."""
    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifact_workspace_created", "workspace_id", "created_at"),
        Index("ix_artifact_run_id", "run_id"),
        # Um pin-cache por (workflow, nó). A duplicata nascia em
        # `_upsert_pin_artifact` quando dois runs do mesmo fluxo terminavam
        # juntos, e a partir dela toda leitura encontrava duas linhas.
        #
        # Parcial porque só a linha FIXADA é única: o mesmo nó produz um
        # artefato normal por execução, e esses podem repetir à vontade.
        # `node_id` nulo fica de fora sozinho — `NULL <> NULL` no índice.
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
    run_id        = Column(String(36), nullable=True)   # id da execução
    node_id       = Column(String(255), nullable=True)

    # Metadados do artefato
    output_key    = Column(String(255), nullable=False)   # label definido no nó
    filename      = Column(String(512), nullable=False)
    format        = Column(String(32), nullable=True)     # geojson, json, csv, …
    size_bytes    = Column(BigInteger, nullable=True)
    features      = Column(Integer, nullable=True)        # número de features (GeoDataFrame)
    s3_key           = Column(String(1024), nullable=True)   # key no MinIO
    # Nome SQL "executor_id" (renomeada em 20260716_0001); atributo Python
    # mantido como executor_id ate R2.3.
    executor_id         = Column("executor_id", String(36), nullable=True)     # id_hash do executor que produziu

    # ── Localidade do conteudo (LGPD) ─────────────────────────────────────────
    # 'minio'    — o objeto esta no storage; s3_key preenchida (o caso de sempre).
    # 'executor' — os bytes NUNCA sairam da maquina do executor. s3_key e NULL e
    #              `local_path` diz onde o arquivo esta, relativo ao
    #              EXECUTOR_ARTIFACTS_DIR daquele executor. O download pela
    #              plataforma nao existe: servir o arquivo exigiria trazer o
    #              conteudo ate o servidor, que e exatamente o que a marcacao
    #              proibe. `executor_id` (derivado de run.host, fonte confiavel)
    #              identifica qual maquina o tem.
    content_location = Column(String(16), nullable=False, server_default=text("'minio'"))
    local_path       = Column(String(1024), nullable=True)

    # Controle de acesso ao download
    credential_id = Column(String(36), nullable=True)     # se definido → download exige token

    # Portal de compartilhamento
    is_published   = Column(Boolean, nullable=False, server_default=text("false"))
    publish_config = Column(JSON, nullable=True)

    # Pin cache
    is_pinned = Column(Boolean, nullable=False, server_default=text("false"))

    # Retenção
    created_at  = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    expires_at  = Column(DateTime, nullable=True)         # null = não expira
