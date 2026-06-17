"""Service layer for FastAPI-native sample workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import SAMPLE_CONFLICT
from app.core.error_codes import SAMPLE_IDEMPOTENCY_CONFLICT
from app.core.error_codes import SAMPLE_INTERNAL_ERROR
from app.core.error_codes import SAMPLE_INVALID_STATUS
from app.core.error_codes import SAMPLE_NOT_FOUND
from app.core.error_codes import STYLE_MASTER_INVALID_REFERENCE
from app.core.exceptions import BusinessException
from app.models.sample import LySampleIdempotency
from app.models.sample import LySampleOrder
from app.models.sample import LySampleTrackingNode
from app.models.sample import LySampleTrackingTemplate
from app.models.style_master import LyStyleMaster
from app.schemas.sample import SampleOrderConvertRequest
from app.schemas.sample import SampleOrderCreateRequest
from app.schemas.sample import SampleOrderItem
from app.schemas.sample import SampleOrderListData
from app.schemas.sample import SampleOrderStatusRequest
from app.schemas.sample import SampleOrderUpdateRequest
from app.schemas.sample import SampleTrackingNodeCreateRequest
from app.schemas.sample import SampleTrackingNodeItem
from app.schemas.sample import SampleTrackingTemplateCreateRequest
from app.schemas.sample import SampleTrackingTemplateItem
from app.schemas.sample import SampleTrackingTemplateListData
from app.schemas.sales_inventory import SalesOrderDraftCreateRequest
from app.schemas.sales_inventory import SalesOrderDraftLineItemCreateRequest
from app.services.sales_inventory_service import SalesInventoryService
from app.services.sales_inventory_service import SalesInventoryServiceError


@dataclass(frozen=True)
class SampleMutationResult:
    """Mutation output plus audit snapshots."""

    item: Any
    before: dict[str, Any] | None
    after: dict[str, Any]
    resource_type: str
    resource_id: int
    resource_no: str
    idempotent: bool = False


class SampleService:
    """Read and mutate sample orders and templates."""

    ORDER_STATUSES = {"draft", "pending", "patterning", "fitting", "sealed", "reversed", "converted"}
    FORM_WRITABLE_ORDER_STATUSES = {"draft"}
    EDITABLE_ORDER_STATUSES = {"draft", "reversed"}

    def __init__(self, session: Session):
        self.session = session

    def list_orders(
        self,
        *,
        company: str | None,
        keyword: str | None,
        status: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> SampleOrderListData:
        try:
            query = self.session.query(LySampleOrder)
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LySampleOrder.company == normalized_company)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LySampleOrder.sample_no).like(like_value))
                    | (func.lower(LySampleOrder.style_no).like(like_value))
                    | (func.lower(LySampleOrder.style_name).like(like_value))
                    | (func.lower(LySampleOrder.customer).like(like_value))
                    | (func.lower(LySampleOrder.factory).like(like_value))
                )
            normalized_status = self._optional_text(status)
            if normalized_status and normalized_status != "all":
                query = query.filter(LySampleOrder.status == self._normalize_order_status(normalized_status))
            if from_date:
                query = query.filter(func.date(LySampleOrder.created_at) >= from_date.isoformat())
            if to_date:
                query = query.filter(func.date(LySampleOrder.created_at) <= to_date.isoformat())

            total = int(query.count())
            rows = (
                query.order_by(LySampleOrder.created_at.desc(), LySampleOrder.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return SampleOrderListData(items=[self._order_item(row) for row in rows], total=total, page=page, page_size=page_size)

    def create_order(self, *, payload: SampleOrderCreateRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        sample_no = self._optional_text(payload.sample_no) or self._next_sample_no()
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(operation="create", entity_type="order", company=company, sample_no=sample_no, payload=payload.model_dump(mode="json"))
        idem = self._get_idempotency(entity_type="order", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create", request_hash=request_hash)
            row = self._get_order_by_id(idem.record_id)
            after = self._snapshot_order(row)
            return self._order_result(row=row, before=after, after=after, idempotent=True)

        if self._get_order_by_no(company=company, sample_no=sample_no):
            raise BusinessException(code=SAMPLE_CONFLICT, message=f"{sample_no} 已存在")
        style = self._resolve_enabled_style(company=company, style_no=payload.style_no)

        try:
            row = LySampleOrder(
                company=company,
                sample_no=sample_no,
                style_no=str(style.ys_style_no),
                style_name=str(style.ys_style_name_cn),
                customer=self._require_text(payload.customer, "customer"),
                factory=self._optional_text(payload.factory) or "",
                sample_type=str(payload.sample_type),
                stage=self._optional_text(payload.stage) or "建档",
                progress=int(payload.progress),
                pattern_maker=self._optional_text(payload.pattern_maker) or "",
                sample_maker=self._optional_text(payload.sample_maker) or "",
                due_date=payload.due_date,
                status=self._normalize_writable_order_status(str(payload.status)),
                image_tone=str(payload.image_tone),
                owner_note=self._optional_text(payload.owner_note) or "",
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="order",
                company=company,
                idempotency_key=idempotency_key,
                operation="create",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_order(row)
        return self._order_result(row=row, before=None, after=after)

    def update_order(self, *, order_id: int, payload: SampleOrderUpdateRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_order_for_mutation(order_id=order_id, company=company)
        if row.status not in self.EDITABLE_ORDER_STATUSES:
            raise BusinessException(code=SAMPLE_INVALID_STATUS, message="当前样板单状态不允许编辑")
        next_values = self._order_next_values(row=row, payload=payload)
        style = self._resolve_enabled_style(company=company, style_no=next_values.get("style_no", row.style_no))
        next_values["style_no"] = str(style.ys_style_no)
        next_values["style_name"] = str(style.ys_style_name_cn)
        request_hash = self._request_hash(operation="update", entity_type="order", company=company, order_id=order_id, payload=next_values)
        idem = self._get_idempotency(entity_type="order", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="update", request_hash=request_hash)
            idem_row = self._get_order_by_id(idem.record_id)
            after = self._snapshot_order(idem_row)
            return self._order_result(row=idem_row, before=after, after=after, idempotent=True)

        before = self._snapshot_order(row)
        try:
            for key, value in next_values.items():
                setattr(row, key, value)
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="order",
                company=company,
                idempotency_key=idempotency_key,
                operation="update",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_order(row)
        return self._order_result(row=row, before=before, after=after)

    def submit_order(self, *, order_id: int, payload: SampleOrderStatusRequest, actor: str) -> SampleMutationResult:
        return self._transition_order(
            order_id=order_id,
            payload=payload,
            actor=actor,
            operation="submit",
            allowed_from={"draft", "reversed"},
            next_status="pending",
            next_stage="待审核",
            next_progress=20,
        )

    def seal_order(self, *, order_id: int, payload: SampleOrderStatusRequest, actor: str) -> SampleMutationResult:
        return self._transition_order(
            order_id=order_id,
            payload=payload,
            actor=actor,
            operation="seal",
            allowed_from={"pending", "patterning", "fitting"},
            next_status="sealed",
            next_stage="已封样",
            next_progress=100,
        )

    def reverse_order(self, *, order_id: int, payload: SampleOrderStatusRequest, actor: str) -> SampleMutationResult:
        return self._transition_order(
            order_id=order_id,
            payload=payload,
            actor=actor,
            operation="reverse",
            allowed_from={"pending", "patterning", "fitting", "sealed"},
            next_status="reversed",
            next_stage="已反审核",
            next_progress=0,
        )

    def convert_order(self, *, order_id: int, payload: SampleOrderConvertRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_order_for_mutation(order_id=order_id, company=company)
        target_sales_order = self._optional_text(payload.target_sales_order)
        request_hash = self._request_hash(
            operation="convert",
            entity_type="order",
            company=company,
            order_id=order_id,
            target_sales_order=target_sales_order,
        )
        idem = self._get_idempotency(entity_type="order", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="convert", request_hash=request_hash)
            idem_row = self._get_order_by_id(idem.record_id)
            after = self._snapshot_order(idem_row)
            return self._order_result(row=idem_row, before=after, after=after, idempotent=True)
        if row.status != "sealed":
            raise BusinessException(code=SAMPLE_INVALID_STATUS, message="只有已封样的样板单可以转大货衔接")

        before = self._snapshot_order(row)
        try:
            sales_draft = self._create_sales_order_draft_from_sample(
                row=row,
                target_sales_order=target_sales_order,
                idempotency_key=idempotency_key,
                actor=actor,
            )
            row.status = "converted"
            row.stage = "已转大货"
            row.progress = 100
            row.bulk_handoff_no = sales_draft.sales_order_no
            row.bulk_handoff_status = "已生成 A4 销售订单草稿"
            row.converted_by = actor
            row.converted_at = datetime.now(UTC)
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="order",
                company=company,
                idempotency_key=idempotency_key,
                operation="convert",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except SalesInventoryServiceError as exc:
            if exc.code == "SALES_ORDER_IDEMPOTENCY_CONFLICT":
                raise BusinessException(code=SAMPLE_CONFLICT, message=exc.message) from exc
            raise BusinessException(code=SAMPLE_INTERNAL_ERROR, message=exc.message) from exc
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_order(row)
        return self._order_result(row=row, before=before, after=after)

    def list_templates(
        self,
        *,
        company: str | None,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> SampleTrackingTemplateListData:
        try:
            query = self.session.query(LySampleTrackingTemplate)
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LySampleTrackingTemplate.company == normalized_company)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LySampleTrackingTemplate.name).like(like_value))
                    | (func.lower(LySampleTrackingTemplate.category).like(like_value))
                    | (func.lower(LySampleTrackingTemplate.owner).like(like_value))
                )
            normalized_status = self._optional_text(status)
            if normalized_status:
                query = query.filter(LySampleTrackingTemplate.status == normalized_status)
            total = int(query.count())
            rows = (
                query.order_by(LySampleTrackingTemplate.updated_at.desc(), LySampleTrackingTemplate.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return SampleTrackingTemplateListData(
            items=[self._template_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_template(self, *, payload: SampleTrackingTemplateCreateRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        template_code = self._optional_text(payload.template_code) or self._next_template_code()
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(operation="create", entity_type="template", company=company, template_code=template_code, payload=payload.model_dump(mode="json"))
        idem = self._get_idempotency(entity_type="template", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create", request_hash=request_hash)
            row = self._get_template_by_id(idem.record_id)
            after = self._snapshot_template(row)
            return self._template_result(row=row, before=after, after=after, idempotent=True)

        if self._get_template_by_code(company=company, template_code=template_code):
            raise BusinessException(code=SAMPLE_CONFLICT, message=f"{template_code} 已存在")

        try:
            row = LySampleTrackingTemplate(
                company=company,
                template_code=template_code,
                name=self._require_text(payload.name, "name"),
                category=self._optional_text(payload.category) or "通用",
                group_name=self._optional_text(payload.group) or "默认分组",
                status=str(payload.status),
                owner=self._optional_text(payload.owner) or "",
                version_no=self._optional_text(payload.version) or "V1",
                summary=self._optional_text(payload.summary) or "",
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="template",
                company=company,
                idempotency_key=idempotency_key,
                operation="create",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_template(row)
        return self._template_result(row=row, before=None, after=after)

    def create_node(self, *, template_id: int, payload: SampleTrackingNodeCreateRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        template = self._get_template_for_mutation(template_id=template_id, company=company)
        request_hash = self._request_hash(operation="create_node", entity_type="node", company=company, template_id=template_id, payload=payload.model_dump(mode="json"))
        idem = self._get_idempotency(entity_type="node", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create_node", request_hash=request_hash)
            row = self._get_node_by_id(idem.record_id)
            after = self._snapshot_node(row)
            return self._node_result(row=row, before=after, after=after, idempotent=True)

        try:
            row = LySampleTrackingNode(
                template_id=int(template.id),
                name=self._require_text(payload.name, "name"),
                role=self._optional_text(payload.role) or "",
                lead_time=self._optional_text(payload.lead_time) or "",
                status=str(payload.status),
                gate=self._optional_text(payload.gate) or "",
                output=self._optional_text(payload.output) or "",
                reminder=self._optional_text(payload.reminder) or "",
                sequence_no=int(payload.sequence_no),
                created_by=actor,
                updated_by=actor,
            )
            template.updated_by = actor
            template.version = int(template.version or 0) + 1
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="node",
                company=company,
                idempotency_key=idempotency_key,
                operation="create_node",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_node(row)
        return self._node_result(row=row, before=None, after=after)

    def _transition_order(
        self,
        *,
        order_id: int,
        payload: SampleOrderStatusRequest,
        actor: str,
        operation: str,
        allowed_from: set[str],
        next_status: str,
        next_stage: str,
        next_progress: int,
    ) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_order_for_mutation(order_id=order_id, company=company)
        if row.status not in allowed_from:
            raise BusinessException(code=SAMPLE_INVALID_STATUS, message="当前样板单状态不允许该操作")
        request_hash = self._request_hash(operation=operation, entity_type="order", company=company, order_id=order_id, next_status=next_status, reason=payload.reason)
        idem = self._get_idempotency(entity_type="order", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation=operation, request_hash=request_hash)
            idem_row = self._get_order_by_id(idem.record_id)
            after = self._snapshot_order(idem_row)
            return self._order_result(row=idem_row, before=after, after=after, idempotent=True)

        before = self._snapshot_order(row)
        try:
            row.status = next_status
            row.stage = next_stage
            row.progress = next_progress
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            if operation == "submit":
                row.submitted_by = actor
                row.submitted_at = datetime.now(UTC)
            if operation == "reverse":
                row.reversed_by = actor
                row.reversed_at = datetime.now(UTC)
                row.reverse_reason = payload.reason or "反审核"
            self._insert_idempotency(
                entity_type="order",
                company=company,
                idempotency_key=idempotency_key,
                operation=operation,
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_order(row)
        return self._order_result(row=row, before=before, after=after)

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _require_text(cls, value: Any, field_name: str) -> str:
        text = cls._optional_text(value)
        if text is None:
            raise BusinessException(code=SAMPLE_CONFLICT, message=f"{field_name} 不能为空")
        return text

    @classmethod
    def _normalize_order_status(cls, value: str) -> str:
        status = str(value or "").strip()
        if status not in cls.ORDER_STATUSES:
            raise BusinessException(code=SAMPLE_INVALID_STATUS, message="样板单状态非法")
        return status

    @classmethod
    def _normalize_writable_order_status(cls, value: str) -> str:
        status = cls._normalize_order_status(value)
        if status not in cls.FORM_WRITABLE_ORDER_STATUSES:
            raise BusinessException(code=SAMPLE_INVALID_STATUS, message="创建/编辑不能直接写入流程状态，请使用提交、封样、反审核或转大货动作")
        return status

    @staticmethod
    def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))

    @classmethod
    def _request_hash(cls, **payload: Any) -> str:
        normalized = cls._clean_payload(payload)
        raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _next_sample_no() -> str:
        return f"SMP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _next_template_code() -> str:
        return f"STPL-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

    def _get_idempotency(self, *, entity_type: str, company: str, idempotency_key: str) -> LySampleIdempotency | None:
        return (
            self.session.query(LySampleIdempotency)
            .filter(
                LySampleIdempotency.entity_type == entity_type,
                LySampleIdempotency.company == company,
                LySampleIdempotency.idempotency_key == idempotency_key,
            )
            .first()
        )

    @staticmethod
    def _ensure_same_idempotency(row: LySampleIdempotency, *, operation: str, request_hash: str) -> None:
        if row.operation != operation or row.request_hash != request_hash:
            raise BusinessException(code=SAMPLE_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

    def _insert_idempotency(
        self,
        *,
        entity_type: str,
        company: str,
        idempotency_key: str,
        operation: str,
        request_hash: str,
        record_id: int,
        actor: str,
    ) -> None:
        self.session.add(
            LySampleIdempotency(
                entity_type=entity_type,
                company=company,
                idempotency_key=idempotency_key,
                operation=operation,
                request_hash=request_hash,
                record_id=record_id,
                created_by=actor,
            )
        )

    def _get_order_by_id(self, order_id: int) -> LySampleOrder:
        row = self.session.query(LySampleOrder).filter(LySampleOrder.id == order_id).first()
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样板单不存在")
        return row

    def _get_order_for_mutation(self, *, order_id: int, company: str) -> LySampleOrder:
        row = (
            self.session.query(LySampleOrder)
            .filter(LySampleOrder.id == order_id, LySampleOrder.company == company)
            .first()
        )
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样板单不存在或 company 不匹配")
        return row

    def _get_order_by_no(self, *, company: str, sample_no: str) -> LySampleOrder | None:
        return (
            self.session.query(LySampleOrder)
            .filter(LySampleOrder.company == company, LySampleOrder.sample_no == sample_no)
            .first()
        )

    def _resolve_enabled_style(self, *, company: str, style_no: str | None) -> LyStyleMaster:
        normalized_style_no = self._require_text(style_no, "style_no")
        row = (
            self.session.query(LyStyleMaster)
            .filter(LyStyleMaster.company == company, LyStyleMaster.ys_style_no == normalized_style_no)
            .first()
        )
        if not row or row.ys_style_status != "enabled":
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"{normalized_style_no} 款式不存在或未启用")
        return row

    def _get_template_by_id(self, template_id: int) -> LySampleTrackingTemplate:
        row = self.session.query(LySampleTrackingTemplate).filter(LySampleTrackingTemplate.id == template_id).first()
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样衣跟进模板不存在")
        return row

    def _get_template_for_mutation(self, *, template_id: int, company: str) -> LySampleTrackingTemplate:
        row = (
            self.session.query(LySampleTrackingTemplate)
            .filter(LySampleTrackingTemplate.id == template_id, LySampleTrackingTemplate.company == company)
            .first()
        )
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样衣跟进模板不存在或 company 不匹配")
        return row

    def _get_template_by_code(self, *, company: str, template_code: str) -> LySampleTrackingTemplate | None:
        return (
            self.session.query(LySampleTrackingTemplate)
            .filter(LySampleTrackingTemplate.company == company, LySampleTrackingTemplate.template_code == template_code)
            .first()
        )

    def _get_node_by_id(self, node_id: int) -> LySampleTrackingNode:
        row = self.session.query(LySampleTrackingNode).filter(LySampleTrackingNode.id == node_id).first()
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样衣跟进节点不存在")
        return row

    def _order_next_values(self, *, row: LySampleOrder, payload: SampleOrderUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key in [
            "style_no",
            "style_name",
            "customer",
            "factory",
            "sample_type",
            "stage",
            "progress",
            "pattern_maker",
            "sample_maker",
            "due_date",
            "status",
            "image_tone",
            "owner_note",
        ]:
            value = getattr(payload, key)
            if value is None:
                continue
            values[key] = self._normalize_writable_order_status(str(value)) if key == "status" else value
        if not values:
            return {}
        return values

    @classmethod
    def _snapshot_order(cls, row: LySampleOrder) -> dict[str, Any]:
        return cls._clean_payload(
            {
                "id": int(row.id),
                "company": row.company,
                "sample_no": row.sample_no,
                "style_no": row.style_no,
                "style_name": row.style_name,
                "customer": row.customer,
                "factory": row.factory,
                "sample_type": row.sample_type,
                "stage": row.stage,
                "progress": int(row.progress or 0),
                "pattern_maker": row.pattern_maker,
                "sample_maker": row.sample_maker,
                "due_date": row.due_date,
                "status": row.status,
                "bulk_handoff_no": row.bulk_handoff_no,
                "bulk_handoff_status": row.bulk_handoff_status,
                "submitted_at": row.submitted_at,
                "reversed_at": row.reversed_at,
                "reverse_reason": row.reverse_reason,
                "converted_at": row.converted_at,
                "version": int(row.version or 0),
            }
        )

    @classmethod
    def _snapshot_template(cls, row: LySampleTrackingTemplate) -> dict[str, Any]:
        return cls._clean_payload(
            {
                "id": int(row.id),
                "company": row.company,
                "template_code": row.template_code,
                "name": row.name,
                "category": row.category,
                "group": row.group_name,
                "status": row.status,
                "owner": row.owner,
                "version": row.version_no,
                "summary": row.summary,
            }
        )

    @classmethod
    def _snapshot_node(cls, row: LySampleTrackingNode) -> dict[str, Any]:
        return cls._clean_payload(
            {
                "id": int(row.id),
                "template_id": int(row.template_id),
                "name": row.name,
                "role": row.role,
                "lead_time": row.lead_time,
                "status": row.status,
                "gate": row.gate,
                "output": row.output,
                "reminder": row.reminder,
                "sequence_no": int(row.sequence_no or 0),
            }
        )

    def _order_item(self, row: LySampleOrder) -> SampleOrderItem:
        return SampleOrderItem(
            id=int(row.id),
            company=row.company,
            sample_no=row.sample_no,
            style_no=row.style_no,
            style_name=row.style_name,
            customer=row.customer,
            factory=row.factory,
            sample_type=row.sample_type,
            stage=row.stage,
            progress=int(row.progress or 0),
            pattern_maker=row.pattern_maker,
            sample_maker=row.sample_maker,
            due_date=row.due_date,
            created_at=row.created_at,
            status=row.status,
            image_tone=row.image_tone,
            owner_note=row.owner_note,
            bulk_handoff_no=row.bulk_handoff_no,
            bulk_handoff_status=row.bulk_handoff_status,
            submitted_at=row.submitted_at,
            reversed_at=row.reversed_at,
            reverse_reason=row.reverse_reason,
            converted_at=row.converted_at,
            version=int(row.version or 0),
        )

    def _template_item(self, row: LySampleTrackingTemplate) -> SampleTrackingTemplateItem:
        return SampleTrackingTemplateItem(
            id=int(row.id),
            company=row.company,
            template_code=row.template_code,
            name=row.name,
            category=row.category,
            group=row.group_name,
            status=row.status,
            owner=row.owner,
            version=row.version_no,
            updated_at=row.updated_at,
            summary=row.summary,
            nodes=[self._node_item(node) for node in row.nodes],
        )

    @staticmethod
    def _node_item(row: LySampleTrackingNode) -> SampleTrackingNodeItem:
        return SampleTrackingNodeItem(
            id=int(row.id),
            template_id=int(row.template_id),
            name=row.name,
            role=row.role,
            lead_time=row.lead_time,
            status=row.status,
            gate=row.gate,
            output=row.output,
            reminder=row.reminder,
            sequence_no=int(row.sequence_no or 0),
        )

    def _create_sales_order_draft_from_sample(
        self,
        *,
        row: LySampleOrder,
        target_sales_order: str | None,
        idempotency_key: str,
        actor: str,
    ):
        sales_idempotency_key = self._sales_draft_idempotency_key(
            company=row.company,
            sample_no=row.sample_no,
            sample_idempotency_key=idempotency_key,
        )
        return SalesInventoryService(session=self.session).create_sales_order_draft(
            payload=SalesOrderDraftCreateRequest(
                company=row.company,
                customer=row.customer,
                operation="create_draft",
                scenario_tag="sample_convert",
                sales_order_no=target_sales_order,
                source_order_ref=f"SAMPLE-{row.sample_no}",
                idempotency_key=sales_idempotency_key,
                transaction_date=date.today(),
                delivery_date=row.due_date,
                currency="CNY",
                items=[
                    SalesOrderDraftLineItemCreateRequest(
                        item_code=row.style_no,
                        item_name=row.style_name,
                        qty=Decimal("1"),
                        rate=None,
                        uom="件",
                        delivery_date=row.due_date,
                    )
                ],
            ),
            current_user=actor,
            scenario_tag="sample_convert",
        )

    @classmethod
    def _sales_draft_idempotency_key(cls, *, company: str, sample_no: str, sample_idempotency_key: str) -> str:
        digest = cls._request_hash(
            operation="sample_convert_sales_order_draft",
            company=company,
            sample_no=sample_no,
            idempotency_key=sample_idempotency_key,
        )
        return f"SAMPLE-CONVERT-{digest[:24]}"

    def _order_result(self, *, row: LySampleOrder, before: dict[str, Any] | None, after: dict[str, Any], idempotent: bool = False) -> SampleMutationResult:
        return SampleMutationResult(
            item=self._order_item(row),
            before=before,
            after=after,
            resource_type="SAMPLE_ORDER",
            resource_id=int(row.id),
            resource_no=row.sample_no,
            idempotent=idempotent,
        )

    def _template_result(self, *, row: LySampleTrackingTemplate, before: dict[str, Any] | None, after: dict[str, Any], idempotent: bool = False) -> SampleMutationResult:
        return SampleMutationResult(
            item=self._template_item(row),
            before=before,
            after=after,
            resource_type="SAMPLE_TRACKING_TEMPLATE",
            resource_id=int(row.id),
            resource_no=row.template_code,
            idempotent=idempotent,
        )

    def _node_result(self, *, row: LySampleTrackingNode, before: dict[str, Any] | None, after: dict[str, Any], idempotent: bool = False) -> SampleMutationResult:
        return SampleMutationResult(
            item=self._node_item(row),
            before=before,
            after=after,
            resource_type="SAMPLE_TRACKING_NODE",
            resource_id=int(row.id),
            resource_no=str(row.id),
            idempotent=idempotent,
        )
