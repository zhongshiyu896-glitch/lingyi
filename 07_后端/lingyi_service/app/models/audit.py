"""SQLAlchemy model for sensitive operation audit log."""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

JSONType = JSON().with_variant(JSONB(), "postgresql")
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LyOperationAuditLog(Base):
    """敏感操作审计日志表。"""

    __tablename__ = "ly_operation_audit_log"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_operation_audit_log"),
        CheckConstraint("result IN ('success', 'failed')", name="ck_ly_operation_audit_log_result"),
        Index("idx_ly_operation_audit_module_action", "module", "action"),
        Index("idx_ly_operation_audit_operator_time", "operator", "created_at"),
        Index("idx_ly_operation_audit_resource", "resource_type", "resource_id"),
        Index("idx_ly_operation_audit_request_id", "request_id"),
        {"schema": "ly_schema", "comment": "敏感操作审计日志"},
    )

    id = Column(IDType, autoincrement=True)
    module = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    operator = Column(String(140), nullable=False)
    operator_roles = Column(JSONType, nullable=False, default=list)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(BigInteger, nullable=True)
    resource_no = Column(String(140), nullable=True)
    before_data = Column(JSONType, nullable=True)
    after_data = Column(JSONType, nullable=True)
    result = Column(String(16), nullable=False)
    error_code = Column(String(64), nullable=True)
    request_id = Column(String(64), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LySecurityAuditLog(Base):
    """安全审计日志表（认证/鉴权拒绝与权限源不可用事件）。"""

    __tablename__ = "ly_security_audit_log"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_ly_security_audit_log"),
        Index("idx_ly_security_audit_log_created_at", "created_at"),
        Index("idx_ly_security_audit_log_user_id", "user_id"),
        Index("idx_ly_security_audit_log_event_type", "event_type"),
        Index("idx_ly_security_audit_log_module_action", "module", "action"),
        Index("idx_ly_security_audit_log_resource", "resource_type", "resource_id"),
        Index("idx_ly_security_audit_log_request_id", "request_id"),
        Index("idx_ly_security_audit_log_dedupe_key_created_at", "dedupe_key", "created_at"),
        {"schema": "ly_schema", "comment": "安全审计日志"},
    )

    id = Column(IDType, autoincrement=True)
    event_type = Column(String(64), nullable=False)
    module = Column(String(64), nullable=False)
    action = Column(String(64), nullable=True)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(140), nullable=True)
    resource_no = Column(String(140), nullable=True)
    user_id = Column(String(140), nullable=True)
    user_roles = Column(JSONType, nullable=True, default=list)
    permission_source = Column(String(32), nullable=True)
    deny_reason = Column(String(255), nullable=False)
    dedupe_key = Column(String(64), nullable=True)
    request_method = Column(String(16), nullable=False)
    request_path = Column(String(255), nullable=False)
    request_id = Column(String(64), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
