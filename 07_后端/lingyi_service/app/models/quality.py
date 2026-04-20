"""SQLAlchemy models for quality management baseline (TASK-012B)."""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()
IDType = BigInteger().with_variant(Integer(), "sqlite")


class LyQualityInspection(Base):
    """质量检验主表。"""

    __tablename__ = "ly_quality_inspection"
    __table_args__ = (
        Index("uk_ly_quality_inspection_no", "inspection_no", unique=True),
        Index("idx_ly_quality_inspection_company_status_date", "company", "status", "inspection_date"),
        Index("idx_ly_quality_inspection_item_date", "item_code", "inspection_date"),
        Index("idx_ly_quality_inspection_supplier_date", "supplier", "inspection_date"),
        Index("idx_ly_quality_inspection_source", "source_type", "source_id"),
        CheckConstraint(
            "source_type IN ('incoming_material','subcontract_receipt','finished_goods','manual')",
            name="ck_ly_quality_inspection_source_type",
        ),
        CheckConstraint("status IN ('draft','confirmed','cancelled')", name="ck_ly_quality_inspection_status"),
        CheckConstraint("result IN ('pending','pass','fail','partial')", name="ck_ly_quality_inspection_result"),
        CheckConstraint("inspected_qty >= 0", name="ck_ly_quality_inspection_inspected_qty_nonnegative"),
        CheckConstraint("accepted_qty >= 0", name="ck_ly_quality_inspection_accepted_qty_nonnegative"),
        CheckConstraint("rejected_qty >= 0", name="ck_ly_quality_inspection_rejected_qty_nonnegative"),
        CheckConstraint("defect_qty >= 0", name="ck_ly_quality_inspection_defect_qty_nonnegative"),
        CheckConstraint(
            "accepted_qty + rejected_qty = inspected_qty",
            name="ck_ly_quality_inspection_qty_balanced",
        ),
        CheckConstraint("defect_qty <= inspected_qty", name="ck_ly_quality_inspection_defect_qty_lte_inspected"),
        {"schema": "ly_schema", "comment": "质量检验主表"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    inspection_no = Column(String(64), nullable=False)
    company = Column(String(140), nullable=False)
    source_type = Column(String(64), nullable=False)
    source_id = Column(String(140), nullable=True)
    item_code = Column(String(140), nullable=False)
    supplier = Column(String(140), nullable=True)
    warehouse = Column(String(140), nullable=True)
    work_order = Column(String(140), nullable=True)
    sales_order = Column(String(140), nullable=True)
    inspection_date = Column(Date, nullable=False)

    inspected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    accepted_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    defect_qty = Column(Numeric(18, 6), nullable=False, default=0)
    defect_rate = Column(Numeric(10, 6), nullable=False, default=0)
    rejected_rate = Column(Numeric(10, 6), nullable=False, default=0)

    result = Column(String(32), nullable=False, default="pending")
    status = Column(String(32), nullable=False, default="draft")
    remark = Column(String(255), nullable=True)

    created_by = Column(String(140), nullable=False)
    updated_by = Column(String(140), nullable=True)
    confirmed_by = Column(String(140), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(String(140), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String(200), nullable=True)

    source_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LyQualityInspectionItem(Base):
    """质量检验抽检/明细行。"""

    __tablename__ = "ly_quality_inspection_item"
    __table_args__ = (
        Index("idx_ly_quality_inspection_item_inspection", "inspection_id", "line_no"),
        CheckConstraint("sample_qty >= 0", name="ck_ly_quality_inspection_item_sample_qty_nonnegative"),
        CheckConstraint("accepted_qty >= 0", name="ck_ly_quality_inspection_item_accepted_qty_nonnegative"),
        CheckConstraint("rejected_qty >= 0", name="ck_ly_quality_inspection_item_rejected_qty_nonnegative"),
        CheckConstraint("defect_qty >= 0", name="ck_ly_quality_inspection_item_defect_qty_nonnegative"),
        CheckConstraint("result IN ('pending','pass','fail','partial')", name="ck_ly_quality_inspection_item_result"),
        {"schema": "ly_schema", "comment": "质量检验明细行"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    inspection_id = Column(IDType, ForeignKey("ly_schema.ly_quality_inspection.id"), nullable=False)
    line_no = Column(Integer, nullable=False)
    item_code = Column(String(140), nullable=False)
    sample_qty = Column(Numeric(18, 6), nullable=False, default=0)
    accepted_qty = Column(Numeric(18, 6), nullable=False, default=0)
    rejected_qty = Column(Numeric(18, 6), nullable=False, default=0)
    defect_qty = Column(Numeric(18, 6), nullable=False, default=0)
    result = Column(String(32), nullable=False, default="pending")
    remark = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyQualityDefect(Base):
    """质量缺陷记录。"""

    __tablename__ = "ly_quality_defect"
    __table_args__ = (
        Index("idx_ly_quality_defect_inspection", "inspection_id", "defect_code"),
        CheckConstraint("defect_qty >= 0", name="ck_ly_quality_defect_qty_nonnegative"),
        CheckConstraint("severity IN ('minor','major','critical')", name="ck_ly_quality_defect_severity"),
        {"schema": "ly_schema", "comment": "质量缺陷记录"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    inspection_id = Column(IDType, ForeignKey("ly_schema.ly_quality_inspection.id"), nullable=False)
    item_id = Column(IDType, ForeignKey("ly_schema.ly_quality_inspection_item.id"), nullable=True)
    defect_code = Column(String(64), nullable=False)
    defect_name = Column(String(140), nullable=False)
    defect_qty = Column(Numeric(18, 6), nullable=False, default=0)
    severity = Column(String(32), nullable=False, default="minor")
    remark = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LyQualityOperationLog(Base):
    """质量检验业务操作日志。"""

    __tablename__ = "ly_quality_operation_log"
    __table_args__ = (
        Index("idx_ly_quality_operation_log_inspection_time", "inspection_id", "operated_at"),
        Index("idx_ly_quality_operation_log_company_time", "company", "operated_at"),
        CheckConstraint("action IN ('create','update','confirm','cancel')", name="ck_ly_quality_operation_log_action"),
        {"schema": "ly_schema", "comment": "质量检验操作日志"},
    )

    id = Column(IDType, primary_key=True, autoincrement=True)
    inspection_id = Column(IDType, ForeignKey("ly_schema.ly_quality_inspection.id"), nullable=False)
    company = Column(String(140), nullable=False)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)
    operator = Column(String(140), nullable=False)
    request_id = Column(String(64), nullable=True)
    remark = Column(String(200), nullable=True)
    operated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
