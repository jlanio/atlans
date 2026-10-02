# app/services/workflow_version_service.py
# Gerenciamento de versões de workflows.

import copy

from sqlalchemy.orm.attributes import set_committed_value

from app.core.utils.logger import get_logger

from app.core.exceptions import WorkflowNotFoundError
from app.core.scheduling.hooks import apply_schedule_if_needed
from app.core.utils.encryption import (
    decrypt_workflow_connections,
    encrypt_workflow_connections,
)
from app.core.utils.redacao import redigir_definition
from app.crud.workflow_crud import WorkflowCRUD
from flow.utils.workflow_contract import _node_properties

_logger = get_logger(__name__)


def _has_substantial_changes(old_def: dict, new_def: dict) -> bool:
    """Retorna True apenas se houve mudanças substanciais na definição do workflow:
    adição/remoção de nós, alteração de conexões ou modificação de propriedades.
    Movimentação de nós (position) não é considerada substancial.
    """
    old_nodes: dict = {n["id"]: n for n in old_def.get("nodes", [])}
    new_nodes: dict = {n["id"]: n for n in new_def.get("nodes", [])}

    # Nós adicionados ou removidos
    if set(old_nodes.keys()) != set(new_nodes.keys()):
        return True

    # Conexões (edges) alteradas
    def _edge_key(e: dict) -> tuple:
        return (e.get("source"), e.get("target"), e.get("sourceHandle"), e.get("targetHandle"))

    old_edges = {_edge_key(e) for e in old_def.get("edges", [])}
    new_edges = {_edge_key(e) for e in new_def.get("edges", [])}
    if old_edges != new_edges:
        return True

    # Propriedades de algum nó alteradas. A definition PERSISTIDA/PUT é plana
    # (`{id, name, type, properties, position}` — sem wrapper `data`, ver
    # `montarPayloadDoGrafo` na web), então ler `node["data"]["properties"]`
    # via cada lado enxergava `{}` vs `{}` e uma edição só-de-propriedade (trocar
    # a cron, a URL de um HttpRequest, o SQL, o credential_id) nunca virava
    # versão. `_node_properties` aceita os dois formatos (o plano de produção e o
    # `data.properties` que só as fixtures montam).
    for node_id, new_node in new_nodes.items():
        old_props = _node_properties(old_nodes[node_id])
        new_props = _node_properties(new_node)
        if old_props != new_props:
            return True

    return False


async def list_versions(crud: WorkflowCRUD, id_hash: str):
    """Lista todas as versões de um workflow."""
    wf = await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")
    return await crud.get_versions(id_hash)


async def get_version(crud: WorkflowCRUD, id_hash: str, version_number: int):
    """Retorna uma versão específica com a definition REDIGIDA.

    Quem consome isto (hoje a tool `get_workflow_version` do MCP; antes, a rota
    `GET /workflows/{id}/versions/{n}`) não exige papel nenhum além de
    pertencer ao workspace — então entregava a `connectionString`
    em texto claro a qualquer `viewer`. Ler o histórico é legítimo para quem só
    lê; conhecer a senha do banco de produção não é, e restaurar uma versão
    tampouco precisa disso (o `restore` copia o blob cifrado sem abri-lo).

    A descriptografia continua acontecendo, e antes da redação, por um motivo:
    é ela que denuncia um token corrompido com um erro explícito. Redigir o
    valor cifrado direto esconderia a corrupção até a próxima execução.

    SEG: nada disso toca a linha VIVA da sessão. Era uma atribuição direta
    (`v.definition = decrypt(...)`) — qualquer commit posterior no mesmo request
    gravaria a connection string em texto claro na tabela de versões, desfazendo
    a criptografia em repouso de um histórico que ninguém mais reescreve.
    `set_committed_value` grava o valor como se tivesse vindo assim do banco: o
    flush não vê diferença nenhuma e não emite UPDATE.

    O `deepcopy` cobre a outra metade: `decrypt_workflow_connections` grava no
    dict que recebe, e esse dict é o mesmo objeto que a linha carregada guarda —
    o mesmo que `restore_version` chega a atribuir direto ao workflow. Trabalhar
    sobre uma cópia deixa o original cifrado para qualquer ponto que já tenha
    referência a ele.

    E o `expunge` fecha a última: sem ele a redação ficaria escrita na instância
    VIVA do identity map, e um `restore_version` na MESMA sessão receberia essa
    mesma instância de volta e gravaria `"<REDACTED>"` na definition do
    workflow — trocando o vazamento da credencial pela DESTRUIÇÃO silenciosa
    dela. Hoje a REST não alcança isso (cada request tem sessão própria, e
    nenhuma rota faz as duas coisas), mas as ferramentas do servidor MCP abrem
    UMA sessão e encadeiam operações nela: ler uma versão e restaurá-la é
    exatamente o par que cairia nessa armadilha. Desanexada, a linha serializa
    igual e um `get_version` seguinte relê o cifrado do banco.
    """
    v = await crud.get_version(id_hash, version_number)
    if not v:
        raise WorkflowNotFoundError(
            f"Versão {version_number} do workflow {id_hash} não encontrada"
        )
    try:
        em_claro = decrypt_workflow_connections(copy.deepcopy(v.definition))
    except Exception as e:
        _logger.error(
            "Falha ao descriptografar versão %s do workflow %s: %s",
            version_number, id_hash, e
        )
        raise ValueError(
            f"Não foi possível descriptografar a versão {version_number} do workflow {id_hash}."
        ) from e
    crud.db.expunge(v)
    set_committed_value(v, "definition", redigir_definition(em_claro))
    return v


async def restore_version(crud: WorkflowCRUD, id_hash: str, version_number: int):
    """Restaura a definição do workflow para uma versão anterior.

    Restaurar troca a definition inteira — inclusive o ScheduleTrigger. Sem
    sincronizar os agendamentos, voltar para uma versão com outro cron (ou sem
    nó de agendamento nenhum) deixava o Schedule antigo valendo no banco: o
    canvas mostrava uma coisa e o AsyncScheduler disparava por outra. É o mesmo
    "scheduler zumbi" que `update_workflow` já fecha no save normal.
    """
    v = await crud.get_version(id_hash, version_number)
    if not v:
        raise WorkflowNotFoundError(
            f"Versão {version_number} do workflow {id_hash} não encontrada"
        )
    wf = await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")
    # Snapshot da versão atual antes de restaurar.
    #
    # `get_by_hash` (sem decrypt) NÃO garante que `wf.definition` esteja
    # cifrada: a dependency desta rota já chamou `get_workflow_by_hash`, que faz
    # `wf.definition = decrypt_workflow_connections(...)` — mutação in place na
    # linha viva. Sendo a mesma sessão, aqui volta o MESMO objeto Python, já em
    # claro, e o snapshot gravaria a credencial legível em `workflow_versions`.
    # Cifrar explicitamente resolve nos dois estados, porque
    # `encrypt_workflow_connections` pula o que já começa com `gAAAA`. Mesmo
    # remédio de `update_workflow` e de `workflow_move_service._aplicar`.
    await crud.create_version(
        workflow_hash=id_hash,
        definition=encrypt_workflow_connections(copy.deepcopy(wf.definition or {})),
        change_note=f"Auto-snapshot antes de restaurar para versão {version_number}",
    )
    # Restaura: a definição armazenada na versão já está criptografada
    wf = await crud.update(wf, {"definition": v.definition})

    # A definition criptografada vai para o hook como está, de propósito: ele lê
    # apenas `properties` do nó ScheduleTrigger, que não é cifrado, e
    # `decrypt_workflow_connections` grava no dict recebido — descriptografar
    # aqui marcaria a linha como suja e o commit seguinte gravaria a connection
    # string em texto claro.
    #
    # Best-effort como nos demais call sites: falhar no agendamento não pode
    # desfazer uma restauração já commitada.
    #
    # Mas engolir em silêncio também não serve: `update_workflow` devolve
    # `schedule_notices` justamente para a tela poder dizer "restaurei, e o cron
    # não sincronizou". Sem isso, quem restaura uma versão com agendamento vê
    # sucesso e descobre dias depois que a rotina parou — o sintoma de
    # agendamento quebrado é o silêncio.
    #
    # `schedule_notices` é atributo TRANSIENTE no objeto ORM, não coluna: um
    # `db.refresh` o apaga. Por isso ele é setado por último, e quem lê o
    # capta na hora (`WorkflowRead.schedule_notices`).
    schedule_notices = []
    try:
        schedule_notices = await apply_schedule_if_needed(wf, wf.definition, crud.db) or []
    except Exception as exc:
        _logger.warning(
            "Falha ao sincronizar agendamento ao restaurar versão %s do workflow %s: %s",
            version_number, id_hash, exc,
        )
        schedule_notices = [
            "O agendamento não pôde ser sincronizado com a versão restaurada. "
            "Abra e salve o fluxo para tentar de novo."
        ]

    wf.schedule_notices = schedule_notices
    return wf
