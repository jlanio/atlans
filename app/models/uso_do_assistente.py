# app/models/uso_do_assistente.py
"""O que cada volta do assistente consumiu — e custou.

Uma linha por VOLTA do laco, e nao por conversa: e onde a cota ja e cobrada, os
dois nunca divergem, e uma conversa abandonada no meio ja deixou registrado o
que gastou ate ali. Somar so no fim perderia essas, e perderia para BAIXO — o
lado errado de errar numa tabela de custo.

**Nenhum conteudo mora aqui.** Contagens, o modelo e o custo. O que esta tabela
responde e de quanto foi a conta, nao do que se falou.

Contrato em docs/assistente-editor.md.
"""
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, func, text

from app.models.base import Base


class UsoDoAssistente(Base):
    __tablename__ = "uso_do_assistente"
    __table_args__ = (
        # As duas perguntas da tabela: quanto esta pessoa consome por dia, e
        # quanto entrou na janela dos ultimos 30 dias.
        Index("ix_uso_do_assistente_user", "user_id", "created_at"),
        Index("ix_uso_do_assistente_quando", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, nullable=False,
                     default=lambda: str(uuid4()))

    user_id = Column(String(36), nullable=False)   # users.id_hash

    # O modelo COM QUE esta volta foi produzida, gravado e nao deduzido: no dia
    # em que alguem trocar o modelo, o historico precisa continuar dizendo com
    # qual ele foi feito, senao comparar antes e depois fica impossivel logo na
    # primeira troca.
    modelo = Column(String(120), nullable=False)
    superficie = Column(String(24), nullable=True)   # home | editor

    # `entrada` JA INCLUI o que veio do cache, e `raciocinio` e um recorte de
    # `saida` — e a mesma convencao de `assistente_service.Uso`, mantida de
    # proposito para que ninguem precise converter nada ao ler.
    entrada = Column(Integer, nullable=False, server_default=text("0"))
    saida = Column(Integer, nullable=False, server_default=text("0"))
    cache_leitura = Column(Integer, nullable=False, server_default=text("0"))
    raciocinio = Column(Integer, nullable=False, server_default=text("0"))

    # O que o provedor disse que custou. NUMERIC e nao FLOAT: sao somas de
    # dinheiro sobre milhares de linhas, e o arredondamento binario aparece no
    # total. E o custo REAL — reprecificar com outro modelo usa as contagens.
    custo_usd = Column(Numeric(12, 6), nullable=False, server_default=text("0"))

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
