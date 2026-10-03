# app/core/utils/allowlist.py
"""Matching a hostname against a workspace allowlist.

Extracted from `run_result_consumer` so it can also be used by the workflow
move impact report, which needs to warn when the workflow's `notification_url`
will no longer be accepted in the destination workspace. Importing the consumer
just for this function would pull in Redis, storage and artifact registration too.
"""
import re

# A hostname label: letters or digits (of any alphabet), with a hyphen only
# in the middle. A domain has at least two labels. Whatever does not match this
# (comma, space, semicolon, leading dot, two dots in a row) would never match
# any hostname at firing time — and, in an applied list, would block every
# webhook without explanation.
_ROTULO = r"(?:[^\W_](?:[^\W_]|-){0,61}[^\W_]|[^\W_])"
_HOSTNAME = re.compile(rf"(?:\*\.)?{_ROTULO}(?:\.{_ROTULO})+")
# A pasted line with several domains: "a.com, b.com" is two.
_SEPARADORES = re.compile(r"[,;\s]+")


def hostname_matches_allowlist(hostname: str, allowlist: list[str]) -> bool:
    """Check whether the hostname matches some pattern in the allowlist.

    Accepted patterns:
      - "example.com"   -> exact match
      - "*.example.com" -> any subdomain (a.example.com, foo.bar.example.com)
                            but NOT the bare domain (example.com).

    Case-insensitive comparison.
    """
    hostname = (hostname or "").lower().strip()
    if not hostname:
        return False
    for pattern in allowlist or []:
        pattern = (pattern or "").lower().strip()
        if not pattern:
            continue
        if pattern.startswith("*."):
            suffix = pattern[1:]  # ".example.com"
            if hostname.endswith(suffix) and hostname != suffix[1:]:
                return True
        elif hostname == pattern:
            return True
    return False


def normalizar_dominio(entrada: str) -> str:
    """The HOST of an allowlist entry, as `hostname_matches_allowlist` compares
    it: `https://Hooks.Slack.com/services/x` → `hooks.slack.com`.

    The global webhook whitelist accepted text with a path and port — which
    would never match a hostname. Serves both writing and reading (what is
    already stored goes through the same rule).
    """
    d = (entrada or "").strip().lower()
    for prefixo in ("https://", "http://"):
        if d.startswith(prefixo):
            d = d[len(prefixo):]
    d = d.split("/", 1)[0]
    host, sep, porta = d.rpartition(":")
    if sep and host and porta.isdigit():
        d = host
    return d


def validar_allowlist(raw: list[str]) -> list[str]:
    """Normalize and validate hostname patterns; `ValueError` for what the matcher
    would ignore.

    Without validation, `https://example.com/hook` would go into the list, would
    never match any hostname (the matcher compares only the host) and the user
    would have every webhook blocked without understanding why. A lone `*`,
    likewise: it is not a wildcard for the matcher, and a list with only it
    would block everything.
    """
    normalized: list[str] = []
    for entry in raw or []:
        pattern = (entry or "").strip().lower()
        if not pattern:
            continue

        if "://" in pattern or "/" in pattern or "@" in pattern or ":" in pattern:
            raise ValueError(
                f"'{entry}' não é um hostname. Informe apenas o host, sem "
                "protocolo, porta ou caminho (ex.: exemplo.com)."
            )
        # A lone `*` and `*example.com` without the dot are not wildcards for the matcher:
        # it only handles the "*." prefix. Accepted silently, they would never match anything.
        if "*" in pattern and not pattern.startswith("*."):
            raise ValueError(
                f"'{entry}' é inválido. O curinga só vale no formato "
                "*.exemplo.com (subdomínios)."
            )
        if pattern.startswith("*.") and "." not in pattern[2:]:
            raise ValueError(
                f"'{entry}' é inválido. Informe o domínio completo após o "
                "curinga (ex.: *.exemplo.com)."
            )
        if not pattern.startswith("*.") and "." not in pattern:
            raise ValueError(f"'{entry}' não parece um hostname válido (ex.: exemplo.com).")
        if not _HOSTNAME.fullmatch(pattern):
            raise ValueError(
                f"'{entry}' não parece um hostname válido (ex.: exemplo.com). Um domínio por "
                "item, sem vírgula, espaço ou ponto sobrando."
            )

        if pattern not in normalized:
            normalized.append(pattern)

    return normalized


def padroes_validos(raw: list[str]) -> list[str]:
    """The patterns in `raw` that the matcher can match, each one normalized
    to the host — the others silently dropped.

    For reading what is ALREADY stored: the global whitelist accepted `*`, URLs
    with a path and `localhost` before it was enforced. None of them matched
    any host; applied as they came, a `*` saved to "allow everything" would
    block every webhook.
    """
    validos: list[str] = []
    for entrada in separar_dominios(raw):
        try:
            validos.extend(p for p in validar_allowlist([normalizar_dominio(entrada)]) if p not in validos)
        except ValueError:
            continue
    return validos


def separar_dominios(entradas) -> list[str]:
    """Each item, split where a pasted line joins several domains:
    `["a.com, b.com"]` → `["a.com", "b.com"]`."""
    partes: list[str] = []
    for entrada in entradas or []:
        partes.extend(p for p in _SEPARADORES.split(str(entrada or "")) if p)
    return partes

