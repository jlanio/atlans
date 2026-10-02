# app/models/conversa.py
"""
Conversas do assistente da Home — persistidas no banco, varias por pessoa, sem prazo.

Diferente do assistente do editor, cujo transcrito vive no Redis com TTL de 24h
(`app/services/assistente_service.py`), a Home guarda a conversa DE VERDADE: a
pessoa reabre a pagina dias depois e a conversa esta la. Duas tabelas:

- `conversas`: uma linha por conversa (dona, titulo, contexto opcional de fluxo,
  origem, total de tokens gastos, datas). `deleted_at` e soft delete — apagar
  some da lista sem perder o historico de verdade.
- `mensagens`: as mensagens em ordem. `blocos` guarda o conteudo VERBATIM no
  formato do projeto (string OU lista de blocos `thinking`/`text`/`tool_use`/
  `tool_result` — ver `app/services/openrouter.py`), porque e isso que o laco
  reenvia ao retomar a conversa — inclusive os `reasoning_details` do bloco de
  raciocinio, que o provedor precisa receber de volta. `uso` e `meta` sao
  opcionais.

A chave estrangeira de `mensagens` para `conversas` e por `id_hash` (o hash
publico, unico), com CASCADE: apagar DE VERDADE uma conversa leva as mensagens
junto. O caminho normal, porem, e o soft delete, que nao dispara cascata.
"""
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)

from app.models.base import Base


class Conversa(Base):
    __tablename__ = "conversas"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid4()))
    # User.id_hash da dona. CASCADE so no hard delete do usuario; o soft delete
    # da conta nao apaga conversa (fica o historico), e a conversa tem o proprio.
    user_id = Column(String(36), ForeignKey("users.id_hash", ondelete="CASCADE"), nullable=False, index=True)
    # Workspace preferido no momento da conversa (opcional) e fluxo de CONTEXTO
    # (opcional) — nao e o fluxo do assistente, e so a referencia que a pessoa abriu.
    workspace_id = Column(String(36), nullable=True)
    workflow_id = Column(String(36), nullable=True)
    titulo = Column(String(120), nullable=True)
    # "home" hoje; a coluna existe para o dia em que o editor tambem persistir aqui.
    origem = Column(String(16), nullable=False, server_default=text("'home'"))
    tokens_total = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    # Carimbado pelo service a cada turno — e por ele que a lista "minhas
    # conversas" ordena (a mais recentemente ativa em cima).
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_conversas_user_updated", "user_id", "updated_at"),
    )


class Mensagem(Base):
    __tablename__ = "mensagens"

    id = Column(Integer, primary_key=True, index=True)
    conversa_id = Column(
        String(36), ForeignKey("conversas.id_hash", ondelete="CASCADE"), nullable=False, index=True
    )
    # A ordem e o indice estavel da mensagem na conversa: o replay a le em ordem
    # crescente, e ela e o que o `anexar` incrementa (max+1).
    ordem = Column(Integer, nullable=False)
    papel = Column(String(16), nullable=False)  # "user" | "assistant"
    # VERBATIM: string OU lista de blocos, no formato do projeto (dicionarios
    # puros, como o laco os grava). A traducao para a rede e do cliente do modelo.
    blocos = Column(JSON, nullable=False)
    uso = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("conversa_id", "ordem", name="uq_mensagens_conversa_ordem"),
    )
