# flow/utils/redacao_log.py
"""Redação de segredos no log por PADRÃO — Bearer, Basic, DSN com senha, PAT,
chave AWS, bloco PEM.

Mora no flow/ porque o flow está nas três imagens (API, executor e o executor
empacotado no desktop). A lista vivia em `app/core/utils/logger.py`, e só os
loggers do app a usavam: o executor, que decifra DSN e monta cabeçalho de
autenticação, logava sem máscara nenhuma. O app reexporta daqui — uma lista só.

Duas formas de ligar:

- `SecretScrubFilter`: filtro por logger (o `get_logger` do app o anexa).
- `instalar_no_processo()`: a fábrica de LogRecord, por onde passa TODO
  registro do processo — inclusive o de biblioteca de terceiro e o de handler
  que ainda nem existe (o executor instala vários: console, arquivos, painel).
  É o mesmo ponto que `segredos_vivos` usa para os segredos em uso.
"""
import logging
import re
import threading

# ── Secret scrubbing ─────────────────────────────────────────────────────────
# Padroes que redigimos ANTES do log ir para stdout/arquivo. Evita que:
#   - Traceback com body de request contendo `"password": "..."` vaze
#   - Header Authorization com JWT chegue ao Loki/CloudWatch
#   - OTPs de enrollment (uso unico mas ainda uteis pra postmortem se
#     capturados) fiquem em plaintext
#   - GitHub PATs / AWS keys / Ed25519 privates deem match acidental
#
# `_SCRUB_PATTERNS` corre em ordem — os mais especificos vem primeiro para
# nao serem mascarados por regras genericas (ex: "Bearer <jwt>" antes de
# "token=..."). O `_REDACTED` mantem o mesmo comprimento visual em qualquer
# match — nao vaza o tamanho do secreto original.
_REDACTED = "<REDACTED>"

_SCRUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Authorization: Bearer <jwt> — case-insensitive
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[\w.\-]+"), rf"\1{_REDACTED}"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{20,}"), rf"\1{_REDACTED}"),
    # Authorization: Basic <base64(usuario:senha)> — a senha do Basic (a
    # credencial "wfs" e a http_basic) viaja assim, e um proxy ou WAF que ecoa
    # os cabeçalhos do pedido a devolve assim, trivialmente reversível.
    (re.compile(r"(?i)(authorization\s*[:=]\s*basic\s+)[A-Za-z0-9+/=_\-]{8,}"), rf"\1{_REDACTED}"),

    # JSON keys sensiveis: "password":"...", "otp":"...", "api_key":"...",
    # "access_token":"...", "refresh_token":"...", "secret":"..."
    (re.compile(
        r'(?i)("(?:password|passwd|otp|api[_-]?key|access[_-]?token|'
        r'refresh[_-]?token|secret|private[_-]?key|fernet[_-]?key|'
        r'signing[_-]?key)"\s*:\s*")[^"]+(")'
    ), rf"\1{_REDACTED}\2"),

    # `authkey` e a chave do modulo authkey do GeoServer, que o no WFS manda na
    # URL — ja codificada: `%2B`, `%2F` e cia. fazem parte dela, e a regra
    # generica abaixo pararia no primeiro `%` deixando o resto da chave.
    (re.compile(r"(?i)\b(authkey)=([^&#\s\"'<>]{6,})"), rf"\1={_REDACTED}"),

    # Query / form: otp=..., password=..., token=... (nao pega palavras curtas).
    (re.compile(
        r"(?i)\b(otp|password|token|api[_-]?key|access[_-]?token|refresh[_-]?token|secret)"
        r"=([\w.\-]{6,})"
    ), rf"\1={_REDACTED}"),

    # GitHub Personal Access Tokens (github_pat_..., ghp_..., ghs_..., etc)
    (re.compile(r"\b(github_pat_|ghp_|ghs_|gho_|ghu_|ghr_)[A-Za-z0-9_]{20,}"), _REDACTED),

    # Tokens pessoais de acesso do Atlans (atl_pat_ + 43 chars url-safe) — o
    # caso "Bearer atl_pat_..." ja cai na regra de Bearer; esta pega o token nu.
    # Sem `\b`: o prefixo e especifico o bastante, e um token colado a outra
    # palavra ("id=atl_pat_...", "_atl_pat_...") tambem tem de sumir.
    (re.compile(r"atl_pat_[A-Za-z0-9_\-]{43}"), _REDACTED),

    # DSN / URL com credencial embutida, como
    #   postgresql://user:senha@host/db  ou  https://user:senha@api/...  # pragma: allowlist secret
    # Falha de asyncpg/SQLAlchemy embute a DSN inteira na mensagem, e
    # `connectionString` legado grava assim. So a senha some: esquema, usuario
    # e host ficam para o diagnostico continuar util. Fica antes das chaves
    # genericas (AWS, sk-) para nenhuma delas mascarar o match pela metade.
    #
    # Os tres tetos sao o que mantem o custo linear: sem eles, cada letra de um
    # texto longo sem "://" abria uma varredura ate o fim (100 KB custavam 26 s
    # de CPU sincrona no event loop, porque o filtro corre em TODO log). O
    # usuario e opcional — `redis://:senha@host` e a forma canonica do REDIS_URL
    # — e a senha e gulosa ate o ultimo "@" antes de "/" ou espaco, senao
    # `user:p@ss@host` deixaria a cauda da senha para tras.
    (re.compile(r"(?i)\b([a-z][a-z0-9+.\-]{0,31}://[^/\s:@]*:)[^\s/]{1,256}(@)"), rf"\1{_REDACTED}\2"),

    # AWS access keys
    (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), _REDACTED),

    # OpenAI / Anthropic style (sk-... com 30+ chars)
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"), _REDACTED),

    # PEM privates — bloco inteiro
    (re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY-----"
        r".*?-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY-----",
        re.DOTALL,
    ), _REDACTED),
]


def _scrub(text: str) -> str:
    """Aplica todos os padroes em ordem e retorna o texto redigido."""
    for pattern, replacement in _SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# Nome publico da mesma funcao: quem redige texto que SAI do servidor (erros
# de run, definitions, payloads de eventos) usa a mesma lista de padroes do
# log — um lugar so para acrescentar formato novo. `_scrub` fica pelos
# chamadores existentes.
scrub_text = _scrub


class SecretScrubFilter(logging.Filter):
    """
    Filter que redige secrets em record.msg + record.args ANTES do formatter
    ser chamado. Anexado a todo logger criado por `get_logger()` — impede que
    handlers de arquivo, console ou qualquer sink (Loki, Sentry) vejam o
    plaintext.

    Falha aberta: se o scrub der exception (regex catastrofica em str gigante),
    o filter deixa o record passar sem modificar. Perda de log seria pior que
    log com secret.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # msg puro (antes de interpolar args)
            if isinstance(record.msg, str):
                record.msg = _scrub(record.msg)
            # args interpolados: substitui em cada string do tuple
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: _scrub(v) if isinstance(v, str) else v
                                   for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(_scrub(a) if isinstance(a, str) else a
                                        for a in record.args)
        except Exception:
            pass
        return True



# Argumentos que o passo dos padrões já viu por inteiro: texto (redigido um a
# um) e número (não carrega segredo). Com todos assim, a mensagem interpolada
# não tem nada a mais para mostrar.
_ARGS_SIMPLES = (str, int, float, bool, type(None))


def _redigir_registro(registro: logging.LogRecord) -> None:
    """O `SecretScrubFilter` e mais o que só aparece INTERPOLADO: um argumento
    que não é string (a exceção do asyncpg traz a DSN no `str()`), e a pilha
    da exceção. O registro mantém a forma (`msg`/`args` um a um) quando nada
    muda na interpolação — há formatadores que leem `record.args`."""
    # 1. Os segredos EM USO (`segredos_vivos`) primeiro, pelo valor exato. Os
    #    padrões param no primeiro `%`, `+` ou `/` do valor (`token=Kq7v%2B…`)
    #    e, rodando antes, cortavam a agulha que a troca exata procura: a
    #    cauda da chave saía no log. Não importa a ordem em que as duas
    #    fábricas foram instaladas — esta aplica as duas, nesta ordem.
    from flow.utils import segredos_vivos

    formas = segredos_vivos._formas
    if formas:
        segredos_vivos._limpar(registro, formas)
    # 2. Os padrões em `msg` e em cada argumento de texto.
    _secret_filter_do_flow.filter(registro)
    # 3. A mensagem interpolada, só quando há o que ela mostre a mais: `msg` que
    #    não é texto, ou argumento que não é texto nem número. Reescanear a
    #    mensagem inteira sempre dobrava o custo de todo registro.
    args = registro.args
    valores = args.values() if isinstance(args, dict) else (args or ())
    if not isinstance(registro.msg, str) or not all(isinstance(v, _ARGS_SIMPLES) for v in valores):
        try:
            mensagem = registro.getMessage()
        except Exception:
            mensagem = None
        if mensagem is not None:
            redigida = _scrub(mensagem)
            if redigida != mensagem:
                registro.msg, registro.args = redigida, None
    # 4. A pilha: formatada uma vez e guardada em `exc_text` (o formatter a usa
    #    pronta em vez de formatar `exc_info` de novo).
    if registro.exc_info and not registro.exc_text:
        texto = logging.Formatter().formatException(registro.exc_info)
        redigido = _scrub(texto)
        registro.exc_text = redigido
        if redigido != texto:
            registro.exc_info = None
    if registro.stack_info:
        registro.stack_info = _scrub(registro.stack_info)


_secret_filter_do_flow = SecretScrubFilter()
_lock = threading.Lock()
_instalada = False


def instalar_no_processo() -> None:
    """Redige todo registro de log deste processo. Idempotente.

    Falha aberta, como o filtro: se a redação levantar, o registro segue como
    veio — perder o log seria pior.
    """
    global _instalada
    with _lock:
        if _instalada:
            return
        anterior = logging.getLogRecordFactory()

        def fabrica(*args, **kwargs):
            registro = anterior(*args, **kwargs)
            try:
                _redigir_registro(registro)
            except Exception:  # o log nunca derruba quem loga
                pass
            return registro

        logging.setLogRecordFactory(fabrica)
        _instalada = True
