# app/core/control_crypto.py
"""
Assinatura Ed25519 das mensagens de comando servidor → executor.

MOTIVAÇÃO (achado S7 da auditoria do executor):
`job` já trafegava assinado (ver app/core/job_crypto.py), mas `control`
(revoked / shutdown / config_changed) e `cancel` iam **em texto puro**, protegidos
apenas pela allowlist de tipos do cliente. Qualquer caminho capaz de escrever no
WebSocket ou de publicar no canal de relay do Redis derrubava a frota inteira com
um `{"type":"control","action":"shutdown"}` — sem forjar assinatura nenhuma,
porque não havia assinatura para forjar. O HMAC do relay (S6) protege apenas o
salto Redis→worker; um comando capturado ali continuava replayável, e nada
protegia o salto worker→executor.

Aqui o comando ganha o mesmo tratamento do job:
  - assinado com a MESMA chave Ed25519 estática do servidor (EXECUTOR_SIGNING_KEY),
    que o executor já fixa localmente após o enrollment (ver executor/server_key.py);
  - amarrado ao destinatário (`target_executor_id`) — um comando capturado não
    pode ser reproduzido contra outro executor;
  - com validade curta (`expires_at`) e `nonce` único — reprodução do mesmo
    comando é rejeitada pelo cache anti-replay do executor.

Formato na rede:
{
  "type":      "control",            # ou "cancel"
  "action":    "revoked",            # campos específicos do tipo…
  "reason":    "…",
  "auth": {
    "target_executor_id": str,
    "issued_at":          str (ISO8601),
    "expires_at":         str (ISO8601),
    "nonce":              str (32 bytes hex)
  },
  "signature": str (base64 — Ed25519 sobre os bytes canônicos)
}

Bytes canônicos = json.dumps(mensagem_sem_signature, sort_keys=True,
                             ensure_ascii=False, separators=(",", ":"))

Assinar a mensagem INTEIRA menos a assinatura (em vez de uma lista fixa de
campos) faz com que qualquer campo novo do protocolo entre na cobertura
automaticamente — não há como adicionar um campo e esquecer de assiná-lo.
"""
import base64
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from app.core.job_crypto import _load_signing_key

# Tipos de mensagem servidor → executor que exigem assinatura. Mantenha em sincronia
# com _SIGNED_SERVER_MESSAGES em executor/connection.py: um tipo que o executor
# exige assinado mas o servidor envia cru vira comando silenciosamente descartado.
SIGNED_MESSAGE_TYPES = frozenset({"control", "cancel"})

# Validade de um comando. Muito mais curta que a de um job (300s): comando é
# interativo (admin clicou em "revogar", usuário clicou em "cancelar") e não tem
# motivo para continuar válido depois disso. Encurtar reduz a janela de replay.
CONTROL_TTL_SECONDS = int(os.getenv("EXECUTOR_CONTROL_TTL_SECONDS", "120"))


def canonical_bytes(message: dict) -> bytes:
    """Bytes assinados: a mensagem inteira menos o campo `signature`.

    `separators` fixo e `sort_keys=True` eliminam ambiguidade de serialização —
    os dois lados precisam produzir exatamente os mesmos bytes.
    """
    unsigned = {k: v for k, v in message.items() if k != "signature"}
    return json.dumps(
        unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode()


def build_signed_control(payload: dict, executor_id: str) -> dict:
    """Devolve `payload` acrescido de `auth` + `signature`.

    Lança RuntimeError se EXECUTOR_SIGNING_KEY não estiver configurada — o mesmo
    contrato de `build_job_message`. Falhar alto é proposital: emitir o comando
    sem assinatura faria o executor descartá-lo, e um "revoked" que não chega é
    pior calado do que barulhento.
    """
    signing_key = _load_signing_key()
    if signing_key is None:
        raise RuntimeError(
            "EXECUTOR_SIGNING_KEY não configurada — não é possível assinar comandos "
            "para o executor. Gere uma chave Ed25519 e defina a variável de ambiente."
        )

    now = datetime.now(timezone.utc)
    message = {
        **payload,
        "auth": {
            "target_executor_id": executor_id,
            "issued_at":          now.isoformat(),
            "expires_at":         (now + timedelta(seconds=CONTROL_TTL_SECONDS)).isoformat(),
            "nonce":              secrets.token_hex(32),
        },
    }
    signature = signing_key.sign(canonical_bytes(message))
    message["signature"] = base64.b64encode(signature).decode()
    return message


def sign_if_needed(data: dict, executor_id: str) -> dict:
    """Assina `data` quando o tipo exige; devolve inalterado caso contrário.

    Ponto único de aplicação, chamado por `ExecutorConnectionRegistry.send_json`.
    Centralizar aqui evita o modo de falha clássico: alguém adiciona um novo
    emissor de `control` num router e esquece de assinar.
    """
    if data.get("type") not in SIGNED_MESSAGE_TYPES:
        return data
    if "signature" in data:
        # Já assinado por um caminho anterior (ex: reenvio) — não assinar de novo,
        # senão o `auth` seria substituído e a assinatura antiga invalidada.
        return data
    return build_signed_control(data, executor_id)
