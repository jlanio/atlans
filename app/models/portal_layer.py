# app/models/portal_layer.py
from sqlalchemy import (
    Column, Integer, String, Float,
    DateTime, JSON, UniqueConstraint, func,
)
from uuid import uuid4
from app.models.base import Base


class PortalLayer(Base):
    """
    Layer published on a workflow's sharing portal.
    Always keeps the latest GeoJSON version per workflow+layer_key.
    Updated via POST /artifacts/portal/publish by the PublishMap node.
    """
    __tablename__ = "portal_layers"
    __table_args__ = (
        UniqueConstraint("workflow_hash", "layer_key", name="ix_portal_layer_workflow_key"),
        {"extend_existing": True},
    )

    id            = Column(Integer, primary_key=True, index=True)
    id_hash       = Column(String(36), unique=True, nullable=False, index=True,
                           default=lambda: str(uuid4()))

    workflow_hash = Column(String(36), nullable=False, index=True)
    layer_key     = Column(String(255), nullable=False)

    # GeoJSON data (latest version — complete FeatureCollection)
    geojson_data  = Column(JSON, nullable=False)
    features      = Column(Integer, nullable=True)

    # Display configuration (separate columns)
    title          = Column(String(255), nullable=False, server_default="Camada")
    color          = Column(String(16), nullable=False, server_default="#3b82f6")
    opacity        = Column(Float, nullable=False, server_default="0.5")
    description    = Column(String(1024), nullable=True)
    visible_fields = Column(JSON, nullable=True)

    # Spatial metadata (filled in on publishing)
    bbox          = Column(JSON, nullable=True)    # [minX, minY, maxX, maxY]
    geometry_type = Column(String(32), nullable=True)  # "Point", "Polygon", etc.

    # Rastreabilidade
    run_id     = Column(String(36), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
