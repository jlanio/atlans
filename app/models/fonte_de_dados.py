# app/models/fonte_de_dados.py
"""
O catalogo de fontes pre-mapeadas: o que o assistente consulta ANTES de
prospectar qualquer dado externo.

Uma linha por fonte (hoje: uma camada de um WFS). Ela guarda tres coisas que
custavam uma execucao inteira para descobrir:

- **o que colar no no** (`propriedades`: url, typeName, sortBy...), ja
  normalizado como o `WFSNode` normaliza;
- **o que sai dela** (`esquema`: crs, bbox, geometria, colunas, contagem),
  vindo do Vault, de um DescribeFeatureType ou de uma execucao — a origem fica
  em `esquema.columns_source`;
- **se ela responde** (`estado` + `verificada_em` + `ultimo_erro`), atualizado
  por endpoint pelo laco de verificacao.

`workspace_id` nulo e fonte da PLATAFORMA (a semente de `catalogo/geoservicos/`
e as registradas pelo admin), visivel a qualquer membro; preenchido e fonte de
um workspace. `origem` diz quem a criou — `vault` (a pasta versionada),
`aprendida` (uma execucao bem-sucedida) ou `manual` (uma pessoa ou o
assistente por `register_source`) — e nunca e rebaixada: uma fonte do Vault
que uma execucao usa continua `vault`.

`chave` e o sha256 de (workspace, tipo, url normalizada, type_name) e e a
unica identidade da linha: e por ela que o upsert nao duplica e que a
validacao confere um no em UMA consulta. `busca` e o texto normalizado (sem
acento, minusculas) que a busca por `LIKE` varre — instituicao, grupo, titulo,
type_name, host, descricao, temas e nomes de colunas —, recalculado a cada
escrita pelo service, nunca a mao.
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
    # NULL = plataforma. Sem FK de proposito: a semente nasce antes de qualquer
    # workspace e nao deve cair em cascata com ele.
    workspace_id = Column(String(36), nullable=True)
    tipo = Column(String(16), nullable=False, server_default=text("'wfs'"))
    no = Column(String(64), nullable=False, server_default=text("'WFS'"))
    url = Column(String(2048), nullable=False)
    type_name = Column(String(255), nullable=True)
    chave = Column(String(64), unique=True, nullable=False)
    propriedades = Column(JSON, nullable=False)
    instituicao = Column(String(120), nullable=True)
    grupo = Column(String(160), nullable=True)
    # TEXT, e não VARCHAR(255): o título é escrito por gente, e o catálogo real
    # tem 48 registros acima de 255 (indicadores do IBGE chegam a 276). Quando
    # ele era limitado, a importação estourava no registro 6.779 e 75 % do
    # catálogo — 19 mil camadas — nunca entrava. Qualquer limite fixo aqui é
    # arbitrário; `descricao` e `dicas` já são TEXT pelo mesmo motivo, e não há
    # índice sobre esta coluna.
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
    # sha256 do registro parseado do Vault: reimportar a mesma pasta e uma
    # consulta e zero escritas.
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
