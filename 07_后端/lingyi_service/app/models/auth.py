"""FastAPI-native authentication models."""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import false

AuthBase = declarative_base()

JSONType = JSON().with_variant(JSONB(), "postgresql")
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LyAuthAdminUser(AuthBase):
    """Single-admin password login account for FastAPI deployments."""

    __tablename__ = "ly_auth_admin_user"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_auth_admin_user"),
        CheckConstraint("status IN ('active','disabled')", name="ck_ly_auth_admin_user_status"),
        Index("uk_ly_auth_admin_user_username", "username", unique=True),
        Index("idx_ly_auth_admin_user_status", "status"),
        {"schema": "ly_schema", "comment": "FastAPI-native admin login account"},
    )

    id = Column(IDType, autoincrement=True)
    username = Column(String(140), nullable=False)
    password_hash = Column(String(255), nullable=False)
    roles = Column(JSONType, nullable=False, default=list)
    status = Column(String(16), nullable=False, server_default="active")
    is_service_account = Column(Boolean, nullable=False, server_default=false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
