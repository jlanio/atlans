# tests/unit/_mcp_harness.py
"""
Ferramental compartilhado dos testes do servidor MCP.

O nome começa com `_` de propósito: o pytest não coleta este arquivo, que não
tem teste nenhum — só o banco, o Redis de mentira e os atalhos que os testes de
`app/mcp/` usam.

Três decisões que valem para todos os testes daqui:

- **Banco de verdade, em memória.** O middleware de PAT faz JOIN entre token,
  usuário e workspaces; um mock de `db.execute` só provaria que o mock devolve o
  que se mandou. SQLite cobre as tabelas envolvidas (nenhuma delas usa JSONB,
  que o SQLite não compila).
- **Infra por dois patches.** `app.mcp.infra.sessao` e `app.mcp.infra.redis_ou_none`
  são os únicos pontos de contato do MCP com Postgres e Redis; trocá-los troca a
  infraestrutura inteira sem tocar em nenhum outro módulo.
- **Cliente que atravessa a pilha.** `cliente_mcp` fala com o app ASGI real
  (middleware de PAT + transporte streamable HTTP), não com o servidor em
  processo — é a única forma de provar que o token chega, que o `Host` é
  checado e que o escopo filtra o catálogo.

Uma limitação que vale conhecer antes de escrever teste de execução: o
`RedisFalso` NÃO tem pub/sub. Ele cobre os comandos de chave (cotas,
idempotência, replay por `LRANGE`) e mais nada — quem testa `run_workflow(wait)`
deve trocar `esperar_run` por um dublê (`patch` no módulo que a tool importa) e
descrever o desfecho com `resultado_de_espera(...)`. Testar a espera de verdade
é papel de `test_run_events_service.py`, que tem o `FakePubSub` para isso.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.mcp.escopo import EscopoEfetivo
from app.models.api_token import ApiToken
from app.models.artifact import Artifact
from app.models.base import Base
from app.models.portal_layer import PortalLayer
from app.models.user import User
from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.models.schedule import Schedule
from app.models.system_config import SystemConfig
from app.models.workflow_version import WorkflowVersion
from app.models.workspace import Workspace
from app.models.platform_file_settings import (
    AllowedFileExtension, PlatformFileSettings,
)
from app.models.workspace_file import WorkspaceFile
from app.models.workspace_member import WorkspaceMember
from app.services import api_token_service
from app.services.run_events_service import ResultadoEspera

TABELAS_DAS_EXTENSOES = [
    tabela for tabela in Base.metadata.sorted_tables
    if any(
        mapper.local_table is tabela and mapper.class_.__module__.startswith("app.extensoes.")
        for mapper in Base.registry.mappers
    )
]

# As tabelas que o MCP toca e que compilam no SQLite. `Credential` e `Executor`
# ficam de fora: usam JSONB, que só existe no Postgres.
TABELAS = [
    User.__table__,
    Workspace.__table__,
    WorkspaceMember.__table__,
    ApiToken.__table__,
    Workflow.__table__,
    WorkflowRun.__table__,
    WorkflowVersion.__table__,
    Schedule.__table__,
    Artifact.__table__,
    # A listagem de artefatos cruza com as camadas do portal para marcar qual
    # versão está publicada; sem a tabela, o SELECT quebra na coleta.
    PortalLayer.__table__,
    # O Drive. `PlatformFileSettings` e `AllowedFileExtension` entram junto
    # porque `validate_upload` consulta as duas ANTES de gravar qualquer coisa:
    # o teto de tamanho e a lista de extensões permitidas. Sem elas, a primeira
    # chamada de escrita quebra na coleta, não na asserção.
    WorkspaceFile.__table__,
    PlatformFileSettings.__table__,
    AllowedFileExtension.__table__,
    # A configuração do sistema (o modelo do assistente e, com os planos, a
    # cota de cada um). Sem a tabela o serviço degrada aberto e devolve o
    # padrão — um teste que editasse a configuração passaria sem nada ler.
    SystemConfig.__table__,
    # As tabelas das extensões presentes (app/extensoes): com os planos, a cota
    # do assistente consulta a assinatura para resolver o teto, e sem elas
    # qualquer teste que exercite `conversar()` quebraria na coleta.
    *TABELAS_DAS_EXTENSOES,
]


@asynccontextmanager
async def banco_em_memoria():
    """Um engine SQLite novo com as tabelas criadas; devolve a fábrica de sessões."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@asynccontextmanager
async def banco_de_executores():
    """Um SQLite novo com a tabela `executors`; devolve a fábrica de sessões.

    Ela fica fora de `TABELAS` porque usa JSONB, que o SQLite não compila: aqui
    vai uma cópia da tabela com JSON no lugar. As consultas do código usam o
    modelo `Executor` de verdade — só o nome da tabela e das colunas importa."""
    from sqlalchemy import JSON, MetaData
    from sqlalchemy.dialects.postgresql import JSONB

    from app.models.executor import Executor

    tabela = Executor.__table__.to_metadata(MetaData())
    for coluna in tabela.columns:
        if isinstance(coluna.type, JSONB):
            coluna.type = JSON()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(tabela.create)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def sessao_de(fabrica):
    """Substituto de `app.mcp.infra.sessao` ligado a esta fábrica.

    Imita o original: rollback no `finally`, para que quem escreve precise
    commitar — exatamente como em produção.
    """

    @asynccontextmanager
    async def _sessao():
        async with fabrica() as sessao:
            try:
                yield sessao
            finally:
                await sessao.rollback()

    return _sessao


async def criar_usuario(db, id_hash: str = "usr-1", username: str = "ana", status: str = "active") -> User:
    usuario = User(
        id_hash=id_hash,
        username=username,
        email=f"{username}@teste.local",
        hashed_password="x",
        status=status,
    )
    db.add(usuario)
    await db.commit()
    return usuario


async def criar_workspace(db, id_hash: str, owner_id: str, name: str = "Principal") -> Workspace:
    workspace = Workspace(id_hash=id_hash, name=name, owner_id=owner_id)
    db.add(workspace)
    await db.commit()
    return workspace


async def criar_pat(db, user_id: str, scopes, workspace_ids=None) -> str:
    """Emite um PAT de verdade e devolve o segredo em texto claro.

    Passa pelo service real (`criar`), não por um INSERT à mão: é o service que
    decide prefixo, hash e validade, e um teste que replicasse isso validaria a
    própria cópia.
    """
    usuario = SimpleNamespace(id_hash=user_id)
    _, segredo = await api_token_service.criar(
        db,
        usuario,
        name="token de teste",
        scopes=list(scopes),
        workspace_ids=None if workspace_ids is None else list(workspace_ids),
    )
    return segredo


async def criar_run(
    db,
    *,
    task_id: str,
    workflow_hash: str,
    workspace_id: str,
    status: str = "success",
    **campos,
) -> WorkflowRun:
    """Uma linha de `workflow_runs` já terminada, pronta para leitura.

    Os horários vêm fixos (e não de `now()`) porque o que os testes de execução
    conferem é a serialização — `duration_seconds`, ordem da listagem, janela de
    data — e um relógio real faria a asserção depender do instante do teste.
    `node_stats` nasce vazio, nunca nulo: é o formato que a serialização espera
    e o nulo só aparece em runs antigos. Run não terminal (`running`, `pending`)
    nasce sem `end_time`, como em produção — pedir `status="running"` e receber
    uma linha com hora de término faria o teste concordar com um estado que o
    banco nunca tem.
    """
    inicio = campos.pop("start_time", datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc))
    termina = status in ("success", "failed", "cancelled")
    fim = campos.pop("end_time", inicio + timedelta(seconds=42) if termina else None)
    duracao = campos.pop("duration_seconds", None)
    if duracao is None and fim is not None:
        duracao = (fim - inicio).total_seconds()
    campos.setdefault("node_stats", {})
    run = WorkflowRun(
        task_id=task_id,
        workflow_hash=workflow_hash,
        workspace_id=workspace_id,
        status=status,
        start_time=inicio,
        end_time=fim,
        duration_seconds=duracao,
        **campos,
    )
    db.add(run)
    await db.commit()
    return run


async def criar_artefato(db, *, run_id: str, workspace_id: str, **campos) -> Artifact:
    """Um artefato no storage, do jeito que o nó de saída o grava.

    O default é o caso comum (`content_location="minio"` com `s3_key`), que é o
    único que rende URL assinada; o caso do conteúdo que ficou no executor se
    escreve passando `content_location="executor", s3_key=None`.
    """
    campos.setdefault("output_key", "saida")
    campos.setdefault("filename", "saida.geojson")
    campos.setdefault("format", "geojson")
    campos.setdefault("size_bytes", 1024)
    campos.setdefault("content_location", "minio")
    if campos["content_location"] == "minio":
        campos.setdefault("s3_key", f"artifacts/{run_id}/{campos['filename']}")
    artefato = Artifact(run_id=run_id, workspace_id=workspace_id, **campos)
    db.add(artefato)
    await db.commit()
    return artefato


def resultado_de_espera(**kw) -> ResultadoEspera:
    """O `ResultadoEspera` que um `esperar_run` dublado devolveria.

    O default descreve o caso feliz — terminou em `success`, sem timeout, com o
    `__workflow_complete__` visto. Cada teste sobrescreve só o campo que
    investiga (`timed_out=True`, `status="failed"`, `redis_indisponivel=True`).
    """
    campos = {
        "status": "success",
        "run": None,
        "concluidos": 0,
        "eventos_descartados": 0,
        "timed_out": False,
        "redis_indisponivel": False,
        "viu_complete": True,
    }
    campos.update(kw)
    return ResultadoEspera(**campos)


def escopo_falso(**kw) -> EscopoEfetivo:
    """Um `EscopoEfetivo` pronto; sobrescreva só o campo que o teste investiga."""
    campos = {
        "user_id": "usr-1",
        "username": "ana",
        "token_id": "tok-1",
        "token_prefix": "atl_pat_Ab3d",
        "scopes": {"workflows:read"},
        "workspace_ids": {"ws-1"},
        "todos_os_workspaces": False,
    }
    campos.update(kw)
    campos["scopes"] = frozenset(campos["scopes"])
    campos["workspace_ids"] = frozenset(campos["workspace_ids"])
    return EscopoEfetivo(**campos)


def ctx_falso(escopo: EscopoEfetivo | None):
    """O `ctx` que uma tool recebe — só o que `escopo_da_chamada` e o progresso leem."""
    estado = SimpleNamespace(escopo=escopo) if escopo is not None else SimpleNamespace()
    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(state=estado)),
        report_progress=AsyncMock(),
    )


def cliente_mcp(app_mcp, segredo: str, *, host: str = "localhost:8000", cabecalhos: dict | None = None) -> Client:
    """Cliente MCP moderno falando com o app ASGI inteiro, por dentro do processo.

    O `host` precisa casar com `MCP_ALLOWED_HOSTS` (o default cobre
    `localhost:*`): o transporte recusa qualquer outro com 421.
    """
    extras = {"Authorization": f"Bearer {segredo}"} if segredo else {}
    extras.update(cabecalhos or {})
    return Client(
        streamable_http_client(
            f"http://{host}/mcp",
            http_client=httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app_mcp),
                base_url=f"http://{host}",
                headers=extras,
            ),
        )
    )


class RedisFalso:
    """Redis de mentira: só os comandos que o MCP usa, num dicionário.

    TTL é contado como "foi pedido tanto", não pelo relógio: os testes checam
    que o `EXPIRE` aconteceu e que o `retry_after_seconds` sai do TTL, não a
    passagem do tempo. "Passou tempo" se escreve à mão, em `ttls[chave]`.

    Também serve aos testes do contador de janela (`contar_na_janela`), que é
    um MULTI/EXEC com `EXPIRE ... NX`: daí o `pipeline()` e o `nx`.
    """

    def __init__(self) -> None:
        self.dados: dict[str, object] = {}
        self.ttls: dict[str, int] = {}
        self.chamadas: list[tuple] = []

    async def get(self, chave):
        self.chamadas.append(("get", chave))
        return self.dados.get(chave)

    async def mget(self, *chaves):
        self.chamadas.append(("mget", chaves))
        return [self.dados.get(chave) for chave in chaves]

    async def set(self, chave, valor, nx: bool = False, ex: int | None = None):
        self.chamadas.append(("set", chave, nx, ex))
        if nx and chave in self.dados:
            return None
        self.dados[chave] = valor
        if ex is not None:
            self.ttls[chave] = ex
        return True

    async def setex(self, chave, segundos, valor):
        self.chamadas.append(("setex", chave, segundos))
        self.dados[chave] = valor
        self.ttls[chave] = segundos
        return True

    async def incr(self, chave):
        self.chamadas.append(("incr", chave))
        novo = int(self.dados.get(chave, 0)) + 1
        self.dados[chave] = novo
        return novo

    async def incrby(self, chave, quanto):
        self.chamadas.append(("incrby", chave, quanto))
        novo = int(self.dados.get(chave, 0)) + int(quanto)
        self.dados[chave] = novo
        return novo

    async def decr(self, chave):
        self.chamadas.append(("decr", chave))
        novo = int(self.dados.get(chave, 0)) - 1
        self.dados[chave] = novo
        return novo

    async def expire(self, chave, segundos, nx: bool = False):
        self.chamadas.append(("expire", chave, segundos))
        if nx and (chave not in self.dados or chave in self.ttls):
            # NX: só arma o prazo de uma chave que existe e não tem nenhum.
            return False
        self.ttls[chave] = segundos
        return True

    def pipeline(self, transaction: bool = True):
        return _PipelineFalso(self, transaction)

    async def ttl(self, chave):
        self.chamadas.append(("ttl", chave))
        return self.ttls.get(chave, -1)

    async def exists(self, *chaves):
        self.chamadas.append(("exists", *chaves))
        return sum(1 for chave in chaves if chave in self.dados)

    async def delete(self, *chaves):
        self.chamadas.append(("delete", *chaves))
        apagadas = 0
        for chave in chaves:
            if self.dados.pop(chave, None) is not None:
                apagadas += 1
            self.ttls.pop(chave, None)
        return apagadas

    async def lrange(self, chave, inicio, fim):
        self.chamadas.append(("lrange", chave, inicio, fim))
        lista = self.dados.get(chave) or []
        if fim == -1:
            return list(lista[inicio:])
        return list(lista[inicio : fim + 1])


class _PipelineFalso:
    """O `pipeline()` do `RedisFalso`: cada comando entra na fila e `execute()`
    roda a fila inteira em ordem, sem ceder o loop no meio — que é, aqui, a
    atomicidade do MULTI/EXEC. Anota `("exec", [comandos])` em `chamadas` para
    o teste ver o que saiu junto na mesma transação."""

    def __init__(self, redis: RedisFalso, transacao: bool) -> None:
        self._redis = redis
        self._transacao = transacao
        self._fila: list[tuple] = []

    def __getattr__(self, nome):
        comando = getattr(self._redis, nome)

        def _enfileirar(*args, **kwargs):
            self._fila.append((nome, comando, args, kwargs))
            return self

        return _enfileirar

    async def execute(self):
        fila, self._fila = self._fila, []
        self._redis.chamadas.append(
            ("exec" if self._transacao else "pipeline", [nome for nome, *_ in fila])
        )
        return [await comando(*args, **kwargs) for _, comando, args, kwargs in fila]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self._fila = []
