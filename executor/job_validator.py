# executor/job_validator.py
"""
Validação de jobs recebidos antes de qualquer descriptografia.

Ordem obrigatória (falha cedo, falha seguro):
  1. Assinatura Ed25519                — autenticidade do servidor
  2. target_executor_id                   — anti-misrouting
  3. frescor temporal                  — anti-replay temporal
  4. nonce único (cache em memória)    — anti-replay de nonce
  5. Descriptografia (em job_executor) — integridade via GCM tag

Env opcional:
  EXECUTOR_MAX_JOB_EXPIRY_SECONDS — teto da DURAÇÃO declarada do envelope
                                    (`expires_at - issued_at`, default 900s).
                                    Também entra no piso do TTL do cache de nonces.
  EXECUTOR_CLOCK_SKEW_SECONDS     — folga aceita entre o relógio do servidor e o
                                    local ao checar expiração (default 300s).

Lidas por executor/_ambiente.py::ler_int: valor inválido (`abc`, negativo) vira o
default com aviso, em vez de derrubar o import do executor com ValueError.
"""
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone

from executor import config
from executor._ambiente import ler_int
from executor.crypto import verify_signature

logger = logging.getLogger(__name__)


# ── Teto da DURAÇÃO declarada de um envelope ──────────────────────────────────
# O servidor emite envelopes com TTL de EXECUTOR_JOB_TTL_SECONDS (default 300s,
# ver app/core/job_crypto.py) e comandos com 120s (app/core/control_crypto.py).
# Sem teto deste lado, um envelope assinado com `expires_at` daqui a 10 anos
# passava na checagem temporal para sempre — e como o cache de nonce é finito,
# bastava esperar a entrada sair do cache para reproduzi-lo.
#
# O teto é aplicado sobre `expires_at - issued_at`, NÃO sobre `expires_at` menos
# o relógio local. A diferença é decisiva: os dois carimbos vêm do MESMO relógio
# (o do servidor), então a medida é imune a clock skew. A primeira versão deste
# fix comparava `expires_at` com `datetime.now()` local e, com isso, um host com
# NTP quebrado 10 min atrasado passava a rejeitar 100% dos jobs — indisponibilidade
# total causada por um problema que não é de segurança. Medir a duração declarada
# barra exatamente o mesmo envelope eterno sem depender de relógio nenhum.
# 900s = 3x o TTL padrão do servidor: dá folga para o operador aumentar o TTL.
# Mínimo 1: com zero, todo envelope (duração > 0) seria recusado.
_MAX_EXPIRY_HORIZON_SECONDS = ler_int("EXECUTOR_MAX_JOB_EXPIRY_SECONDS", 900, minimo=1)

# ── Tolerância de clock skew ──────────────────────────────────────────────────
# A checagem de EXPIRAÇÃO (`agora_local > expires_at`) é inerentemente dependente
# do relógio local — não há como ancorar frescor absoluto sem ele. Por isso ela
# ganha uma folga explícita e configurável, em vez de zero folga: alguns minutos
# de deriva de NTP não podem derrubar o executor inteiro. Zero é aceito (é
# escolha do operador); negativo recusaria o envelope antes de ele vencer.
_CLOCK_SKEW_TOLERANCE_SECONDS = ler_int("EXECUTOR_CLOCK_SKEW_SECONDS", 300, minimo=0)

# ── Teto RÍGIDO de clock skew ─────────────────────────────────────────────────
# A tolerância acima é assimétrica por construção: ela solta o envelope que já
# passou de `expires_at`, mas nada barra o caso oposto — relógio local ATRASADO.
# Com o relógio para trás, `agora_local` nunca alcança `expires_at` e o envelope
# permanece aceitável por (atraso + duração) segundos LOCAIS, enquanto o nonce só
# é lembrado pelo TTL do cache. Passado o TTL, o mesmo envelope assinado volta a
# ser aceito: replay, silencioso, sem nada no log ligando a falha ao relógio.
#
# O teto fecha isso nos DOIS sentidos, medindo |agora_local - issued_at|. Acima
# dele o envelope é REJEITADO com mensagem de NTP. É uma escolha deliberada de
# falhar RUIDOSO em vez de ficar silenciosamente replayável: um host com mais de
# 15 min de deriva está quebrado de um jeito que o operador precisa saber, e a
# mensagem diz exatamente o que corrigir. Entre a tolerância e o teto o envelope
# é aceito, mas `_warn_on_clock_skew` já avisa.
_MAX_CLOCK_SKEW_SECONDS = ler_int("EXECUTOR_MAX_CLOCK_SKEW_SECONDS", 900, minimo=0)

if _MAX_CLOCK_SKEW_SECONDS < _CLOCK_SKEW_TOLERANCE_SECONDS:
    # Configuração contraditória: o teto rejeitaria antes de a folga ser usada.
    # Alinhar em vez de abortar — o executor não pode deixar de subir por causa
    # de duas env vars mal combinadas.
    logger.warning(
        "EXECUTOR_MAX_CLOCK_SKEW_SECONDS (%ds) é menor que "
        "EXECUTOR_CLOCK_SKEW_SECONDS (%ds) — o teto rígido venceria a tolerância. "
        "Usando %ds para os dois.",
        _MAX_CLOCK_SKEW_SECONDS, _CLOCK_SKEW_TOLERANCE_SECONDS, _CLOCK_SKEW_TOLERANCE_SECONDS,
    )
    _MAX_CLOCK_SKEW_SECONDS = _CLOCK_SKEW_TOLERANCE_SECONDS


def _nonce_ttl_seconds() -> float:
    """
    TTL efetivo do cache de nonces.

    AMARRAÇÃO OBRIGATÓRIA: um nonce só pode ser esquecido DEPOIS que o envelope
    correspondente deixou de ser aceitável — senão abre-se uma janela em que o
    mesmo job ainda passa na checagem temporal mas o cache já não lembra dele
    (replay). Portanto o TTL cobre a JANELA MÁXIMA DE ACEITAÇÃO medida no relógio
    LOCAL, que é o que o cache usa (`time.monotonic`):

        duração declarada máxima  (_MAX_EXPIRY_HORIZON_SECONDS)
      + folga concedida na expiração (_CLOCK_SKEW_TOLERANCE_SECONDS)
      + deriva máxima tolerada do relógio (_MAX_CLOCK_SKEW_SECONDS)

    O terceiro termo é o que a primeira versão esquecia: sem o teto rígido a
    deriva era ilimitada e nenhum TTL finito conseguia cobrir a janela. Com o
    teto, a soma é finita e o invariante volta a valer por construção.
    """
    return max(
        config.NONCE_CACHE_TTL,
        _MAX_EXPIRY_HORIZON_SECONDS
        + _CLOCK_SKEW_TOLERANCE_SECONDS
        + _MAX_CLOCK_SKEW_SECONDS,
    )


# ── Cache de nonces em memória ────────────────────────────────────────────────
# OrderedDict em ordem de inserção: (nonce → timestamp_de_inserção monotônico).
# Limitado para evitar crescimento ilimitado.
#
# LIMITAÇÃO CONHECIDA: o cache é só em memória, então um restart do executor o
# zera. A defesa remanescente nessa janela é o `expires_at` com teto acima — um
# replay só funciona dentro do horizonte curto e apenas se o processo reiniciar
# exatamente nesse intervalo.
_nonce_cache: OrderedDict[str, float] = OrderedDict()
_NONCE_CACHE_MAX = 10_000


def _nonce_seen(nonce: str) -> bool:
    """
    Retorna True se o nonce já foi processado (replay detectado).
    Registra o nonce se for novo.
    """
    now = time.monotonic()
    ttl = _nonce_ttl_seconds()

    # PERF: o OrderedDict está em ordem de inserção e o TTL é fixo, então os
    # expirados são sempre um prefixo. Expurgar pelo início até achar o primeiro
    # ainda válido custa O(expirados) — a versão anterior varria as 10k entradas
    # a cada job, no caminho quente.
    while _nonce_cache:
        oldest_nonce, oldest_ts = next(iter(_nonce_cache.items()))
        if now - oldest_ts <= ttl:
            break
        _nonce_cache.pop(oldest_nonce, None)

    if nonce in _nonce_cache:
        return True  # replay

    # Estouro de capacidade só acontece com >10k jobs LEGÍTIMOS (a assinatura já
    # foi verificada antes daqui) dentro da janela de TTL. Descartar em silêncio
    # o mais antigo — como era feito antes — remove um nonce AINDA VÁLIDO e abre
    # buraco de replay sem deixar rastro. Mantemos o limite de memória, mas o
    # descarte vira ruidoso para o operador poder subir NONCE_CACHE_TTL/capacidade.
    if len(_nonce_cache) >= _NONCE_CACHE_MAX:
        evicted, _ = _nonce_cache.popitem(last=False)
        logger.error(
            "Cache anti-replay cheio (%d entradas, TTL %.0fs): nonce '%s…' AINDA VÁLIDO "
            "foi descartado para dar lugar a um novo. Enquanto durar a saturação, um "
            "replay do job correspondente não seria detectado.",
            _NONCE_CACHE_MAX, ttl, evicted[:16],
        )

    _nonce_cache[nonce] = now
    return False


# ── Validação principal ───────────────────────────────────────────────────────

class JobValidationError(Exception):
    """Levantada quando uma validação de segurança falha."""


# ── Frescor temporal (compartilhado por job e control) ────────────────────────

# Intervalo mínimo entre dois avisos de clock skew. O aviso é diagnóstico e roda
# no caminho quente de todo job — sem throttle viraria uma linha de WARNING por
# job e afogaria o log justamente quando o operador precisa lê-lo.
_SKEW_WARN_INTERVAL_SECONDS = 300.0
# None = nunca avisou. Ancorar em 0.0 fazia `agora_mono - 0.0 < 300` engolir o
# PRIMEIRO aviso enquanto o host tivesse menos de 5 min de vida — no Linux
# `time.monotonic()` e o uptime da maquina. Ou seja, o aviso sumia justamente no
# cenario em que ele importa: container subindo numa VM recem-criada, com o NTP
# ainda torto. Depois do primeiro aviso o throttle funciona normalmente.
_last_skew_warn_monotonic: float | None = None


def _parse_iso_utc(value: str, field: str) -> datetime:
    """ISO8601 → datetime tz-aware. Sem timezone, assume UTC (o servidor sempre
    manda offset, mas um envelope naive não pode virar TypeError na subtração)."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise JobValidationError(f"Campo '{field}' inválido: {exc}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _warn_on_clock_skew(now_utc: datetime, issued_at: datetime) -> None:
    """Avisa quando o relógio local diverge do servidor além da tolerância.

    Puramente diagnóstico: não rejeita nada. Existe porque a falha por relógio se
    disfarça de ataque — sem este aviso o operador só vê a rejeição, que fala em
    replay, e vai caçar um adversário que não existe.
    """
    global _last_skew_warn_monotonic

    skew = (now_utc - issued_at).total_seconds()
    if abs(skew) <= _CLOCK_SKEW_TOLERANCE_SECONDS:
        return
    agora_mono = time.monotonic()
    if (
        _last_skew_warn_monotonic is not None
        and agora_mono - _last_skew_warn_monotonic < _SKEW_WARN_INTERVAL_SECONDS
    ):
        return
    _last_skew_warn_monotonic = agora_mono
    logger.warning(
        "Relógio local diverge do servidor em %.0fs (%s) — tolerância %ds, "
        "teto rígido %ds. Ainda estamos aceitando envelopes, mas corrija o NTP "
        "deste host: ao passar do teto TODO job e TODO comando serão recusados "
        "(de propósito — com deriva grande o anti-replay deixa de proteger).",
        skew,
        "local ATRASADO" if skew < 0 else "local ADIANTADO",
        _CLOCK_SKEW_TOLERANCE_SECONDS,
        _MAX_CLOCK_SKEW_SECONDS,
    )


def _assert_fresh(
    issued_at_str: str | None,
    expires_at_str: str | None,
    *,
    kind: str,
    prefix: str = "",
) -> None:
    """Valida o frescor de um envelope assinado. Lança JobValidationError.

    Duas checagens de naturezas diferentes:

    (a) DURAÇÃO DECLARADA — `expires_at - issued_at` contra o teto. Comparação
        entre dois instantes do mesmo relógio (o do servidor), portanto imune a
        clock skew. É ela que fecha o buraco de replay do envelope "eterno".

    (b) EXPIRAÇÃO — `agora_local > expires_at`, com folga explícita de skew.
        Depende do relógio local por definição; a folga impede que NTP quebrado
        vire rejeição de 100% dos jobs.

    `issued_at` é OBRIGATÓRIO: sem ele não há como medir (a) e a única alternativa
    seria voltar a ancorar o teto no relógio local. Servidor e executor sobem
    juntos e ambos os emissores (job_crypto e control_crypto) já o enviam.
    """
    if not expires_at_str:
        raise JobValidationError(f"{kind} sem campo '{prefix}expires_at'.")
    if not issued_at_str:
        raise JobValidationError(
            f"{kind} sem campo '{prefix}issued_at' — sem ele a duração declarada "
            "do envelope não pode ser limitada. Servidor desatualizado."
        )

    issued_at = _parse_iso_utc(issued_at_str, f"{prefix}issued_at")
    expires_at = _parse_iso_utc(expires_at_str, f"{prefix}expires_at")

    duracao = (expires_at - issued_at).total_seconds()
    if duracao <= 0:
        raise JobValidationError(
            f"{kind} com '{prefix}expires_at' ({expires_at_str}) anterior ou igual a "
            f"'{prefix}issued_at' ({issued_at_str}) — envelope malformado, rejeitado."
        )
    if duracao > _MAX_EXPIRY_HORIZON_SECONDS:
        raise JobValidationError(
            f"{kind} declara validade de {duracao:.0f}s ({issued_at_str} → "
            f"{expires_at_str}), acima do teto de {_MAX_EXPIRY_HORIZON_SECONDS}s. "
            "Envelope de vida longa demais volta a ser replayável assim que o nonce "
            "sai do cache — rejeitado. (Não é relógio: a duração é medida entre dois "
            "carimbos do próprio servidor.)"
        )

    now_utc = datetime.now(timezone.utc)

    # (c) TETO RÍGIDO DE SKEW — antes da expiração, de propósito: quando o
    # relógio está muito fora, "expirado" é sintoma e "relógio" é a causa, e é a
    # causa que o operador precisa ler. Simétrico: pega tanto o relógio adiantado
    # (que rejeitaria tudo como expirado) quanto o ATRASADO — este último não
    # dispara nenhuma outra checagem e é justamente o que abria a janela de
    # replay descrita em _nonce_ttl_seconds.
    skew = (now_utc - issued_at).total_seconds()
    if abs(skew) > _MAX_CLOCK_SKEW_SECONDS:
        # skew = agora_local - issued_at. Negativo => o relógio local ainda não
        # chegou no instante em que o servidor emitiu, ou seja, está ATRASADO.
        direcao = "atrasado" if skew < 0 else "adiantado"
        raise JobValidationError(
            f"{kind} rejeitado: o relógio local está {abs(skew):.0f}s {direcao} em "
            f"relação ao servidor (emitido em {issued_at_str}), acima do teto de "
            f"{_MAX_CLOCK_SKEW_SECONDS}s. NÃO é replay — CORRIJA O NTP DESTE HOST. "
            "Enquanto a deriva persistir, TODOS os jobs e comandos serão recusados: "
            "é intencional, porque aceitar envelope de um relógio tão fora tornaria "
            "o anti-replay ineficaz (ver _nonce_ttl_seconds)."
        )

    atraso = (now_utc - expires_at).total_seconds()
    if atraso > _CLOCK_SKEW_TOLERANCE_SECONDS:
        raise JobValidationError(
            f"{kind} expirado em {expires_at_str} (há {atraso:.0f}s, além da "
            f"tolerância de skew de {_CLOCK_SKEW_TOLERANCE_SECONDS}s) — rejeitado. "
            "Se TODOS os envelopes estão sendo rejeitados assim, suspeite do relógio "
            "local adiantado (NTP) antes de suspeitar de replay."
        )

    _warn_on_clock_skew(now_utc, issued_at)


def validate_job(message: dict) -> None:
    """
    Executa todas as validações de segurança em sequência.
    Lança JobValidationError com motivo detalhado se qualquer verificação falhar.

    NÃO descriptografa o payload — isso é responsabilidade do executor.
    """
    envelope = message.get("envelope")
    if not isinstance(envelope, dict):
        raise JobValidationError("Mensagem sem envelope válido.")

    # ── 1. Assinatura Ed25519 ─────────────────────────────────────────────────
    if not verify_signature(message, config.SERVER_SIGNING_PUBLIC_KEY):
        raise JobValidationError("Assinatura Ed25519 inválida — job rejeitado.")

    # ── 2. Destinatário correto ───────────────────────────────────────────────
    if envelope.get("target_executor_id") != config.EXECUTOR_ID:
        raise JobValidationError(
            f"Job destinado a '{envelope.get('target_executor_id')}', "
            f"mas este executor é '{config.EXECUTOR_ID}'."
        )

    # ── 3. Validade temporal ──────────────────────────────────────────────────
    _assert_fresh(envelope.get("issued_at"), envelope.get("expires_at"), kind="Job")

    # ── 4. Nonce único (anti-replay) ──────────────────────────────────────────
    nonce = envelope.get("nonce")
    if not nonce:
        raise JobValidationError("Envelope sem campo 'nonce'.")
    if _nonce_seen(nonce):
        raise JobValidationError(f"Nonce '{nonce[:16]}…' já foi processado — replay rejeitado.")

    # ── 5. Campos obrigatórios ────────────────────────────────────────────────
    for field in ("job_id", "job_type", "workspace_id"):
        if not envelope.get(field):
            raise JobValidationError(f"Campo obrigatório ausente no envelope: '{field}'.")


# ── Comandos servidor → executor (control / cancel) ───────────────────────────
# Contraparte de app/core/control_crypto.py. Ver a docstring de lá para o
# formato na rede e o motivo de existir.

def _control_canonical_bytes(message: dict) -> bytes:
    """Bytes assinados: a mensagem inteira menos `signature`.

    Precisa produzir EXATAMENTE os mesmos bytes que
    `app.core.control_crypto.canonical_bytes` — daí `sort_keys`, `ensure_ascii`
    e `separators` fixos nos dois lados.
    """
    import json
    unsigned = {k: v for k, v in message.items() if k != "signature"}
    return json.dumps(
        unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode()


def validate_control_message(message: dict) -> None:
    """Valida a assinatura e o frescor de um `control`/`cancel` do servidor.

    Mesma ordem de checagem do job (falha cedo, falha seguro): assinatura →
    destinatário → prazo → nonce. Compartilha o cache anti-replay de
    `validate_job`: o espaço de nonce é o mesmo (32 bytes aleatórios do
    servidor), então uma entrada só pode ser consumida uma vez, seja por job ou
    por comando.

    Lança JobValidationError. NÃO retorna bool: um `if not valida(...)` esquecido
    em algum caller viraria bypass silencioso.
    """
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(message, dict):
        raise JobValidationError("Comando não é um objeto JSON.")

    signature_b64 = message.get("signature")
    if not signature_b64:
        raise JobValidationError(
            f"Comando '{message.get('type')}' sem assinatura — rejeitado. "
            "Servidor desatualizado ou mensagem injetada."
        )

    auth = message.get("auth")
    if not isinstance(auth, dict):
        raise JobValidationError("Comando sem bloco 'auth' válido.")

    # ── 1. Assinatura Ed25519 ─────────────────────────────────────────────────
    server_pub = config.SERVER_SIGNING_PUBLIC_KEY
    if not server_pub:
        raise JobValidationError(
            "Chave pública de assinatura do servidor indisponível — "
            "impossível validar o comando."
        )
    try:
        pub_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(server_pub))
        pub_key.verify(base64.b64decode(signature_b64), _control_canonical_bytes(message))
    except Exception as exc:
        raise JobValidationError(
            f"Assinatura inválida no comando '{message.get('type')}': {exc}"
        ) from exc

    # ── 2. Destinatário correto ───────────────────────────────────────────────
    # Sem isto, um comando legítimo capturado no canal de um executor poderia ser
    # reproduzido contra qualquer outro.
    target = auth.get("target_executor_id")
    if target != config.EXECUTOR_ID:
        raise JobValidationError(
            f"Comando destinado a '{target}', mas este executor é '{config.EXECUTOR_ID}'."
        )

    # ── 3. Validade temporal ──────────────────────────────────────────────────
    # Mesmo critério do job: teto sobre a duração declarada (imune a skew) e
    # expiração com folga de skew. Vale sublinhar por que a folga aqui é segura:
    # revogar um executor NÃO depende dele obedecer ao `control/revoked` — o
    # servidor fecha o WS com 4403 e a blacklist de cert barra a reconexão (ver
    # app/api/routers/executores_router.py). A checagem temporal do comando é
    # defesa contra replay, não o mecanismo de revogação.
    _assert_fresh(
        auth.get("issued_at"), auth.get("expires_at"), kind="Comando", prefix="auth.",
    )

    # ── 4. Nonce único (anti-replay) ──────────────────────────────────────────
    nonce = auth.get("nonce")
    if not nonce:
        raise JobValidationError("Comando sem 'auth.nonce'.")
    if _nonce_seen(nonce):
        raise JobValidationError(
            f"Nonce '{nonce[:16]}…' já processado — replay de comando rejeitado."
        )
