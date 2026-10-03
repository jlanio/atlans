# app/services/credential_resolver.py
# Resolution and injection of credentials into workflow definitions.

import copy
from typing import Collection
from uuid import UUID

from app.core.authorization.credential_loader import resolve_credentials_from_ids

# Credentials that do not describe a connection, but rather how to sign an HTTP
# request. They go to the node in `http_auth` instead of `connectionString`: the
# node builds the authentication from there — the HttpRequest's `Authorization`,
# the authkey key (parameter or header) and the WFS node's Basic.
#
# SECURITY — "using" one of these secrets ≡ "being able to extract it". The HTTP
# request node builds `Authorization: Bearer/Basic <segredo>` and sends it to the
# URL the node's AUTHOR chooses; the SSRF guard blocks internal targets, not
# exfiltration to a public host. Therefore, whoever has permission to USE an HTTP
# credential (today: any member of the workflow's workspace) can read it by
# pointing a node at their own server. Unlike database credentials, whose
# destination is embedded in the DSN and is not an author parameter — those are
# usable without being extractable. Product consequence: sharing an HTTP
# credential with the workspace is, in practice, entrusting the token to the
# members (the UI warns about this). If some day "use without being able to
# extract" is needed for HTTP types, the mitigation belongs in the node/egress
# (destination allowlist when there is a credential), not here. The same goes
# for the WFS ones: the node's URL is also the author's.
_TIPOS_AUTH_HTTP = ("http_bearer", "http_basic", "wfs", "geoserver_authkey")

# Fields that can make up the authentication. A closed list on purpose: the
# decrypted credential carries other keys (`expires_at`, `type`) that have no
# reason to travel all the way to the executor. Per TYPE, only the ones the
# credential catalog declares for it count (`_campos_de_autenticacao`): a
# credential that used to be of another type carries extra fields in `data`,
# and the `password` from when it was Basic must not travel along with the
# authkey key.
_CAMPOS_AUTH_HTTP = ("token", "username", "password", "parameter", "location")


# The `s3` credential goes into the node in `s3_auth`, with the catalog's fields
# and nothing else (closed list for the same reason as `_CAMPOS_AUTH_HTTP`). The
# node builds the client with `flow.utils.s3_cliente.cliente_s3` — the same one
# as the connection test.
_CAMPOS_S3 = ("access_key_id", "secret_access_key", "region", "bucket", "endpoint_url")


def s3_auth_da_credencial(cred: dict) -> dict | None:
    """The `s3_auth` the node receives from a resolved credential — or None, if it
    is not of type `s3`."""
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
    """The `http_auth` the node receives from a resolved credential — or None, if
    it does not sign HTTP requests (database ones become `connectionString`).

    It is also what the WFS layer listing in the editor uses, to list with the
    SAME authentication the execution will use.
    """
    tipo = cred.get("type")
    if tipo not in _TIPOS_AUTH_HTTP:
        return None
    return {
        "type": tipo,
        **{campo: cred[campo] for campo in _campos_de_autenticacao(tipo) if campo in cred},
    }


def _id_canonico(cid) -> str:
    """The id as the resolver returns it (lowercase UUID). Written in
    uppercase on the node, it matched nothing and the credential vanished
    without warning — while the guard (`assert_credentials_accessible`), which
    converts to UUID, accepted it."""
    try:
        return str(UUID(str(cid)))
    except (ValueError, AttributeError, TypeError):
        return str(cid)


def propriedade_que_recebe(tipo: str) -> str | None:
    """Where a credential of this type goes into the node: `http_auth` (the ones
    that sign HTTP requests), `s3_auth` (the S3 one), `connectionString` (the
    database ones) — or None (the ones the node uses by their own id, like
    `webhook_token`, and the free-form types)."""
    if tipo in _TIPOS_AUTH_HTTP:
        return "http_auth"
    if tipo == "s3":
        return "s3_auth"
    if tipo in ("postgresql", "mysql"):
        return "connectionString"
    return None


def tipos_aceitos_do_descriptor(descriptor: dict) -> frozenset | None:
    """The credential types the descriptor's `credential_id` accepts — or
    None when the field does not exist or does not carry the list."""
    for prop in descriptor.get("properties") or []:
        if isinstance(prop, dict) and prop.get("name") == "credential_id" and prop.get("credential_types"):
            return frozenset(prop["credential_types"])
    return None


def _contrato_do_no(node: dict) -> tuple[frozenset | None, frozenset | None]:
    """(credential types the node accepts, properties it declares) —
    each one None when it cannot be known (node outside the registry, broken
    descriptor, field without the list): then the usual applies, no filter.

    Only the screen filters the credential by type; through the API and the
    assistant any credential arrives. It is here, with what the node declares,
    that the server checks. And what gets injected has to be a DECLARED
    property: `validate()` rebuilds the parameters from the descriptor's list and
    would discard the rest — the node would lose the credential AND the id, and
    would go out anonymous without anyone warning.
    """
    from flow.registry import NODE_REGISTRY

    cls = NODE_REGISTRY.get(node.get("name") or (node.get("data") or {}).get("name") or "")
    if cls is None:
        return None, None
    try:
        descriptor = cls.description()
    except Exception:  # a broken descriptor does not bring down the trigger
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
    """Injects resolved credentials into the definition's nodes (without saving to the database).

    Returns a deep copy of the definition with the credential injected
    (`connectionString`, `http_auth` or `s3_auth`) and `credential_id` removed — only
    from the nodes where there was SOMETHING to inject. A credential of a type the
    node does not declare, or that becomes neither a DSN nor HTTP authentication
    (a DataOutput's `webhook_token`, for example), leaves the id where it is: the
    node that needs the secret refuses for not having it, and the one that uses
    its own id (DataOutput protects the artifact with it) still has it. Before,
    the id vanished with nothing in its place — the WFS queried anonymously, and
    a non-public DataOutput refused with "exige uma credencial" (requires a
    credential) with the credential chosen.

    If pre_resolved is provided, it skips the database call — useful when
    start_analysis has already resolved credentials for trigger validation. Only
    the path without pre_resolved needs `allowed_owner_ids`, which delimits whose
    credentials they may be (see credential_loader).

    With no `credential_id` at all, the definition comes back WITHOUT a copy. The
    `copy.deepcopy` was paid unconditionally — ~16 ms for a 1.7 MB definition,
    once for the root and once more per sub-workflow — to produce a clone nobody
    was going to write to, blocking the worker's event loop on every trigger. The
    loop below is the only writer, and it does not run when `cred_ids` is empty;
    the return goes straight into the job envelope, which only serializes it.
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
            # Nothing travels: neither a database's DSN to a WFS node, nor a
            # GeoServer's key to a database node.
            continue
        if (http_auth := http_auth_da_credencial(cred)) is not None:
            # Without this clause, an HTTP credential was resolved, had its
            # `credential_id` removed right below and vanished without a trace:
            # the node received the definition already without the id and with
            # nothing in its place, and the request went out anonymous. Since
            # only `connectionString` was injected, the `http_bearer`/`http_basic`
            # types — which have always existed and are declared for action
            # nodes — had no consumer.
            #
            # The TYPE decides, and before the DSN: a credential that used to be
            # a database one and became HTTP still carries the old
            # `connectionString` in `data` (editing changed the type and kept
            # the fields), and it would win.
            if declaradas is not None and "http_auth" not in declaradas:
                continue  # nowhere to receive it: the id stays, and the node refuses for not having the secret
            props["http_auth"] = http_auth
        elif (s3_auth := s3_auth_da_credencial(cred)) is not None:
            # The `s3` type existed in the vault (with a connection test) with no
            # consumer: SaveToS3 asked for the secret key typed into the node, in plain text.
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
            # SaveToS3 with the Webhook Token from the old usage and no registered
            # copy: the token protects nothing. Leaving it would make the node
            # refuse with "credencial S3 não resolvida" (S3 credential not
            # resolved; an id left over with no `s3_auth` and no copy is the
            # sign of that) — a workflow that used to run would stop.
            pass
        else:
            continue  # nothing to inject: the id stays (see the docstring)
        props.pop("credential_id", None)

    return enriched
