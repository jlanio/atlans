# app/services/credential_resolver.py
# Resolução e injeção de credenciais em definições de workflow.

import copy
from typing import Collection
from uuid import UUID

from app.core.authorization.credential_loader import resolve_credentials_from_ids

# Credenciais que não descrevem uma conexão, e sim como assinar uma requisição
# HTTP. Vão para o nó em `http_auth` em vez de `connectionString`: o nó monta a
# autenticação a partir daí — o `Authorization` do HttpRequest, a chave authkey
# (parâmetro ou cabeçalho) e o Basic do nó WFS.
#
# SEGURANÇA — "usar" um segredo destes ≡ "poder extraí-lo". O nó de requisição
# HTTP monta `Authorization: Bearer/Basic <segredo>` e envia para a URL que o
# AUTOR do nó escolhe; o SSRF-guard barra alvo interno, não exfiltração para um
# host público. Portanto, quem tem permissão de USAR uma credencial HTTP (hoje:
# qualquer membro do workspace do workflow) consegue lê-la apontando um nó para
# um servidor próprio. Diferente das credenciais de banco, cujo destino é
# embutido no DSN e não é parâmetro do autor — essas são usáveis sem serem
# extraíveis. Consequência de produto: compartilhar uma credencial HTTP com o
# workspace é, na prática, confiar o token aos membros (a UI avisa disso). Se
# um dia for preciso "usar sem poder extrair" para tipos HTTP, a mitigação é no
# nó/egress (allowlist de destino quando há credencial), não aqui. O mesmo vale
# para as do WFS: a URL do nó também é do autor.
_TIPOS_AUTH_HTTP = ("http_bearer", "http_basic", "wfs", "geoserver_authkey")

# Campos que podem compor a autenticação. Lista fechada de propósito: a
# credencial descriptografada carrega outras chaves (`expires_at`, `type`) que
# não têm por que atravessar até o executor. Por TIPO, valem só os que o
# catálogo de credenciais declara para ele (`_campos_de_autenticacao`): uma
# credencial que já foi de outro tipo carrega campos a mais no `data`, e o
# `password` de quando era Basic não deve viajar junto com a chave authkey.
_CAMPOS_AUTH_HTTP = ("token", "username", "password", "parameter", "location")


# A credencial `s3` entra no nó em `s3_auth`, com os campos do catálogo e nada
# mais (lista fechada pelo mesmo motivo de `_CAMPOS_AUTH_HTTP`). O nó monta o
# cliente com `flow.utils.s3_cliente.cliente_s3` — o mesmo do teste de conexão.
_CAMPOS_S3 = ("access_key_id", "secret_access_key", "region", "bucket", "endpoint_url")


def s3_auth_da_credencial(cred: dict) -> dict | None:
    """O `s3_auth` que o nó recebe de uma credencial resolvida — ou None, se ela
    não é do tipo `s3`."""
    if cred.get("type") != "s3":
        return None
    return {campo: cred[campo] for campo in _CAMPOS_S3 if cred.get(campo) not in (None, "")}


def _campos_de_autenticacao(tipo: str) -> tuple[str, ...]:
    from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS

    esquema = CREDENTIAL_TYPE_SCHEMAS.get(tipo)
    if esquema is None:
        return _CAMPOS_AUTH_HTTP
    return tuple(f.key for f in esquema.fields if f.key in _CAMPOS_AUTH_HTTP)


def http_auth_da_credencial(cred: dict) -> dict | None:
    """O `http_auth` que o nó recebe de uma credencial resolvida — ou None, se
    ela não assina requisição HTTP (as de banco viram `connectionString`).

    Também é o que a listagem de camadas do WFS no editor usa, para listar com a
    MESMA autenticação que a execução vai usar.
    """
    tipo = cred.get("type")
    if tipo not in _TIPOS_AUTH_HTTP:
        return None
    return {
        "type": tipo,
        **{campo: cred[campo] for campo in _campos_de_autenticacao(tipo) if campo in cred},
    }


def _id_canonico(cid) -> str:
    """O id como o resolver o devolve (UUID em minúsculas). Gravado em
    maiúsculas no nó, ele não casava com nada e a credencial sumia sem aviso —
    enquanto a guarda (`assert_credentials_accessible`), que converte para
    UUID, o aceitava."""
    try:
        return str(UUID(str(cid)))
    except (ValueError, AttributeError, TypeError):
        return str(cid)


def propriedade_que_recebe(tipo: str) -> str | None:
    """Onde uma credencial deste tipo entra no nó: `http_auth` (as que assinam
    requisição HTTP), `s3_auth` (a do S3), `connectionString` (as de banco) — ou
    None (as que o nó usa pelo próprio id, como `webhook_token`, e os tipos
    livres)."""
    if tipo in _TIPOS_AUTH_HTTP:
        return "http_auth"
    if tipo == "s3":
        return "s3_auth"
    if tipo in ("postgresql", "mysql"):
        return "connectionString"
    return None


def tipos_aceitos_do_descriptor(descriptor: dict) -> frozenset | None:
    """Os tipos de credencial que o `credential_id` do descriptor aceita — ou
    None quando o campo não existe ou não traz a lista."""
    for prop in descriptor.get("properties") or []:
        if isinstance(prop, dict) and prop.get("name") == "credential_id" and prop.get("credential_types"):
            return frozenset(prop["credential_types"])
    return None


def _contrato_do_no(node: dict) -> tuple[frozenset | None, frozenset | None]:
    """(tipos de credencial que o nó aceita, propriedades que ele declara) —
    cada um None quando não dá para saber (nó fora do registro, descriptor
    quebrado, campo sem a lista): aí vale o de sempre, sem filtro.

    Só a tela filtra a credencial pelo tipo; pela API e pelo assistente chega
    qualquer uma. É aqui, com o que o nó declara, que o servidor confere. E o
    que se injeta tem de ser uma propriedade DECLARADA: `validate()` reconstrói
    os parâmetros a partir da lista do descriptor e descartaria o resto — o nó
    perderia a credencial E o id, e sairia anônimo sem ninguém avisar.
    """
    from flow.registry import NODE_REGISTRY

    cls = NODE_REGISTRY.get(node.get("name") or (node.get("data") or {}).get("name") or "")
    if cls is None:
        return None, None
    try:
        descriptor = cls.description()
    except Exception:  # descriptor quebrado não derruba o disparo
        return None, None
    declaradas = frozenset(
        p.get("name") for p in descriptor.get("properties") or [] if isinstance(p, dict) and p.get("name")
    )
    return tipos_aceitos_do_descriptor(descriptor), declaradas


async def inject_credentials(
    definition: dict,
    pre_resolved: dict | None = None,
    *,
    allowed_owner_ids: Collection[str] | None = None,
) -> dict:
    """Injeta credenciais resolvidas nos nós da definição (sem salvar no banco).

    Retorna uma cópia profunda da definition com a credencial injetada
    (`connectionString`, `http_auth` ou `s3_auth`) e `credential_id` removido — só dos nós
    em que houve O QUE injetar. Credencial de um tipo que o nó não declara, ou
    que não vira nem DSN nem autenticação HTTP (`webhook_token` de um
    DataOutput, por exemplo), deixa o id onde está: o nó que precisa do segredo
    recusa por não tê-lo, e o que usa o próprio id (o DataOutput protege o
    artefato com ele) continua o tendo. Antes o id sumia sem nada no lugar — o
    WFS consultava anônimo, e um DataOutput não-público recusava por "exige uma
    credencial" com a credencial escolhida.

    Se pre_resolved for fornecido, pula a chamada ao banco — útil quando
    start_analysis já resolveu credenciais para a validação de triggers. Só o
    caminho sem pre_resolved precisa de `allowed_owner_ids`, que delimita de
    quem as credenciais podem ser (ver credential_loader).

    Sem nenhum `credential_id` a definition volta SEM cópia. O `copy.deepcopy`
    era pago incondicionalmente — ~16 ms para uma definition de 1,7 MB, uma vez
    pela raiz e mais uma por sub-fluxo — para produzir um clone que ninguém ia
    escrever, travando o event loop do worker a cada disparo. O laço abaixo é o
    único escritor, e ele não roda quando `cred_ids` está vazio; o retorno segue
    direto para o envelope do job, que apenas o serializa.
    """
    nodes = definition.get("nodes", [])

    cred_ids = list({
        _id_canonico(props.get("credential_id"))
        for node in nodes
        for props in [(node.get("data", {}).get("properties") or node.get("properties") or {})]
        if props.get("credential_id")
    })

    if not cred_ids:
        return definition

    enriched = copy.deepcopy(definition)

    resolved = (
        pre_resolved
        if pre_resolved is not None
        else await resolve_credentials_from_ids(cred_ids, allowed_owner_ids=allowed_owner_ids)
    )
    for node in enriched.get("nodes", []):
        props = node.get("data", {}).get("properties") or node.get("properties") or {}
        cid = _id_canonico(props.get("credential_id")) if props.get("credential_id") else None
        if not cid or cid not in resolved:
            continue
        cred = resolved[cid]
        aceitos, declaradas = _contrato_do_no(node)
        if aceitos is not None and cred.get("type") not in aceitos:
            # Nada viaja: nem a DSN de um banco até um nó WFS, nem a chave de
            # um GeoServer até um nó de banco.
            continue
        if (http_auth := http_auth_da_credencial(cred)) is not None:
            # Sem esta cláusula, uma credencial HTTP era resolvida, tinha o
            # `credential_id` removido logo abaixo e sumia sem deixar rastro:
            # o nó recebia a definição já sem o id e sem nada no lugar, e a
            # requisição saía anônima. Como só `connectionString` era injetada,
            # os tipos `http_bearer`/`http_basic` — que existem desde sempre e
            # são declarados para nós de ação — não tinham consumidor.
            #
            # O TIPO decide, e antes da DSN: uma credencial que já foi de banco
            # e virou HTTP ainda carrega a `connectionString` antiga no `data`
            # (a edição trocava o tipo e mantinha os campos), e ela ganharia.
            if declaradas is not None and "http_auth" not in declaradas:
                continue  # sem onde receber: o id fica, e o nó recusa por não ter o segredo
            props["http_auth"] = http_auth
        elif (s3_auth := s3_auth_da_credencial(cred)) is not None:
            # O tipo `s3` existia no cofre (com teste de conexão) sem consumidor:
            # o SaveToS3 pedia a chave secreta digitada no nó, em texto puro.
            if declaradas is not None and "s3_auth" not in declaradas:
                continue
            props["s3_auth"] = s3_auth
        elif "connectionString" in cred:
            if declaradas is not None and "connectionString" not in declaradas:
                continue
            props["connectionString"] = cred["connectionString"]
        elif (
            declaradas is not None and "s3_auth" in declaradas
            and props.get("registerArtifact") not in (True, "true", "True", 1, "1")
        ):
            # SaveToS3 com o Webhook Token do uso antigo e sem cópia registrada:
            # o token não protege nada. Deixá-lo faria o nó recusar como
            # "credencial S3 não resolvida" (um id que sobra sem `s3_auth` e
            # sem cópia é o sinal disso) — um fluxo que rodava pararia.
            pass
        else:
            continue  # nada a injetar: o id fica (ver a docstring)
        props.pop("credential_id", None)

    return enriched
