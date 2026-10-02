# app/core/utils/allowlist.py
"""Casamento de hostname contra allowlist de workspace.

Extraído de `run_result_consumer` para poder ser usado também pelo relatório de
impacto do move de workflow, que precisa avisar quando a `notification_url` do
workflow deixará de ser aceita no workspace de destino. Importar o consumer só
para esta função puxaria Redis, storage e o registro de artefatos junto.
"""
import re

# Um rótulo de hostname: letras ou dígitos (de qualquer alfabeto), com hífen só
# no meio. Um domínio tem ao menos dois rótulos. O que não casa com isto
# (vírgula, espaço, ponto-e-vírgula, ponto no começo, dois pontos seguidos)
# nunca casaria com hostname nenhum no disparo — e, numa lista aplicada,
# bloquearia todo webhook sem explicar.
_ROTULO = r"(?:[^\W_](?:[^\W_]|-){0,61}[^\W_]|[^\W_])"
_HOSTNAME = re.compile(rf"(?:\*\.)?{_ROTULO}(?:\.{_ROTULO})+")
# Uma linha colada com vários domínios: "a.com, b.com" são dois.
_SEPARADORES = re.compile(r"[,;\s]+")


def hostname_matches_allowlist(hostname: str, allowlist: list[str]) -> bool:
    """Verifica se hostname casa com algum padrao na allowlist.

    Padroes aceitos:
      - "exemplo.com"   -> match exato
      - "*.exemplo.com" -> qualquer subdominio (a.exemplo.com, foo.bar.exemplo.com)
                            mas NAO o dominio nu (exemplo.com).

    Comparacao case-insensitive.
    """
    hostname = (hostname or "").lower().strip()
    if not hostname:
        return False
    for pattern in allowlist or []:
        pattern = (pattern or "").lower().strip()
        if not pattern:
            continue
        if pattern.startswith("*."):
            suffix = pattern[1:]  # ".exemplo.com"
            if hostname.endswith(suffix) and hostname != suffix[1:]:
                return True
        elif hostname == pattern:
            return True
    return False


def normalizar_dominio(entrada: str) -> str:
    """O HOST de uma entrada de allowlist, como `hostname_matches_allowlist` o
    compara: `https://Hooks.Slack.com/services/x` → `hooks.slack.com`.

    A whitelist global de webhooks aceitava o texto com caminho e porta — que
    nunca casaria com um hostname. Serve à gravação e à leitura (o que já está
    gravado passa pela mesma regra).
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
    """Normaliza e valida padrões de hostname; `ValueError` no que o matcher
    ignoraria.

    Sem validação, `https://exemplo.com/hook` entraria na lista, nunca casaria
    com hostname nenhum (o matcher compara só o host) e o usuário ficaria com
    todos os webhooks bloqueados sem entender por quê. `*` sozinho, idem: não é
    curinga para o matcher, e uma lista só com ele bloquearia tudo.
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
        # `*` sozinho e `*exemplo.com` sem o ponto nao sao curinga para o matcher:
        # ele so trata prefixo "*.". Aceitos em silencio, nunca casariam com nada.
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
    """Os padrões de `raw` que o matcher consegue casar, cada um normalizado
    para o host — os demais descartados em silêncio.

    Para ler o que JÁ está gravado: a whitelist global aceitava `*`, URL com
    caminho e `localhost` antes de ser aplicada. Nenhum deles casava com host
    nenhum; aplicados como vieram, um `*` gravado para "liberar tudo"
    bloquearia todos os webhooks.
    """
    validos: list[str] = []
    for entrada in separar_dominios(raw):
        try:
            validos.extend(p for p in validar_allowlist([normalizar_dominio(entrada)]) if p not in validos)
        except ValueError:
            continue
    return validos


def separar_dominios(entradas) -> list[str]:
    """Cada item, dividido onde uma linha colada junta vários domínios:
    `["a.com, b.com"]` → `["a.com", "b.com"]`."""
    partes: list[str] = []
    for entrada in entradas or []:
        partes.extend(p for p in _SEPARADORES.split(str(entrada or "")) if p)
    return partes

