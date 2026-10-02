# tests/unit/test_nos_renomeados.py
"""Fluxos salvos com nomes antigos de nós (renomeação "sem shim" de 27/07).

Em 25/09 o TESTE_BPA, agendado, falhava todo dia na partida com "Node
'DriveTrigger' não encontrado" — o nó tinha virado `DataInput` e ninguém
migrou as definições salvas. O Geoserver (com `ArtifactOutput`) estava igual.
"""

from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.services.nos_renomeados import migrar_definicao, migrar_nos
from flow.nodes.contrato import NOMES_ANTIGOS, NOS_REMOVIDOS, dica_de_no_desconhecido


def _definicao(*nos):
    return {"nodes": list(nos), "edges": [{"source": "a", "target": "b"}]}


# ── A reescrita de uma definição ─────────────────────────────────────────────

def test_drive_trigger_vira_data_input_lendo_do_drive():
    antes = _definicao(
        {"id": "a", "name": "DriveTrigger", "properties": {"driveFileId": "f-1", "crs": "EPSG:4674"}},
        {"id": "b", "name": "Buffer", "properties": {"distance": 10}},
    )

    depois, trocas = migrar_definicao(antes)

    assert trocas == [("a", "DriveTrigger", "DataInput")]
    assert depois["nodes"][0] == {
        "id": "a", "name": "DataInput", "alias": "DriveTrigger",
        "properties": {"driveFileId": "f-1", "crs": "EPSG:4674", "context": "drive"},
    }
    assert depois["nodes"][1] == antes["nodes"][1]
    assert depois["edges"] == antes["edges"]
    # O original não é tocado: quem chama decide se grava.
    assert antes["nodes"][0]["name"] == "DriveTrigger"


def test_artifact_output_protegido_continua_protegido():
    """No ArtifactOutput a credencial protegia o download; no DataOutput o
    padrão é público e a credencial só vale com isPublic=False. Renomear sem
    isso publicaria um artefato que era protegido."""
    antes = _definicao({"id": "a", "name": "ArtifactOutput", "properties": {
        "label": "resultado", "credential_id": "cred-1", "destination": "artifacts",
    }})

    depois, _ = migrar_definicao(antes)

    props = depois["nodes"][0]["properties"]
    assert depois["nodes"][0]["name"] == "DataOutput"
    assert props["isPublic"] is False
    assert props["credential_id"] == "cred-1"
    assert props["context"] == "artifacts" and "destination" not in props


def test_artifact_output_sem_credencial_continua_publico():
    depois, _ = migrar_definicao(_definicao({"id": "a", "name": "ArtifactOutput", "properties": {
        "label": "r", "credential_id": "", "destination": "drive",
    }}))

    props = depois["nodes"][0]["properties"]
    assert "isPublic" not in props            # default do DataOutput: público, como era
    assert props["context"] == "drive"


def test_nome_em_data_tambem_e_migrado():
    depois, trocas = migrar_definicao(_definicao(
        {"id": "a", "data": {"name": "DriveTrigger", "properties": {"driveFileId": "f"}}},
    ))

    assert trocas == [("a", "DriveTrigger", "DataInput")]
    assert depois["nodes"][0]["data"]["name"] == "DataInput"
    assert depois["nodes"][0]["data"]["properties"]["context"] == "drive"


def test_e_idempotente():
    uma_vez, _ = migrar_definicao(_definicao({"id": "a", "name": "DriveTrigger", "properties": {}}))

    de_novo, trocas = migrar_definicao(uma_vez)

    assert trocas == [] and de_novo is uma_vez


@pytest.mark.parametrize("definicao", [None, "texto", {}, {"nodes": "x"}, {"nodes": [None, 3]}])
def test_definicao_estranha_nao_quebra(definicao):
    assert migrar_definicao(definicao) == (definicao, [])


# ── As expressões que citam o nó migrado ─────────────────────────────────────

def _renderizar(texto: str, contexto: dict) -> str:
    from flow.utils.expression_service import ExpressionService
    return ExpressionService().render(texto, contexto)


def test_expressoes_que_citam_o_no_continuam_resolvendo():
    """Sem alias válido (o editor grava o rótulo "Drive de arquivos"), os outros
    nós citam o nó pelo NOME. Trocar o nome sem fixar o alias quebraria
    `{{ DriveTrigger... }}` ("undefined") e — pior — mandaria `$DriveTrigger...`
    como TEXTO para o nó seguinte, sem erro nenhum."""
    antes = _definicao(
        {"id": "a", "name": "DriveTrigger", "alias": "Drive de arquivos",
         "properties": {"driveFileId": "f-1"}},
        {"id": "b", "name": "SendEmail", "alias": "Aviso", "properties": {
            "subject": "Chegou $DriveTrigger.metadata.original_name",
            "body": "id={{ DriveTrigger.metadata.drive_file_id }} "
                    "e {{ DriveTrigger.metadata['drive_file_id'] }}",
            "params": {"ids": ["$DriveTrigger.metadata.drive_file_id"]},
            "outro": "{{ MeuDriveTrigger.metadata.drive_file_id }}",
        }},
    )

    depois, trocas = migrar_definicao(antes)

    no = depois["nodes"][0]
    assert (no["name"], no["alias"]) == ("DataInput", "DriveTrigger")
    from flow.core.aliases import resolve_alias
    assert resolve_alias(no) == "DriveTrigger"   # como o executor o registra

    props = depois["nodes"][1]["properties"]
    assert props["subject"] == "Chegou $DriveTrigger.metadata.original_name"
    assert props["params"] == {"ids": ["$DriveTrigger.metadata.file_id"]}
    assert props["outro"] == "{{ MeuDriveTrigger.metadata.drive_file_id }}"   # outro nó
    assert ("b", "metadata.drive_file_id", "metadata.file_id") in trocas

    # O que o DataInput entrega de verdade (flow/nodes/datasource/data_input.py).
    saida = {"DriveTrigger": {"metadata": {"file_id": "f-1", "original_name": "x.geojson"}}}
    assert _renderizar(props["subject"], saida) == "Chegou x.geojson"
    assert _renderizar(props["body"], saida) == "id=f-1 e f-1"


def test_formas_de_subscrito_e_get_tambem_sao_reescritas():
    depois, _ = migrar_definicao(_definicao(
        {"id": "a", "name": "DriveTrigger", "properties": {"driveFileId": "f-1"}},
        {"id": "b", "name": "SendEmail", "properties": {
            "um": "{{ DriveTrigger['metadata']['drive_file_id'] }}",
            "dois": "{{ DriveTrigger.metadata.get('drive_file_id') }}",
            "tres": '{{ DriveTrigger["metadata"].get( "drive_file_id") }}',
        }},
    ))

    props = depois["nodes"][1]["properties"]
    assert props == {
        "um": "{{ DriveTrigger['metadata']['file_id'] }}",
        "dois": "{{ DriveTrigger.metadata.get('file_id') }}",
        "tres": '{{ DriveTrigger["metadata"].get( "file_id") }}',
    }
    # O `.get()` antigo não quebrava: rendia None em silêncio. Agora resolve.
    saida = {"DriveTrigger": {"metadata": {"file_id": "f-1"}}}
    assert [_renderizar(v, saida) for v in props.values()] == ["f-1", "f-1", "f-1"]


def test_o_que_o_comando_nao_reescreve_sai_para_revisar():
    """`named.X`, `nodes['id']`, entrada mapeada e código Python citam a saída
    sem o alias na frente — reescrever às cegas quebraria outra coisa."""
    from app.services.nos_renomeados import sobras_para_revisar

    depois, _ = migrar_definicao(_definicao(
        {"id": "a", "name": "DriveTrigger", "properties": {"driveFileId": "f-1"}},
        {"id": "b", "name": "PythonScript", "properties": {
            "code": "fid = inputs['metadata']['drive_file_id']",
        }},
        {"id": "c", "name": "SendEmail", "properties": {"body": "{{ named.DriveTrigger.metadata.drive_file_id }}"}},
        {"id": "d", "name": "SendEmail", "properties": {"body": "{{ DriveTrigger.metadata.drive_file_id }}"}},
    ))

    assert sobras_para_revisar(depois) == ["b", "c"]   # o "d" foi reescrito


def test_alias_customizado_fica_e_as_expressoes_dele_sao_reescritas():
    depois, trocas = migrar_definicao(_definicao(
        {"id": "a", "name": "DriveTrigger", "alias": "Entrada", "properties": {"driveFileId": "f"}},
        {"id": "b", "name": "PythonScript", "properties": {
            "code": "x = '{{ Entrada.metadata.drive_file_id }}'",
            "nota": "$DriveTrigger.metadata.drive_file_id",   # não é este nó
        }},
    ))

    assert depois["nodes"][0]["alias"] == "Entrada"
    props = depois["nodes"][1]["properties"]
    assert props["code"] == "x = '{{ Entrada.metadata.file_id }}'"
    assert props["nota"] == "$DriveTrigger.metadata.drive_file_id"
    assert trocas == [
        ("a", "DriveTrigger", "DataInput"),
        ("b", "metadata.drive_file_id", "metadata.file_id"),
    ]


def test_artifact_output_tambem_mantem_o_nome_pelo_qual_e_citado():
    depois, _ = migrar_definicao(_definicao(
        {"id": "a", "name": "ArtifactOutput", "alias": "Saída de Artefato", "properties": {}},
    ))

    assert depois["nodes"][0]["alias"] == "ArtifactOutput"


# ── O comando sobre o banco ──────────────────────────────────────────────────

@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[Workflow.__table__, WorkflowVersion.__table__],
        )
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as sessao:
        yield sessao
    await engine.dispose()


async def _semear(db):
    quebrado = Workflow(id_hash="wf-bpa", name="TESTE_BPA", workspace_id="ws", definition=_definicao(
        {"id": "e5c072df", "name": "DriveTrigger", "properties": {"driveFileId": "f-1"}},
    ))
    saudavel = Workflow(id_hash="wf-ok", name="Ok", workspace_id="ws", definition=_definicao(
        {"id": "a", "name": "DataInput", "properties": {"driveFileId": "f-2"}},
    ))
    versao = WorkflowVersion(workflow_hash="wf-bpa", version_number=1, definition=_definicao(
        {"id": "x", "name": "ArtifactOutput", "properties": {"credential_id": "c"}},
    ))
    db.add_all([quebrado, saudavel, versao])
    await db.commit()


async def test_simulacao_lista_sem_gravar(db):
    await _semear(db)

    relatorio = await migrar_nos(db, aplicar=False)

    assert sorted((r["tipo"], r["workflow"]) for r in relatorio) == [
        ("versao", "wf-bpa"), ("workflow", "wf-bpa"),
    ]
    await db.rollback()
    wf = (await db.execute(select(Workflow).where(Workflow.id_hash == "wf-bpa"))).scalar_one()
    assert wf.definition["nodes"][0]["name"] == "DriveTrigger"


async def test_aplicar_grava_e_a_segunda_rodada_nao_acha_nada(db):
    await _semear(db)

    assert len(await migrar_nos(db, aplicar=True)) == 2

    wf = (await db.execute(select(Workflow).where(Workflow.id_hash == "wf-bpa"))).scalar_one()
    assert wf.definition["nodes"][0]["name"] == "DataInput"
    versao = (await db.execute(select(WorkflowVersion))).scalar_one()
    assert versao.definition["nodes"][0]["properties"]["isPublic"] is False
    assert await migrar_nos(db, aplicar=True) == []


async def test_nome_antigo_desabilitado_pelo_admin_e_avisado(db, monkeypatch):
    """A marca de "desabilitado" é por nome e não passa para o nó novo —
    desabilitar o DataOutput pararia também quem já o usa. O comando avisa."""
    from app.services import disabled_nodes_service
    from app.services.nos_renomeados import nomes_antigos_desabilitados

    async def _lista(_db):
        return {"ArtifactOutput": {"reason": "auditoria"}, "SendEmail": {}}

    monkeypatch.setattr(disabled_nodes_service, "list_disabled", _lista)

    assert await nomes_antigos_desabilitados(db) == ["ArtifactOutput"]


async def test_cli_simula_pede_backup_e_avisa_o_desabilitado(db, monkeypatch, capsys):
    from app import cli
    from app.services import disabled_nodes_service

    await _semear(db)

    @asynccontextmanager
    async def _sessao():
        yield db

    async def _lista(_db):
        return {"DriveTrigger": {}}

    monkeypatch.setattr("app.core.db.get_session_async", _sessao)
    monkeypatch.setattr(disabled_nodes_service, "list_disabled", _lista)

    assert await cli._migrar_nos(aplicar=False) == 0

    saida = capsys.readouterr().out
    assert "workflow wf-bpa (TESTE_BPA): DriveTrigger -> DataInput (no e5c072df)" in saida
    assert "ATENCAO: o admin desabilitou 'DriveTrigger'" in saida
    # O pg_dump não aceita o driver no esquema nem o `?ssl=` do asyncpg — e a
    # dica tem de funcionar colada em sh/dash, não só em bash.
    assert "U=$(printf %s \"$DATABASE_URL\" | sed -e 's/+asyncpg//' -e 's/?.*//')" in saida
    assert 'pg_dump "$U" -t workflows -t workflow_versions' in saida
    await db.rollback()
    wf = (await db.execute(select(Workflow).where(Workflow.id_hash == "wf-bpa"))).scalar_one()
    assert wf.definition["nodes"][0]["name"] == "DriveTrigger"   # simulação não grava


async def test_cli_aponta_o_que_revisar_a_mao(db, monkeypatch, capsys):
    from app import cli
    from app.services import disabled_nodes_service

    db.add(Workflow(id_hash="wf-py", name="Com script", workspace_id="ws", definition=_definicao(
        {"id": "a", "name": "DriveTrigger", "properties": {"driveFileId": "f-1"}},
        {"id": "b", "name": "PythonScript", "properties": {"code": "x = inputs['metadata']['drive_file_id']"}},
    )))
    await db.commit()

    @asynccontextmanager
    async def _sessao():
        yield db

    async def _nada(_db):
        return {}

    monkeypatch.setattr("app.core.db.get_session_async", _sessao)
    monkeypatch.setattr(disabled_nodes_service, "list_disabled", _nada)

    await cli._migrar_nos(aplicar=False)

    assert "REVISAR a mao: no(s) b ainda citam drive_file_id" in capsys.readouterr().out


# ── O mapa e as mensagens ────────────────────────────────────────────────────

def test_todo_nome_antigo_aponta_para_um_no_que_existe():
    from flow.registry import NODE_REGISTRY

    for antigo, novo in NOMES_ANTIGOS.items():
        assert novo in NODE_REGISTRY, f"{antigo} aponta para {novo}, que não existe"
        assert antigo not in NODE_REGISTRY, f"{antigo} voltou a existir — tire do mapa"


def test_no_desconhecido_diz_para_onde_o_no_foi():
    """A falha diária do TESTE_BPA só dizia "não encontrado"; agora diz o que fazer."""
    from flow.factory import NodeFactory
    from flow.utils.definition_lint import lint_definition

    rel = lint_definition(
        [{"id": "n1", "name": "DriveTrigger", "type": "trigger", "parameters": {}}], [],
        registry_names={"DataInput"},
    )
    mensagem = rel.errors[0].message
    # O prefixo da factory continua à letra (é o que scripts/validar.py procura).
    assert mensagem.startswith("Node 'DriveTrigger' não encontrado para instância (id=n1).")
    assert "renomeado para 'DataInput'" in mensagem

    with pytest.raises(ValueError, match="renomeado para 'DataInput'"):
        NodeFactory().create({"id": "n1", "name": "DriveTrigger", "properties": {}})


def test_nome_que_nunca_existiu_mantem_a_mensagem_de_sempre():
    assert dica_de_no_desconhecido("NaoExiste") == ""


def test_todo_no_removido_saiu_mesmo_do_registro():
    from flow.registry import NODE_REGISTRY

    for nome in NOS_REMOVIDOS:
        assert nome not in NODE_REGISTRY, f"{nome} voltou a existir — tire do mapa"
        assert nome not in NOMES_ANTIGOS, f"{nome} está nos dois mapas"


def test_no_removido_diz_que_saiu_e_nao_sugere_typo():
    """Um fluxo salvo com o Cluster (removido no Lote 1) passou a falhar na
    construção — até com o nó num ramo que não roda. "Confira o nome exato no
    catálogo" mandava procurar um erro de digitação que não existe."""
    from flow.factory import NodeFactory
    from flow.utils.definition_lint import lint_definition

    rel = lint_definition(
        [{"id": "c1", "name": "Cluster", "type": "spatial", "parameters": {}}], [],
        registry_names={"Buffer"},
    )
    mensagem = rel.errors[0].message
    assert mensagem.startswith("Node 'Cluster' não encontrado para instância (id=c1).")
    assert "saiu do catálogo" in mensagem
    assert "Confira o nome exato" not in mensagem

    with pytest.raises(ValueError, match="saiu do catálogo"):
        NodeFactory().create({"id": "c1", "name": "Cluster", "properties": {}})


@pytest.mark.parametrize("shell", ["sh", "bash"])
def test_a_dica_de_pg_dump_limpa_a_url_em_sh_e_em_bash(shell):
    """A dica é colada num terminal qualquer — dash (o `sh` do Debian) não tem
    `${VAR/a/b}`, que era o que ela usava."""
    import shutil
    import subprocess

    if shutil.which(shell) is None:
        pytest.skip(f"{shell} indisponível")
    comando = "U=$(printf %s \"$DATABASE_URL\" | sed -e 's/+asyncpg//' -e 's/?.*//'); printf %s \"$U\""
    for url, esperado in [
        ("postgresql+asyncpg://u:p@db:5432/atlans?ssl=require", "postgresql://u:p@db:5432/atlans"),
        ("postgresql+asyncpg://u:p@db:5432/atlans", "postgresql://u:p@db:5432/atlans"),
    ]:
        r = subprocess.run([shell, "-c", comando], capture_output=True, text=True,
                           env={"DATABASE_URL": url, "PATH": "/usr/bin:/bin"}, timeout=10)
        assert r.stdout == esperado, (shell, url, r.stderr)
