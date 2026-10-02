# app/services/assistente_superficie.py
"""
A superfície Home do assistente — o mesmo laço do assistente, outro pacote.

O laço, a cota, o escopo que viaja no `ContextVar`, o transcrito retomável: tudo
vem de `assistente_service`. Este módulo só monta a `Superficie` da Home e importa
`assistente_service` (NUNCA o contrário — o editor não conhece a Home).

O que a Home faz de diferente do editor:

- **A entrega é uma CAMADA no globo, não um desenho no canvas.** O assistente
  cria e roda os PRÓPRIOS fluxos (marcados `origem="assistente"` pela identidade,
  escondidos das listagens) SEM clique — é assim que a resposta chega ao globo — e
  põe uma saída de execução no globo com `exibir_no_globo`.
- **Alcance completo, com CONFIRMAÇÃO POR CLIQUE no que já existia.** A `Superficie`
  permite toda tool do MCP (`permitida = n in GUARDAS`); o que segura o que ela pode
  destruir é o portão de confirmação, verificado no servidor — nunca uma promessa
  de texto. Apagar um agendamento, apagar um arquivo do Drive, rodar ou editar um
  fluxo QUE A PESSOA criou: tudo isso emite um quadro `confirmacao` e ESPERA o
  clique. Rodar e editar os fluxos do próprio assistente não pede clique.

A confirmação, em detalhe: o portão intercepta a chamada confirmável, guarda
`{token, tool, args}` no Redis por 15 min sob
`agente:confirmacao:{user}:{conversa}:{tool_use_id}`, emite o quadro `confirmacao`
e devolve ao modelo um `tool_result` NÃO-erro "aguardando" — um erro faria o modelo
repetir a chamada e duplicar o botão. O clique (no PR da API) valida posse e token,
consome a chave uma única vez e executa os args ARMAZENADOS por `chamar_no_servidor`,
sob o escopo do usuário. Os argumentos que rodam são os do SERVIDOR, nunca os que o
cliente mandar no clique.
"""
from __future__ import annotations

import json
import secrets
import unicodedata
from typing import Any

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.mcp import infra
from app.mcp.guardas import GUARDAS
from app.mcp.resolucao import carregar_workflow
from app.services.assistente_service import (
    EstadoDoLaco,
    Evento,
    Superficie,
    _resumo,
)

logger = get_logger("app.agente.superficie")


# ── A entrega: `exibir_no_globo` ─────────────────────────────────────────────
# O análogo do `desenhar_no_canvas` do editor. NÃO existe no MCP: não entra em
# `GUARDAS`, um cliente externo nunca a vê. O globo é da Home, e só faz sentido
# para quem está olhando para ele. Ela é um PONTEIRO: emite um quadro `camada`
# com o `artifact_id`, e o globo busca a geometria e os metadados por
# `GET /assistente/camadas/{id}` (portão de membro).
NOME_DO_GLOBO = "exibir_no_globo"

FERRAMENTA_DO_GLOBO: dict[str, Any] = {
    "name": NOME_DO_GLOBO,
    "description": (
        "Põe uma saída de execução (um artefato GeoJSON, ou uma camada publicada) "
        "no globo da Home, AGORA. É a sua entrega: enquanto você não chamar isto, a "
        "pessoa não vê camada nenhuma no globo.\n\n"
        "Passe o `artifact_id` de um artefato que já existe (de uma execução que "
        "você rodou, ou que a pessoa mencionou). O globo busca a geometria pelo id; "
        "você não precisa mandar o conteúdo. Não grava nada."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "artifact_id": {
                "type": "string",
                "description": "O id do artefato de execução a exibir no globo.",
            },
            "nome": {
                "type": "string",
                "description": "Um rótulo curto para a camada, para a pessoa reconhecer.",
            },
        },
        "required": ["artifact_id"],
    },
}


async def _exibir_no_globo(argumentos: Any, estado: EstadoDoLaco) -> tuple[str, bool]:
    """Valida os argumentos e devolve o texto que o modelo lê. Não vai ao servidor.

    NÃO emite o quadro `camada` aqui: quem o monta é `_quadros_da_home`, a partir
    dos `argumentos`. Um `emitir` daqui sairia no SSE e sumiria no replay (que só
    reexecuta `quadros_extras`), e a camada desapareceria do globo ao reabrir o
    chat. Um caminho só serve os dois.
    """
    aid = _artefato_pedido(argumentos)
    if aid is None:
        return ("`artifact_id` precisa ser o id de um artefato de execução.", True)
    return (
        f"Camada {aid} enviada ao globo. A pessoa está vendo agora — o globo busca a "
        "geometria e os metadados pelo id.",
        False,
    )


def _artefato_pedido(argumentos: Any) -> str | None:
    aid = argumentos.get("artifact_id") if isinstance(argumentos, dict) else None
    if not isinstance(aid, str) or not aid.strip():
        return None
    return aid.strip()


def _quadro_do_globo(argumentos: Any) -> list[Evento]:
    """O quadro `camada` de um `exibir_no_globo` bem-sucedido.

    `available=True` de propósito: o quadro é PONTEIRO e a verdade é
    `GET /assistente/camadas/{id}`. Omitir o campo fazia o front normalizá-lo como
    `False` e desenhar o cartão de alerta ("sem prévia no globo") enquanto a
    camada aparecia no globo.
    """
    aid = _artefato_pedido(argumentos)
    if aid is None:
        return []
    dados: dict[str, Any] = {"artifact_id": aid, "available": True}
    nome = argumentos.get("nome") if isinstance(argumentos, dict) else None
    if isinstance(nome, str) and nome.strip():
        dados["nome"] = nome.strip()[:120]
    return [Evento("camada", dados)]


# ── As respostas rápidas: `sugerir_respostas` ────────────────────────────────
# A segunda ferramenta LOCAL da Home, no molde de `exibir_no_globo`: não vai ao
# servidor, não entra em `GUARDAS`, e o quadro (`respostas_rapidas`) nasce dos
# ARGUMENTOS em `_quadros_da_home` — nunca de um `emitir` aqui —, para o replay
# reconstruí-lo pelo mesmo caminho. O que ela faz é oferecer à pessoa até três
# continuações curtas (chips sob a resposta) que viram a próxima mensagem dela
# com um clique. Quem decide se ainda valem é a web: só no último turno.
NOME_DAS_RESPOSTAS = "sugerir_respostas"
TETO_DE_RESPOSTAS = 3
TAMANHO_DA_RESPOSTA = 80

FERRAMENTA_DAS_RESPOSTAS: dict[str, Any] = {
    "name": NOME_DAS_RESPOSTAS,
    "description": (
        "Oferece à pessoa até três RESPOSTAS RÁPIDAS: continuações curtas que ela "
        "escolhe com um clique e que viram a próxima mensagem dela (refinar o "
        "período, cruzar com outra camada, ver por município, agendar). Chame UMA "
        "vez por resposta, DEPOIS do texto final, e só quando houver continuação "
        "natural. Cada opção é o que a pessoa diria, em até 60 caracteres. Não "
        "repita as opções no texto. Perguntas essenciais para continuar você faz "
        "no texto, não aqui."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "opcoes": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": TETO_DE_RESPOSTAS,
                "description": "As frases, como a pessoa as diria. De uma a três.",
            },
        },
        "required": ["opcoes"],
    },
}


def _opcoes_pedidas(argumentos: Any) -> list[str] | None:
    """As opções válidas, limpas e limitadas — ou `None` se não sobrou nenhuma.

    Só strings; espaços normalizados; vazias fora; repetidas fora (a primeira
    fica); cada uma cortada em `TAMANHO_DA_RESPOSTA`; só as `TETO_DE_RESPOSTAS`
    primeiras. Tolera `argumentos` que não é dict (a entrada cortada no stream).
    """
    cru = argumentos.get("opcoes") if isinstance(argumentos, dict) else None
    if not isinstance(cru, list):
        return None
    opcoes: list[str] = []
    for item in cru:
        if not isinstance(item, str):
            continue
        frase = " ".join(item.split())[:TAMANHO_DA_RESPOSTA].strip()
        if frase and frase not in opcoes:
            opcoes.append(frase)
        if len(opcoes) == TETO_DE_RESPOSTAS:
            break
    return opcoes or None


async def _sugerir_respostas(argumentos: Any, estado: EstadoDoLaco) -> tuple[str, bool]:
    """Valida as opções e devolve o texto que o modelo lê. Não vai ao servidor.

    NÃO emite o quadro aqui — quem o monta é `_quadros_da_home`, a partir dos
    argumentos (a mesma razão de `_exibir_no_globo`: um `emitir` sumiria no
    replay). O texto devolvido manda ENCERRAR o turno: é o que evita o modelo
    repetir as opções em prosa depois de pô-las na tela.
    """
    opcoes = _opcoes_pedidas(argumentos)
    if opcoes is None:
        return ("`opcoes` precisa ser uma lista de 1 a 3 frases curtas.", True)
    return (
        f"Respostas rápidas na tela ({len(opcoes)}). Encerre o turno: a pessoa "
        "escolhe uma ou digita outra coisa.",
        False,
    )


def _quadro_das_respostas(argumentos: Any) -> list[Evento]:
    """O quadro `respostas_rapidas` de um `sugerir_respostas` bem-sucedido."""
    opcoes = _opcoes_pedidas(argumentos)
    if opcoes is None:
        return []
    return [Evento("respostas_rapidas", {"opcoes": opcoes})]


# ── O que exige clique ───────────────────────────────────────────────────────
# Duas listas, e a diferença é deliberada:
#
# - SEMPRE: mexe no que já existia, sem alvo ambíguo — apagar/criar/alterar
#   agendamento, apagar arquivo do Drive, restaurar versão, ligar/desligar um
#   fluxo, publicar no portal, re-executar. Toda ação aqui destrói ou expõe dado
#   de outra pessoa do workspace, ou dispara custo — e "limpa os agendamentos
#   antigos" é uma frase que alguém digita sem pensar.
# - SE O FLUXO É DA PESSOA: editar ou rodar um fluxo. O assistente edita e roda
#   os PRÓPRIOS fluxos (origem="assistente") sem clique — é o que faz a resposta
#   chegar ao globo. Só quando o alvo é um fluxo que a PESSOA criou é que o clique
#   entra: aí ele está mexendo no que já existia.
#
# O DEFAULT É INVERTIDO de propósito: `CONFIRMAVEIS_SEMPRE` é DERIVADA de
# `GUARDAS` — toda tool que não é `read_only` confirma, salvo as duas da
# allowlist abaixo. Enquanto a lista era escrita à mão, uma tool de escrita nova
# nascia LIVRE (foi o que aconteceu com `cancel_run`, `pin_node_output`,
# `unpin_node_output`, `duplicate_workflow` e o par de upload do Drive: o
# assistente cancelava a execução de outro membro sem cartão nenhum). Agora ela
# nasce confirmável, e liberá-la exige um nome explícito aqui.
CONFIRMAVEIS_SE_FLUXO_DA_PESSOA: frozenset[str] = frozenset({"update_workflow", "run_workflow"})

# A allowlist: as ÚNICAS escritas que o assistente faz sem clique. Duas são o
# caminho de ele montar os PRÓPRIOS fluxos — `validate_workflow` não grava nada
# (simula), e `create_workflow` nasce `origem="assistente"`, escondido das
# listagens da pessoa. Nenhuma das duas toca no que já existia. A terceira,
# `register_source`, é decisão do dono: guardar no catálogo uma fonte que a
# sondagem confirmou é barato, reversível e não executa nada — e pedir clique a
# cada fonte nova devolveria o custo que o catálogo veio tirar. `probe_source`
# entra pelo mesmo motivo: sondar é livre (só metadados; atualiza o estado de
# uma fonte já catalogada).
ESCRITAS_SEM_CLIQUE: frozenset[str] = frozenset({"validate_workflow", "create_workflow", "probe_source", "register_source"})

CONFIRMAVEIS_SEMPRE: frozenset[str] = frozenset(
    nome
    for nome, guarda in GUARDAS.items()
    if not guarda.read_only
    and nome not in ESCRITAS_SEM_CLIQUE
    and nome not in CONFIRMAVEIS_SE_FLUXO_DA_PESSOA
)


# ── O portão da confirmação ──────────────────────────────────────────────────
# A chave do Redis é (usuário, conversa, tool_use_id): o clique casa com a chamada
# exata pelo `tool_use_id`, e o par (usuário, conversa) impede que o token de uma
# conversa valha noutra. 15 min é folga para a pessoa ler e decidir, e curto o
# bastante para uma decisão esquecida sumir sozinha.
TTL_DA_CONFIRMACAO_S = 15 * 60

MENSAGEM_AGUARDANDO = (
    "Aguardando a confirmação da pessoa pelo botão. Diga em uma linha o que está "
    "pendente e ENCERRE o turno — não repita esta chamada nem peça confirmação por texto."
)

MENSAGEM_SEM_CONFIRMACAO = (
    "Não foi possível abrir a confirmação desta ação agora. Explique à pessoa que a "
    "ação não pôde ser preparada e siga sem executá-la."
)

MENSAGEM_FORA_DO_ALCANCE = (
    "Esta ferramenta não está disponível no assistente da Home."
)


def chave_de_confirmacao(user_id: str, conversa_id: str | None, tool_use_id: str) -> str:
    return f"agente:confirmacao:{user_id}:{conversa_id or 'novo'}:{tool_use_id}"


async def _fluxo_e_da_pessoa(estado: EstadoDoLaco, argumentos: Any) -> bool:
    """True quando o alvo NÃO é um fluxo do próprio assistente — então pede clique.

    Falha FECHADA: sem alvo claro, ou quando o fluxo não carrega (id inexistente,
    erro de banco), trata como "da pessoa" e confirma. Rodar o fluxo de alguém sem
    clique por causa de um erro transitório seria o pior lado para errar. Só um
    `origem == "assistente"` positivo dispensa a confirmação.

    A LEITURA de `origem` mora DENTRO do `async with`, e isso não é estilo.
    `infra.sessao()` dá `rollback()` no `finally`, e um rollback EXPIRA todo
    objeto da sessão — inclusive numa sessão que só leu. Fora do bloco, qualquer
    atributo dispara um refresh numa instância já destacada e levanta
    `DetachedInstanceError`. Pior: `getattr(wf, "origem", <default>)` NÃO
    protege, porque o default só cobre `AttributeError`. O efeito em produção
    era o assistente não conseguir rodar NENHUM fluxo próprio — que é o caminho
    inteiro da Home (criar o fluxo, rodar, mandar a camada ao globo).
    """
    ref = argumentos.get("workflow_id") if isinstance(argumentos, dict) else None
    if not ref:
        return True
    try:
        async with infra.sessao() as db:
            wf, _papel = await carregar_workflow(db, estado.escopo, str(ref))
            origem = getattr(wf, "origem", "usuario")
    except Exception:
        logger.exception("Nao foi possivel ler a origem do fluxo %s; exigindo clique.", ref)
        return True
    return origem != "assistente"


async def _confirmavel(estado: EstadoDoLaco, nome: str, argumentos: Any) -> bool:
    if nome in CONFIRMAVEIS_SEMPRE:
        return True
    if nome in CONFIRMAVEIS_SE_FLUXO_DA_PESSOA:
        return await _fluxo_e_da_pessoa(estado, argumentos)
    return False


def _alvo(argumentos: Any) -> str | None:
    """Um identificador do alvo, para o cartão de confirmação mostrar no que ela mexe."""
    if not isinstance(argumentos, dict):
        return None
    for chave in ("workflow_id", "job_id", "schedule_id", "file_id", "run_id", "version_number", "source_id", "url", "id"):
        valor = argumentos.get(chave)
        if valor not in (None, ""):
            return str(valor)[:120]
    return None


async def _pedir_confirmacao(
    estado: EstadoDoLaco, nome: str, argumentos: Any, tool_use_id: str | None
) -> tuple[str, bool]:
    """Guarda `{token, tool, args}` no Redis, emite o quadro `confirmacao` e devolve
    ao modelo um `tool_result` NÃO-erro "aguardando".

    Não-erro de propósito: um `is_error=True` faria o modelo tentar de novo e
    duplicar o botão. O que segura o modelo é a instrução (`INSTRUCOES_DA_HOME`),
    que manda encerrar o turno ao ver "aguardando".

    O `tool_use_id` chega como ARGUMENTO, e não de um campo "chamada atual" no
    estado: as ferramentas de uma volta rodam em paralelo, e um campo
    compartilhado casaria o clique de confirmação com a chamada errada.
    """
    if estado.redis is None or not tool_use_id:
        # Sem Redis não há como guardar o token para validar o clique depois; sem
        # `tool_use_id` não há como casar o clique com a chamada. Recusa fechada, e
        # não uma confirmação que nunca poderá ser honrada.
        return (MENSAGEM_SEM_CONFIRMACAO, True)

    token = secrets.token_urlsafe(24)
    payload = json.dumps(
        {
            "token": token,
            "tool": nome,
            # Os args ARMAZENADOS: é isto que o clique executa, nunca o que o
            # cliente mandar no POST de confirmação.
            "args": argumentos if isinstance(argumentos, dict) else {},
            "criado_em": utc_now_naive().isoformat(),
        },
        ensure_ascii=False,
    )
    chave = chave_de_confirmacao(estado.escopo.user_id, estado.conversa_id, tool_use_id)
    try:
        await estado.redis.set(chave, payload, ex=TTL_DA_CONFIRMACAO_S)
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao guardar a confirmação: %s", exc.__class__.__name__)
        return (MENSAGEM_SEM_CONFIRMACAO, True)

    await estado.emitir(
        Evento(
            "confirmacao",
            {
                "tool_use_id": tool_use_id,
                "token": token,
                "acao": {"tool": nome, "argumentos": _resumo(argumentos), "alvo": _alvo(argumentos)},
            },
        )
    )
    return (MENSAGEM_AGUARDANDO, False)


async def _portao_da_home(
    estado: EstadoDoLaco, nome: str, argumentos: Any, tool_use_id: str | None = None
) -> tuple[str, bool] | None:
    """O portão da Home: confirmação por clique para o que mexe no que já existia.

    `None` quando a ferramenta pode seguir direto para o servidor (o assistente
    cria e roda os próprios fluxos sem clique).
    """
    if nome not in GUARDAS:
        # `permitida` já filtra a lista que o modelo vê; recusar aqui também mantém
        # a resposta uniforme e é a mesma separação `list_tools`/`call_tool` do MCP.
        return (MENSAGEM_FORA_DO_ALCANCE, True)
    if not await _confirmavel(estado, nome, argumentos):
        return None
    return await _pedir_confirmacao(estado, nome, argumentos, tool_use_id)


# ── Os quadros que a Home emite depois de uma ferramenta ─────────────────────


def _json_ou_none(resultado: str) -> Any:
    try:
        return json.loads(resultado)
    except (TypeError, ValueError):
        return None


def _quadro_fluxo(corpo: dict) -> list[Evento]:
    """`create_workflow` bem-sucedido → um quadro `fluxo` (o badge junto do chat)."""
    wid = corpo.get("id")
    if not wid:
        return []
    nome = (corpo.get("untrusted_data") or {}).get("name")
    return [Evento("fluxo", {"workflow_id": wid, "nome": nome})]


def _quadros_camada(corpo: dict) -> list[Evento]:
    """Os artefatos GeoJSON de uma execução → um quadro `camada` cada.

    É o que faz "a resposta chegar ao globo" sem o modelo pedir `exibir_no_globo`.
    O quadro é PONTEIRO (só o id e um rótulo); a verdade é `GET /assistente/camadas/{id}`.
    `run_workflow` lista em `artifacts`, `get_run_artifacts` em `items` — os dois
    são aceitos.
    """
    artefatos = corpo.get("artifacts")
    if not isinstance(artefatos, list):
        artefatos = corpo.get("items")
    if not isinstance(artefatos, list):
        return []

    quadros: list[Evento] = []
    for art in artefatos:
        if not isinstance(art, dict) or art.get("format") != "geojson":
            continue
        aid = art.get("id")
        if not aid:
            continue
        rotulo = art.get("untrusted_data") or {}
        dados: dict[str, Any] = {
            "artifact_id": aid,
            "nome": rotulo.get("filename") or rotulo.get("output_key"),
            "format": "geojson",
            # `available=False` acompanha com o motivo (executor-local, sem storage):
            # o globo mostra "sem prévia" em vez de tentar buscar e falhar.
            "available": bool(art.get("available")),
        }
        if art.get("hint"):
            dados["hint"] = art["hint"]
        quadros.append(Evento("camada", dados))
    return quadros


def _quadros_da_home(
    estado: EstadoDoLaco, nome: str, argumentos: Any, resultado: str, deu_erro: bool
) -> list[Evento]:
    """`fluxo` de um `create_workflow`; `camada` dos artefatos de uma execução (ou
    de um `exibir_no_globo`); `respostas_rapidas` de um `sugerir_respostas`."""
    if deu_erro:
        return []
    if nome == "create_workflow":
        corpo = _json_ou_none(resultado)
        return _quadro_fluxo(corpo) if isinstance(corpo, dict) else []
    if nome in ("run_workflow", "get_run_artifacts"):
        corpo = _json_ou_none(resultado)
        return _quadros_camada(corpo) if isinstance(corpo, dict) else []
    if nome == NOME_DO_GLOBO:
        return _quadro_do_globo(argumentos)
    if nome == NOME_DAS_RESPOSTAS:
        return _quadro_das_respostas(argumentos)
    return []


# ── As mensagens que SÓ o servidor escreve ───────────────────────────────────
# Uma grafia única, importada pelos três pontos que precisavam concordar: a
# guarda de entrada da rota, o texto que o servidor grava depois do clique, e o
# que `INSTRUCOES_DA_HOME` ensina o modelo a reconhecer. Enquanto a guarda
# comparava "[Acao" e o prompt ensinava "[Ação", uma mensagem digitada com acento
# passava pela guarda e o modelo a lia como desfecho de um clique que não houve.
MENSAGEM_CONFIRMADA = "[Ação confirmada pela pessoa pelo botão]"
MENSAGEM_RECUSADA = "[Ação recusada pela pessoa]"

# O que a guarda compara, já sem acento e em minúsculas — ver `parece_sintetica`.
_PREFIXO_NORMALIZADO = "[acao"


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def parece_sintetica(mensagem: str) -> bool:
    """A mensagem imita o prefixo que só o servidor escreve?

    Compara SEM acento e SEM caixa: `startswith("[Acao")` deixava passar tanto a
    grafia acentuada que o próprio prompt ensina ("[Ação confirmada…") quanto a
    minúscula ("[acao confirmada…").
    """
    return _sem_acento((mensagem or "").lstrip()).casefold().startswith(_PREFIXO_NORMALIZADO)


# ── As instruções da Home ────────────────────────────────────────────────────
# O bloco [1] do system prompt na superfície Home. Corrige onde a política do MCP
# (`INSTRUCOES`) não vale aqui: lá se pede confirmação EM TEXTO antes de criar ou
# executar; aqui o assistente cria e roda os PRÓPRIOS fluxos sem pedir, e a
# confirmação é POR CLIQUE, só para o que mexe no que já existia.
INSTRUCOES_DA_HOME = """\
Você é o assistente do Atlans, conversando sobre um globo 3D. A pessoa não vê
fluxo nenhum: ela vê o resultado no globo. O trabalho aqui é responder à pergunta
espacial dela PONDO UMA CAMADA NO GLOBO, não explicando como faria.

SUA ENTREGA É UMA CAMADA NO GLOBO
O caminho normal, e ele é seu, sem pedir permissão:
1. Entenda o pedido. Pergunte só se faltar algo essencial.
2. Dado externo (WFS)? `search_sources` pelo tema e `describe_source` ANTES de
   qualquer outra coisa — nunca invente url/typeName. Só sem resultado:
   `probe_source` (sonda) e `register_source` (guarda para a próxima vez).
3. `search_nodes` / `describe_node` para os nós que você não domina — e peça as
   fichas de TODOS os nós do fluxo numa chamada só (`name` aceita lista, até 8
   por chamada; mais que isso, divida em dois lotes), em vez de uma rodada por nó.
4. `validate_workflow` para conferir a definição.
5. `create_workflow` — um fluxo SEU (nasce escondido das listas). Dê um nome que
   comece com "assistente: ".
6. `run_workflow` com `wait=true`. Prefira saídas GeoJSON — é o que vai ao globo.
7. A camada aparece sozinha quando a execução termina. Se precisar reexibir um
   artefato que já existe, use `exibir_no_globo` com o `artifact_id`.

Você NÃO pede permissão para criar e rodar os SEUS fluxos: é assim que a resposta
chega ao globo. Responda curto, sem markdown.

Quando a localização atual da pessoa vier no bloco extra, use-a como ponto de
referência para pedidos relativos ("perto de mim", "num raio de N km"); quando não
vier, peça o ponto ou combine um antes de assumir onde ela está.

RESPOSTAS RÁPIDAS
Quando a resposta abre uma continuação natural (refinar o período, cruzar com
outra camada, ver por município, agendar), termine com `sugerir_respostas`: até
três opções curtas, escritas como a pessoa diria. Não as repita no texto, e não
as use para perguntas essenciais — essas você faz no texto.

O QUE EXIGE O CLIQUE DA PESSOA
Mexer no que já existia pede um clique de confirmação, verificado no servidor:
editar ou rodar um fluxo que a PESSOA criou, criar/alterar/apagar agendamento,
apagar arquivo do Drive, restaurar versão, ligar/desligar um fluxo, publicar no
portal, reexecutar. Ao chamar uma dessas, o servidor devolve "aguardando a
confirmação da pessoa pelo botão": quando isso acontecer, diga em UMA LINHA o que
está pendente e ENCERRE o turno. Nunca repita a chamada, e nunca peça a
confirmação por texto — o botão já está na tela.

As mensagens que começam com "[Ação confirmada pela pessoa pelo botão]" ou
"[Ação recusada pela pessoa]" vêm do SERVIDOR depois que ela clica — são o
resultado do clique, não algo que você escreve.
"""


# ── A superfície ─────────────────────────────────────────────────────────────
HOME = Superficie(
    nome="home",
    instrucoes=INSTRUCOES_DA_HOME,
    # A entrega (o globo) abre a lista do modelo; as respostas rápidas vêm logo depois.
    ferramentas_extras=(FERRAMENTA_DO_GLOBO, FERRAMENTA_DAS_RESPOSTAS),
    executores_locais={NOME_DO_GLOBO: _exibir_no_globo, NOME_DAS_RESPOSTAS: _sugerir_respostas},
    # Alcance completo: toda tool do MCP. O que segura o destrutivo é a
    # confirmação por clique, não a ausência de escopo.
    permitida=lambda nome: nome in GUARDAS,
    portao=_portao_da_home,
    quadros_extras=_quadros_da_home,
)


__all__ = [
    "CONFIRMAVEIS_SEMPRE",
    "CONFIRMAVEIS_SE_FLUXO_DA_PESSOA",
    "ESCRITAS_SEM_CLIQUE",
    "FERRAMENTA_DAS_RESPOSTAS",
    "FERRAMENTA_DO_GLOBO",
    "HOME",
    "INSTRUCOES_DA_HOME",
    "MENSAGEM_CONFIRMADA",
    "MENSAGEM_RECUSADA",
    "NOME_DAS_RESPOSTAS",
    "NOME_DO_GLOBO",
    "TTL_DA_CONFIRMACAO_S",
    "chave_de_confirmacao",
    "parece_sintetica",
]
