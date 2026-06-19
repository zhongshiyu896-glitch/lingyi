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

from app.core.error_codes import BOM_NOT_FOUND
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
from app.models.sample import LySampleCostLine
from app.models.sample import LySampleCostOperation
from app.models.sample import LySampleMaterialBom
from app.models.sample import LySampleMaterialBomItem
from app.models.sample import LySampleMaterialBomOperation
from app.models.sample import LySampleOrder
from app.models.sample import LySampleTrackingEvent
from app.models.sample import LySampleTrackingNode
from app.models.sample import LySampleTrackingTemplate
from app.models.style_master import LyStyleMaster
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.master_data import LyMasterDataRecord
from app.schemas.sample import SampleOrderConvertRequest
from app.schemas.sample import SampleOrderCreateRequest
from app.schemas.sample import SampleOrderItem
from app.schemas.sample import SampleOrderListData
from app.schemas.sample import SampleOrderStatusRequest
from app.schemas.sample import SampleOrderUpdateRequest
from app.schemas.sample import SampleCostData
from app.schemas.sample import SampleCostLineItem
from app.schemas.sample import SampleCostUpsertRequest
from app.schemas.sample import SampleMaterialBomCopyRequest
from app.schemas.sample import SampleMaterialBomData
from app.schemas.sample import SampleMaterialBomExplodeData
from app.schemas.sample import SampleMaterialBomHeader
from app.schemas.sample import SampleMaterialBomItem
from app.schemas.sample import SampleMaterialBomRequirementItem
from app.schemas.sample import SampleMaterialBomUpsertRequest
from app.schemas.sample import SampleTrackingNodeCreateRequest
from app.schemas.sample import SampleTrackingNodeItem
from app.schemas.sample import SampleTrackingNodeUpdateRequest
from app.schemas.sample import SampleTrackingActionRequest
from app.schemas.sample import SampleTrackingEventCreateRequest
from app.schemas.sample import SampleTrackingEventItem
from app.schemas.sample import SampleTrackingEventListData
from app.schemas.sample import SampleTrackingTemplateCreateRequest
from app.schemas.sample import SampleTrackingTemplateItem
from app.schemas.sample import SampleTrackingTemplateListData
from app.schemas.sample import SampleTrackingTemplateUpdateRequest
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
    MATERIAL_BOM_WRITABLE_ORDER_STATUSES = {"draft", "reversed", "pending", "patterning", "fitting"}

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

    def list_order_tracking_events(
        self,
        *,
        order_id: int,
        company: str | None,
        page: int,
        page_size: int,
    ) -> SampleTrackingEventListData:
        normalized_company = self._require_text(company, "company")
        order = self._get_order_for_read(order_id=order_id, company=normalized_company)
        try:
            query = self.session.query(LySampleTrackingEvent).filter(
                LySampleTrackingEvent.company == normalized_company,
                LySampleTrackingEvent.sample_order_id == order_id,
            )
            total = int(query.count())
            rows = (
                query.order_by(LySampleTrackingEvent.happened_at.desc(), LySampleTrackingEvent.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return SampleTrackingEventListData(
            items=[self._event_item(row, order=order) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

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
        style = self._resolve_enabled_style(
            company=company,
            style_no=payload.style_no,
            style_master_id=payload.style_master_id,
        )

        try:
            row = LySampleOrder(
                company=company,
                sample_no=sample_no,
                style_no=str(style.ys_style_no),
                style_name=str(style.ys_style_name_cn),
                style_master_id=int(style.id),
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
        style_changed = False
        if self._style_change_requested(row=row, values=next_values):
            target_style_master_id = next_values.get("style_master_id")
            if "style_master_id" not in next_values and "style_no" not in next_values:
                target_style_master_id = row.style_master_id
            requested_style_no = next_values.get("style_no", row.style_no)
            if "style_master_id" in next_values and "style_no" not in next_values:
                requested_style_no = None
            style = self._resolve_enabled_style(
                company=company,
                style_no=requested_style_no,
                style_master_id=target_style_master_id,
            )
            style_changed = int(style.id) != int(row.style_master_id or 0) or str(style.ys_style_no) != str(row.style_no or "")
            next_values["style_master_id"] = int(style.id)
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
            if style_changed:
                self._reset_sample_material_bom_for_style_change(order=row, actor=actor)
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

    def start_patterning_order(self, *, order_id: int, payload: SampleOrderStatusRequest, actor: str) -> SampleMutationResult:
        return self._transition_order(
            order_id=order_id,
            payload=payload,
            actor=actor,
            operation="start_patterning",
            allowed_from={"pending"},
            next_status="patterning",
            next_stage="打版中",
            next_progress=45,
        )

    def start_fitting_order(self, *, order_id: int, payload: SampleOrderStatusRequest, actor: str) -> SampleMutationResult:
        return self._transition_order(
            order_id=order_id,
            payload=payload,
            actor=actor,
            operation="start_fitting",
            allowed_from={"patterning"},
            next_status="fitting",
            next_stage="试穿中",
            next_progress=70,
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

    def create_order_tracking_event(
        self,
        *,
        order_id: int,
        payload: SampleTrackingEventCreateRequest,
        actor: str,
    ) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        order = self._get_order_for_mutation(order_id=order_id, company=company)
        node = self._resolve_tracking_node(company=company, template_id=payload.template_id, node_id=payload.node_id)
        template_id = int(node.template_id) if node else payload.template_id
        node_name = self._optional_text(payload.node_name) or (node.name if node else payload.stage)
        event_actor = self._optional_text(payload.actor) or actor
        request_hash = self._request_hash(
            operation="create_tracking_event",
            entity_type="tracking_event",
            company=company,
            order_id=order_id,
            template_id=template_id,
            node_id=payload.node_id,
            node_name=node_name,
            stage=payload.stage,
            progress=payload.progress,
            result=payload.result,
            remark=payload.remark,
            actor=event_actor,
        )
        idem = self._get_idempotency(entity_type="tracking_event", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create_tracking_event", request_hash=request_hash)
            row = self._get_event_by_id(idem.record_id)
            after = self._snapshot_event(row, order=order)
            return self._event_result(row=row, order=order, before=after, after=after, idempotent=True)

        try:
            before_order = self._snapshot_order(order)
            row = LySampleTrackingEvent(
                company=company,
                sample_order_id=int(order.id),
                template_id=template_id,
                node_id=payload.node_id,
                node_name=node_name,
                stage=self._require_text(payload.stage, "stage"),
                progress=int(payload.progress),
                result=str(payload.result),
                remark=self._optional_text(payload.remark) or "",
                actor=event_actor,
                created_by=actor,
            )
            order.stage = row.stage
            order.progress = int(row.progress)
            order.updated_by = actor
            order.version = int(order.version or 0) + 1
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="tracking_event",
                company=company,
                idempotency_key=idempotency_key,
                operation="create_tracking_event",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_event(row, order=order)
        after["order_before"] = before_order
        after["order_after"] = self._snapshot_order(order)
        return self._event_result(row=row, order=order, before=None, after=after)

    def get_material_bom(self, *, order_id: int, company: str | None) -> SampleMaterialBomData:
        company = self._require_text(company, "company")
        order = self._get_order_for_read(order_id=order_id, company=company)
        bom = self._find_sample_material_bom(order=order)
        if bom is None:
            return SampleMaterialBomData(bom=None, items=[])
        return self._sample_material_bom_data(order=order, bom=bom)

    def upsert_material_bom(
        self,
        *,
        order_id: int,
        payload: SampleMaterialBomUpsertRequest,
        actor: str,
    ) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        order = self._get_order_for_mutation(order_id=order_id, company=company)
        self._ensure_sample_material_bom_writable(order)
        request_hash = self._request_hash(
            operation="sample_material_bom_upsert",
            company=company,
            order_id=order_id,
            version_no=payload.version_no,
            items=[item.model_dump(mode="json") for item in payload.items],
        )
        existing_operation = self._get_material_bom_operation(
            company=company,
            operation="upsert",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if existing_operation.request_hash != request_hash:
                raise BusinessException(code=SAMPLE_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")
            bom = self._must_get_sample_material_bom_by_id(int(existing_operation.bom_id))
            data = self._sample_material_bom_data(order=order, bom=bom)
            return SampleMutationResult(
                item=data,
                before=data.model_dump(mode="json"),
                after=data.model_dump(mode="json"),
                resource_type="SAMPLE_MATERIAL_BOM",
                resource_id=int(bom.id),
                resource_no=str(order.sample_no),
                idempotent=True,
            )

        self._ensure_material_bom_items_active(company=company, items=payload.items)
        bom = self._find_sample_material_bom(order=order)
        before = self._sample_material_bom_data(order=order, bom=bom).model_dump(mode="json") if bom else None
        try:
            bom = self._upsert_sample_material_bom_header(
                order=order,
                source_bom_id=(int(bom.source_bom_id) if bom and bom.source_bom_id is not None else None),
                version_no=payload.version_no,
                actor=actor,
                existing=bom,
            )
            self.session.query(LySampleMaterialBomItem).filter(LySampleMaterialBomItem.bom_id == int(bom.id)).delete()
            next_item_id = self._next_id(LySampleMaterialBomItem)
            for item in payload.items:
                self.session.add(
                    LySampleMaterialBomItem(
                        id=next_item_id,
                        bom_id=int(bom.id),
                        source_bom_item_id=None,
                        material_item_code=item.material_item_code.strip(),
                        color=self._optional_text(item.color),
                        part=self._optional_text(item.part),
                        qty_per_piece=item.qty_per_piece,
                        loss_rate=item.loss_rate,
                        uom=item.uom.strip(),
                        is_alternative=1 if item.is_alternative else 0,
                        replace_group=self._optional_text(item.replace_group),
                        remark=self._optional_text(item.remark),
                    )
                )
                next_item_id += 1
            self.session.flush()
            data = self._sample_material_bom_data(order=order, bom=bom)
            self._insert_material_bom_operation(
                bom_id=int(bom.id),
                company=company,
                operation="upsert",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=data,
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        return SampleMutationResult(
            item=data,
            before=before,
            after=data.model_dump(mode="json"),
            resource_type="SAMPLE_MATERIAL_BOM",
            resource_id=int(data.bom.id) if data.bom else int(order.id),
            resource_no=str(order.sample_no),
        )

    def copy_material_bom_from_style(
        self,
        *,
        order_id: int,
        payload: SampleMaterialBomCopyRequest,
        actor: str,
    ) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        order = self._get_order_for_mutation(order_id=order_id, company=company)
        self._ensure_sample_material_bom_writable(order)
        style_bom = self._resolve_style_material_bom_for_sample(order=order, style_bom_id=payload.style_bom_id)
        source_items = (
            self.session.query(LyApparelBomItem)
            .filter(LyApparelBomItem.bom_id == int(style_bom.id))
            .order_by(LyApparelBomItem.id.asc())
            .all()
        )
        if not source_items:
            raise BusinessException(code=BOM_NOT_FOUND, message="款式用料 BOM 明细为空，无法复制到样板")

        self._ensure_material_bom_items_active(company=company, items=source_items)
        request_hash = self._request_hash(
            operation="sample_material_bom_copy_from_style",
            company=company,
            order_id=order_id,
            source_bom_id=int(style_bom.id),
            source_item_ids=[int(item.id) for item in source_items],
        )
        existing_operation = self._get_material_bom_operation(
            company=company,
            operation="copy_from_style",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if existing_operation.request_hash != request_hash:
                raise BusinessException(code=SAMPLE_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")
            bom = self._must_get_sample_material_bom_by_id(int(existing_operation.bom_id))
            data = self._sample_material_bom_data(order=order, bom=bom)
            return SampleMutationResult(
                item=data,
                before=data.model_dump(mode="json"),
                after=data.model_dump(mode="json"),
                resource_type="SAMPLE_MATERIAL_BOM",
                resource_id=int(bom.id),
                resource_no=str(order.sample_no),
                idempotent=True,
            )

        bom = self._find_sample_material_bom(order=order)
        before = self._sample_material_bom_data(order=order, bom=bom).model_dump(mode="json") if bom else None
        try:
            bom = self._upsert_sample_material_bom_header(
                order=order,
                source_bom_id=int(style_bom.id),
                version_no="S1",
                actor=actor,
                existing=bom,
            )
            self.session.query(LySampleMaterialBomItem).filter(LySampleMaterialBomItem.bom_id == int(bom.id)).delete()
            next_item_id = self._next_id(LySampleMaterialBomItem)
            for item in source_items:
                self.session.add(
                    LySampleMaterialBomItem(
                        id=next_item_id,
                        bom_id=int(bom.id),
                        source_bom_item_id=int(item.id),
                        material_item_code=str(item.material_item_code),
                        color=item.color,
                        part=getattr(item, "part", None),
                        qty_per_piece=Decimal(str(item.qty_per_piece)),
                        loss_rate=Decimal(str(item.loss_rate or 0)),
                        uom=str(item.uom),
                        is_alternative=0,
                        replace_group=None,
                        remark=item.remark,
                    )
                )
                next_item_id += 1
            self.session.flush()
            data = self._sample_material_bom_data(order=order, bom=bom)
            self._insert_material_bom_operation(
                bom_id=int(bom.id),
                company=company,
                operation="copy_from_style",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=data,
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        return SampleMutationResult(
            item=data,
            before=before,
            after=data.model_dump(mode="json"),
            resource_type="SAMPLE_MATERIAL_BOM",
            resource_id=int(data.bom.id) if data.bom else int(order.id),
            resource_no=str(order.sample_no),
        )

    def explode_material_bom(self, *, order_id: int, company: str | None, order_qty: Decimal) -> SampleMaterialBomExplodeData:
        company = self._require_text(company, "company")
        order = self._get_order_for_read(order_id=order_id, company=company)
        bom = self._find_sample_material_bom(order=order)
        if bom is None:
            raise BusinessException(code=BOM_NOT_FOUND, message="该样板单未维护打样用料 BOM")
        data = self._sample_material_bom_data(order=order, bom=bom)
        if not data.items:
            raise BusinessException(code=BOM_NOT_FOUND, message="该样板单打样用料 BOM 明细为空")
        items: list[SampleMaterialBomRequirementItem] = []
        total = Decimal("0")
        for item in data.items:
            required_qty = (Decimal(str(order_qty)) * item.qty_per_piece * (Decimal("1") + item.loss_rate)).quantize(Decimal("0.000001"))
            total += required_qty
            items.append(
                SampleMaterialBomRequirementItem(
                    material_item_code=item.material_item_code,
                    color=item.color,
                    part=item.part,
                    uom=item.uom,
                    qty_per_piece=item.qty_per_piece,
                    loss_rate=item.loss_rate,
                    required_qty=required_qty,
                )
            )
        return SampleMaterialBomExplodeData(
            sample_order_id=int(order.id),
            order_qty=Decimal(str(order_qty)),
            items=items,
            total_required_qty=total.quantize(Decimal("0.000001")),
        )

    def get_costs(self, *, order_id: int, company: str | None) -> SampleCostData:
        company = self._require_text(company, "company")
        order = self._get_order_for_read(order_id=order_id, company=company)
        return self._sample_cost_data(order=order)

    def upsert_costs(self, *, order_id: int, payload: SampleCostUpsertRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        order = self._get_order_for_mutation(order_id=order_id, company=company)
        normalized_items = [self._normalize_cost_payload(item) for item in payload.items]
        request_hash = self._request_hash(
            operation="sample_cost_upsert",
            company=company,
            order_id=order_id,
            items=normalized_items,
        )
        existing_operation = self._get_cost_operation(
            company=company,
            operation="upsert",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if existing_operation.request_hash != request_hash:
                raise BusinessException(code=SAMPLE_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")
            data = self._sample_cost_data(order=order)
            return SampleMutationResult(
                item=data,
                before=data.model_dump(mode="json"),
                after=data.model_dump(mode="json"),
                resource_type="SAMPLE_COST",
                resource_id=int(order.id),
                resource_no=str(order.sample_no),
                idempotent=True,
            )

        before = self._sample_cost_data(order=order).model_dump(mode="json")
        try:
            self.session.query(LySampleCostLine).filter(
                LySampleCostLine.company == company,
                LySampleCostLine.sample_order_id == int(order.id),
            ).delete()
            next_id = self._next_id(LySampleCostLine)
            now = datetime.now(UTC)
            for item in normalized_items:
                self.session.add(
                    LySampleCostLine(
                        id=next_id,
                        company=company,
                        sample_order_id=int(order.id),
                        cost_type=item["cost_type"],
                        description=item["description"],
                        qty=item["qty"],
                        unit_price=item["unit_price"],
                        amount=item["amount"],
                        occurred_date=item["occurred_date"],
                        remark=item["remark"],
                        created_by=actor,
                        updated_by=actor,
                        updated_at=now,
                    )
                )
                next_id += 1
            self.session.flush()
            data = self._sample_cost_data(order=order)
            self._insert_cost_operation(
                sample_order_id=int(order.id),
                company=company,
                operation="upsert",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=data,
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        return SampleMutationResult(
            item=data,
            before=before,
            after=data.model_dump(mode="json"),
            resource_type="SAMPLE_COST",
            resource_id=int(order.id),
            resource_no=str(order.sample_no),
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

    def update_template(self, *, template_id: int, payload: SampleTrackingTemplateUpdateRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_template_for_mutation(template_id=template_id, company=company)
        next_values = self._template_next_values(payload=payload)
        request_hash = self._request_hash(operation="update", entity_type="template", company=company, template_id=template_id, payload=next_values)
        idem = self._get_idempotency(entity_type="template", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="update", request_hash=request_hash)
            idem_row = self._get_template_by_id(idem.record_id)
            after = self._snapshot_template(idem_row)
            return self._template_result(row=idem_row, before=after, after=after, idempotent=True)

        before = self._snapshot_template(row)
        try:
            for key, value in next_values.items():
                setattr(row, key, value)
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="template",
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
        after = self._snapshot_template(row)
        return self._template_result(row=row, before=before, after=after)

    def deactivate_template(self, *, template_id: int, payload: SampleTrackingActionRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_template_for_mutation(template_id=template_id, company=company)
        request_hash = self._request_hash(operation="deactivate", entity_type="template", company=company, template_id=template_id, reason=payload.reason)
        idem = self._get_idempotency(entity_type="template", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="deactivate", request_hash=request_hash)
            idem_row = self._get_template_by_id(idem.record_id)
            after = self._snapshot_template(idem_row)
            return self._template_result(row=idem_row, before=after, after=after, idempotent=True)

        before = self._snapshot_template(row)
        try:
            row.status = "disabled"
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="template",
                company=company,
                idempotency_key=idempotency_key,
                operation="deactivate",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_template(row)
        return self._template_result(row=row, before=before, after=after)

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

    def update_node(self, *, template_id: int, node_id: int, payload: SampleTrackingNodeUpdateRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        template = self._get_template_for_mutation(template_id=template_id, company=company)
        row = self._get_node_for_mutation(template_id=template_id, node_id=node_id)
        next_values = self._node_next_values(payload=payload)
        request_hash = self._request_hash(operation="update", entity_type="node", company=company, template_id=template_id, node_id=node_id, payload=next_values)
        idem = self._get_idempotency(entity_type="node", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="update", request_hash=request_hash)
            idem_row = self._get_node_by_id(idem.record_id)
            after = self._snapshot_node(idem_row)
            return self._node_result(row=idem_row, before=after, after=after, idempotent=True)

        before = self._snapshot_node(row)
        try:
            for key, value in next_values.items():
                setattr(row, key, value)
            row.updated_by = actor
            template.updated_by = actor
            template.version = int(template.version or 0) + 1
            self._insert_idempotency(
                entity_type="node",
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
        after = self._snapshot_node(row)
        return self._node_result(row=row, before=before, after=after)

    def delete_node(self, *, template_id: int, node_id: int, payload: SampleTrackingActionRequest, actor: str) -> SampleMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        template = self._get_template_for_mutation(template_id=template_id, company=company)
        request_hash = self._request_hash(operation="delete_node", entity_type="node", company=company, template_id=template_id, node_id=node_id, reason=payload.reason)
        idem = self._get_idempotency(entity_type="node", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="delete_node", request_hash=request_hash)
            deleted = {"id": int(idem.record_id), "deleted": True}
            return SampleMutationResult(
                item=deleted,
                before=None,
                after=deleted,
                resource_type="SAMPLE_TRACKING_NODE",
                resource_id=int(idem.record_id),
                resource_no=str(idem.record_id),
                idempotent=True,
            )
        row = self._get_node_for_mutation(template_id=template_id, node_id=node_id)
        before = self._snapshot_node(row)
        deleted = {"id": int(row.id), "template_id": int(template.id), "deleted": True}
        try:
            self._insert_idempotency(
                entity_type="node",
                company=company,
                idempotency_key=idempotency_key,
                operation="delete_node",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            template.updated_by = actor
            template.version = int(template.version or 0) + 1
            self.session.delete(row)
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        return SampleMutationResult(
            item=deleted,
            before=before,
            after=deleted,
            resource_type="SAMPLE_TRACKING_NODE",
            resource_id=int(node_id),
            resource_no=str(node_id),
        )

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

    def _next_id(self, model: type[Any]) -> int:
        current = self.session.query(func.max(model.id)).scalar()
        return int(current or 0) + 1

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

    def _find_sample_material_bom(self, *, order: LySampleOrder) -> LySampleMaterialBom | None:
        return (
            self.session.query(LySampleMaterialBom)
            .filter(
                LySampleMaterialBom.company == order.company,
                LySampleMaterialBom.sample_order_id == int(order.id),
            )
            .order_by(LySampleMaterialBom.id.desc())
            .first()
        )

    def _must_get_sample_material_bom_by_id(self, bom_id: int) -> LySampleMaterialBom:
        row = self.session.query(LySampleMaterialBom).filter(LySampleMaterialBom.id == int(bom_id)).first()
        if row is None:
            raise BusinessException(code=BOM_NOT_FOUND, message="样板用料 BOM 不存在")
        return row

    def _reset_sample_material_bom_for_style_change(self, *, order: LySampleOrder, actor: str) -> None:
        bom = self._find_sample_material_bom(order=order)
        if bom is None:
            return
        self.session.query(LySampleMaterialBomItem).filter(LySampleMaterialBomItem.bom_id == int(bom.id)).delete()
        bom.style_master_id = int(order.style_master_id) if order.style_master_id is not None else None
        bom.item_code = str(order.style_no)
        bom.source_bom_id = None
        bom.version_no = "S1"
        bom.status = "draft"
        bom.updated_by = actor
        bom.updated_at = datetime.now(UTC)

    def _sample_material_bom_data(self, *, order: LySampleOrder, bom: LySampleMaterialBom) -> SampleMaterialBomData:
        items = (
            self.session.query(LySampleMaterialBomItem)
            .filter(LySampleMaterialBomItem.bom_id == int(bom.id))
            .order_by(LySampleMaterialBomItem.id.asc())
            .all()
        )
        return SampleMaterialBomData(
            bom=SampleMaterialBomHeader(
                id=int(bom.id),
                company=str(bom.company),
                sample_order_id=int(order.id),
                sample_no=str(order.sample_no),
                style_master_id=int(bom.style_master_id) if bom.style_master_id is not None else None,
                item_code=str(bom.item_code),
                source_bom_id=int(bom.source_bom_id) if bom.source_bom_id is not None else None,
                version_no=str(bom.version_no),
                status=str(bom.status),
                updated_at=bom.updated_at,
            ),
            items=[
                SampleMaterialBomItem(
                    id=int(item.id),
                    source_bom_item_id=int(item.source_bom_item_id) if item.source_bom_item_id is not None else None,
                    material_item_code=str(item.material_item_code),
                    color=item.color,
                    part=item.part,
                    qty_per_piece=Decimal(str(item.qty_per_piece)),
                    loss_rate=Decimal(str(item.loss_rate or 0)),
                    uom=str(item.uom),
                    is_alternative=bool(item.is_alternative),
                    replace_group=item.replace_group,
                    remark=item.remark,
                )
                for item in items
            ],
        )

    def _upsert_sample_material_bom_header(
        self,
        *,
        order: LySampleOrder,
        source_bom_id: int | None,
        version_no: str,
        actor: str,
        existing: LySampleMaterialBom | None,
    ) -> LySampleMaterialBom:
        now = datetime.now(UTC)
        if existing is not None:
            existing.company = str(order.company)
            existing.sample_order_id = int(order.id)
            existing.style_master_id = int(order.style_master_id) if order.style_master_id is not None else None
            existing.item_code = str(order.style_no)
            existing.source_bom_id = source_bom_id
            existing.version_no = str(version_no or "S1")
            existing.status = "draft"
            existing.updated_by = actor
            existing.updated_at = now
            self.session.flush()
            return existing

        row = LySampleMaterialBom(
            id=self._next_id(LySampleMaterialBom),
            company=str(order.company),
            sample_order_id=int(order.id),
            style_master_id=int(order.style_master_id) if order.style_master_id is not None else None,
            item_code=str(order.style_no),
            source_bom_id=source_bom_id,
            version_no=str(version_no or "S1"),
            status="draft",
            created_by=actor,
            updated_by=actor,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def _resolve_style_material_bom_for_sample(self, *, order: LySampleOrder, style_bom_id: int | None) -> LyApparelBom:
        query = self.session.query(LyApparelBom).filter(LyApparelBom.company == order.company)
        if style_bom_id is not None:
            query = query.filter(LyApparelBom.id == int(style_bom_id))
        else:
            if order.style_master_id is None:
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message="样板单缺少 style_master_id，无法复制款用料 BOM")
            query = query.filter(
                LyApparelBom.style_master_id == int(order.style_master_id),
                LyApparelBom.item_code == str(order.style_no),
                LyApparelBom.status == "active",
                LyApparelBom.is_default.is_(True),
            )
        row = query.order_by(LyApparelBom.id.desc()).first()
        if row is None:
            raise BusinessException(code=BOM_NOT_FOUND, message="该样板所选款式未维护默认用料 BOM")
        if str(row.item_code) != str(order.style_no):
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message="款 BOM 与样板单款号不一致")
        return row

    def _ensure_sample_material_bom_writable(self, order: LySampleOrder) -> None:
        if str(order.status) not in self.MATERIAL_BOM_WRITABLE_ORDER_STATUSES:
            raise BusinessException(code=SAMPLE_INVALID_STATUS, message="当前样板单状态不允许维护打样用料 BOM")

    def _ensure_material_bom_items_active(self, *, company: str, items: list[Any]) -> None:
        codes: list[str] = []
        for item in items:
            code = self._require_text(getattr(item, "material_item_code", ""), "material_item_code")
            if code not in codes:
                codes.append(code)
        if not codes:
            return
        try:
            rows = (
                self.session.query(LyMasterDataRecord.code)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == company,
                    LyMasterDataRecord.code.in_(codes),
                    LyMasterDataRecord.status == "active",
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        active_codes = {str(row.code) for row in rows}
        invalid_codes = [code for code in codes if code not in active_codes]
        if invalid_codes:
            raise BusinessException(
                code=STYLE_MASTER_INVALID_REFERENCE,
                message=f"物料主数据不存在或已停用: {', '.join(invalid_codes)}",
            )

    def _get_material_bom_operation(
        self,
        *,
        company: str,
        operation: str,
        idempotency_key: str,
    ) -> LySampleMaterialBomOperation | None:
        return (
            self.session.query(LySampleMaterialBomOperation)
            .filter(
                LySampleMaterialBomOperation.company == company,
                LySampleMaterialBomOperation.operation == operation,
                LySampleMaterialBomOperation.idempotency_key == idempotency_key,
            )
            .first()
        )

    def _insert_material_bom_operation(
        self,
        *,
        bom_id: int,
        company: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        response: SampleMaterialBomData,
        actor: str,
    ) -> None:
        self.session.add(
            LySampleMaterialBomOperation(
                bom_id=bom_id,
                company=company,
                operation=operation,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=json.dumps(response.model_dump(mode="json"), ensure_ascii=False, default=str),
                created_by=actor,
            )
        )

    def _sample_cost_data(self, *, order: LySampleOrder) -> SampleCostData:
        rows = (
            self.session.query(LySampleCostLine)
            .filter(
                LySampleCostLine.company == order.company,
                LySampleCostLine.sample_order_id == int(order.id),
            )
            .order_by(LySampleCostLine.id.asc())
            .all()
        )
        items = [
            SampleCostLineItem(
                id=int(row.id),
                cost_type=str(row.cost_type),
                description=str(row.description or ""),
                qty=Decimal(str(row.qty or 0)),
                unit_price=Decimal(str(row.unit_price or 0)),
                amount=Decimal(str(row.amount or 0)),
                occurred_date=row.occurred_date,
                remark=row.remark,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
        total = sum((item.amount for item in items), Decimal("0")).quantize(Decimal("0.000001"))
        return SampleCostData(
            sample_order_id=int(order.id),
            sample_no=str(order.sample_no),
            company=str(order.company),
            total_amount=total,
            items=items,
        )

    def _normalize_cost_payload(self, item: Any) -> dict[str, Any]:
        qty = Decimal(str(item.qty or 0))
        unit_price = Decimal(str(item.unit_price or 0))
        amount = Decimal(str(item.amount)) if item.amount is not None else (qty * unit_price)
        return {
            "cost_type": self._require_text(item.cost_type, "cost_type"),
            "description": self._optional_text(item.description) or "",
            "qty": qty.quantize(Decimal("0.000001")),
            "unit_price": unit_price.quantize(Decimal("0.000001")),
            "amount": amount.quantize(Decimal("0.000001")),
            "occurred_date": item.occurred_date,
            "remark": self._optional_text(item.remark),
        }

    def _get_cost_operation(
        self,
        *,
        company: str,
        operation: str,
        idempotency_key: str,
    ) -> LySampleCostOperation | None:
        return (
            self.session.query(LySampleCostOperation)
            .filter(
                LySampleCostOperation.company == company,
                LySampleCostOperation.operation == operation,
                LySampleCostOperation.idempotency_key == idempotency_key,
            )
            .first()
        )

    def _insert_cost_operation(
        self,
        *,
        sample_order_id: int,
        company: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        response: SampleCostData,
        actor: str,
    ) -> None:
        self.session.add(
            LySampleCostOperation(
                sample_order_id=sample_order_id,
                company=company,
                operation=operation,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=json.dumps(response.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, default=str),
                created_by=actor,
            )
        )

    def _get_order_for_mutation(self, *, order_id: int, company: str) -> LySampleOrder:
        row = (
            self.session.query(LySampleOrder)
            .filter(LySampleOrder.id == order_id, LySampleOrder.company == company)
            .first()
        )
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样板单不存在或 company 不匹配")
        return row

    def _get_order_for_read(self, *, order_id: int, company: str) -> LySampleOrder:
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

    def _style_change_requested(self, *, row: LySampleOrder, values: dict[str, Any]) -> bool:
        if "style_master_id" in values and values["style_master_id"] != row.style_master_id:
            return True
        if "style_no" in values and self._optional_text(values["style_no"]) != self._optional_text(row.style_no):
            return True
        if "style_name" in values and self._optional_text(values["style_name"]) != self._optional_text(row.style_name):
            return True
        return False

    def _resolve_enabled_style(
        self,
        *,
        company: str,
        style_no: str | None,
        style_master_id: int | None = None,
    ) -> LyStyleMaster:
        normalized_style_no = self._optional_text(style_no)
        if style_master_id is not None:
            row = (
                self.session.query(LyStyleMaster)
                .filter(LyStyleMaster.id == int(style_master_id), LyStyleMaster.company == company)
                .first()
            )
            if not row or row.ys_style_status != "enabled":
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"{style_master_id} 款式主档不存在或未启用")
            if normalized_style_no and normalized_style_no != str(row.ys_style_no):
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message="样板单款式主档与款号不一致")
            return row

        normalized_style_no = self._require_text(normalized_style_no, "style_no")
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

    def _get_node_for_mutation(self, *, template_id: int, node_id: int) -> LySampleTrackingNode:
        row = (
            self.session.query(LySampleTrackingNode)
            .filter(LySampleTrackingNode.id == node_id, LySampleTrackingNode.template_id == template_id)
            .first()
        )
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样衣跟进节点不存在或模板不匹配")
        return row

    def _resolve_tracking_node(
        self,
        *,
        company: str,
        template_id: int | None,
        node_id: int | None,
    ) -> LySampleTrackingNode | None:
        if node_id is None:
            if template_id is not None:
                self._get_template_for_mutation(template_id=template_id, company=company)
            return None
        row = self.session.query(LySampleTrackingNode).filter(LySampleTrackingNode.id == node_id).first()
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样衣跟进节点不存在")
        template = self._get_template_for_mutation(template_id=int(row.template_id), company=company)
        if template_id is not None and int(template.id) != int(template_id):
            raise BusinessException(code=SAMPLE_CONFLICT, message="样衣跟进节点与模板不匹配")
        return row

    def _get_event_by_id(self, event_id: int) -> LySampleTrackingEvent:
        row = self.session.query(LySampleTrackingEvent).filter(LySampleTrackingEvent.id == event_id).first()
        if row is None:
            raise BusinessException(code=SAMPLE_NOT_FOUND, message="样板单跟进事件不存在")
        return row

    def _order_next_values(self, *, row: LySampleOrder, payload: SampleOrderUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key in [
            "style_master_id",
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

    def _template_next_values(self, *, payload: SampleTrackingTemplateUpdateRequest) -> dict[str, Any]:
        mapping = {
            "name": "name",
            "category": "category",
            "group": "group_name",
            "status": "status",
            "owner": "owner",
            "version": "version_no",
            "summary": "summary",
        }
        values: dict[str, Any] = {}
        for source_key, target_key in mapping.items():
            value = getattr(payload, source_key)
            if value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
            values[target_key] = value
        return values

    def _node_next_values(self, *, payload: SampleTrackingNodeUpdateRequest) -> dict[str, Any]:
        mapping = {
            "name": "name",
            "role": "role",
            "lead_time": "lead_time",
            "status": "status",
            "gate": "gate",
            "output": "output",
            "reminder": "reminder",
            "sequence_no": "sequence_no",
        }
        values: dict[str, Any] = {}
        for source_key, target_key in mapping.items():
            value = getattr(payload, source_key)
            if value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
            values[target_key] = value
        return values

    @classmethod
    def _snapshot_order(cls, row: LySampleOrder) -> dict[str, Any]:
        return cls._clean_payload(
            {
                "id": int(row.id),
                "company": row.company,
                "sample_no": row.sample_no,
                "style_master_id": int(row.style_master_id) if row.style_master_id is not None else None,
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

    @classmethod
    def _snapshot_event(cls, row: LySampleTrackingEvent, *, order: LySampleOrder) -> dict[str, Any]:
        return cls._clean_payload(
            {
                "id": int(row.id),
                "company": row.company,
                "sample_order_id": int(row.sample_order_id),
                "sample_no": order.sample_no,
                "template_id": int(row.template_id) if row.template_id is not None else None,
                "node_id": int(row.node_id) if row.node_id is not None else None,
                "node_name": row.node_name,
                "stage": row.stage,
                "progress": int(row.progress or 0),
                "result": row.result,
                "remark": row.remark,
                "actor": row.actor,
                "happened_at": row.happened_at,
            }
        )

    def _order_item(self, row: LySampleOrder) -> SampleOrderItem:
        return SampleOrderItem(
            id=int(row.id),
            company=row.company,
            sample_no=row.sample_no,
            style_master_id=int(row.style_master_id) if row.style_master_id is not None else None,
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

    def _event_item(self, row: LySampleTrackingEvent, *, order: LySampleOrder) -> SampleTrackingEventItem:
        return SampleTrackingEventItem(
            id=int(row.id),
            company=row.company,
            sample_order_id=int(row.sample_order_id),
            sample_no=order.sample_no,
            template_id=int(row.template_id) if row.template_id is not None else None,
            node_id=int(row.node_id) if row.node_id is not None else None,
            node_name=row.node_name,
            stage=row.stage,
            progress=int(row.progress or 0),
            result=row.result,
            remark=row.remark,
            actor=row.actor,
            happened_at=row.happened_at,
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
                        style_master_id=int(row.style_master_id) if row.style_master_id is not None else None,
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

    def _event_result(
        self,
        *,
        row: LySampleTrackingEvent,
        order: LySampleOrder,
        before: dict[str, Any] | None,
        after: dict[str, Any],
        idempotent: bool = False,
    ) -> SampleMutationResult:
        return SampleMutationResult(
            item=self._event_item(row, order=order),
            before=before,
            after=after,
            resource_type="SAMPLE_TRACKING_EVENT",
            resource_id=int(row.id),
            resource_no=f"{order.sample_no}#{int(row.id)}",
            idempotent=idempotent,
        )
