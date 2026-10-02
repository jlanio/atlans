# app/mcp/tools/acervo.py
"""
Tools do acervo: o histórico de um fluxo, a cópia dele, e o que ele produziu.

É o domínio que torna seguro deixar um agente editar um fluxo de produção. Sem
`restore_workflow_version`, um erro dele não tem desfazer; sem
`duplicate_workflow`, experimentar exige mexer no original.

Três decisões moldam o módulo:

- **Nenhum dos serviços daqui autoriza coisa alguma.** `list_versions`,
  `get_version`, `restore_version` e `duplicate_workflow` não conhecem papel
  nem workspace — na REST quem barra é o router. As quatro
  tools que apontam para UM workflow abrem com o par
  `carregar_workflow(decifrar=False)` + `exigir_papel`, e é essa dupla, não o
  serviço, que fecha a porta. O que o serviço confere é outra coisa: que as
  credenciais da definition gravada (cópia ou versão restaurada) estejam ao
  alcance de quem grava (SEG-12).
  `list_artifacts` é a exceção, pelo mesmo motivo que `get_run_artifacts`: ela
  não aponta para um workflow, então não há papel a conferir contra coisa
  nenhuma. O corte é `escopo.workspace_ids` dentro do WHERE, que já é a
  interseção entre os workspaces do usuário e o alcance do token — equivalente
  a exigir `viewer`, que é o menor papel que existe.
- **A listagem de versões faz a própria consulta.** `list_versions` devolve a
  definition inteira de cada versão; numa tool isso seriam N blobs cifrados
  lidos do banco para serem descartados. Aqui se seleciona só o que a pergunta
  precisa — mesmo motivo de `_contar_versoes` existir em `construcao.py`.
- **Nenhuma definition sai daqui sem passar pela redação.** A de uma versão já
  vem redigida do serviço; a que o `restore` devolve, não — ela volta cifrada
  do banco, e entregá-la crua seria despejar `gAAAA…` no contexto de quem lê.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from mcp.server.mcpserver import Context
from sqlalchemy import func, select

from app.core.authorization.workflow_access import exigir_papel
from app.core.exceptions import WorkflowNotFoundError
from app.core.rbac import ROLE_EDITOR, ROLE_VIEWER
from app.core.storage import presigned_get_async
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.core.utils.redacao import compactar_definition, redigir_definition
from app.crud.workflow_crud import WorkflowCRUD
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow, resolver_workspace
from app.mcp.saida import envelope, higienizar, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.models.workflow_version import WorkflowVersion
from app.services.artifact_service import listar_artefatos
from app.services.workflow_service import WorkflowService
from app.services.workflow_version_service import get_version
from flow.utils.workflow_contract import validate_subworkflow_references_against_db

# Teto da listagem de versões. Um fluxo muito editado acumula centenas de
# snapshots, e quem pergunta "o que mudou" quer os últimos.
MAX_VERSOES = 50

# Teto da listagem de artefatos por resposta — o mesmo orçamento de contexto das
# outras listagens do servidor.
MAX_ARTEFATOS = 100

# Validade da URL assinada, igual à das demais: o link é portador e viaja por
# uma conversa que pode ficar registrada.
VALIDADE_DO_LINK_S = 300

# Os dois recortes que a listagem de artefatos entende — os mesmos que a rota
# REST valida por `pattern`.
RECORTES = ("execution", "publication")

logger = get_logger("app.mcp.tools.acervo")

_MENSAGEM_PAPEL_LEITURA = "Requer papel 'viewer' ou superior neste workspace."
_MENSAGEM_PAPEL_ESCRITA = "Requer papel 'editor' ou superior neste workspace."


def _versao_nao_encontrada(numero: Any):
    return erro(
        "not_found",
        f"Este workflow não tem a versão {numero}.",
        "use list_workflow_versions(workflow_id) para ver as versões que existem",
    )


# ── Versões ──────────────────────────────────────────────────────────────────


@ferramenta
async def list_workflow_versions(
    ctx: Context, workflow_id: str, limit: int = MAX_VERSOES, offset: int = 0
) -> dict:
    """O histórico de snapshots de um workflow, do mais novo para o mais antigo.

    Devolve só o que identifica cada versão — número, nota da mudança e data.
    A definition de cada uma sai por `get_workflow_version(workflow_id, n)`, uma
    por vez e redigida: despejar o conteúdo de todas aqui custaria mais contexto
    do que qualquer pergunta sobre histórico justifica.

    Uma versão nasce quando `update_workflow` muda o conjunto de nós, e também
    logo antes de um `restore_workflow_version` — o auto-snapshot que torna o
    restore reversível. Ou seja: usar as tools deste domínio faz o histórico
    crescer, e por isso `offset` existe. Com `has_more: true`, a página seguinte
    é `offset = offset + returned`; sem isso, as versões mais antigas de um
    fluxo muito editado ficariam inalcançáveis por esta tool.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")
    teto = max(1, min(int(limit), MAX_VERSOES))
    salto = max(0, int(offset))

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL_LEITURA)
        id_hash = wf.id_hash

        # Consulta própria, e não `list_versions`: aquela traz a coluna
        # `definition` de cada linha — N blobs cifrados lidos do banco só para
        # serem descartados aqui. A pergunta é "que versões existem", e a
        # resposta cabe em três colunas.
        linhas = (
            await db.execute(
                select(
                    WorkflowVersion.version_number,
                    WorkflowVersion.change_note,
                    WorkflowVersion.created_at,
                )
                .where(WorkflowVersion.workflow_hash == id_hash)
                .order_by(WorkflowVersion.version_number.desc())
                .limit(teto + 1)
                .offset(salto)
            )
        ).all()

    cortou = len(linhas) > teto
    itens = [
        {"version_number": numero, "created_at": iso(criada)}
        for numero, _, criada in linhas[:teto]
    ]
    # A nota da mudança é escrita por gente: desce para `untrusted_data`, na
    # mesma ordem dos itens do topo.
    notas = [nota for _, nota, _ in linhas[:teto]]

    return envelope(
        {
            "workflow_id": id_hash,
            "items": itens,
            "returned": len(itens),
            "limit": teto,
            "offset": salto,
            "has_more": cortou,
        },
        change_notes=notas or None,
    )


@ferramenta
async def get_workflow_version(ctx: Context, workflow_id: str, version_number: int) -> dict:
    """Uma versão do histórico, com a definition REDIGIDA.

    Redigida sem exceção: o histórico guarda a connection string cifrada, e
    abri-la para quem lê entregaria a senha do banco de produção a qualquer
    membro do workspace. Restaurar não precisa disso — o restore copia o blob
    cifrado sem abri-lo.

    A forma da versão continua inteira: o que se perde é o segredo, não os nós.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL_LEITURA)
        id_hash = wf.id_hash

        try:
            versao = await get_version(WorkflowCRUD(db), id_hash, int(version_number))
        except WorkflowNotFoundError as exc:
            # O workflow já foi carregado acima, então aqui isto só pode ser a
            # VERSÃO. Sem traduzir, o erro chega sem dica — e a pergunta
            # seguinte de quem errou o número é sempre a mesma.
            raise _versao_nao_encontrada(version_number) from exc
        except ValueError as exc:
            # Token que não decifra. O serviço denuncia em vez de devolver texto
            # ilegível como se fosse conteúdo, e a tool não transforma isso em
            # "não encontrado": o dado existe, o que falhou foi abri-lo.
            raise erro(
                "internal_error",
                "A definition desta versão não pôde ser decifrada.",
                "a chave de criptografia pode ter mudado; procure o administrador",
            ) from exc

        # O objeto vem DESANEXADO do serviço (`expunge`), de propósito: sem
        # isso, um restore na mesma sessão pegaria esta instância redigida pelo
        # identity map e gravaria `<REDACTED>` na definition do workflow. O
        # preço é que nada pode ser lido por lazy load — tudo sai agora, do que
        # o SELECT já trouxe.
        numero = versao.version_number
        nota = versao.change_note
        criada = versao.created_at
        segura = compactar_definition(versao.definition or {})

    return envelope(
        {
            "workflow_id": id_hash,
            "version_number": numero,
            "created_at": iso(criada),
        },
        change_note=nota,
        definition=segura,
    )


@ferramenta
async def restore_workflow_version(
    ctx: Context, workflow_id: str, version_number: int
) -> dict:
    """Devolve o workflow ao estado de uma versão anterior.

    **É reversível.** Antes de restaurar, o estado atual vira um snapshot novo
    no histórico, então um restore errado se desfaz com outro restore — o número
    da versão criada volta em `snapshot_version`.

    O agendamento é ressincronizado a partir da definition restaurada: se a
    versão antiga tinha outro cron, o agendamento passa a ser o dela; se não
    tinha gatilho de agenda, ele é removido. Essa sincronia é best-effort no
    núcleo — se ela falhar, a restauração **ainda assim vale**, e a resposta não
    tem como avisar. Confirme com `get_workflow(workflow_id)` quando o fluxo
    depender de agendamento.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)
        id_hash = wf.id_hash

        antes = await _ultimo_numero_de_versao(db, id_hash)
        try:
            # Pelo serviço, e não pelo `restore_version` do módulo de versões: é
            # o serviço que confere as credenciais da versão contra quem restaura
            # (SEG-12) — a mesma guarda da REST.
            restaurado = await WorkflowService(db).restore_version(
                id_hash, int(version_number), restored_by=escopo.user_id,
            )
        except WorkflowNotFoundError as exc:
            raise _versao_nao_encontrada(version_number) from exc

        # `restore_version` grava o blob CIFRADO da versão no workflow, sem
        # abri-lo — é o que mantém a credencial protegida em repouso. Para SAIR
        # daqui, porém, ele precisa passar pela redação: entregar `gAAAA…` ao
        # chamador não informa nada e ainda custa contexto.
        segura = compactar_definition(redigir_definition(restaurado.definition or {}))
        nome = restaurado.name
        ativo = bool(restaurado.flag_ative)

        # A restauração já commitou neste ponto. A sincronia de agendamento que
        # vem depois dela é best-effort e engole a própria falha — mas se o que
        # falhou foi um statement de BANCO, a transação fica abortada e esta
        # consulta seguinte levantaria, transformando em "erro inesperado" uma
        # operação que DEU CERTO e está gravada. A docstring promete o
        # contrário, então o risco é da consulta, não da resposta.
        try:
            depois = await _ultimo_numero_de_versao(db, id_hash)
            indeterminado = False
        except Exception:  # noqa: BLE001 — qualquer falha aqui é só de leitura
            logger.warning(
                "Restauração de %s gravou, mas o número do snapshot não pôde ser lido.",
                id_hash, exc_info=True,
            )
            depois, indeterminado = None, True

    dados = {
        "workflow_id": id_hash,
        "restored_from_version": int(version_number),
        # O auto-snapshot só existe se o número subiu; se `create_version` não
        # chegou a gravar, dizer que existe mandaria o chamador restaurar uma
        # versão inexistente para desfazer.
        "snapshot_version": depois if depois and depois != antes else None,
        "is_active": ativo,
    }
    # Inserção condicional, e não `"hint": … if … else None`: o `envelope`
    # descarta chave nula apenas dentro de `untrusted_data`, então um
    # `"hint": None` no topo sobreviveria. `None` no campo acima quer dizer "não
    # houve snapshot"; esta dica é para o caso diferente — houve, mas não deu
    # para ler o número —, que sem ela ficaria indistinguível do primeiro.
    if indeterminado:
        dados["hint"] = (
            "a restauração foi gravada, mas o número do snapshot anterior não pôde ser "
            "lido; use list_workflow_versions(workflow_id) para encontrá-lo"
        )

    return envelope(dados, name=nome, definition=segura)


async def _ultimo_numero_de_versao(db, workflow_hash: str) -> Optional[int]:
    """O maior `version_number` do fluxo — como o CRUD o calcula para criar."""
    resultado = await db.execute(
        select(func.max(WorkflowVersion.version_number)).where(
            WorkflowVersion.workflow_hash == workflow_hash
        )
    )
    valor = resultado.scalar()
    return int(valor) if valor is not None else None


# ── Duplicar ─────────────────────────────────────────────────────────────────


@ferramenta
async def duplicate_workflow(
    ctx: Context, workflow_id: str, name: str | None = None
) -> dict:
    """Cria uma cópia do workflow, no MESMO workspace.

    Serve para experimentar sem arriscar o original: edite a cópia, execute,
    e o fluxo de produção fica intacto.

    O que **não** acompanha a cópia, e não é esquecimento: os pins (apontam para
    artefatos de execuções que esta cópia nunca teve), o estado do portal (uma
    cópia não nasce publicada porque o original estava) e o histórico de versões
    (ele descreve edições que não aconteceram aqui). O agendamento acompanha,
    mas **desligado** — duplicar costuma preceder uma edição, e nascer
    disparando sozinho dobraria a carga em silêncio.

    Sem `name`, a cópia recebe um nome derivado ("Cópia de X").
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)
        id_hash = wf.id_hash

        # A mesma checagem que a rota REST faz, e que o serviço NÃO faz: um
        # SubWorkflow referenciado pode ter sido desativado ou removido depois
        # que o original foi salvo. Sem ela, a cópia nasce quebrada e só falha
        # na execução, com erro bem menos claro do que a lista de referências.
        quebradas = await validate_subworkflow_references_against_db(
            wf.definition or {}, db, workspace_id=wf.workspace_id
        )
        if quebradas:
            # `higienizar` explícito: `erro()` só redige extra que seja STRING
            # (`erros.py`), e este é uma lista. As mensagens do validador ecoam
            # o `id` do nó e o hash do alvo — os dois escritos por quem edita o
            # fluxo —, então sem isto uma frase de comando (ou um segredo de
            # definição legada) sairia verbatim no corpo do erro e no log do
            # SDK. Mesmo tratamento que `construcao.py` dá ao `report`.
            raise erro(
                "validation",
                "O workflow referencia sub-fluxos que não estão utilizáveis.",
                "corrija as referências no original antes de duplicar",
                errors=higienizar(
                    [{"path": "definition.nodes", "message": m} for m in quebradas]
                ),
            )

        # Autoria vem de quem chamou — "quem criou isto" é a primeira pergunta
        # de quem encontra um fluxo duplicado meses depois. O carimbo era feito
        # aqui à mão porque o serviço não o fazia; agora ele faz, e a rota REST
        # carimba pela mesma porta. Uma regra só, nos dois caminhos.
        copia = await WorkflowService(db).duplicate_workflow(
            id_hash, name, duplicated_by=escopo.user_id,
        )
        await db.commit()

        dados = {
            "id": copia.id_hash,
            "workspace_id": copia.workspace_id,
            "copied_from": id_hash,
            "is_active": bool(copia.flag_ative),
            "created_by_id": copia.created_by_id,
        }
        nome_da_copia = copia.name

    return envelope(dados, name=nome_da_copia)


# ── Artefatos do workspace ───────────────────────────────────────────────────


@ferramenta
async def list_artifacts(
    ctx: Context,
    workspace_id: str | None = None,
    workflow_id: str | None = None,
    run_id: str | None = None,
    fmt: str | None = None,
    search: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Os arquivos que as execuções de um workspace produziram.

    Diferente de `get_run_artifacts`, que responde "o que ESTA execução gerou",
    esta responde "o que existe no acervo" — com filtros por fluxo, execução,
    formato e texto, e paginação.

    `kind` recorta entre `execution` (saída de execução) e `publication`
    (camadas publicadas no portal).

    Cada item diz se dá para baixar (`available`). **Um artefato indisponível
    não é erro**: conteúdo que ficou no executor e nunca subiu para a nuvem
    aparece com `available: false` e a explicação, porque ele existe — o que não
    existe é a possibilidade de baixá-lo por aqui.

    Nem todo item disponível traz link. `protected: true` marca o artefato cujo
    download exige credencial pela aplicação, e ele sai com `available: true` e
    **sem** URL: a URL pré-assinada é portadora, e assiná-la passaria por cima
    justamente da credencial que a aplicação exige. O que falta ali é o direito,
    não o conteúdo — e o `hint` de cada item diz qual dos casos é.

    Artefatos de pin-cache ficam de fora: são estado interno do motor, não saída
    que alguém pediu.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")
    teto = max(1, min(int(limit), MAX_ARTEFATOS))

    # A rota REST recusa `kind` fora do par com 422 (`pattern=` no `Query`); aqui
    # não há Pydantic na borda, e o `if/elif` do núcleo não tem `else`: um valor
    # errado — "publications" no plural, "Execution" com maiúscula — viraria
    # "sem filtro", devolvendo o acervo INTEIRO sem nada dizer que o recorte foi
    # ignorado. Quem pediu publicações leria execuções como publicações.
    if kind is not None and kind not in RECORTES:
        raise erro(
            "validation",
            f"`kind` aceita {' ou '.join(sorted(RECORTES))}, ou nada para não recortar.",
            "use kind='publication' para as camadas do portal e kind='execution' para o resto",
            errors=[{"path": "kind", "message": f"valor não reconhecido: {kind!r}"}],
        )

    async with infra.sessao() as db:
        alvo_workspace = (
            await resolver_workspace(db, escopo, workspace_id)
            if workspace_id is not None
            else None
        )
        alvo_workflow = None
        if workflow_id is not None:
            # Resolvido aqui, e não passado cru ao núcleo, pelos mesmos dois
            # motivos de `list_runs`: para que a tool aceite o NOME do workflow
            # como todas as outras — é o que `docs/mcp.md` promete em
            # "convenções de entrada, valendo para todas" —, e para que um id
            # fora do alcance responda o mesmo "não encontrado" de sempre, em
            # vez de uma lista vazia que o chamador leria como "nunca produziu
            # nada".
            wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
            exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL_LEITURA)
            alvo_workflow = wf.id_hash

        pagina = await listar_artefatos(
            db,
            sorted(escopo.workspace_ids),
            workspace_id=alvo_workspace,
            workflow_id=alvo_workflow,
            run_id=run_id,
            fmt=fmt,
            search=search,
            kind=kind,
            limit=teto,
            offset=max(0, int(offset)),
            incluir_chave=True,
        )

    itens = []
    nomes = []
    expira_em = iso(utc_now_naive() + timedelta(seconds=VALIDADE_DO_LINK_S))
    for bruto in pagina["items"]:
        local = bruto.get("content_location") or "minio"
        chave = bruto.get("s3_key")
        # Duas condições, como em `get_run_artifacts`: sem `s3_key` não há
        # objeto a assinar, mesmo que a localidade diga "minio" — artefato
        # antigo ou gravação interrompida.
        disponivel = local != "executor" and bool(chave)
        protegido = bool(bruto.get("protected"))

        item = {
            "id": bruto["id_hash"],
            "workspace_id": bruto["workspace_id"],
            "workflow_id": bruto["workflow_id"],
            "run_id": bruto["run_id"],
            "format": bruto["format"],
            "size_bytes": bruto["size_bytes"],
            "features": bruto["features"],
            "protected": protegido,
            "is_published": bruto["is_published"],
            "content_location": local,
            "created_at": bruto["created_at"],
            # `content_expires_at`, e não `expires_at`: na tool irmã
            # `get_run_artifacts` essa chave é o prazo do LINK, e aqui seria o
            # da retenção do arquivo. Duas coisas com ordens de grandeza
            # diferentes — minutos contra dias — sob o mesmo nome fariam um
            # cliente concluir que o link dura uma semana.
            "content_expires_at": bruto["expires_at"],
            "available": disponivel,
        }
        if disponivel and not protegido:
            item["download_url"] = await presigned_get_async(
                chave, expires=VALIDADE_DO_LINK_S, filename=bruto["filename"]
            )
            item["url_expires_at"] = expira_em
        else:
            item["hint"] = _por_que_sem_link(local, disponivel, protegido)

        itens.append(item)
        # Texto de gente, na mesma ordem dos itens. `output_key` entra aqui
        # junto dos outros dois: é o rótulo que a pessoa escreveu no nó de
        # saída, não um valor que a plataforma gera — e no topo ele escaparia
        # do `higienizar` do `envelope`. É o que `get_run_artifacts` já faz.
        nomes.append({
            "filename": bruto["filename"],
            "workflow_name": bruto["workflow_name"],
            "output_key": bruto["output_key"],
        })

    return envelope(
        {
            "items": itens,
            "total": pagina["total"],
            "limit": pagina["limit"],
            "offset": pagina["offset"],
            "has_more": pagina["has_more"],
            "expires_in_seconds": VALIDADE_DO_LINK_S,
        },
        names=nomes or None,
    )


def _por_que_sem_link(local: str, disponivel: bool, protegido: bool) -> str:
    """UMA explicação, em cascata — a mais específica que couber."""
    if local == "executor":
        return (
            "o conteúdo deste artefato permanece no executor e nunca foi enviado para a "
            "nuvem: não há download pela plataforma"
        )
    if not disponivel:
        return "este artefato não tem conteúdo no storage"
    return "este artefato exige credencial para download; baixe pela aplicação"


def registrar(server) -> None:
    """Registra as tools deste domínio."""
    server.tool(
        name="list_workflow_versions",
        title="Histórico de versões",
        description=(
            "Snapshots de um workflow, do mais novo para o mais antigo: número, nota da "
            "mudança e data. A definition de cada versão sai por get_workflow_version, uma "
            "por vez e redigida."
        ),
        annotations=anotacoes("list_workflow_versions"),
    )(list_workflow_versions)

    server.tool(
        name="get_workflow_version",
        title="Uma versão do histórico",
        description=(
            "A definition de uma versão anterior, sempre REDIGIDA: o histórico guarda "
            "credencial cifrada, e abri-la entregaria a senha do banco a qualquer membro. "
            "Restaurar não precisa disso — o restore copia o blob sem abri-lo."
        ),
        annotations=anotacoes("get_workflow_version"),
    )(get_workflow_version)

    server.tool(
        name="restore_workflow_version",
        title="Restaurar uma versão",
        description=(
            "Devolve o workflow ao estado de uma versão anterior. É REVERSÍVEL: o estado "
            "atual vira um snapshot novo antes da troca, e o número dele volta na resposta. "
            "O agendamento é ressincronizado pela definition restaurada, best-effort."
        ),
        annotations=anotacoes("restore_workflow_version"),
    )(restore_workflow_version)

    server.tool(
        name="duplicate_workflow",
        title="Duplicar workflow",
        description=(
            "Cria uma cópia no MESMO workspace, para experimentar sem arriscar o original. "
            "Pins, estado do portal e histórico de versões NÃO acompanham; o agendamento "
            "acompanha desligado. Sub-fluxo quebrado é recusado antes de copiar."
        ),
        annotations=anotacoes("duplicate_workflow"),
    )(duplicate_workflow)

    server.tool(
        name="list_artifacts",
        title="Artefatos do workspace",
        description=(
            "Os arquivos que as execuções produziram, com filtro por fluxo, execução, "
            "formato e texto. Diferente de get_run_artifacts, que olha uma execução só. "
            "Artefato que ficou no executor aparece com available:false e explicação, não "
            "como erro. URL de download vale 5 minutos."
        ),
        annotations=anotacoes("list_artifacts"),
    )(list_artifacts)
