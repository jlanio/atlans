# executor/server_key.py
"""
Resolução e PINNING da chave pública Ed25519 de assinatura do servidor.

MOTIVAÇÃO (achado S8 da auditoria):
Antes, quando `SERVER_SIGNING_PUBLIC_KEY` não estava no `.env` (o caso padrão —
nem o enroll nem o setup a gravavam), o executor buscava a chave em
`GET /executores/server-public-key` **a cada boot**, com `follow_redirects=True`
e sem persistir nada. Isso torna a camada de assinatura de jobs decorativa: quem
vencesse o canal em qualquer boot entregava a própria chave e passava a assinar
jobs arbitrários — que o executor então executa com as credenciais do workspace.
A assinatura não acrescentava nada sobre o TLS, e o comprometimento se repetia a
cada reinício sem deixar rastro.

Ordem de precedência agora:
  1. `SERVER_SIGNING_PUBLIC_KEY` no ambiente — override explícito do operador.
  2. Arquivo fixado em `CERT_DIR/server_signing.pub` — gravado no enrollment
     (sem janela de confiança nenhuma: chega junto do cert, dentro do mesmo
     bundle autenticado pelo OTP) ou pelo TOFU do passo 3.
  3. TOFU **uma única vez**: busca sobre mTLS com a CA interna já fixada, com
     redirect desligado, e PERSISTE. Boots seguintes usam o arquivo do passo 2.

A diferença que importa: no modelo antigo toda reinicialização era uma nova
oportunidade de ataque; agora existe no máximo UMA janela, e apenas para
executores enrolados antes desta mudança. Enrollments novos nunca a têm.

Divergência (a chave do servidor mudou) é tratada como ERRO, não como
atualização silenciosa: rotação de chave de assinatura exige ação do operador
(re-enroll ou apagar o arquivo fixado conscientemente). Aceitar a chave nova
automaticamente reabriria exatamente o buraco que o pinning fecha.

E a divergência PARA O BOOT, não só o enroll: `pin_key` registra um marcador
`server_signing.pub.conflict` e `resolve_server_signing_key` o transforma em
ServerKeyError. Sem isso o executor subia com o pin obsoleto, conectava, pedia
jobs e rejeitava 100% deles com "Assinatura Ed25519 inválida" — um modo de falha
mudo, em que nada no boot menciona chave. Falhar no boot é ruidoso e acionável.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SERVER_SIGNING_PUB_FILE = "server_signing.pub"
SERVER_SIGNING_CONFLICT_FILE = "server_signing.pub.conflict"


class ServerKeyError(RuntimeError):
    """Falha ao estabelecer confiança na chave de assinatura do servidor."""


class ServerKeyPersistError(ServerKeyError):
    """Não foi possível GRAVAR o pin — mas a chave em si é confiável.

    Subclasse de propósito: enroll/renewal já tratam ServerKeyError e continuam
    logando o problema. Quem precisa distinguir é o boot, que pode seguir com a
    chave em memória (ela veio por mTLS verificado) em vez de morrer por causa de
    um diretório somente-leitura.
    """


def pinned_key_path(cert_dir: str | Path) -> Path:
    return Path(cert_dir) / SERVER_SIGNING_PUB_FILE


def conflict_marker_path(cert_dir: str | Path) -> Path:
    return Path(cert_dir) / SERVER_SIGNING_CONFLICT_FILE


def load_pinned_key(cert_dir: str | Path) -> str | None:
    """Lê a chave fixada. Devolve None APENAS quando não há pin nenhum.

    Distinção importante: "arquivo ausente" e "arquivo presente mas ilegível/
    vazio" NÃO podem ter o mesmo desfecho. Tratar os dois como None faria o
    executor cair no TOFU da rede — ou seja, quem conseguisse corromper ou
    truncar o arquivo (ou um erro de disco) rebaixaria a confiança fixada de
    volta para "aceita a primeira resposta que chegar", que é exatamente o que o
    pinning existe para impedir. Pin quebrado é ERRO, não ausência.
    """
    path = pinned_key_path(cert_dir)
    if not path.exists():
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ServerKeyError(
            f"Chave de assinatura fixada em '{path}' existe mas não pôde ser lida: {exc}. "
            "Corrija a permissão do arquivo ou apague-o conscientemente para refazer o pin."
        ) from exc
    if not value:
        raise ServerKeyError(
            f"Chave de assinatura fixada em '{path}' está vazia. "
            "Apague o arquivo conscientemente para refazer o pin, ou restaure-o do backup."
        )
    return value


def _validate_key_b64(key_b64: str) -> None:
    """Confirma que a string é mesmo uma chave pública Ed25519 (32 bytes raw)."""
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        raw = base64.b64decode(key_b64, validate=True)
    except Exception as exc:
        raise ServerKeyError(f"Chave de assinatura não é base64 válido: {exc}") from exc
    if len(raw) != 32:
        raise ServerKeyError(
            f"Chave de assinatura tem {len(raw)} bytes; Ed25519 exige exatamente 32."
        )
    try:
        Ed25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        raise ServerKeyError(f"Chave de assinatura não é uma chave Ed25519 válida: {exc}") from exc


def _divergence_message(path: Path, existing: str, key_b64: str, source: str) -> str:
    return (
        "A chave de assinatura do servidor MUDOU.\n"
        f"  fixada em disco: {existing[:16]}…\n"
        f"  recebida ({source}): {key_b64[:16]}…\n"
        "Isto é ou uma rotação legítima da chave do servidor, ou um ataque. "
        "O executor NÃO aceita a troca automaticamente e NÃO sobe enquanto o "
        "conflito existir — subir com o pin antigo faria ele rejeitar todo job "
        "sem dizer por quê.\n"
        "Se a rotação for legítima, confirme a chave nova com o admin e então "
        f"apague '{path}' e '{conflict_marker_path(path.parent)}' e reinicie "
        "(ou defina SERVER_SIGNING_PUBLIC_KEY no ambiente)."
    )


def _clear_conflict_marker(cert_dir: str | Path) -> None:
    """Remove o marcador quando o pin volta a ser coerente. Sem isto o executor
    ficaria travado para sempre depois de o operador já ter resolvido o caso."""
    marker = conflict_marker_path(cert_dir)
    try:
        marker.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Não foi possível remover o marcador '%s': %s", marker, exc)


def pin_key(cert_dir: str | Path, key_b64: str, *, source: str) -> None:
    """Fixa a chave em disco.

    Se já houver uma chave fixada DIFERENTE, grava um marcador de conflito e
    levanta ServerKeyError em vez de sobrescrever — o marcador é o que faz o
    boot seguinte PARAR (ver `resolve_server_signing_key`), em vez de carregar o
    pin obsoleto em silêncio.

    Falha ao GRAVAR (dir somente-leitura, ENOSPC) vira ServerKeyPersistError, que
    o boot pode degradar para uso em memória — a chave em si já é confiável.
    """
    key_b64 = (key_b64 or "").strip()
    if not key_b64:
        raise ServerKeyError("Servidor não forneceu chave de assinatura.")
    _validate_key_b64(key_b64)

    path = pinned_key_path(cert_dir)
    existing = load_pinned_key(cert_dir)
    if existing and existing != key_b64:
        _record_conflict(cert_dir, existing, key_b64, source)
        raise ServerKeyError(_divergence_message(path, existing, key_b64, source))
    if existing == key_b64:
        _clear_conflict_marker(cert_dir)
        return  # já fixada, nada a fazer

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key_b64 + "\n", encoding="utf-8")
    except OSError as exc:
        # Simétrico ao que `load_pinned_key` faz na leitura: erro de IO vira
        # mensagem acionável, nunca traceback cru no meio do boot.
        raise ServerKeyPersistError(
            f"Não foi possível fixar a chave de assinatura em '{path}': {exc}. "
            "Torne o diretório de certs gravável (o bind `:ro` do compose é a "
            "causa mais comum) ou defina SERVER_SIGNING_PUBLIC_KEY no ambiente."
        ) from exc
    try:
        os.chmod(path, 0o600)
    except (OSError, NotImplementedError):
        pass  # Windows: o ACL do NTFS já restringe
    _clear_conflict_marker(cert_dir)
    logger.info("Chave de assinatura do servidor fixada em '%s' (origem: %s).", path, source)


def _record_conflict(cert_dir: str | Path, existing: str, key_b64: str, source: str) -> None:
    """Persiste a divergência para o boot seguinte poder abortar com contexto.

    Best-effort: se nem o marcador puder ser escrito, o ServerKeyError da
    divergência ainda é levantado — perder o marcador não pode mascarar o
    conflito que acabou de ser detectado.
    """
    marker = conflict_marker_path(cert_dir)
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"{source}\n{key_b64}\n", encoding="utf-8")
    except OSError as exc:
        logger.error(
            "Divergência de chave detectada mas o marcador '%s' não pôde ser gravado "
            "(%s) — o próximo boot NÃO vai conseguir avisar sobre o conflito.",
            marker, exc,
        )


async def resolve_server_signing_key(cert_dir: str | Path, server_url: str) -> str:
    """Devolve a chave de assinatura a usar, fixando-a quando necessário.

    Levanta ServerKeyError quando não há como estabelecer confiança (incluindo o
    caso de divergência registrada) — o caller deve abortar o boot. Rodar sem
    chave confiável significa aceitar jobs de qualquer um que vença o canal.

    A única falha que NÃO aborta é a de persistência do pin: a chave já foi
    obtida por mTLS, então vale mais seguir com ela em memória do que derrubar o
    executor por causa de um volume somente-leitura.
    """
    # 1. Override explícito do operador — é a ação consciente que resolve até um
    #    conflito registrado, então vence inclusive o marcador (só avisa).
    env_key = (os.getenv("SERVER_SIGNING_PUBLIC_KEY") or "").strip()
    if env_key:
        _validate_key_b64(env_key)
        marker = conflict_marker_path(cert_dir)
        if marker.exists():
            logger.warning(
                "Há um conflito de chave registrado em '%s', mas SERVER_SIGNING_PUBLIC_KEY "
                "foi definida explicitamente e vence. Apague o marcador e o pin depois de "
                "confirmar a rotação com o admin.", marker,
            )
        logger.info("Chave de assinatura do servidor definida via ambiente.")
        return env_key

    # 1.5. Conflito registrado por um enroll/renewal anterior.
    _assert_no_conflict(cert_dir)

    # 2. Chave já fixada (enrollment ou TOFU anterior).
    pinned = load_pinned_key(cert_dir)
    if pinned:
        _validate_key_b64(pinned)
        logger.info("Chave de assinatura do servidor carregada do pin local.")
        return pinned

    # 3. TOFU único, sobre mTLS, e persistido.
    logger.warning(
        "Nenhuma chave de assinatura fixada — buscando do servidor UMA VEZ e fixando "
        "em '%s'. Executores enrolados a partir de agora recebem a chave já no bundle "
        "do enroll e não passam por esta etapa.",
        pinned_key_path(cert_dir),
    )
    fetched = await _fetch_server_key(server_url)
    try:
        pin_key(cert_dir, fetched, source="GET /executores/server-public-key")
    except ServerKeyPersistError as exc:
        # A chave veio por mTLS com a CA interna já fixada, então ela é confiável
        # NESTA sessão. Matar o boot por causa de um diretório somente-leitura
        # trocaria um risco de segurança por indisponibilidade total. O preço é
        # que a janela de TOFU se repete a cada boot — daí o ERROR, não WARNING.
        logger.error(
            "%s\nSeguindo com a chave APENAS EM MEMÓRIA nesta sessão: a janela de "
            "TOFU vai se repetir a cada reinício até o pin conseguir ser gravado.",
            exc,
        )
    return fetched


def _assert_no_conflict(cert_dir: str | Path) -> None:
    """Aborta o boot se um enroll/renewal anterior detectou troca de chave.

    Este é o elo que faltava: `pin_key` só roda no enroll e no renewal, então
    sem o marcador a divergência morria numa linha de log e o boot seguinte
    carregava o pin obsoleto — rejeitando todo job por assinatura inválida, sem
    nada no boot ligando a falha à chave.
    """
    marker = conflict_marker_path(cert_dir)
    if not marker.exists():
        return
    try:
        linhas = marker.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        linhas = []
    source = linhas[0] if linhas else "origem desconhecida"
    recebida = linhas[1] if len(linhas) > 1 else "?"
    existing = "?"
    try:
        existing = load_pinned_key(cert_dir) or "?"
    except ServerKeyError:
        pass
    raise ServerKeyError(
        _divergence_message(pinned_key_path(cert_dir), existing, recebida, source)
    )


async def _fetch_server_key(server_url: str) -> str:
    """Busca a chave em `/executores/server-public-key` sobre mTLS.

    `follow_redirects=False` de propósito: seguir um redirect aqui permitiria a
    um proxy hostil desviar a requisição para um host que devolve a chave dele.
    """
    import httpx

    from executor.utils import mtls_httpx_kwargs, ws_to_http

    base = ws_to_http(server_url)
    url = f"{base}/executores/server-public-key"
    try:
        async with httpx.AsyncClient(
            timeout=15, follow_redirects=False, **mtls_httpx_kwargs(base)
        ) as client:
            resp = await client.get(url)
    except Exception as exc:
        raise ServerKeyError(
            f"Não foi possível buscar a chave de assinatura em {url}: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise ServerKeyError(
            f"Servidor respondeu HTTP {resp.status_code} em {url} — chave de "
            "assinatura não obtida. (Redirects não são seguidos de propósito.)"
        )
    try:
        key_b64 = resp.json()["ed25519_public_key_b64"]
    except Exception as exc:
        raise ServerKeyError(f"Resposta inesperada de {url}: {exc}") from exc
    return key_b64
