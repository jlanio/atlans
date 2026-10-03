# app/core/control_crypto.py
"""
Ed25519 signing of server → executor command messages.

MOTIVATION (finding S7 of the executor audit):
`job` already traveled signed (see app/core/job_crypto.py), but `control`
(revoked / shutdown / config_changed) and `cancel` went **in plain text**, protected
only by the client's type allowlist. Any path able to write to the
WebSocket or publish to the Redis relay channel brought down the whole fleet with
a `{"type":"control","action":"shutdown"}` — without forging any signature,
because there was no signature to forge. The relay HMAC (S6) protects only the
Redis→worker hop; a command captured there was still replayable, and nothing
protected the worker→executor hop.

Here the command gets the same treatment as the job:
  - signed with the SAME static Ed25519 server key (EXECUTOR_SIGNING_KEY),
    which the executor already pins locally after enrollment (see executor/server_key.py);
  - bound to the recipient (`target_executor_id`) — a captured command cannot
    be replayed against another executor;
  - with a short validity (`expires_at`) and a unique `nonce` — a replay of the same
    command is rejected by the executor's anti-replay cache.

Wire format:
{
  "type":      "control",            # or "cancel"
  "action":    "revoked",            # type-specific fields…
  "reason":    "…",
  "auth": {
    "target_executor_id": str,
    "issued_at":          str (ISO8601),
    "expires_at":         str (ISO8601),
    "nonce":              str (32 bytes hex)
  },
  "signature": str (base64 — Ed25519 over the canonical bytes)
}

Canonical bytes = json.dumps(mensagem_sem_signature, sort_keys=True,
                             ensure_ascii=False, separators=(",", ":"))

Signing the WHOLE message minus the signature (instead of a fixed list of
fields) makes any new protocol field fall under coverage
automatically — there is no way to add a field and forget to sign it.
"""
import base64
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from app.core.job_crypto import _load_signing_key

# Server → executor message types that require a signature. Keep in sync
# with _SIGNED_SERVER_MESSAGES in executor/connection.py: a type the executor
# requires signed but the server sends raw becomes a silently discarded command.
SIGNED_MESSAGE_TYPES = frozenset({"control", "cancel"})

# Validity of a command. Much shorter than a job's (300s): a command is
# interactive (an admin clicked "revoke", a user clicked "cancel") and has no
# reason to remain valid after that. Shortening it reduces the replay window.
CONTROL_TTL_SECONDS = int(os.getenv("EXECUTOR_CONTROL_TTL_SECONDS", "120"))


def canonical_bytes(message: dict) -> bytes:
    """Signed bytes: the whole message minus the `signature` field.

    Fixed `separators` and `sort_keys=True` remove serialization ambiguity —
    both sides must produce exactly the same bytes.
    """
    unsigned = {k: v for k, v in message.items() if k != "signature"}
    return json.dumps(
        unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode()


def build_signed_control(payload: dict, executor_id: str) -> dict:
    """Returns `payload` with `auth` + `signature` added.

    Raises RuntimeError if EXECUTOR_SIGNING_KEY is not configured — the same
    contract as `build_job_message`. Failing loudly is on purpose: emitting the command
    unsigned would make the executor discard it, and a "revoked" that never arrives is
    worse silent than noisy.
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
    """Signs `data` when the type requires it; returns it unchanged otherwise.

    Single point of application, called by `ExecutorConnectionRegistry.send_json`.
    Centralizing it here avoids the classic failure mode: someone adds a new
    `control` emitter in a router and forgets to sign.
    """
    if data.get("type") not in SIGNED_MESSAGE_TYPES:
        return data
    if "signature" in data:
        # Already signed by an earlier path (e.g. a resend) — don't sign again,
        # otherwise `auth` would be replaced and the old signature invalidated.
        return data
    return build_signed_control(data, executor_id)
