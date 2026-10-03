# app/models/fonte_de_dados.py
"""
The catalog of pre-mapped sources: what the assistant consults BEFORE
prospecting any external data.

One row per source (today: one layer of a WFS). It stores three things that
used to cost a whole run to find out:

- **what to paste into the node** (`propriedades`: url, typeName, sortBy...),
  already normalized the way `WFSNode` normalizes it;
- **what comes out of it** (`esquema`: crs, bbox, geometry, columns, count),
  coming from the Vault, from a DescribeFeatureType or from a run — the origin
  is recorded in `esquema.columns_source`;
- **whether it responds** (`estado` + `verificada_em` + `ultimo_erro`),
  updated per endpoint by the check loop.

A null `workspace_id` is a PLATFORM source (the seed from `catalogo/geoservicos/`
and the ones registered by the admin), visible to any member; filled in, it is
a workspace source. `origem` says who created it — `vault` (the versioned
folder), `aprendida` (a successful run) or `manual` (a person or the assistant
via `register_source`) — and it is never downgraded: a Vault source that a run
uses stays `vault`.

`chave` is the sha256 of (workspace, type, normalized url, type_name) and is
the row's only identity: it is what keeps the upsert from duplicating and lets
validation check a node in ONE query. `busca` is the normalized text (no
accents, lowercase) that the `LIKE` search scans — institution, group, title,
type_name, host, description, themes and column names —, recomputed on every
write by the service, never by hand.
"""
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)

from app.models.base import Base


class FonteDeDados(Base):
    __tablename__ = "fontes_de_dados"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    # NULL = platform. No FK on purpose: the seed is born before any workspace
    # and must not be cascade-deleted with it.
    workspace_id = Column(String(36), nullable=True)
    tipo = Column(String(16), nullable=False, server_default=text("'wfs'"))
    no = Column(String(64), nullable=False, server_default=text("'WFS'"))
    url = Column(String(2048), nullable=False)
    type_name = Column(String(255), nullable=True)
    chave = Column(String(64), unique=True, nullable=False)
    propriedades = Column(JSON, nullable=False)
    instituicao = Column(String(120), nullable=True)
    grupo = Column(String(160), nullable=True)
    # TEXT, not VARCHAR(255): the title is written by people, and the real
    # catalog has 48 records above 255 (IBGE indicators reach 276). When it
    # was limited, the import blew up at record 6,779 and 75 % of the catalog —
    # 19 thousand layers — never got in. Any fixed limit here is arbitrary;
    # `descricao` and `dicas` are already TEXT for the same reason, and there
    # is no index on this column.
    titulo = Column(Text, nullable=True)
    descricao = Column(Text, nullable=True)
    temas = Column(JSON, nullable=True)
    esquema = Column(JSON, nullable=True)
    dicas = Column(Text, nullable=True)
    busca = Column(Text, nullable=False, server_default=text("''"))
    # 1 preferida · 2 normal · 3 secundaria — o Vault marca, a busca ordena.
    prioridade = Column(SmallInteger, nullable=False, server_default=text("2"))
    origem = Column(String(16), nullable=False, server_default=text("'manual'"))
    estado = Column(String(16), nullable=False, server_default=text("'nao_verificada'"))
    verificada_em = Column(DateTime, nullable=True)
    ultimo_erro = Column(Text, nullable=True)
    # sha256 of the record parsed from the Vault: reimporting the same folder is
    # one query and zero writes.
    vault_hash = Column(String(64), nullable=True)
    usos = Column(Integer, nullable=False, server_default=text("0"))
    usada_em = Column(DateTime, nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_fontes_de_dados_workspace_id", "workspace_id"),
        Index("ix_fontes_de_dados_tipo_url", "tipo", "url"),
        Index("ix_fontes_de_dados_instituicao", "instituicao"),
    )
