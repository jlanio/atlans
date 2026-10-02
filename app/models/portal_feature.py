# app/models/portal_feature.py
from sqlalchemy import Column, Integer, Float, JSON, Index, ForeignKey
from geoalchemy2 import Geometry
from app.models.base import Base


class PortalFeature(Base):
    """
    Feature individual de uma camada do portal.
    Armazena geometria PostGIS para geração de MVT (Mapbox Vector Tiles) via ST_AsMVT.
    """
    __tablename__ = "portal_features"
    __table_args__ = (
        Index("ix_portal_feature_layer_bbox", "layer_id", "min_x", "min_y", "max_x", "max_y"),
        Index("ix_portal_features_geom", "geom", postgresql_using="gist"),
        {"extend_existing": True},
    )

    id       = Column(Integer, primary_key=True, index=True)
    layer_id = Column(Integer, ForeignKey("portal_layers.id", ondelete="CASCADE"), nullable=False, index=True)

    properties = Column(JSON, nullable=True)
    geom       = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=False)

    min_x = Column(Float, nullable=True)
    min_y = Column(Float, nullable=True)
    max_x = Column(Float, nullable=True)
    max_y = Column(Float, nullable=True)
