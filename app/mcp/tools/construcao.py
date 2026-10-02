# app/mcp/tools/construcao.py
"""
Tools de construção: validar, criar, atualizar, (des)ativar e publicar.

São as cinco ferramentas que ESCREVEM no acervo — e, por isso, as que carregam
três cuidados que as de leitura não precisam ter:

1. **Segredo não entra.** Toda definition recebida passa por
   `definition_contem_segredo` ANTES de qualquer outra coisa. Uma senha em
   `connectionString` ou um `Authorization` em `headers` gravados na definition
   ficariam cifrados no banco, mas continuariam sendo um segredo que viajou por
   um transporte, um histórico de cliente e um log — e que a redação da saída
   depois apagaria, dando a falsa impressão de que ele não está lá. A recusa
   cita o CAMINHO do campo e nunca o valor (`erros.erro_de_segredo`).
2. **Validar antes de gravar é o default.** `validate_first=True` roda o
   núcleo de validação (`validate_service.validar_definicao`) e recusa a
   gravação quando o relatório traz erros. `force=True` passa por cima dos
   erros comuns — mas nunca dos FATAIS (nó inexistente, id duplicado, ciclo,
   `credential_id` que não é UUID): esses `validar_definicao` levanta como
   `DefinicaoInvalidaError` antes de montar relatório nenhum, e gravar uma
   definição que o executor nem constrói seria criar um workflow que só pode
   falhar.
3. **A autoria vem da identidade, nunca do corpo.** `created_by_id` e
   `updated_by_id` são carimbados com o dono do token. `WorkflowCreate` não é
   `extra="forbid"` e tem `id_hash` com default, então jogar um dicionário do
   cliente lá dentro deixaria o chamador escolher o id do workflow e o nome de
   quem o criou; aqui o que chega do cliente são parâmetros nomeados e o que
   vai ao service é uma lista branca.

A ordem "sessão → resolve → papel → fecha → valida → sessão → grava" é
deliberada: `validar_definicao` abre a PRÓPRIA sessão, e mantê-la aninhada
dentro da nossa empilharia duas sessões sobre a mesma conexão. O custo é uma
janela mínima entre a checagem de papel e a escrita, que o banco fecha de todo
jeito (as chaves e o índice único valem no INSERT).
"""
from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.authorization.workflow_access import exigir_papel, get_workspace_member_role
from app.core.rbac import ROLE_EDITOR
from app.core.utils.redacao import definition_contem_segredo, params_schema_contem_segredo
from app.mcp import infra
from app.mcp.erros import erro, erro_de_segredo
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow, resolver_workspace
from app.mcp.saida import envelope, higienizar
from app.mcp.tools.base import anotacoes, ferramenta
# `_share_url` é da mesma família de tools e é a ÚNICA definição da URL absoluta
# do portal. Copiá-la para cá por causa do underscore criaria duas verdades sobre
# o mesmo endereço — e a que envelhecesse seria descoberta por quem clicasse.
from app.mcp.tools.workflows import _share_url
from app.models.workflow_version import WorkflowVersion
from app.schemas.workflow import WorkflowUpdate
from app.services import validate_service
from app.services.workflow_service import WorkflowService

_MENSAGEM_PAPEL = "Requer papel 'editor' ou superior neste workspace."

# Os três estados do portal, na mesma ordem em que a tela os oferece. É a mesma
# lista do `pattern` de `PortalSettingsSchema` na REST.
ACESSOS_DO_PORTAL = ("disabled", "public", "private")

# Teto de itens de erro de forma repassados ao cliente: um corpo muito errado
# rende dezenas de itens, e a lista inteira só afoga a primeira linha, que é a
# que interessa.
_MAX_ERROS_DE_FORMA = 20


def _erros_de_forma(exc: ValidationError) -> list:
    """`[{path, message}]` a partir de um erro do Pydantic — sem o valor recebido.

    O `str(exc)` do Pydantic ecoa o INPUT de cada campo reprovado, e o input
    aqui é a definition que o cliente mandou: devolvê-lo inteiro faria uma
    senha gravada no lugar errado dar mais uma volta pelo transporte e pelo log
    do SDK. Caminho e motivo bastam para corrigir.
    """
    itens = []
    for detalhe in exc.errors()[:_MAX_ERROS_DE_FORMA]:
        caminho = ".".join(str(parte) for parte in detalhe.get("loc", ()))
        itens.append({"path": caminho, "message": str(detalhe.get("msg", ""))})
    return itens


def _recusar_segredo(definition: Any) -> None:
    """Recusa a definition que traz segredo em texto claro.

    Só um dict é inspecionado: um corpo de outro tipo (um `params_schema` que é
    string) é erro de FORMA, e a validação do Pydantic adiante o responde com o
    caminho do campo — aqui ele derrubava a ferramenta com erro interno.
    """
    if not isinstance(definition, dict):
        return
    caminhos = definition_contem_segredo(definition)
    if caminhos:
        raise erro_de_segredo(caminhos)


def _recusar_segredo_no_schema(params_schema: Any) -> None:
    """Recusa o `params_schema` que grava segredo como VALOR de um parâmetro
    (`params_schema.token.default`). Declarar um parâmetro `token` sem valor,
    como o próprio lint sugere, passa."""
    caminhos = params_schema_contem_segredo(params_schema)
    if caminhos:
        raise erro_de_segredo(caminhos)


def _relatorio(saida: Any) -> dict:
    """O `__report__` da validação — dict vazio quando a saída não o traz."""
    relatorio = saida.get("__report__") if isinstance(saida, dict) else None
    return relatorio if isinstance(relatorio, dict) else {}


def _resumo_da_validacao(relatorio: dict) -> dict:
    """O que cabe no topo da resposta: o veredito e as contagens.

    As MENSAGENS do relatório ficam de fora de propósito — elas citam nome de
    nó e texto escrito por quem monta o fluxo, e é no bloco `untrusted_data`
    que esse tipo de texto pode aparecer.
    """
    return {
        "ok": bool(relatorio.get("ok")),
        "error_count": len(relatorio.get("errors") or []),
        "warning_count": len(relatorio.get("warnings") or []),
    }


def _avisos_de_agendamento(wf) -> list:
    """`schedule_notices` (atributo transiente do service) como dicts.

    São objetos Pydantic: sem isto, a resposta não serializa e a falha só
    apareceria quando o workflow tivesse um `ScheduleTrigger`.
    """
    brutos = getattr(wf, "schedule_notices", None) or []
    avisos = []
    for aviso in brutos:
        if hasattr(aviso, "model_dump"):
            avisos.append(aviso.model_dump())
        elif isinstance(aviso, dict):
            avisos.append(dict(aviso))
    return avisos


async def _contar_versoes(db, workflow_hash: str) -> int:
    """Quantos snapshots o workflow tem. Contagem, e não `list_versions`: a
    listagem traz a definition de cada versão, e aqui só se quer o número."""
    resultado = await db.execute(
        select(func.count())
        .select_from(WorkflowVersion)
        .where(WorkflowVersion.workflow_hash == workflow_hash)
    )
    return int(resultado.scalar() or 0)


async def _validar(definition: Any, *, user_id: str, workspace_id: str) -> dict:
    """`validar_definicao` com o corpo mal formado traduzido.

    Um `pydantic.ValidationError` — nó sem `id`, aresta sem `target`, `nodes`
    que não é lista — subiria como erro inesperado ("erro interno"), que é a
    pior resposta possível para um corpo que o cliente consegue corrigir
    sozinho.
    """
    try:
        return await validate_service.validar_definicao(
            definition or {}, user_id=user_id, workspace_id=workspace_id
        )
    except ValidationError as exc:
        raise erro(
            "validation",
            "O corpo de definition não tem a forma esperada.",
            "cada nó precisa de id, name e type; cada aresta, de source e target",
            errors=_erros_de_forma(exc),
        ) from exc


async def _validar_antes_de_gravar(
    definition: Any, *, user_id: str, workspace_id: str, force: bool
) -> dict:
    """Valida e recusa a gravação quando há erros — salvo `force`.

    O caso FATAL não chega aqui nem com `force=True`: `validar_definicao` o
    levanta como `DefinicaoInvalidaError`, que o decorador traduz em
    `validation` com o mesmo relatório. É a assimetria que se quer — `force`
    existe para o erro de julgamento (um nó que a simulação não consegue
    exercitar sem dados reais), não para gravar um grafo que o executor nem
    monta.
    """
    relatorio = _relatorio(await _validar(definition, user_id=user_id, workspace_id=workspace_id))
    erros = relatorio.get("errors") or []
    if erros and not force:
        raise erro(
            "validation",
            f"A definição tem {len(erros)} erro(s) de validação e não foi gravada.",
            "corrija os itens de report.errors ou repita com force=true",
            # O relatório vai higienizado: `erro()` redige as strings que recebe
            # no topo, mas não desce por uma estrutura aninhada, e a mensagem de
            # um `simulate_error` repete o que o nó tentou fazer — inclusive uma
            # URL que a simulação montou.
            report=higienizar(relatorio),
        )
    return relatorio


async def _workspace_editavel(db, escopo, workspace_id: str | None) -> str:
    """O workspace da chamada, já conferido o papel mínimo de editor."""
    alvo = await resolver_workspace(db, escopo, workspace_id)
    papel = await get_workspace_member_role(db, alvo, escopo.user_id)
    exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL)
    return alvo


# ── Ferramentas ───────────────────────────────────────────────────────────────


@ferramenta
async def validate_workflow(
    ctx: Context, definition: dict, workspace_id: str | None = None
) -> dict:
    """Valida uma definição sem gravar nada.

    `workspace_id` é obrigatório aqui, ao contrário do núcleo, onde é opcional:
    é o workspace que decide quais credenciais entram no escopo da simulação,
    quais nós estão desabilitados e quais sub-fluxos existem. Sem ele a
    validação passaria a mentir por omissão — aprovaria uma definição que o
    run depois recusa. Quando o token alcança um workspace só, omitir continua
    valendo (o parâmetro é resolvido para esse único).

    A recusa por segredo acontece aqui no MESMO lugar das tools irmãs — logo
    depois do escopo e antes de tudo o que toca o banco —, ainda que esta não
    grave nada. O lint do núcleo também acusa `secret_in_definition`, mas só
    como item de `report.errors`, e deixá-lo dar a resposta custaria três
    coisas: (a) a recusa é a única verificação que fala só sobre o corpo que o
    próprio chamador mandou, e fazê-la primeiro impede que a senha chegue ao
    caminho de validação, que abre sessão própria e simula os nós; (b) um erro
    `secret_in_definition` com os CAMINHOS dos campos é diagnóstico melhor do
    que um item enterrado num relatório de dezenas de linhas; (c) a promessa de
    `docs/mcp.md` — recusa na entrada, antes de qualquer validação — passa a
    valer para as três tools que recebem definition, e não para duas delas.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")
    _recusar_segredo(definition)

    async with infra.sessao() as db:
        alvo = await _workspace_editavel(db, escopo, workspace_id)

    saida = await _validar(definition, user_id=escopo.user_id, workspace_id=alvo)
    relatorio = _relatorio(saida)
    # O corpo do validate é `{node_id: {...}}` mais as chaves reservadas `__*`.
    # Aqui ele sai separado em duas partes, e as duas são texto de quem escreve
    # a definition: o id e o apelido dos nós, as mensagens do lint, o
    # `suggested_params_schema`.
    por_no = {
        chave: valor for chave, valor in saida.items() if not str(chave).startswith("__")
    }
    dados = {"workspace_id": alvo}
    dados.update(_resumo_da_validacao(relatorio))
    return envelope(
        dados,
        report=relatorio,
        nodes=por_no,
        edge_diagnostics=saida.get("__edge_diagnostics__"),
    )


@ferramenta
async def create_workflow(
    ctx: Context,
    name: str,
    definition: dict,
    workspace_id: str | None = None,
    description: str | None = None,
    params_schema: dict | None = None,
    validate_first: bool = True,
    force: bool = False,
) -> dict:
    """Cria um workflow no workspace indicado.

    A recusa por segredo vem ANTES de tudo o que toca o banco: é a única
    verificação que fala só sobre o corpo que o próprio chamador mandou, e
    fazê-la primeiro garante que uma senha em texto claro não chegue sequer ao
    caminho de validação.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")
    _recusar_segredo(definition)
    # `params_schema` é coluna irmã e vai crua para o banco (não passa por
    # `encrypt_workflow_connections`): a mesma recusa da REST — só sobre o que
    # o schema grava como valor, e não sobre `required: true` de um `token`.
    _recusar_segredo_no_schema(params_schema)

    async with infra.sessao() as db:
        alvo = await _workspace_editavel(db, escopo, workspace_id)

    relatorio: dict = {}
    if validate_first:
        relatorio = await _validar_antes_de_gravar(
            definition, user_id=escopo.user_id, workspace_id=alvo, force=force
        )

    # Lista branca: só estas colunas chegam ao service, e a autoria é sempre a
    # do dono do token. `WorkflowCreate` aceita campo extra e tem `id_hash` com
    # default — repassar o que o cliente mandou deixaria escolher o id do
    # workflow e forjar quem o criou.
    extras: dict = {
        "created_by_id": escopo.user_id,
        "updated_by_id": escopo.user_id,
        # Proveniencia carimbada pela IDENTIDADE, nunca por argumento do corpo:
        # "usuario" para PAT e assistente, "assistente" para o assistente da Home.
        "origem": escopo.origem_dos_fluxos,
    }
    if description is not None:
        extras["description"] = description
    if params_schema is not None:
        extras["params_schema"] = params_schema

    async with infra.sessao() as db:
        wf = await WorkflowService(db).create_workflow(
            name=name, definition=definition or {}, workspace_id=alvo, **extras
        )
        # O CRUD já commitou o workflow; este commit fecha o que o agendamento
        # tenha acrescentado. `infra.sessao` faz rollback no finally — o que
        # não for commitado aqui não existe.
        await db.commit()
        dados = {
            "id": wf.id_hash,
            "workspace_id": wf.workspace_id,
            "is_active": bool(wf.flag_ative),
            "created_by_id": wf.created_by_id,
            "validated": bool(validate_first),
        }
        nome = wf.name

    if validate_first:
        dados["validation"] = _resumo_da_validacao(relatorio)
    return envelope(dados, name=nome, validation_report=relatorio or None)


@ferramenta
async def update_workflow(
    ctx: Context,
    workflow_id: str,
    definition: dict | None = None,
    name: str | None = None,
    description: str | None = None,
    params_schema: dict | None = None,
    change_note: str | None = None,
    validate_first: bool = True,
    force: bool = False,
) -> dict:
    """Atualiza um workflow existente. Só os campos enviados mudam.

    Ativar e desativar NÃO passa por aqui: `flag_ative` tem ferramenta própria
    (`set_workflow_active`), porque ligar um fluxo é uma decisão de operação,
    não de edição, e misturá-la a um `update` faria uma chamada que só queria
    renomear ligar o agendamento junto.

    Trocar a definition pode gerar um snapshot em `workflow_versions` (a regra
    é do núcleo: só mudança substancial versiona) — a resposta diz se gerou.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")
    if definition is not None:
        _recusar_segredo(definition)
    if params_schema is not None:
        _recusar_segredo_no_schema(params_schema)

    campos: dict = {}
    for chave, valor in (
        ("definition", definition),
        ("name", name),
        ("description", description),
        ("params_schema", params_schema),
    ):
        if valor is not None:
            campos[chave] = valor
    if not campos:
        raise erro(
            "validation",
            "Nada a atualizar: nenhum campo foi enviado.",
            "envie definition, name, description ou params_schema",
        )

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL)
        id_hash = wf.id_hash
        workspace_id = wf.workspace_id
        versoes_antes = await _contar_versoes(db, id_hash)

    relatorio: dict = {}
    if definition is not None and validate_first:
        relatorio = await _validar_antes_de_gravar(
            definition, user_id=escopo.user_id, workspace_id=workspace_id, force=force
        )

    try:
        # `WorkflowUpdate` é `extra="forbid"` e não expõe `workspace_id` nem
        # `updated_by_id`: mudar de tenant ou forjar autoria não passa por aqui.
        workflow_in = WorkflowUpdate(**campos)
    except ValidationError as exc:
        raise erro(
            "validation",
            "Campos inválidos para a atualização.",
            "confira os tipos em errors[] e repita",
            errors=_erros_de_forma(exc),
        ) from exc

    async with infra.sessao() as db:
        atualizado = await WorkflowService(db).update_workflow(
            id_hash, workflow_in, change_note=change_note, updated_by_id=escopo.user_id
        )
        await db.commit()
        avisos = _avisos_de_agendamento(atualizado)
        versoes_depois = await _contar_versoes(db, id_hash)
        dados = {
            "id": atualizado.id_hash,
            "workspace_id": atualizado.workspace_id,
            "is_active": bool(atualizado.flag_ative),
            "updated_fields": sorted(campos),
            "version_snapshot": versoes_depois > versoes_antes,
            "versions_count": versoes_depois,
            # O código do aviso é fechado e gerado pela plataforma; a mensagem,
            # que cita a expressão de agendamento escrita por gente, vai no
            # bloco não confiável.
            "schedule_notice_codes": [str(a.get("code")) for a in avisos],
        }
        nome = atualizado.name

    if definition is not None and validate_first:
        dados["validation"] = _resumo_da_validacao(relatorio)
    return envelope(
        dados,
        name=nome,
        schedule_notices=avisos or None,
        validation_report=relatorio or None,
    )


@ferramenta
async def set_workflow_active(ctx: Context, workflow_id: str, active: bool) -> dict:
    """Liga ou desliga o workflow — o único caminho para `flag_ative`.

    Desligar não é só um campo: o núcleo sincroniza os agendamentos com o novo
    estado, para que um fluxo desativado não continue sendo disparado pelo
    agendador. Os avisos dessa sincronização voltam na resposta.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL)
        atualizado = await WorkflowService(db).update_workflow(
            wf.id_hash,
            WorkflowUpdate(flag_ative=bool(active)),
            updated_by_id=escopo.user_id,
        )
        await db.commit()
        avisos = _avisos_de_agendamento(atualizado)
        dados = {
            "id": atualizado.id_hash,
            "workspace_id": atualizado.workspace_id,
            "is_active": bool(atualizado.flag_ative),
            "schedule_notice_codes": [str(a.get("code")) for a in avisos],
        }
        nome = atualizado.name

    return envelope(dados, name=nome, schedule_notices=avisos or None)


def _lista_de_compartilhamento(shared_with: Any) -> list | None:
    """A lista de quem enxerga o portal privado, higienizada.

    `None` continua `None` ("com ninguém ainda"), que é o que a REST grava
    quando o corpo não traz a lista. Qualquer outra coisa que não seja lista é
    recusada em vez de coagida: gravar `"ana"` como `["a","n","a"]` é o tipo de
    conserto silencioso que só aparece quando alguém abre o portal.
    """
    if shared_with is None:
        return None
    if not isinstance(shared_with, (list, tuple)):
        raise erro(
            "validation",
            "shared_with precisa ser uma lista de identificadores.",
            'exemplo: ["ana", "bruno"]',
        )
    return [str(item).strip() for item in shared_with if str(item).strip()]


@ferramenta
async def set_portal_access(
    ctx: Context, workflow_id: str, access: str, shared_with: list[str] | None = None
) -> dict:
    """Publica (ou despublica) o workflow no portal.

    `private` é o único estado em que a lista de compartilhamento significa
    alguma coisa: em `public` e `disabled` ela é ZERADA, e não apenas ignorada.
    Guardá-la "para quando voltar a ser privado" deixaria no banco uma lista de
    pessoas que ninguém vê na tela e que voltaria a valer sem novo aval.

    A URL devolvida é absoluta — um cliente MCP não tem base para completar um
    caminho relativo.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    alvo = str(access or "").strip().lower()
    if alvo not in ACESSOS_DO_PORTAL:
        raise erro(
            "validation",
            "access precisa ser disabled, public ou private.",
            "use private com shared_with para restringir a pessoas",
            allowed=list(ACESSOS_DO_PORTAL),
        )
    lista = _lista_de_compartilhamento(shared_with) if alvo == "private" else None

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL)
        # Gravação direta no ORM, como o `PATCH /workflows/{id}/portal`:
        # `WorkflowUpdate` não tem `portal_access` (e não deve ter — trocar o
        # estado de publicação pelo PUT genérico esconderia a decisão dentro
        # de um "salvar").
        wf.portal_access = alvo
        wf.portal_shared_with = lista
        dados = {
            "id": wf.id_hash,
            "workspace_id": wf.workspace_id,
            "portal_access": alvo,
            "share_url": _share_url(wf),
        }
        com_quem = list(lista or [])
        nome = wf.name
        await db.commit()

    # Lista vazia continua aparecendo: "compartilhado com ninguém" é resposta.
    return envelope(dados, name=nome, shared_with=com_quem)


def registrar(server) -> None:
    """Registra as tools deste domínio."""
    server.tool(
        name="validate_workflow",
        title="Validar definição",
        description=(
            "Valida uma definição de workflow sem gravar nada: erros e avisos do lint, "
            "schema de saída de cada nó, nós desabilitados, referências de sub-fluxo e "
            "sugestão de params_schema. Informe `workspace_id` (obrigatório) para que "
            "credenciais, nós desabilitados e sub-fluxos sejam conferidos. Recusa na "
            "entrada, sem validar, a definição com segredo em texto claro — referencie "
            "credenciais por `credential_id` (list_credentials)."
        ),
        annotations=anotacoes("validate_workflow"),
    )(validate_workflow)

    server.tool(
        name="create_workflow",
        title="Criar workflow",
        description=(
            "Cria um workflow no workspace indicado. Valida antes de gravar "
            "(`validate_first`, use `force=true` para gravar apesar de erros não fatais) e "
            "recusa definição com segredo em texto claro — referencie credenciais por "
            "`credential_id` (list_credentials)."
        ),
        annotations=anotacoes("create_workflow"),
    )(create_workflow)

    server.tool(
        name="update_workflow",
        title="Atualizar workflow",
        description=(
            "Atualiza um workflow existente (id ou nome). Só os campos enviados mudam; "
            "trocar a definition pode gerar um snapshot de versão, e `change_note` descreve "
            "a mudança. Para ativar ou desativar, use set_workflow_active."
        ),
        annotations=anotacoes("update_workflow"),
    )(update_workflow)

    server.tool(
        name="set_workflow_active",
        title="Ativar ou desativar workflow",
        description=(
            "Ativa ou desativa o workflow, sincronizando os agendamentos com o novo estado. "
            "É o único caminho para mudar `is_active`."
        ),
        annotations=anotacoes("set_workflow_active"),
    )(set_workflow_active)

    server.tool(
        name="set_portal_access",
        title="Acesso ao portal",
        description=(
            "Define a publicação do workflow no portal: disabled, public ou private "
            "(com `shared_with`). Devolve o endereço absoluto de compartilhamento; fora de "
            "`private` a lista de compartilhamento é zerada."
        ),
        annotations=anotacoes("set_portal_access"),
    )(set_portal_access)
