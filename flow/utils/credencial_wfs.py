# flow/utils/credencial_wfs.py
#
# The credential of a WFS service, from `http_auth` (what the server injects when
# resolving the saved credential — see app/services/credential_resolver.py) to
# what signs each request: the key of GeoServer's authkey module, as a URL
# parameter (its default) or as a header, or username and password (Basic,
# the "wfs" credential).
#
# Lives here, and not in the node, because three sides read the SAME credential
# and must accept and reject the same things: the WFS node, on the executor (via
# owslib), the editor's layer listing, on the server (`GET /nodes/wfs/layers`, via
# httpx), and the Credentials screen, on save and on "Testar" (see
# app/services/credential_service.py). Copies of the rules would diverge at the
# first change — and the editor would list with a credential the run
# rejects, or the screen would save one that nobody can use.
import base64
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, quote_plus

_KEY_NAME_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
# Headers that decide the request's destination or framing: the key in place
# of one of them would send the request to another virtual host, or break it.
_RESERVED_HEADERS = {"host", "content-length", "transfer-encoding", "connection"}
# WFS's own parameters: a key with one of these names would be erased or
# overwritten by owslib when building the requests (and the request would go out without it).
_WFS_PARAMETERS = {
    "service", "version", "request", "typename", "typenames", "count", "maxfeatures",
    "startindex", "outputformat", "srsname", "bbox", "cql_filter", "filter", "resulttype",
    "sortby", "propertyname", "featureid", "resourceid", "namespaces", "exceptions",
}
# Control characters (CR/LF in the middle of the key): `requests` rejects the
# header by repeating the ESCAPED key in the message — a form the redaction does
# not recognize.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

# Below this the secret cannot be protected in messages: redacting
# "geo" or "2024" would mangle every error message ("C***m***d***") and, through
# the LogRecord factory (segredos_vivos), dates and ids in every log of the
# process while the fetch runs. A GeoServer authkey is a UUID; a password
# shorter than this is weak anyway. It is the same minimum as
# `segredos_vivos._MIN_LENGTH`.
MIN_SECRET_LENGTH = 6


@dataclass(frozen=True, repr=False)
class AutenticacaoWFS:
    tipo: str                 # "authkey" | "basic"
    segredo: str              # a chave (authkey) ou a senha (basic)
    nome: str = "authkey"     # the key's parameter (or header)
    no_cabecalho: bool = False
    usuario: str = ""

    def __repr__(self) -> str:
        return f"AutenticacaoWFS(tipo={self.tipo!r}, nome={self.nome!r}, no_cabecalho={self.no_cabecalho})"

    @property
    def fingerprint(self) -> str:
        """Identifies the credential in a cache without storing the secret in plain text."""
        # JSON, and not "|".join: with the separator, user "a|b" with password "c"
        # and user "a" with password "b|c" gave the same fingerprint.
        bruto = json.dumps([self.tipo, self.nome, self.no_cabecalho, self.usuario, self.segredo])
        return hashlib.sha256(bruto.encode()).hexdigest()[:24]

    def parametros(self) -> dict[str, str]:
        """The URL parameters of a hand-made request: the key, when it goes in the URL."""
        if self.tipo == "authkey" and not self.no_cabecalho:
            return {self.nome: self.segredo}
        return {}

    def cabecalhos(self) -> dict[str, str]:
        """The headers of a hand-made request: the key in the header, or Basic."""
        if self.tipo == "basic":
            return {"Authorization": f"Basic {self._basic_pair()}"}
        if self.no_cabecalho:
            return {self.nome: self.segredo}
        return {}

    def _basic_pair(self) -> str:
        """`base64(usuario:senha)` — the form in which the password TRAVELS in the header."""
        return base64.b64encode(f"{self.usuario}:{self.segredo}".encode()).decode()


def _short_secret(o_que: str) -> ValueError:
    return ValueError(
        f"{o_que} tem menos de {MIN_SECRET_LENGTH} caracteres. Um segredo tão curto não "
        f"tem como ser protegido nas mensagens de erro e nos logs; use um maior."
    )


def wfs_authentication(credential_id: Any, http_auth: Any) -> AutenticacaoWFS | None:
    """The resolved, validated credential — or None (public service)."""
    # The server REMOVES `credential_id` when injecting `http_auth` (see the
    # resolver). Id present and nothing injected = the resolution did not happen:
    # credential deleted, outside the scope of whoever triggered the run, or orphaned.
    # Proceeding anonymously here would return only what the server shows anyone.
    if credential_id and not http_auth:
        raise ValueError(
            "A credencial escolhida para este nó não pôde ser resolvida — ela pode ter sido "
            "apagada, não estar acessível a quem disparou a execução, ou ser de um tipo que o nó "
            "WFS não usa (use uma do tipo 'GeoServer (authkey)' ou 'WFS'). A consulta NÃO foi "
            "feita, para não sair sem autenticação."
        )
    if not isinstance(http_auth, dict) or not http_auth.get("type"):
        return None
    tipo = http_auth.get("type")
    if tipo == "geoserver_authkey":
        chave = str(http_auth.get("token") or "").strip()
        if not chave:
            raise ValueError("A credencial authkey escolhida não tem a chave preenchida.")
        if _CONTROL_RE.search(chave):
            raise ValueError("A chave da credencial authkey tem caracteres de controle (quebra de linha?).")
        if len(chave) < MIN_SECRET_LENGTH:
            raise _short_secret("A chave da credencial authkey")
        # The Credentials screen only DISPLAYS these fields' default; empty = default.
        nome = str(http_auth.get("parameter") or "").strip() or "authkey"
        if not _KEY_NAME_RE.fullmatch(nome):
            raise ValueError(f"O nome do parâmetro da credencial authkey não é válido: {nome!r}.")
        local = str(http_auth.get("location") or "").strip().lower() or "url"
        if local not in ("url", "header"):
            raise ValueError(f"A credencial authkey diz enviar a chave como {local!r}; use 'url' ou 'header'.")
        if local == "header" and nome.lower() in _RESERVED_HEADERS:
            raise ValueError(f"A credencial authkey não pode mandar a chave no cabeçalho {nome!r}.")
        if local == "header" and not (chave.isascii() and chave.isprintable()):
            # The strictest transport decides: the listing's httpx only accepts
            # ASCII in a header, and the node's http.client only latin-1 — and both
            # fail with a codec error that does not say the problem is the key.
            raise ValueError(
                "A chave da credencial authkey tem caracteres fora do ASCII; no modo cabeçalho só "
                "letras, dígitos e pontuação simples são aceitos (confira se não há aspas curvas "
                "ou acentos colados à chave)."
            )
        if local == "url" and nome.lower() in _WFS_PARAMETERS:
            raise ValueError(f"O nome do parâmetro da credencial authkey é um parâmetro do próprio WFS: {nome!r}.")
        return AutenticacaoWFS("authkey", chave, nome, local == "header")
    if tipo == "wfs":
        usuario = str(http_auth.get("username") or "")
        senha = str(http_auth.get("password") or "")
        if not usuario or not senha:
            raise ValueError("A credencial WFS escolhida não tem usuário e senha preenchidos.")
        if len(senha) < MIN_SECRET_LENGTH:
            raise _short_secret("A senha da credencial WFS")
        return AutenticacaoWFS("basic", senha, usuario=usuario)
    raise ValueError(
        f"A credencial escolhida (tipo '{tipo}') não serve para o nó WFS: use uma do tipo "
        f"'GeoServer (authkey)' ou 'WFS'."
    )


def secret_forms(auth: AutenticacaoWFS | None) -> tuple[str, ...]:
    """The secret in plain text and in every form in which it TRAVELS — largest first.

    In the URL it goes percent-encoded (`quote`/`quote_plus`); in Basic it goes as
    `base64(usuario:senha)`, and that is the form that a proxy or WAF echoing the
    request headers puts on its error page — trivially reversible.
    Forms below the minimum are left out: they cannot be redacted without mangling
    the surrounding text (and `wfs_authentication` already rejects such a short secret).
    """
    if auth is None or not auth.segredo:
        return ()
    brutas = {auth.segredo}
    if auth.tipo == "basic":
        brutas.add(auth._basic_pair())
    formas = set()
    for bruta in brutas:
        formas.update({bruta, quote(bruta, safe=""), quote_plus(bruta)})
    return tuple(sorted((f for f in formas if len(f) >= MIN_SECRET_LENGTH), key=len, reverse=True))


def without_secret(texto: str, auth: AutenticacaoWFS | None) -> str:
    """The text without the secret — in plain text and in the forms in which it travels."""
    for forma in secret_forms(auth):
        texto = texto.replace(forma, "***")
    return texto
