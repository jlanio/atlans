# app/models/user.py
from sqlalchemy import Boolean, Column, Integer, String, DateTime, func, text
from uuid import uuid4
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    id_hash = Column(String(36), unique=True, default=lambda: str(uuid4()), nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    email_verified = Column(Boolean, nullable=False, server_default=text("false"))
    # "active" | "suspended" | "deleted"
    status = Column(String(20), nullable=False, server_default="active", index=True)
    # "admin" | "user" — default "user"
    role = Column(String(20), nullable=False, server_default="user")
    # Individual quota of dedicated executors the user can create (0 = cannot).
    # Global admins ignore the quota (unlimited creation).
    agent_quota = Column(Integer, nullable=False, server_default="0")
    workspace_id = Column(String(36), nullable=True, index=True)
    suspended_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def is_active(self) -> bool:
        """Compatibilidade retroativa — retorna True se status == 'active'."""
        return self.status == "active"
