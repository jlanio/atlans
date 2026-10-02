# tests/unit/test_versao_nao_vaza_connection_string.py
"""O historico de versoes guarda connection string CIFRADA — nos dois sentidos.

Ler: `get_version` fazia `v.definition = decrypt_workflow_connections(v.definition)`
numa linha VIVA da sessao. A atribuicao marca a linha como suja: qualquer commit
posterior no mesmo request gravava a connection string em TEXTO CLARO na tabela
`workflow_versions` — criptografia em repouso desfeita por um GET, num historico
que ninguem mais reescreve.

Escrever: `update_workflow` decifra a definition atual para compara-la com a
nova, e `decrypt_workflow_connections` MUTA o dict que recebe. O snapshot da
linha seguinte — o que o comentario do codigo chama de "snapshot criptografado" —
saia em texto claro pela mesma referencia. Era o mesmo vazamento pela porta
oposta, e nenhum teste o via: este arquivo cobria so a leitura, e o teste de
servico mocka justamente a funcao que muta.

Os testes rodam contra SQLite de verdade e Fernet de verdade: o que importa aqui
e o que sobra gravado depois do commit.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.utils.encryption import encrypt_workflow_connections
from app.crud.workflow_crud import WorkflowCRUD
from app.models.models import Schedule, Workflow, WorkflowGroup, WorkflowVersion
from app.schemas.workflow import WorkflowUpdate
from app.services.workflow_service import WorkflowService
from app.services.workflow_version_service import get_version, restore_version

# Credencial ficticia: precisa ter forma de connection string de verdade para o
# teste provar alguma coisa, e e justamente isso que o BasicAuthDetector marca.
SEGREDO = "postgresql://usuario:senha-secretissima@host:5432/base"  # pragma: allowlist secret


def _definition(conn: str = SEGREDO) -> dict:
    return {
        "nodes": [
            {
                "id": "n1",
                "type": "action",
                "name": "PostgresQuery",
                "properties": {"connectionString": conn},
            }
        ]
    }


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[
                WorkflowGroup.__table__,
                Workflow.__table__,
                WorkflowVersion.__table__,
                # `update_workflow` sincroniza agendamento no fim; sem a tabela o
                # erro seria engolido pelo try/except de la e o teste passaria a
                # exercitar um caminho diferente do de producao.
                Schedule.__table__,
            ],
        )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    async with AsyncSession(engine) as sessao:
        sessao.add(Workflow(id_hash="wf-1", name="wf", workspace_id="ws-1", definition={}))
        sessao.add(WorkflowVersion(
            workflow_hash="wf-1",
            version_number=1,
            definition=encrypt_workflow_connections(_definition()),
        ))
        await sessao.commit()
        yield sessao


async def _definition_no_banco(engine) -> dict:
    """Le a linha numa sessao NOVA — o identity map da outra nao serve de prova."""
    async with AsyncSession(engine) as outra:
        v = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.version_number == 1)
        )).scalar_one()
        return v.definition


async def test_get_version_devolve_a_definition_redigida(db):
    """A rota que consome isto nao exige papel: entregava a credencial a viewer.

    Ler o historico e legitimo para quem so le; conhecer a senha do banco de
    producao nao e. E restaurar tampouco precisa disso — o `restore` copia o
    blob cifrado sem abri-lo.
    """
    v = await get_version(WorkflowCRUD(db), "wf-1", 1)

    assert v.definition["nodes"][0]["properties"]["connectionString"] == "<REDACTED>"
    assert SEGREDO not in str(v.definition)
    # A forma continua inteira: o que se perde e o segredo, nao a versao.
    assert v.definition["nodes"][0]["id"] == "n1"
    assert v.definition["nodes"][0]["name"] == "PostgresQuery"


async def test_commit_depois_do_get_version_nao_grava_o_segredo_em_claro(db, engine):
    """A regressao. Antes, este commit persistia a connection string legivel."""
    await get_version(WorkflowCRUD(db), "wf-1", 1)
    await db.commit()

    gravado = (await _definition_no_banco(engine))["nodes"][0]["properties"]["connectionString"]
    assert gravado != SEGREDO
    assert gravado.startswith("gAAAA")


async def test_get_version_nao_suja_a_sessao(db):
    """Nem chega a existir UPDATE pendente para um commit alheio carregar junto."""
    await get_version(WorkflowCRUD(db), "wf-1", 1)

    assert not db.dirty


async def test_update_workflow_grava_o_snapshot_ainda_cifrado(db, engine):
    """A regressao do outro lado: ESCREVER a versao.

    `update_workflow` pega `wf` por `get_by_hash` (sem decrypt) exatamente para
    nao sujar a sessao — e o comentario no codigo diz isso. Na linha seguinte
    chamava `decrypt_workflow_connections(wf.definition)`, que MUTA o dict e
    devolve o mesmo objeto: dali em diante `wf.definition` estava em claro, e o
    `definition=wf.definition` do snapshot gravava a credencial legivel em
    `workflow_versions`.
    """
    db.add(Workflow(
        id_hash="wf-2",
        name="fluxo",
        workspace_id="ws-1",
        definition=encrypt_workflow_connections(_definition()),
    ))
    await db.commit()

    # Muda o conjunto de ids de no: e o que `_has_substantial_changes` exige
    # para versionar. Sem isso nao ha snapshot e o teste nao prova nada.
    nova = {"nodes": [{"id": "n2", "type": "action", "name": "Outro", "properties": {}}]}
    await WorkflowService(db).update_workflow("wf-2", WorkflowUpdate(definition=nova), updated_by_id="u-1")

    async with AsyncSession(engine) as outra:
        versao = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.workflow_hash == "wf-2")
        )).scalar_one()

    gravado = versao.definition["nodes"][0]["properties"]["connectionString"]
    assert SEGREDO not in str(versao.definition)
    assert gravado.startswith("gAAAA")


async def test_snapshot_cifrado_mesmo_com_a_sessao_ja_decifrada(db, engine):
    """O caso que o teste acima NAO cobria — e que e o da rota real.

    `update_workflow` busca com `get_by_hash` (sem decrypt) e o comentario no
    codigo dizia que isso bastava. Nao basta: a dependency da rota
    (`get_accessible_workflow_with_role`) ja chamou `get_workflow_by_hash`, que
    faz `wf.definition = decrypt_workflow_connections(...)` — mutacao in place
    na linha VIVA. Sendo a mesma sessao, `get_by_hash` devolve o MESMO objeto
    Python, ja em claro, e copia-lo so duplica o texto claro.

    Chamar `get_workflow_by_hash` antes reproduz exatamente o estado que a
    dependency deixa. E preciso guardar a referencia: o identity map e fraco, e
    sem alguem segurando o objeto o SELECT seguinte traz a linha cifrada do
    banco — foi assim que o defeito passou despercebido.
    """
    svc = WorkflowService(db)
    db.add(Workflow(
        id_hash="wf-3",
        name="fluxo",
        workspace_id="ws-1",
        definition=encrypt_workflow_connections(_definition()),
    ))
    await db.commit()

    vivo = await svc.get_workflow_by_hash("wf-3")          # o que a dependency faz
    assert vivo.definition["nodes"][0]["properties"]["connectionString"] == SEGREDO

    nova = {"nodes": [{"id": "n2", "type": "action", "name": "Outro", "properties": {}}]}
    await svc.update_workflow("wf-3", WorkflowUpdate(definition=nova), updated_by_id="u-1")

    async with AsyncSession(engine) as outra:
        versao = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.workflow_hash == "wf-3")
        )).scalar_one()

    assert SEGREDO not in str(versao.definition)
    assert versao.definition["nodes"][0]["properties"]["connectionString"].startswith("gAAAA")


async def test_restore_version_tambem_guarda_o_auto_snapshot_cifrado(db, engine):
    """O mesmo vazamento no segundo call site de `create_version`.

    `restore_version` tira um auto-snapshot do estado atual antes de restaurar,
    pela mesma rota e com a mesma dependency. Fechar so o `update_workflow`
    deixaria um restore repor a credencial legivel no historico.
    """
    svc = WorkflowService(db)
    db.add(Workflow(
        id_hash="wf-4",
        name="fluxo",
        workspace_id="ws-1",
        definition=encrypt_workflow_connections(_definition()),
    ))
    db.add(WorkflowVersion(
        workflow_hash="wf-4",
        version_number=1,
        definition=encrypt_workflow_connections(_definition("postgresql://a:b@c:5432/d")),
    ))
    await db.commit()

    vivo = await svc.get_workflow_by_hash("wf-4")          # a dependency de novo
    assert vivo.definition["nodes"][0]["properties"]["connectionString"] == SEGREDO

    await restore_version(WorkflowCRUD(db), "wf-4", 1)

    async with AsyncSession(engine) as outra:
        auto = (await outra.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_hash == "wf-4")
            .where(WorkflowVersion.version_number != 1)
        )).scalar_one()

    assert SEGREDO not in str(auto.definition)
    assert auto.definition["nodes"][0]["properties"]["connectionString"].startswith("gAAAA")


async def test_restore_depois_de_get_version_nao_grava_redacted(db, engine):
    """A redacao nao pode virar destruicao da credencial.

    `set_committed_value` escreve na instancia; sem desanexa-la, um
    `restore_version` na MESMA sessao receberia a mesma linha pelo identity map
    e gravaria `"<REDACTED>"` na definition do workflow — perda irreversivel do
    token cifrado. A REST nao alcanca isso (um request, uma sessao), mas as
    ferramentas do servidor MCP encadeiam operacoes numa sessao so.
    """
    v = await get_version(WorkflowCRUD(db), "wf-1", 1)
    assert v.definition["nodes"][0]["properties"]["connectionString"] == "<REDACTED>"

    await restore_version(WorkflowCRUD(db), "wf-1", 1)

    async with AsyncSession(engine) as outra:
        wf = (await outra.execute(
            select(Workflow).where(Workflow.id_hash == "wf-1")
        )).scalar_one()

    gravado = wf.definition["nodes"][0]["properties"]["connectionString"]
    assert gravado != "<REDACTED>"
    assert gravado.startswith("gAAAA")


async def test_definition_indecifravel_vira_erro_explicito(db, engine):
    """Token corrompido nao pode passar batido como se fosse texto normal."""
    async with AsyncSession(engine) as outra:
        v = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.version_number == 1)
        )).scalar_one()
        v.definition = _definition("gAAAAlixo-que-nao-decifra")
        await outra.commit()

    with pytest.raises(ValueError, match="descriptografar"):
        await get_version(WorkflowCRUD(db), "wf-1", 1)
