# flow/utils/credencial_wfs.py
#
# A credencial de um serviço WFS, de `http_auth` (o que o servidor injeta ao
# resolver a credencial salva — ver app/services/credential_resolver.py) até o
# que assina cada pedido: a chave do módulo authkey do GeoServer, como
# parâmetro da URL (o padrão dele) ou como cabeçalho, ou usuário e senha (Basic,
# a credencial "wfs").
#
# Mora aqui, e não no nó, porque três lados leem a MESMA credencial e têm de
# aceitar e recusar as mesmas coisas: o nó WFS, no executor (pelo owslib), a
# listagem de camadas do editor, no servidor (`GET /nodes/wfs/layers`, pelo
# httpx), e a tela de Credenciais, ao gravar e ao "Testar" (ver
# app/services/credential_service.py). Cópias das regras divergiriam na
# primeira mudança — e o editor listaria com uma credencial que a execução
# recusa, ou a tela gravaria uma que ninguém consegue usar.
import base64
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, quote_plus

_NOME_DA_CHAVE_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
# Cabeçalhos que decidem o destino ou o enquadramento do pedido: a chave no
# lugar de um deles mandaria o pedido a outro virtual host, ou o quebraria.
_CABECALHOS_RESERVADOS = {"host", "content-length", "transfer-encoding", "connection"}
# Parâmetros do próprio WFS: a chave com um destes nomes seria apagada ou
# sobrescrita pelo owslib ao montar os pedidos (e o pedido sairia sem ela).
_PARAMETROS_DO_WFS = {
    "service", "version", "request", "typename", "typenames", "count", "maxfeatures",
    "startindex", "outputformat", "srsname", "bbox", "cql_filter", "filter", "resulttype",
    "sortby", "propertyname", "featureid", "resourceid", "namespaces", "exceptions",
}
# Caracteres de controle (CR/LF no meio da chave): o `requests` recusa o
# cabeçalho repetindo a chave ESCAPADA na mensagem — forma que a redação não
# reconhece.
_CONTROLE_RE = re.compile(r"[\x00-\x1f\x7f]")

# Abaixo disto o segredo não tem como ser protegido nas mensagens: redigir
# "geo" ou "2024" mutilaria toda mensagem de erro ("C***m***d***") e, pela
# fábrica de LogRecord (segredos_vivos), datas e ids de todo log do processo
# enquanto a busca roda. Uma chave authkey do GeoServer é um UUID; uma senha
# menor que isto é fraca de qualquer jeito. É o mesmo mínimo de
# `segredos_vivos._TAMANHO_MINIMO`.
TAMANHO_MINIMO_DO_SEGREDO = 6


@dataclass(frozen=True, repr=False)
class AutenticacaoWFS:
    tipo: str                 # "authkey" | "basic"
    segredo: str              # a chave (authkey) ou a senha (basic)
    nome: str = "authkey"     # o parâmetro (ou cabeçalho) da chave
    no_cabecalho: bool = False
    usuario: str = ""

    def __repr__(self) -> str:
        return f"AutenticacaoWFS(tipo={self.tipo!r}, nome={self.nome!r}, no_cabecalho={self.no_cabecalho})"

    @property
    def impressao(self) -> str:
        """Identifica a credencial num cache sem guardar o segredo em claro."""
        # JSON, e não "|".join: com o separador, o usuário "a|b" com a senha "c"
        # e o usuário "a" com a senha "b|c" davam a mesma impressão.
        bruto = json.dumps([self.tipo, self.nome, self.no_cabecalho, self.usuario, self.segredo])
        return hashlib.sha256(bruto.encode()).hexdigest()[:24]

    def parametros(self) -> dict[str, str]:
        """Os parâmetros de URL de um pedido feito à mão: a chave, quando vai na URL."""
        if self.tipo == "authkey" and not self.no_cabecalho:
            return {self.nome: self.segredo}
        return {}

    def cabecalhos(self) -> dict[str, str]:
        """Os cabeçalhos de um pedido feito à mão: a chave no cabeçalho, ou o Basic."""
        if self.tipo == "basic":
            return {"Authorization": f"Basic {self._par_do_basic()}"}
        if self.no_cabecalho:
            return {self.nome: self.segredo}
        return {}

    def _par_do_basic(self) -> str:
        """`base64(usuario:senha)` — a forma em que a senha VIAJA no cabeçalho."""
        return base64.b64encode(f"{self.usuario}:{self.segredo}".encode()).decode()


def _segredo_curto(o_que: str) -> ValueError:
    return ValueError(
        f"{o_que} tem menos de {TAMANHO_MINIMO_DO_SEGREDO} caracteres. Um segredo tão curto não "
        f"tem como ser protegido nas mensagens de erro e nos logs; use um maior."
    )


def autenticacao_wfs(credential_id: Any, http_auth: Any) -> AutenticacaoWFS | None:
    """A credencial resolvida, validada — ou None (serviço público)."""
    # O servidor REMOVE `credential_id` ao injetar `http_auth` (ver o
    # resolver). Id presente e nada injetado = a resolução não aconteceu:
    # credencial apagada, fora do escopo de quem disparou, ou órfã. Seguir
    # anônimo aqui devolveria só o que o servidor mostra a qualquer um.
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
        if _CONTROLE_RE.search(chave):
            raise ValueError("A chave da credencial authkey tem caracteres de controle (quebra de linha?).")
        if len(chave) < TAMANHO_MINIMO_DO_SEGREDO:
            raise _segredo_curto("A chave da credencial authkey")
        # A tela de Credenciais só EXIBE o padrão destes campos; vazio = padrão.
        nome = str(http_auth.get("parameter") or "").strip() or "authkey"
        if not _NOME_DA_CHAVE_RE.fullmatch(nome):
            raise ValueError(f"O nome do parâmetro da credencial authkey não é válido: {nome!r}.")
        local = str(http_auth.get("location") or "").strip().lower() or "url"
        if local not in ("url", "header"):
            raise ValueError(f"A credencial authkey diz enviar a chave como {local!r}; use 'url' ou 'header'.")
        if local == "header" and nome.lower() in _CABECALHOS_RESERVADOS:
            raise ValueError(f"A credencial authkey não pode mandar a chave no cabeçalho {nome!r}.")
        if local == "header" and not (chave.isascii() and chave.isprintable()):
            # O transporte mais estrito decide: o httpx da listagem só aceita
            # ASCII num cabeçalho, e o http.client do nó só latin-1 — e os dois
            # falham com um erro de codec que não diz que o problema é a chave.
            raise ValueError(
                "A chave da credencial authkey tem caracteres fora do ASCII; no modo cabeçalho só "
                "letras, dígitos e pontuação simples são aceitos (confira se não há aspas curvas "
                "ou acentos colados à chave)."
            )
        if local == "url" and nome.lower() in _PARAMETROS_DO_WFS:
            raise ValueError(f"O nome do parâmetro da credencial authkey é um parâmetro do próprio WFS: {nome!r}.")
        return AutenticacaoWFS("authkey", chave, nome, local == "header")
    if tipo == "wfs":
        usuario = str(http_auth.get("username") or "")
        senha = str(http_auth.get("password") or "")
        if not usuario or not senha:
            raise ValueError("A credencial WFS escolhida não tem usuário e senha preenchidos.")
        if len(senha) < TAMANHO_MINIMO_DO_SEGREDO:
            raise _segredo_curto("A senha da credencial WFS")
        return AutenticacaoWFS("basic", senha, usuario=usuario)
    raise ValueError(
        f"A credencial escolhida (tipo '{tipo}') não serve para o nó WFS: use uma do tipo "
        f"'GeoServer (authkey)' ou 'WFS'."
    )


def formas_do_segredo(auth: AutenticacaoWFS | None) -> tuple[str, ...]:
    """O segredo em claro e em toda forma em que ele VIAJA — maiores primeiro.

    Na URL ele vai percent-encoded (`quote`/`quote_plus`); no Basic vai como
    `base64(usuario:senha)`, e é essa forma que um proxy ou WAF que ecoa os
    cabeçalhos do pedido põe na página de erro — trivialmente reversível.
    Formas abaixo do mínimo ficam de fora: não dá para redigi-las sem mutilar
    o texto em volta (e `autenticacao_wfs` já não aceita segredo tão curto).
    """
    if auth is None or not auth.segredo:
        return ()
    brutas = {auth.segredo}
    if auth.tipo == "basic":
        brutas.add(auth._par_do_basic())
    formas = set()
    for bruta in brutas:
        formas.update({bruta, quote(bruta, safe=""), quote_plus(bruta)})
    return tuple(sorted((f for f in formas if len(f) >= TAMANHO_MINIMO_DO_SEGREDO), key=len, reverse=True))


def sem_segredo(texto: str, auth: AutenticacaoWFS | None) -> str:
    """O texto sem o segredo — em claro e nas formas em que ele viaja."""
    for forma in formas_do_segredo(auth):
        texto = texto.replace(forma, "***")
    return texto
