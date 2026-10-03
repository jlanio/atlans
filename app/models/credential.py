# models/credential.py
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

from app.models.base import Base
from app.core.utils.encryption import encrypt_string

class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # id_hash: public identifier consistent with the other entities (Workflow, Schedule, etc.)
    # Derived from the primary UUID — keeps compatibility with existing routes that use UUID.
    id_hash = Column(String(36), unique=True, nullable=False, index=True,
                     default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # ex: "postgresql", "webhook_token", etc.
    data = Column(JSONB, nullable=False)   # Encrypted key-value data
    owner_id = Column(String(36), nullable=True, index=True)   # Creator's User.id_hash
    # workspace_id: when filled in, the credential is SHARED — visible to all
    # members of that workspace, not only to the owner. NULL = the owner's
    # private credential (legacy behavior). See credential_service.list_* and
    # credential_loader.resolve_credentials_from_ids.
    workspace_id = Column(String(36), nullable=True, index=True)
    # Organizational, non-secret metadata — that is why they are their own
    # columns and do not go into `data` (which is encrypted by encrypt_and_store).
    description = Column(String, nullable=True)
    tags = Column(JSONB, nullable=True)   # list of strings
    # Last time the credential was RESOLVED for execution. Written best-effort
    # by the resolver (credential_loader); never a critical path.
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def expires_at(self) -> Optional[datetime]:
        """Expiry derived from `data['expires_at']` — it is not a column.

        Expiry has always lived inside the `data` JSONB (plain text;
        encrypt_and_store never encrypts that key), and that is where the
        resolver enforces it from. A parallel column would be a second source
        of truth the resolver would ignore. Exposing it as a property keeps a
        single source and still makes Pydantic (from_attributes) fill in
        CredentialOut.expires_at — the expiry badge in the UI depended on it
        and always came back null.

        Returns None when absent or malformed; validating/refusing is the
        writer's job, not the job of whoever reads it for display.
        """
        raw = (self.data or {}).get("expires_at")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def encrypt_and_store(self, plain_data: dict):
        for k, v in plain_data.items():
            # ✅ validation: expires_at must be an ISO 8601 string
            if k == "expires_at" and v:
                try:
                    datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    raise ValueError("O campo 'expires_at' deve estar em formato ISO 8601.")

        # Audit (SEG-19): do NOT skip encryption based on a "gAAAA" prefix. The
        # legitimate paths (create/update) always pass PLAINTEXT here — update
        # decrypts the current blob, merges and re-encrypts. The only way for a
        # value to arrive already starting with "gAAAA" was the client SENDING
        # someone else's ciphertext: without encryption, it was stored as is
        # and GET /credentials/{id}/data decrypted it with the platform key —
        # an oracle that turned "I have the ciphertext" into "I have the
        # secret". Always encrypting turns a sent "gAAAA" into a ciphertext of
        # itself: decrypting returns the string "gAAAA…", never someone
        # else's secret.
        self.data = {
            k: encrypt_string(v)
            if isinstance(v, str) and k != "expires_at"  # expires_at is NOT encrypted
            else v
            for k, v in plain_data.items()
        }
