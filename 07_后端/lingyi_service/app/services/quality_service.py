"""Quality management service and fail-closed source validation (TASK-012B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import ROUND_HALF_UP
import os
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import QUALITY_INVALID_RESULT
from app.core.error_codes import QUALITY_INVALID_SOURCE
from app.core.error_codes import QUALITY_INVALID_SOURCE_TYPE
from app.core.error_codes import QUALITY_INVALID_STATUS
from app.core.error_codes import QUALITY_INVALID_QTY
from app.core.error_codes import QUALITY_NOT_FOUND
from app.core.error_codes import QUALITY_QTY_MISMATCH
from app.core.error_codes import QUALITY_SOURCE_UNAVAILABLE
from app.core.exceptions import BusinessException
from app.models.quality import LyQualityDefect
from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityInspectionItem
from app.models.quality import LyQualityOperationLog
from app.models.subcontract import LySubcontractInspection
from app.schemas.quality import QualityDefectInput
from app.schemas.quality import QualityDefectData
from app.schemas.quality import QualityExportData
from app.schemas.quality import QualityExportRow
from app.schemas.quality import QualityDiagnosticData
from app.schemas.quality import QualityInspectionActionData
from app.schemas.quality import QualityInspectionCreateRequest
from app.schemas.quality import QualityInspectionDefectCreateRequest
from app.schemas.quality import QualityInspectionDetailData
from app.schemas.quality import QualityInspectionItemData
from app.schemas.quality import QualityInspectionItemInput
from app.schemas.quality import QualityInspectionListData
from app.schemas.quality import QualityInspectionListItem
from app.schemas.quality import QualityInspectionUpdateRequest
from app.schemas.quality import QualityOperationLogData
from app.schemas.quality import QualityStatisticsAggregateData
from app.schemas.quality import QualityStatisticsData
from app.schemas.quality import QualityStatisticsTrendData
from app.schemas.quality import QualityStatisticsTrendPoint
from app.schemas.quality_outbox import QualityOutboxStatusData
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_quality_adapter import ERPNextQualityAdapter
from app.services.quality_outbox_service import QualityOutboxService

SOURCE_TYPES = {"incoming_material", "subcontract_receipt", "finished_goods", "manual"}
SOURCE_TYPE_LABELS = {
    "incoming_material": "来料检验",
    "subcontract_receipt": "外发收货检验",
    "finished_goods": "成品检验",
    "manual": "手工检验",
}
RESULT_VALUES = {"pending", "pass", "fail", "partial"}
FINAL_STATUSES = {"confirmed", "cancelled"}
_RATE_QUANT = Decimal("0.000001")


@dataclass(frozen=True)
class QualitySourceValidationSnapshot:
    """Safe snapshot produced by source validation."""

    master_data: dict[str, Any]
    source: dict[str, Any] | None = None


class QualitySourceValidator:
    """Read ERPNext master/source facts under fail-closed policy."""

    def __init__(self, request_obj: Request | None = None):
        self.request_obj = request_obj
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")
        self.adapter = ERPNextQualityAdapter(request_obj=request_obj, base_url=self.base_url)

    def validate_for_payload(
        self,
        *,
        company: str,
        item_code: str,
        supplier: str | None,
        warehouse: str | None,
        source_type: str,
        source_id: str | None,
    ) -> QualitySourceValidationSnapshot:
        """Validate ERPNext master data and optional external source."""
        master_data: dict[str, Any] = {
            "company": self._require_resource("Company", company, require_submitted=False),
            "item": self._require_resource("Item", item_code, require_submitted=False),
        }
        if supplier:
            master_data["supplier"] = self._require_resource("Supplier", supplier, require_submitted=False)
        if warehouse:
            warehouse_doc = self._require_resource("Warehouse", warehouse, require_submitted=False)
            doc_company = _text(warehouse_doc.get("company"))
            if doc_company and doc_company != company:
                raise BusinessException(code=QUALITY_INVALID_SOURCE, message="Warehouse 与 company 不匹配")
            master_data["warehouse"] = warehouse_doc

        source_snapshot: dict[str, Any] | None = None
        if source_type == "incoming_material" and source_id:
            source_snapshot = self._require_resource("Purchase Receipt", source_id, require_submitted=True)
            _validate_source_ownership(source_snapshot, company=company, item_code=item_code, supplier=supplier, source_doctype="Purchase Receipt")
        elif source_type == "finished_goods" and source_id:
            source_snapshot = self._require_resource("Stock Entry", source_id, require_submitted=True)
            _validate_source_ownership(source_snapshot, company=company, item_code=item_code, supplier=None, source_doctype="Stock Entry")
        return QualitySourceValidationSnapshot(master_data=master_data, source=source_snapshot)

    def _require_resource(self, doctype: str, name: str, *, require_submitted: bool) -> dict[str, Any]:
        return self.adapter.require_resource(
            doctype=doctype,
            name=name,
            require_submitted=require_submitted,
        )


class QualityService:
    """Business service for quality inspections."""

    def __init__(self, session: Session, source_validator: QualitySourceValidator | None = None):
        self.session = session
        self.source_validator = source_validator or QualitySourceValidator()
        self.outbox_service = QualityOutboxService(session=session)

    def create_inspection(
        self,
        *,
        payload: QualityInspectionCreateRequest,
        operator: str,
        request_id: str | None,
    ) -> QualityInspectionDetailData:
        normalized = _normalize_create_payload(payload)
        snapshot = self._validate_sources(normalized)
        inspection = LyQualityInspection(
            inspection_no=self._next_inspection_no(),
            company=normalized["company"],
            source_type=normalized["source_type"],
            source_id=normalized.get("source_id"),
            item_code=normalized["item_code"],
            supplier=normalized.get("supplier"),
            warehouse=normalized.get("warehouse"),
            work_order=normalized.get("work_order"),
            sales_order=normalized.get("sales_order"),
            inspection_date=normalized["inspection_date"],
            inspected_qty=normalized["inspected_qty"],
            accepted_qty=normalized["accepted_qty"],
            rejected_qty=normalized["rejected_qty"],
            defect_qty=normalized["defect_qty"],
            defect_rate=normalized["defect_rate"],
            rejected_rate=normalized["rejected_rate"],
            result=normalized["result"],
            status="draft",
            remark=normalized.get("remark"),
            created_by=operator,
            updated_by=operator,
            source_snapshot=_snapshot_to_dict(snapshot),
        )
        self.session.add(inspection)
        self.session.flush()
        self._replace_items_and_defects(inspection=inspection, items=normalized["items"], defects=normalized["defects"])
        self._add_log(inspection=inspection, action="create", from_status=None, to_status="draft", operator=operator, request_id=request_id, remark=None)
        self.session.flush()
        return self.get_detail_data(inspection.id)

    def update_inspection(
        self,
        *,
        inspection_id: int,
        payload: QualityInspectionUpdateRequest,
        operator: str,
        request_id: str | None,
    ) -> QualityInspectionDetailData:
        inspection = self._get_or_raise(inspection_id)
        if inspection.status != "draft":
            raise BusinessException(code=QUALITY_INVALID_STATUS)
        before_status = str(inspection.status)
        normalized = _merge_update_payload(inspection=inspection, payload=payload)
        snapshot = self._validate_sources(normalized)
        inspection.supplier = normalized.get("supplier")
        inspection.warehouse = normalized.get("warehouse")
        inspection.work_order = normalized.get("work_order")
        inspection.sales_order = normalized.get("sales_order")
        inspection.inspection_date = normalized["inspection_date"]
        inspection.inspected_qty = normalized["inspected_qty"]
        inspection.accepted_qty = normalized["accepted_qty"]
        inspection.rejected_qty = normalized["rejected_qty"]
        inspection.defect_qty = normalized["defect_qty"]
        inspection.defect_rate = normalized["defect_rate"]
        inspection.rejected_rate = normalized["rejected_rate"]
        inspection.result = normalized["result"]
        inspection.remark = normalized.get("remark")
        inspection.updated_by = operator
        inspection.source_snapshot = _snapshot_to_dict(snapshot)
        if payload.items is not None or payload.defects is not None:
            self._replace_items_and_defects(inspection=inspection, items=normalized["items"], defects=normalized["defects"])
        self._add_log(
            inspection=inspection,
            action="update",
            from_status=before_status,
            to_status=str(inspection.status),
            operator=operator,
            request_id=request_id,
            remark=None,
        )
        self.session.flush()
        return self.get_detail_data(inspection.id)

    def confirm_inspection(
        self,
        *,
        inspection_id: int,
        operator: str,
        request_id: str | None,
        remark: str | None = None,
    ) -> QualityInspectionActionData:
        inspection = self._get_or_raise(inspection_id)
        if inspection.status != "draft":
            raise BusinessException(code=QUALITY_INVALID_STATUS)
        self._validate_sources(_payload_from_inspection(inspection, self._item_inputs(inspection), self._defect_inputs(inspection)))
        now = _now()
        inspection.status = "confirmed"
        inspection.confirmed_by = operator
        inspection.confirmed_at = now
        inspection.updated_by = operator
        self._add_log(
            inspection=inspection,
            action="confirm",
            from_status="draft",
            to_status="confirmed",
            operator=operator,
            request_id=request_id,
            remark=remark,
        )
        self.outbox_service.create_outbox(
            inspection_id=int(inspection.id),
            company=str(inspection.company),
            payload_json=self._build_outbox_payload(inspection),
            created_by=operator,
            max_attempts=3,
        )
        self.session.flush()
        return QualityInspectionActionData(
            id=int(inspection.id),
            inspection_no=str(inspection.inspection_no),
            status="confirmed",
            operator=operator,
            operated_at=now,
        )

    def get_outbox_status(self, inspection_id: int) -> QualityOutboxStatusData:
        inspection = self._get_or_raise(inspection_id)
        row = self.outbox_service.find_latest_by_inspection(inspection_id=int(inspection.id))
        if row is None:
            return QualityOutboxStatusData(
                inspection_id=int(inspection.id),
                status="not_queued",
                attempts=0,
                max_attempts=3,
                next_retry_at=None,
                last_error_code=None,
                last_error_message=None,
                stock_entry_name=None,
            )
        return QualityOutboxStatusData(
            inspection_id=int(inspection.id),
            status=str(row.status),
            attempts=int(row.attempts or 0),
            max_attempts=int(row.max_attempts or 3),
            next_retry_at=row.next_retry_at,
            last_error_code=_text(row.last_error_code),
            last_error_message=_text(row.last_error_message),
            stock_entry_name=_text(row.stock_entry_name),
        )

    def cancel_inspection(
        self,
        *,
        inspection_id: int,
        operator: str,
        request_id: str | None,
        reason: str | None = None,
    ) -> QualityInspectionActionData:
        inspection = self._get_or_raise(inspection_id)
        if inspection.status != "confirmed":
            raise BusinessException(code=QUALITY_INVALID_STATUS)
        now = _now()
        inspection.status = "cancelled"
        inspection.cancelled_by = operator
        inspection.cancelled_at = now
        inspection.cancel_reason = _text(reason)
        inspection.updated_by = operator
        self._add_log(
            inspection=inspection,
            action="cancel",
            from_status="confirmed",
            to_status="cancelled",
            operator=operator,
            request_id=request_id,
            remark=reason,
        )
        self.session.flush()
        return QualityInspectionActionData(
            id=int(inspection.id),
            inspection_no=str(inspection.inspection_no),
            status="cancelled",
            operator=operator,
            operated_at=now,
        )

    def add_defects(
        self,
        *,
        inspection_id: int,
        payload: QualityInspectionDefectCreateRequest,
        operator: str,
        request_id: str | None,
    ) -> QualityInspectionDetailData:
        inspection = self._get_or_raise(inspection_id)
        if inspection.status != "draft":
            raise BusinessException(code=QUALITY_INVALID_STATUS)

        line_to_item_id: dict[int, int] = {
            int(row.line_no): int(row.id)
            for row in (
                self.session.query(LyQualityInspectionItem)
                .filter(LyQualityInspectionItem.inspection_id == inspection.id)
                .order_by(LyQualityInspectionItem.line_no.asc())
                .all()
            )
        }

        existing_defect_qty = (
            self.session.query(LyQualityDefect)
            .filter(LyQualityDefect.inspection_id == inspection.id)
            .all()
        )
        existing_total = sum((_decimal(row.defect_qty) for row in existing_defect_qty), Decimal("0"))
        incoming_total = sum((_decimal(defect.defect_qty) for defect in payload.defects), Decimal("0"))
        next_total = existing_total + incoming_total
        if next_total > _decimal(inspection.inspected_qty):
            raise BusinessException(code=QUALITY_INVALID_QTY, message="缺陷数量不能超过检验数量")

        for defect in payload.defects:
            item_id = None
            if defect.item_line_no is not None:
                item_id = line_to_item_id.get(int(defect.item_line_no))
                if item_id is None:
                    raise BusinessException(code=QUALITY_INVALID_SOURCE, message="缺陷记录引用的明细行不存在")
            self.session.add(
                LyQualityDefect(
                    inspection_id=inspection.id,
                    item_id=item_id,
                    defect_code=_clean_required(defect.defect_code, QUALITY_INVALID_SOURCE),
                    defect_name=_clean_required(defect.defect_name, QUALITY_INVALID_SOURCE),
                    defect_qty=_decimal(defect.defect_qty),
                    severity=_normalize_severity(defect.severity),
                    remark=_text(defect.remark),
                )
            )

        inspection.defect_qty = next_total
        inspection.defect_rate = _rate(next_total, _decimal(inspection.inspected_qty))
        inspection.updated_by = operator
        self._add_log(
            inspection=inspection,
            action="update",
            from_status=str(inspection.status),
            to_status=str(inspection.status),
            operator=operator,
            request_id=request_id,
            remark="add_defect",
        )
        self.session.flush()
        return self.get_detail_data(inspection.id)

    def list_inspections(
        self,
        *,
        company: str | None = None,
        item_code: str | None = None,
        supplier: str | None = None,
        warehouse: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> QualityInspectionListData:
        query = self._filtered_query(
            company=company,
            item_code=item_code,
            supplier=supplier,
            warehouse=warehouse,
            source_type=source_type,
            source_id=source_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
        )
        total = query.count()
        rows = (
            query.order_by(LyQualityInspection.inspection_date.desc(), LyQualityInspection.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return QualityInspectionListData(
            items=[_to_list_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_detail_data(self, inspection_id: int) -> QualityInspectionDetailData:
        inspection = self._get_or_raise(inspection_id)
        items = (
            self.session.query(LyQualityInspectionItem)
            .filter(LyQualityInspectionItem.inspection_id == inspection.id)
            .order_by(LyQualityInspectionItem.line_no.asc())
            .all()
        )
        defects = (
            self.session.query(LyQualityDefect)
            .filter(LyQualityDefect.inspection_id == inspection.id)
            .order_by(LyQualityDefect.id.asc())
            .all()
        )
        logs = (
            self.session.query(LyQualityOperationLog)
            .filter(LyQualityOperationLog.inspection_id == inspection.id)
            .order_by(LyQualityOperationLog.operated_at.asc(), LyQualityOperationLog.id.asc())
            .all()
        )
        return _to_detail(inspection, items=items, defects=defects, logs=logs)

    def statistics(
        self,
        *,
        company: str | None = None,
        item_code: str | None = None,
        supplier: str | None = None,
        warehouse: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> QualityStatisticsData:
        rows = self._filtered_query(
            company=company,
            item_code=item_code,
            supplier=supplier,
            warehouse=warehouse,
            source_type=source_type,
            source_id=source_id,
            status=None,
            from_date=from_date,
            to_date=to_date,
        ).filter(LyQualityInspection.status != "cancelled").all()
        inspected = sum((_decimal(row.inspected_qty) for row in rows), Decimal("0"))
        accepted = sum((_decimal(row.accepted_qty) for row in rows), Decimal("0"))
        rejected = sum((_decimal(row.rejected_qty) for row in rows), Decimal("0"))
        defects = sum((_decimal(row.defect_qty) for row in rows), Decimal("0"))
        by_result: dict[str, int] = {}
        for row in rows:
            by_result[str(row.result)] = by_result.get(str(row.result), 0) + 1
        by_supplier = self._build_group_aggregates(
            rows=rows,
            key_getter=lambda row: _group_key(row.supplier, "unknown_supplier"),
            label_getter=lambda row, key: _text(row.supplier) or "未填写供应商",
        )
        by_item_code = self._build_group_aggregates(
            rows=rows,
            key_getter=lambda row: _group_key(row.item_code, "unknown_item"),
            label_getter=lambda row, key: _text(row.item_code) or "未填写物料",
        )
        by_warehouse = self._build_group_aggregates(
            rows=rows,
            key_getter=lambda row: _group_key(row.warehouse, "unknown_warehouse"),
            label_getter=lambda row, key: _text(row.warehouse) or "未填写仓库",
        )
        by_source_type = self._build_group_aggregates(
            rows=rows,
            key_getter=lambda row: _group_key(row.source_type, "unknown_source_type"),
            label_getter=lambda row, key: SOURCE_TYPE_LABELS.get(_text(row.source_type), _text(row.source_type) or "未知来源"),
        )
        top_defective_suppliers = sorted(
            by_supplier,
            key=lambda row: (row.overall_defect_rate, row.total_rejected_qty, row.total_count, row.key),
            reverse=True,
        )[:5]
        top_defective_items = sorted(
            by_item_code,
            key=lambda row: (row.overall_defect_rate, row.total_rejected_qty, row.total_count, row.key),
            reverse=True,
        )[:5]
        return QualityStatisticsData(
            total_count=len(rows),
            total_inspected_qty=inspected,
            total_accepted_qty=accepted,
            total_rejected_qty=rejected,
            total_defect_qty=defects,
            overall_defect_rate=_rate(defects, inspected),
            inspected_qty=inspected,
            accepted_qty=accepted,
            rejected_qty=rejected,
            defect_qty=defects,
            defect_rate=_rate(defects, inspected),
            rejected_rate=_rate(rejected, inspected),
            by_result=by_result,
            by_supplier=by_supplier,
            by_item_code=by_item_code,
            by_warehouse=by_warehouse,
            by_source_type=by_source_type,
            top_defective_suppliers=top_defective_suppliers,
            top_defective_items=top_defective_items,
        )

    def statistics_trend(
        self,
        *,
        period: str,
        company: str | None = None,
        item_code: str | None = None,
        supplier: str | None = None,
        warehouse: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> QualityStatisticsTrendData:
        rows = self._filtered_query(
            company=company,
            item_code=item_code,
            supplier=supplier,
            warehouse=warehouse,
            source_type=source_type,
            source_id=source_id,
            status=None,
            from_date=from_date,
            to_date=to_date,
        ).filter(LyQualityInspection.status != "cancelled").all()
        trend: dict[str, dict[str, Decimal | int]] = {}
        for row in rows:
            date_key = _trend_period_key(row.inspection_date, period)
            bucket = trend.setdefault(
                date_key,
                {
                    "total_count": 0,
                    "total_inspected_qty": Decimal("0"),
                    "total_accepted_qty": Decimal("0"),
                    "total_rejected_qty": Decimal("0"),
                    "total_defect_qty": Decimal("0"),
                },
            )
            bucket["total_count"] = int(bucket["total_count"]) + 1
            bucket["total_inspected_qty"] = _decimal(bucket["total_inspected_qty"]) + _decimal(row.inspected_qty)
            bucket["total_accepted_qty"] = _decimal(bucket["total_accepted_qty"]) + _decimal(row.accepted_qty)
            bucket["total_rejected_qty"] = _decimal(bucket["total_rejected_qty"]) + _decimal(row.rejected_qty)
            bucket["total_defect_qty"] = _decimal(bucket["total_defect_qty"]) + _decimal(row.defect_qty)

        points = [
            QualityStatisticsTrendPoint(
                period_key=key,
                inspection_count=int(value["total_count"]),
                defect_rate=_rate(
                    _decimal(value["total_defect_qty"]),
                    _decimal(value["total_inspected_qty"]),
                ),
                rejected_rate=_rate(
                    _decimal(value["total_rejected_qty"]),
                    _decimal(value["total_inspected_qty"]),
                ),
                period=key,
                total_count=int(value["total_count"]),
                total_inspected_qty=_decimal(value["total_inspected_qty"]),
                total_accepted_qty=_decimal(value["total_accepted_qty"]),
                total_rejected_qty=_decimal(value["total_rejected_qty"]),
                total_defect_qty=_decimal(value["total_defect_qty"]),
                overall_defect_rate=_rate(
                    _decimal(value["total_defect_qty"]),
                    _decimal(value["total_inspected_qty"]),
                ),
            )
            for key, value in sorted(trend.items(), key=lambda item: item[0])
        ]
        return QualityStatisticsTrendData(period=period, points=points)

    def export_rows(self, **filters: Any) -> QualityExportData:
        data = self.list_inspections(page=1, page_size=1000, **filters)
        rows = [QualityExportRow(**item.model_dump()) for item in data.items]
        return QualityExportData(rows=rows, total=len(rows))

    def export_details(
        self,
        *,
        company: str | None = None,
        item_code: str | None = None,
        supplier: str | None = None,
        warehouse: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        inspection_id: int | None = None,
    ) -> list[QualityInspectionDetailData]:
        if inspection_id is not None:
            detail = self.get_detail_data(inspection_id)
            if detail.status == "cancelled":
                return []
            if not self._detail_matches_filters(
                detail=detail,
                company=company,
                item_code=item_code,
                supplier=supplier,
                warehouse=warehouse,
                source_type=source_type,
                source_id=source_id,
                status=status,
                from_date=from_date,
                to_date=to_date,
            ):
                return []
            return [detail]

        if _text(status) == "cancelled":
            return []

        rows = (
            self._filtered_query(
                company=company,
                item_code=item_code,
                supplier=supplier,
                warehouse=warehouse,
                source_type=source_type,
                source_id=source_id,
                status=status,
                from_date=from_date,
                to_date=to_date,
            )
            .filter(LyQualityInspection.status != "cancelled")
            .order_by(LyQualityInspection.inspection_date.desc(), LyQualityInspection.id.desc())
            .all()
        )
        return [self.get_detail_data(int(row.id)) for row in rows]

    def diagnostic(self, **filters: Any) -> QualityDiagnosticData:
        rows = self._filtered_query(status=None, **filters).all()
        by_status = {"draft": 0, "confirmed": 0, "cancelled": 0}
        by_source_type: dict[str, int] = {}
        missing_source_count = 0
        for row in rows:
            status = str(row.status)
            if status in by_status:
                by_status[status] += 1
            source_type = str(row.source_type)
            by_source_type[source_type] = by_source_type.get(source_type, 0) + 1
            if source_type != "manual" and not _text(row.source_id):
                missing_source_count += 1
        return QualityDiagnosticData(
            total_count=len(rows),
            draft_count=by_status["draft"],
            confirmed_count=by_status["confirmed"],
            cancelled_count=by_status["cancelled"],
            missing_source_count=missing_source_count,
            by_source_type=by_source_type,
        )

    def _filtered_query(self, **filters: Any):
        query = self.session.query(LyQualityInspection)
        for field in ("company", "item_code", "supplier", "warehouse", "source_type", "source_id", "status"):
            value = _text(filters.get(field))
            if value:
                query = query.filter(getattr(LyQualityInspection, field) == value)
        if filters.get("from_date"):
            query = query.filter(LyQualityInspection.inspection_date >= filters["from_date"])
        if filters.get("to_date"):
            query = query.filter(LyQualityInspection.inspection_date <= filters["to_date"])
        return query

    @staticmethod
    def _detail_matches_filters(
        *,
        detail: QualityInspectionDetailData,
        company: str | None = None,
        item_code: str | None = None,
        supplier: str | None = None,
        warehouse: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> bool:
        if company and detail.company != company:
            return False
        if item_code and detail.item_code != item_code:
            return False
        if supplier and (_text(detail.supplier) or "") != supplier:
            return False
        if warehouse and (_text(detail.warehouse) or "") != warehouse:
            return False
        if source_type and detail.source_type != source_type:
            return False
        if source_id and (_text(detail.source_id) or "") != source_id:
            return False
        if status and detail.status != status:
            return False
        if from_date and detail.inspection_date < from_date:
            return False
        if to_date and detail.inspection_date > to_date:
            return False
        return True

    def _build_group_aggregates(
        self,
        *,
        rows: list[LyQualityInspection],
        key_getter,
        label_getter,
    ) -> list[QualityStatisticsAggregateData]:
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = str(key_getter(row))
            group = grouped.setdefault(
                key,
                {
                    "key": key,
                    "label": str(label_getter(row, key)),
                    "total_count": 0,
                    "total_inspected_qty": Decimal("0"),
                    "total_accepted_qty": Decimal("0"),
                    "total_rejected_qty": Decimal("0"),
                    "total_defect_qty": Decimal("0"),
                },
            )
            group["total_count"] = int(group["total_count"]) + 1
            group["total_inspected_qty"] = _decimal(group["total_inspected_qty"]) + _decimal(row.inspected_qty)
            group["total_accepted_qty"] = _decimal(group["total_accepted_qty"]) + _decimal(row.accepted_qty)
            group["total_rejected_qty"] = _decimal(group["total_rejected_qty"]) + _decimal(row.rejected_qty)
            group["total_defect_qty"] = _decimal(group["total_defect_qty"]) + _decimal(row.defect_qty)
        return [
            QualityStatisticsAggregateData(
                key=str(value["key"]),
                label=str(value["label"]),
                count=int(value["total_count"]),
                defect_rate=_rate(
                    _decimal(value["total_defect_qty"]),
                    _decimal(value["total_inspected_qty"]),
                ),
                total_count=int(value["total_count"]),
                total_inspected_qty=_decimal(value["total_inspected_qty"]),
                total_accepted_qty=_decimal(value["total_accepted_qty"]),
                total_rejected_qty=_decimal(value["total_rejected_qty"]),
                total_defect_qty=_decimal(value["total_defect_qty"]),
                overall_defect_rate=_rate(
                    _decimal(value["total_defect_qty"]),
                    _decimal(value["total_inspected_qty"]),
                ),
            )
            for value in sorted(
                grouped.values(),
                key=lambda item: (int(item["total_count"]), str(item["key"])),
                reverse=True,
            )
        ]

    def _get_or_raise(self, inspection_id: int) -> LyQualityInspection:
        row = self.session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one_or_none()
        if row is None:
            raise BusinessException(code=QUALITY_NOT_FOUND)
        return row

    def _validate_sources(self, payload: dict[str, Any]) -> QualitySourceValidationSnapshot:
        if payload["source_type"] != "manual" and not payload.get("source_id"):
            raise BusinessException(code=QUALITY_INVALID_SOURCE)
        self._validate_subcontract_source(payload)
        try:
            return self.source_validator.validate_for_payload(
                company=payload["company"],
                item_code=payload["item_code"],
                supplier=payload.get("supplier"),
                warehouse=payload.get("warehouse"),
                source_type=payload["source_type"],
                source_id=payload.get("source_id"),
            )
        except BusinessException:
            raise
        except ERPNextAdapterException as exc:
            raise BusinessException(code=_quality_code_for_erpnext(exc), message=exc.safe_message) from exc
        except Exception as exc:
            raise BusinessException(code=QUALITY_SOURCE_UNAVAILABLE) from exc

    def _validate_subcontract_source(self, payload: dict[str, Any]) -> None:
        if payload["source_type"] != "subcontract_receipt":
            return
        source_id = _text(payload.get("source_id"))
        if not source_id:
            raise BusinessException(code=QUALITY_INVALID_SOURCE)
        query = self.session.query(LySubcontractInspection)
        if source_id.isdigit():
            query = query.filter(LySubcontractInspection.id == int(source_id))
        else:
            query = query.filter(LySubcontractInspection.inspection_no == source_id)
        row = query.one_or_none()
        if row is None:
            raise BusinessException(code=QUALITY_INVALID_SOURCE)
        if _text(row.company) != payload["company"] or _text(row.item_code) != payload["item_code"]:
            raise BusinessException(code=QUALITY_INVALID_SOURCE)
        status = _text(row.status)
        if status not in {"inspected", "received", "completed"}:
            raise BusinessException(code=QUALITY_INVALID_SOURCE)

    def _replace_items_and_defects(
        self,
        *,
        inspection: LyQualityInspection,
        items: list[QualityInspectionItemInput],
        defects: list[QualityDefectInput],
    ) -> None:
        self.session.query(LyQualityDefect).filter(LyQualityDefect.inspection_id == inspection.id).delete()
        self.session.query(LyQualityInspectionItem).filter(LyQualityInspectionItem.inspection_id == inspection.id).delete()
        line_to_item_id: dict[int, int] = {}
        for index, item in enumerate(items, start=1):
            row = LyQualityInspectionItem(
                inspection_id=inspection.id,
                line_no=index,
                item_code=_clean_required(item.item_code, QUALITY_INVALID_SOURCE),
                sample_qty=_decimal(item.sample_qty),
                accepted_qty=_decimal(item.accepted_qty),
                rejected_qty=_decimal(item.rejected_qty),
                defect_qty=_decimal(item.defect_qty),
                result=_normalize_result(item.result),
                remark=_text(item.remark),
            )
            self.session.add(row)
            self.session.flush()
            line_to_item_id[index] = int(row.id)
        for defect in defects:
            item_id = None
            if defect.item_line_no is not None:
                item_id = line_to_item_id.get(int(defect.item_line_no))
                if item_id is None:
                    raise BusinessException(code=QUALITY_INVALID_SOURCE, message="缺陷记录引用的明细行不存在")
            row = LyQualityDefect(
                inspection_id=inspection.id,
                item_id=item_id,
                defect_code=_clean_required(defect.defect_code, QUALITY_INVALID_SOURCE),
                defect_name=_clean_required(defect.defect_name, QUALITY_INVALID_SOURCE),
                defect_qty=_decimal(defect.defect_qty),
                severity=_normalize_severity(defect.severity),
                remark=_text(defect.remark),
            )
            self.session.add(row)

    def _add_log(
        self,
        *,
        inspection: LyQualityInspection,
        action: str,
        from_status: str | None,
        to_status: str,
        operator: str,
        request_id: str | None,
        remark: str | None,
    ) -> None:
        self.session.add(
            LyQualityOperationLog(
                inspection_id=inspection.id,
                company=inspection.company,
                action=action,
                from_status=from_status,
                to_status=to_status,
                operator=operator,
                request_id=request_id,
                remark=_text(remark),
            )
        )

    def _next_inspection_no(self) -> str:
        prefix = f"QI-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        count = self.session.query(LyQualityInspection).count() + 1
        return f"{prefix}-{count:04d}"

    def _item_inputs(self, inspection: LyQualityInspection) -> list[QualityInspectionItemInput]:
        rows = (
            self.session.query(LyQualityInspectionItem)
            .filter(LyQualityInspectionItem.inspection_id == inspection.id)
            .order_by(LyQualityInspectionItem.line_no.asc())
            .all()
        )
        return [
            QualityInspectionItemInput(
                item_code=str(row.item_code),
                sample_qty=_decimal(row.sample_qty),
                accepted_qty=_decimal(row.accepted_qty),
                rejected_qty=_decimal(row.rejected_qty),
                defect_qty=_decimal(row.defect_qty),
                result=str(row.result),
                remark=_text(row.remark),
            )
            for row in rows
        ]

    def _defect_inputs(self, inspection: LyQualityInspection) -> list[QualityDefectInput]:
        rows = self.session.query(LyQualityDefect).filter(LyQualityDefect.inspection_id == inspection.id).all()
        return [
            QualityDefectInput(
                defect_code=str(row.defect_code),
                defect_name=str(row.defect_name),
                defect_qty=_decimal(row.defect_qty),
                severity=str(row.severity),
                item_line_no=None,
                remark=_text(row.remark),
            )
            for row in rows
        ]

    @staticmethod
    def _build_outbox_payload(inspection: LyQualityInspection) -> dict[str, Any]:
        return {
            "inspection_id": int(inspection.id),
            "inspection_no": str(inspection.inspection_no),
            "company": str(inspection.company),
            "source_type": str(inspection.source_type),
            "source_id": _text(inspection.source_id),
            "item_code": str(inspection.item_code),
            "supplier": _text(inspection.supplier),
            "warehouse": _text(inspection.warehouse),
            "accepted_qty": str(_decimal(inspection.accepted_qty)),
            "rejected_qty": str(_decimal(inspection.rejected_qty)),
            "confirmed_at": inspection.confirmed_at.isoformat() if inspection.confirmed_at else None,
        }


def _normalize_create_payload(payload: QualityInspectionCreateRequest) -> dict[str, Any]:
    data = payload.model_dump()
    data["items"] = list(payload.items)
    data["defects"] = list(payload.defects)
    data["company"] = _clean_required(data.get("company"), QUALITY_INVALID_SOURCE)
    data["item_code"] = _clean_required(data.get("item_code"), QUALITY_INVALID_SOURCE)
    data["source_type"] = _normalize_source_type(data.get("source_type"))
    for field in ("source_id", "supplier", "warehouse", "work_order", "sales_order", "remark"):
        data[field] = _text(data.get(field))
    _apply_qty_rules(data)
    if not data.get("items"):
        data["items"] = [
            QualityInspectionItemInput(
                item_code=data["item_code"],
                sample_qty=data["inspected_qty"],
                accepted_qty=data["accepted_qty"],
                rejected_qty=data["rejected_qty"],
                defect_qty=data["defect_qty"],
                result=data["result"],
            )
        ]
    return data


def _merge_update_payload(inspection: LyQualityInspection, payload: QualityInspectionUpdateRequest) -> dict[str, Any]:
    data = _payload_from_inspection(
        inspection,
        [
            QualityInspectionItemInput(
                item_code=str(row.item_code),
                sample_qty=_decimal(row.sample_qty),
                accepted_qty=_decimal(row.accepted_qty),
                rejected_qty=_decimal(row.rejected_qty),
                defect_qty=_decimal(row.defect_qty),
                result=str(row.result),
                remark=_text(row.remark),
            )
            for row in []
        ],
        [],
    )
    current_items = payload.items
    current_defects = payload.defects
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"items", "defects"}:
            continue
        data[field] = _text(value) if isinstance(value, str | type(None)) else value
    if current_items is None:
        current_items = [
            QualityInspectionItemInput(
                item_code=str(row.item_code),
                sample_qty=_decimal(row.sample_qty),
                accepted_qty=_decimal(row.accepted_qty),
                rejected_qty=_decimal(row.rejected_qty),
                defect_qty=_decimal(row.defect_qty),
                result=str(row.result),
                remark=_text(row.remark),
            )
            for row in inspection_items(inspection)
        ]
    if current_defects is None:
        current_defects = [
            QualityDefectInput(
                defect_code=str(row.defect_code),
                defect_name=str(row.defect_name),
                defect_qty=_decimal(row.defect_qty),
                severity=str(row.severity),
                item_line_no=None,
                remark=_text(row.remark),
            )
            for row in inspection_defects(inspection)
        ]
    data["items"] = current_items
    data["defects"] = current_defects
    _apply_qty_rules(data)
    return data


def _payload_from_inspection(
    inspection: LyQualityInspection,
    items: list[QualityInspectionItemInput],
    defects: list[QualityDefectInput],
) -> dict[str, Any]:
    data = {
        "company": str(inspection.company),
        "source_type": str(inspection.source_type),
        "source_id": _text(inspection.source_id),
        "item_code": str(inspection.item_code),
        "supplier": _text(inspection.supplier),
        "warehouse": _text(inspection.warehouse),
        "work_order": _text(inspection.work_order),
        "sales_order": _text(inspection.sales_order),
        "inspection_date": inspection.inspection_date,
        "inspected_qty": _decimal(inspection.inspected_qty),
        "accepted_qty": _decimal(inspection.accepted_qty),
        "rejected_qty": _decimal(inspection.rejected_qty),
        "defect_qty": _decimal(inspection.defect_qty),
        "result": str(inspection.result),
        "remark": _text(inspection.remark),
        "items": items,
        "defects": defects,
    }
    _apply_qty_rules(data)
    return data


def inspection_items(inspection: LyQualityInspection) -> list[LyQualityInspectionItem]:
    session = inspection._sa_instance_state.session
    if session is None:
        return []
    return (
        session.query(LyQualityInspectionItem)
        .filter(LyQualityInspectionItem.inspection_id == inspection.id)
        .order_by(LyQualityInspectionItem.line_no.asc())
        .all()
    )


def inspection_defects(inspection: LyQualityInspection) -> list[LyQualityDefect]:
    session = inspection._sa_instance_state.session
    if session is None:
        return []
    return session.query(LyQualityDefect).filter(LyQualityDefect.inspection_id == inspection.id).order_by(LyQualityDefect.id.asc()).all()


def _apply_qty_rules(data: dict[str, Any]) -> None:
    source_type = _normalize_source_type(data.get("source_type"))
    data["source_type"] = source_type
    result = _normalize_result(data.get("result"))
    inspected = _decimal(data.get("inspected_qty"))
    accepted = _decimal(data.get("accepted_qty"))
    rejected = _decimal(data.get("rejected_qty"))
    defects = _decimal(data.get("defect_qty"))
    if min(inspected, accepted, rejected, defects) < Decimal("0"):
        raise BusinessException(code=QUALITY_INVALID_QTY)
    if accepted + rejected != inspected:
        raise BusinessException(code=QUALITY_QTY_MISMATCH)
    if defects > inspected:
        raise BusinessException(code=QUALITY_INVALID_QTY, message="缺陷数量不能超过检验数量")
    data["inspected_qty"] = inspected
    data["accepted_qty"] = accepted
    data["rejected_qty"] = rejected
    data["defect_qty"] = defects
    data["defect_rate"] = _rate(defects, inspected)
    data["rejected_rate"] = _rate(rejected, inspected)
    data["result"] = result


def _normalize_source_type(value: Any) -> str:
    source_type = _text(value)
    if source_type not in SOURCE_TYPES:
        raise BusinessException(code=QUALITY_INVALID_SOURCE_TYPE)
    return source_type


def _normalize_result(value: Any) -> str:
    result = _text(value) or "pending"
    if result not in RESULT_VALUES:
        raise BusinessException(code=QUALITY_INVALID_RESULT)
    return result


def _normalize_severity(value: Any) -> str:
    severity = _text(value) or "minor"
    if severity not in {"minor", "major", "critical"}:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message="缺陷等级非法")
    return severity


def _clean_required(value: Any, code: str) -> str:
    text = _text(value)
    if not text:
        raise BusinessException(code=code)
    return text


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _rate(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == Decimal("0"):
        return Decimal("0")
    return (numerator / denominator).quantize(_RATE_QUANT, rounding=ROUND_HALF_UP)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _group_key(value: Any, fallback: str) -> str:
    return _text(value) or fallback


def _trend_period_key(inspection_date: date, period: str) -> str:
    if period == "monthly":
        return inspection_date.strftime("%Y-%m")
    if period == "weekly":
        iso = inspection_date.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    raise BusinessException(code=QUALITY_INVALID_SOURCE, message="趋势周期仅支持 monthly 或 weekly")


def _now() -> datetime:
    return datetime.now(UTC)


def _validate_source_ownership(
    source_doc: dict[str, Any],
    *,
    company: str,
    item_code: str,
    supplier: str | None,
    source_doctype: str,
) -> None:
    doc_company = _text(source_doc.get("company"))
    if not doc_company or doc_company != company:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message=f"{source_doctype} 与 company 不匹配")

    item_codes = _extract_source_item_codes(source_doc)
    if item_code not in item_codes:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message=f"{source_doctype} 与 item_code 不匹配")

    doc_supplier = _text(source_doc.get("supplier"))
    if supplier and doc_supplier and doc_supplier != supplier:
        raise BusinessException(code=QUALITY_INVALID_SOURCE, message=f"{source_doctype} 与 supplier 不匹配")


def _extract_source_item_codes(source_doc: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for key in ("item_code", "production_item", "fg_item", "finished_item_code"):
        value = _text(source_doc.get(key))
        if value:
            codes.add(value)
    items = source_doc.get("items")
    if isinstance(items, list):
        for row in items:
            if not isinstance(row, dict):
                continue
            for key in ("item_code", "production_item", "fg_item", "finished_item_code"):
                value = _text(row.get(key))
                if value:
                    codes.add(value)
    return codes


def _quality_code_for_erpnext(exc: ERPNextAdapterException) -> str:
    if exc.error_code == EXTERNAL_SERVICE_UNAVAILABLE:
        return QUALITY_SOURCE_UNAVAILABLE
    return QUALITY_INVALID_SOURCE


def _snapshot_to_dict(snapshot: QualitySourceValidationSnapshot) -> dict[str, Any]:
    return {"master_data": snapshot.master_data, "source": snapshot.source}


def _to_list_item(row: LyQualityInspection) -> QualityInspectionListItem:
    return QualityInspectionListItem(
        id=int(row.id),
        inspection_no=str(row.inspection_no),
        company=str(row.company),
        source_type=str(row.source_type),
        source_id=_text(row.source_id),
        item_code=str(row.item_code),
        supplier=_text(row.supplier),
        warehouse=_text(row.warehouse),
        inspection_date=row.inspection_date,
        inspected_qty=_decimal(row.inspected_qty),
        accepted_qty=_decimal(row.accepted_qty),
        rejected_qty=_decimal(row.rejected_qty),
        defect_qty=_decimal(row.defect_qty),
        defect_rate=_decimal(row.defect_rate),
        rejected_rate=_decimal(row.rejected_rate),
        result=str(row.result),
        status=str(row.status),
        created_by=str(row.created_by),
        created_at=row.created_at,
    )


def _to_detail(
    row: LyQualityInspection,
    *,
    items: list[LyQualityInspectionItem],
    defects: list[LyQualityDefect],
    logs: list[LyQualityOperationLog],
) -> QualityInspectionDetailData:
    base = _to_list_item(row).model_dump()
    return QualityInspectionDetailData(
        **base,
        work_order=_text(row.work_order),
        sales_order=_text(row.sales_order),
        remark=_text(row.remark),
        confirmed_by=_text(row.confirmed_by),
        confirmed_at=row.confirmed_at,
        cancelled_by=_text(row.cancelled_by),
        cancelled_at=row.cancelled_at,
        cancel_reason=_text(row.cancel_reason),
        source_snapshot=row.source_snapshot if isinstance(row.source_snapshot, dict) else None,
        items=[
            QualityInspectionItemData(
                id=int(item.id),
                line_no=int(item.line_no),
                item_code=str(item.item_code),
                sample_qty=_decimal(item.sample_qty),
                accepted_qty=_decimal(item.accepted_qty),
                rejected_qty=_decimal(item.rejected_qty),
                defect_qty=_decimal(item.defect_qty),
                result=str(item.result),
                remark=_text(item.remark),
            )
            for item in items
        ],
        defects=[
            QualityDefectData(
                id=int(defect.id),
                item_id=int(defect.item_id) if defect.item_id is not None else None,
                defect_code=str(defect.defect_code),
                defect_name=str(defect.defect_name),
                defect_qty=_decimal(defect.defect_qty),
                severity=str(defect.severity),
                remark=_text(defect.remark),
            )
            for defect in defects
        ],
        logs=[
            QualityOperationLogData(
                action=str(log.action),
                operator=str(log.operator),
                operated_at=log.operated_at,
                from_status=_text(log.from_status),
                to_status=str(log.to_status),
                remark=_text(log.remark),
            )
            for log in logs
        ],
    )
