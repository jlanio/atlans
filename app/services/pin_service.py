# app/services/pin_service.py
"""
Pins — fixar a saída de um nó para a próxima execução reaproveitar.

A lógica inteira nasceu dentro de três rotas de `workflows_router.py` e ficou
lá, sem service e sem teste nenhum. Agora há dois chamadores: a tela e o
servidor MCP, que não passa por request nenhuma. Copiar as regras para o segundo
transporte duplicaria a ordem do unpin, o parsing da expiração, o portão do nó
de saída e a leitura que cruza `pinned_outputs` com `pin_metadata` — e a
primeira vez que uma delas mudasse, os dois responderiam coisas diferentes.

Quem chama já resolveu QUEM pergunta (papel e workspace); aqui se resolve O QUE
fazer. É a mesma fronteira de `app/services/artifact_service.py`.

## As duas colunas, que não dizem a mesma coisa

`pin_metadata[nid]` é a INTENÇÃO: alguém pediu o pin, quando, e até quando.
`pinned_outputs[nid]` é a MATERIALIZAÇÃO: `{}` enquanto o cache não existe, e
`{"__pin_s3_key__": …}` depois que uma execução gravou o objeto.

Quem escreve cada uma é diferente, e é isso que faz a distinção valer:
a intenção só nasce aqui, por pedido explícito; a materialização é gravada pelo
consumidor do resultado da execução (`run_result_consumer._persist_pinned_outputs_if_present`).
Um nó com intenção e sem cache é um pin que ainda vai acontecer — e é
exatamente a pergunta "por que meu fluxo continua recalculando".

## Quem honra o TTL

O executor, e ele **deliberadamente não zera a referência** quando o pin expira
(contrato fixado em `tests/unit/test_pin_ciclo_de_vida.py`). Por isso `expired`
aqui é informativo: este módulo relata, não age. Uma limpeza automática de pins
vencidos quebraria aquele contrato.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact

logger = get_logger(__name__)

# Teto do TTL: um ano. O valor em si é arbitrário; o que não é arbitrário é
# existir um teto — sem ele, `timedelta(hours=…)` com um inteiro grande levanta
# `OverflowError` e a rota devolve 500 para uma entrada que o schema aceitou.
TTL_MAXIMO_HORAS = 8760

# Tipos de nó cuja saída não pode ser fixada. Ver `e_no_de_saida`.
TIPO_DE_SAIDA = "output"


# ── Leitura ──────────────────────────────────────────────────────────────────


def _instante(valor: Any) -> Optional[datetime]:
    """Lê um instante gravado em `pin_metadata`, tolerando o que aparecer.

    O escritor de hoje grava `utc_now_naive().isoformat()` — ingênuo, sem
    sufixo. Mas este campo é JSON num banco que já viu outras versões do
    código, e um `fromisoformat` nu quebra de quatro jeitos distintos, todos
    virando **500** numa rota de leitura:

    - sufixo `Z` → `ValueError` no `fromisoformat` do 3.10 (o runtime antes
      do 3.12);
    - offset (`+00:00`) → o valor volta ciente, e comparar com o ingênuo de
      `utc_now_naive()` levanta `TypeError`;
    - valor não-string (um número, um `null` que virou `0`) → `TypeError`;
    - a própria entrada não ser um dict → `AttributeError` no `.get`.

    A receita é a de `artifacts_router._recusar_se_token_expirado`, que faz
    este mesmo cálculo certo: aceita `Z`, normaliza o fuso e, aqui, devolve
    `None` no que não parsear — porque numa LISTAGEM "não consigo ler esta
    data" não é motivo para derrubar a resposta inteira.
    """
    if not isinstance(valor, str) or not valor:
        return None
    try:
        lido = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Normaliza para ingênuo-UTC, que é o contrato das colunas do projeto e o
    # que `utc_now_naive()` devolve.
    if lido.tzinfo is not None:
        lido = lido.astimezone(timezone.utc).replace(tzinfo=None)
    return lido


def listar_pins(
    pin_metadata: Any,
    pinned_outputs: Any,
    *,
    node_ids_existentes: Optional[set[str]] = None,
) -> list[dict]:
    """Os pins de um workflow, com intenção e materialização lado a lado.

    Função pura: não toca no banco. Quem chama passa as duas colunas e, se
    quiser, o conjunto de nós que a definition ainda tem.

    `node_ids_existentes=None` significa "não filtre" — é o que a REST faz hoje.
    Passando o conjunto, pins de nós apagados somem, que é o critério que o
    `get_workflow` do MCP já usa (`app/mcp/saida.py`).

    Percorre a UNIÃO das duas colunas, e não uma delas. Os dois leitores
    anteriores discordavam — a rota iterava `pinned_outputs`, o MCP iterava
    `pin_metadata` — e cada um perdia o que só existia do outro lado: uma
    entrada de `pinned_outputs` sem metadata (resíduo de auto-pin, que o
    despacho ainda pode enviar ao executor) sumia da visão do MCP, e uma
    intenção registrada cujo cache nunca materializou sumia da visão da tela.
    A união não perde nenhum dos dois, e `cached` distingue os casos.

    `expired` tem TRÊS valores, não dois: `True`, `False` e `None`. `None` é
    "há uma data gravada e eu não consigo lê-la" — que não é a mesma coisa que
    "não expira" (esse é `expires_at: None`), e achatar os dois em `False`
    esconderia dado corrompido atrás de uma resposta tranquilizadora.
    """
    metadata = pin_metadata if isinstance(pin_metadata, dict) else {}
    saidas = pinned_outputs if isinstance(pinned_outputs, dict) else {}
    agora = utc_now_naive()

    # `dict.fromkeys` para preservar a ordem de inserção e remover repetição —
    # a ordenação final é por `node_id`, mas a origem determinística ajuda
    # quando duas chaves colidem depois do `str()`.
    todos = dict.fromkeys([*metadata.keys(), *saidas.keys()])

    pins: list[dict] = []
    for node_id in todos:
        nid = str(node_id)
        if node_ids_existentes is not None and nid not in node_ids_existentes:
            continue

        # A entrada pode não ser um dict: `.get` num valor solto é AttributeError.
        bruto = metadata.get(node_id)
        meta = bruto if isinstance(bruto, dict) else {}
        expires_at = meta.get("expires_at")
        instante = _instante(expires_at)

        if not expires_at:
            expirado: Optional[bool] = False
        elif instante is None:
            expirado = None
        else:
            expirado = agora > instante

        ref = saidas.get(node_id)
        pins.append({
            "node_id": nid,
            "pinned_at": meta.get("pinned_at"),
            "expires_at": expires_at if isinstance(expires_at, str) else None,
            "ttl_hours": meta.get("ttl_hours") if isinstance(meta.get("ttl_hours"), int) else None,
            "expired": expirado,
            # "o cache já existe" — a resposta para "por que ainda recalcula".
            "cached": isinstance(ref, dict) and bool(ref.get("__pin_s3_key__")),
        })

    pins.sort(key=lambda p: p["node_id"])
    return pins


# ── O portão do nó de saída ──────────────────────────────────────────────────


def e_no_de_saida(nome_do_no: Any) -> bool:
    """O nó grava um arquivo, e por isso não pode ter a saída fixada.

    Fixar a saída de um nó de saída cria um artefato fantasma: o executor
    reaproveita o valor congelado e **suprime a gravação**, então o fluxo
    "roda com sucesso" e o arquivo que ele existia para produzir não aparece.
    O pin fica lá, parecendo estar ajudando.

    Lê `NODE_REGISTRY` direto, e **não** `NodeService.list_nodes`, que filtra os
    nós desabilitados pelo admin: um nó de saída desabilitado continua sendo nó
    de saída, e este portão não pode abrir por causa de uma decisão de catálogo.

    Nome desconhecido → `False`. Recusar o que não se reconhece transformaria
    todo nó novo, ou de uma versão anterior do registro, em nó não-fixável.
    """
    if not isinstance(nome_do_no, str) or not nome_do_no:
        return False
    from flow.registry import NODE_REGISTRY

    classe = NODE_REGISTRY.get(nome_do_no)
    if classe is None:
        return False
    try:
        descricao = classe.description() or {}
    except Exception:  # noqa: BLE001 — descriptor quebrado não fecha o portão
        logger.warning("description() do nó '%s' levantou; portão de pin aberto.", nome_do_no)
        return False
    return descricao.get("type") == TIPO_DE_SAIDA


def nome_do_no_na_definition(definition: Any, node_id: str) -> Optional[str]:
    """O `name` do nó (a chave do registro), lido da definition. `None` se não há."""
    if not isinstance(definition, dict):
        return None
    nos = definition.get("nodes")
    if not isinstance(nos, list):
        return None
    for no in nos:
        if isinstance(no, dict) and str(no.get("id")) == str(node_id):
            nome = no.get("name")
            return nome if isinstance(nome, str) else None
    return None


# ── Escrita ──────────────────────────────────────────────────────────────────


class PinEmNoDeSaidaError(ValueError):
    """Pedido de pin num nó cuja saída é um arquivo gravado."""


class NoInexistenteError(ValueError):
    """Pedido de pin num `node_id` que a definition não tem."""


def _validar_ttl(ttl_hours: Optional[int]) -> Optional[int]:
    """`None` = sem expiração. Fora disso, um inteiro dentro da faixa.

    `0` é recusado de propósito em vez de aceito: no código anterior ele caía
    no ramo falsy e virava "sem expiração" — o oposto do que quem digita `0`
    está pedindo, e em silêncio. Quem quer "sem expiração" manda `null`.
    """
    if ttl_hours is None:
        return None
    if not isinstance(ttl_hours, int) or isinstance(ttl_hours, bool):
        raise ValueError("ttl_hours deve ser um número inteiro de horas ou nulo.")
    if ttl_hours < 1 or ttl_hours > TTL_MAXIMO_HORAS:
        raise ValueError(
            f"ttl_hours deve estar entre 1 e {TTL_MAXIMO_HORAS} horas "
            f"(um ano), ou nulo para não expirar."
        )
    return ttl_hours


async def fixar_saida(
    db: AsyncSession,
    wf,
    node_id: str,
    *,
    outputs: Optional[dict] = None,
    ttl_hours: Optional[int] = None,
    user_id: Optional[str] = None,
    exigir_no_existente: bool = True,
) -> dict:
    """Marca o nó para ter a saída congelada a partir da próxima execução.

    `outputs={}` (o default) é o caso normal e o único que o MCP usa: significa
    "fixe na próxima run" — o nó roda uma vez e o auto-pin grava o cache. Um
    dict com conteúdo é gravado como veio, para paridade com a rota de hoje,
    e o despacho o coage a `{}` de qualquer forma
    (`workflow_execution_service._safe_pinned_outputs`).

    `exigir_no_existente=False` existe para a REST não passar a recusar o que
    aceitava: fixar um `node_id` que não está na definition é inútil, mas
    transformar isso em erro é mudança de contrato de uma rota que a tela usa.
    O MCP pede a checagem; a rota, não.
    """
    ttl = _validar_ttl(ttl_hours)

    nome = nome_do_no_na_definition(getattr(wf, "definition", None), node_id)
    if nome is None and exigir_no_existente:
        raise NoInexistenteError(f"O fluxo não tem nó com id '{node_id}'.")
    if e_no_de_saida(nome):
        raise PinEmNoDeSaidaError(
            f"O nó '{node_id}' ({nome}) grava um arquivo. Fixar a saída dele faria o "
            f"executor reaproveitar o valor congelado e PULAR a gravação — o fluxo "
            f"terminaria com sucesso e sem produzir o arquivo."
        )

    # Auditoria (SEG-10): NUNCA gravar o `outputs` do cliente. Antes, um `outputs`
    # com `__pin_s3_key__` forjado era persistido aqui e, no desfixar, virava um
    # delete de objeto de OUTRO workspace. O despacho ja coage tudo a `{}`
    # (`_safe_pinned_outputs`) e a referencia real do pin so e escrita pelo
    # consumer (server-side, com prefixo pin-cache/{workspace}/…). Gravar `{}`
    # significa "fixe na proxima run" sem nenhum caminho de forja.
    if outputs and any(isinstance(k, str) and k.startswith("__pin") for k in outputs):
        raise ValueError("outputs de pin nao pode conter chaves internas (__pin*).")
    pinned = dict(wf.pinned_outputs or {})
    pinned[node_id] = {}
    wf.pinned_outputs = pinned
    flag_modified(wf, "pinned_outputs")

    agora = utc_now_naive()
    meta = dict(wf.pin_metadata or {})
    entrada = {
        "pinned_at": agora.isoformat(),
        "ttl_hours": ttl,
        "expires_at": (agora + timedelta(hours=ttl)).isoformat() if ttl else None,
        "pinned_by": user_id,
    }
    meta[node_id] = entrada
    wf.pin_metadata = meta
    flag_modified(wf, "pin_metadata")

    await db.commit()
    return {
        "pinned": node_id,
        "total_pinned": len(pinned),
        "pinned_at": entrada["pinned_at"],
        "expires_at": entrada["expires_at"],
        "ttl_hours": ttl,
    }


async def _artefato_de_pin(db: AsyncSession, workflow_hash: str, node_id: str):
    """A linha de pin-cache do nó, ou `None`. A MAIS NOVA, se houver mais de uma.

    Era `scalar_one_or_none()`, que levanta `MultipleResultsFound` com duas
    linhas — e duas linhas são alcançáveis: `artifacts` não tem constraint
    única em `(workflow_hash, node_id, is_pinned)` (`models/artifact.py`), e o
    `_upsert_pin_artifact` do consumidor insere quando não acha. Dois runs do
    mesmo fluxo terminando juntos não acham nada, cada um insere a sua, e a
    partir daí toda leitura levantava.

    `ORDER BY id DESC LIMIT 1` em vez de índice único porque o deploy não roda
    migração e um `CREATE UNIQUE INDEX` falharia se a duplicata já existir em
    produção. O índice fica registrado para depois que o dado estiver limpo.
    """
    resultado = await db.execute(
        select(Artifact)
        .where(
            Artifact.workflow_hash == workflow_hash,
            Artifact.node_id == node_id,
            Artifact.is_pinned.is_(True),
        )
        .order_by(Artifact.id.desc())
        .limit(1)
    )
    return resultado.scalar_one_or_none()


async def desfixar_saida(db: AsyncSession, wf, node_id: str) -> dict:
    """Desfixa o nó e apaga o objeto de cache — nessa ordem, de propósito.

    A ordem é a decisão central deste módulo, e ela diverge do irmão
    `artifacts_router`, que apaga do storage primeiro com `delete_strict_async`
    e devolve 502 na falha. Aqui é o contrário, porque os dois modos de falha
    não pesam o mesmo:

    - **objeto órfão no MinIO** (commit ok, storage falhou): bytes
      desperdiçados. O reconcile varre, e nada no produto quebra.
    - **referência pendurada** (storage ok, commit falhou): `pinned_outputs`
      continua com um `__pin_s3_key__` apontando para um objeto que não existe
      mais. O executor pede o objeto, não acha, e o pin fica quebrado **para
      sempre** — `_safe_pinned_outputs` só dispara auto-pin com ref vazia, e
      nada zera a ref sozinho.

    Então o banco fecha primeiro e o storage depois. A falha do storage vira
    `storage_warning` na resposta, não exceção: o pin já saiu, e responder erro
    faria o cliente repetir um unpin que já aconteceu.
    """
    pinned = dict(wf.pinned_outputs or {})
    estava = node_id in pinned
    ref = pinned.pop(node_id, None)
    wf.pinned_outputs = pinned or None
    flag_modified(wf, "pinned_outputs")

    meta = dict(wf.pin_metadata or {})
    tinha_meta = meta.pop(node_id, None) is not None
    wf.pin_metadata = meta or None
    flag_modified(wf, "pin_metadata")

    artefato = await _artefato_de_pin(db, wf.id_hash, node_id)
    # As duas chaves podem divergir; apagar as duas é o que não deixa objeto
    # para trás. `dict.fromkeys` preserva a ordem e remove a repetição.
    #
    # Auditoria (SEG-10): só apaga chave DENTRO do prefixo do workspace deste
    # fluxo. As chaves legítimas são derivadas no servidor como
    # `pin-cache/{workspace_id}/…`; qualquer chave fora disso (entrada forjada
    # antiga) é ignorada, não apagada.
    prefixo = f"pin-cache/{wf.workspace_id}/"
    chaves = dict.fromkeys(
        k for k in (
            ref.get("__pin_s3_key__") if isinstance(ref, dict) else None,
            getattr(artefato, "s3_key", None),
        )
        if isinstance(k, str) and k.startswith(prefixo) and ".." not in k
    )
    if artefato is not None:
        await db.delete(artefato)

    await db.commit()

    aviso: Optional[str] = None
    if chaves:
        from app.core import storage as s3

        falhas = []
        for chave in chaves:
            try:
                await s3.delete_strict_async(chave, allow_missing=True)
            except Exception as exc:  # noqa: BLE001 — o pin já saiu; isto é relato
                logger.error(
                    "Unpin de %s/%s: objeto %s ficou no storage (%s). O pin já foi "
                    "removido; o reconcile recolhe o órfão.",
                    wf.id_hash, node_id, chave, exc,
                )
                falhas.append(chave)
        if falhas:
            aviso = (
                f"O pin foi removido, mas {len(falhas)} objeto(s) de cache não "
                f"puderam ser apagados do storage e serão recolhidos depois."
            )

    return {
        "unpinned": node_id,
        "outcome": "unpinned" if (estava or tinha_meta) else "not_pinned",
        "total_pinned": len(pinned),
        **({"storage_warning": aviso} if aviso else {}),
    }
