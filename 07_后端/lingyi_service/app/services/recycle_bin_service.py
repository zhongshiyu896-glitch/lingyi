"""Service layer for the unified recoverable recycle bin."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
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
from app.core.error_codes import MASTER_DATA_CONFLICT
from app.core.error_codes import RECYCLE_BIN_CONFLICT
from app.core.error_codes import RECYCLE_BIN_NOT_FOUND
from app.core.exceptions import BusinessException
from app.models.master_data import LyMasterDataRecord
from app.models.production import LyProductionFollowupTemplate
from app.models.production import LyProductionFollowupTemplateNode
from app.models.recycle_bin import LyRecycleBinItem
from app.models.sample import LySampleTrackingNode
from app.models.sample import LySampleTrackingTemplate
from app.models.style_master import LyStyleDictionary
from app.schemas.recycle_bin import RecycleBinItem
from app.schemas.recycle_bin import RecycleBinListData

ENTITY_TYPE_TO_PATH = {
    "customer": "customers",
    "supplier": "suppliers",
    "factory": "factories",
    "warehouse": "warehouses",
    "material": "materials",
    "sample_type": "sample-types",
    "common_address": "common-addresses",
    "trade_term": "trade-terms",
    "invoice_type": "invoice-types",
    "cost_type": "cost-types",
    "size_sort": "size-sorts",
    "distribution_channel": "distribution-channels",
    "bank_account": "bank-accounts",
}


class RecycleBinService:
    """Create, list, restore and permanently purge deletion snapshots."""

    def __init__(self, session: Session):
        self.session = session

    def list_items(
        self,
        *,
        page: int,
        page_size: int,
        module: str | None = None,
        entity_type: str | None = None,
        company: str | None = None,
        keyword: str | None = None,
    ) -> RecycleBinListData:
        try:
            query = self.session.query(LyRecycleBinItem).filter(LyRecycleBinItem.status == "deleted")
            normalized_module = self._optional_text(module)
            if normalized_module:
                query = query.filter(LyRecycleBinItem.module == normalized_module)
            normalized_entity_type = self._optional_text(entity_type)
            if normalized_entity_type:
                query = query.filter(LyRecycleBinItem.entity_type == normalized_entity_type)
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyRecycleBinItem.company == normalized_company)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyRecycleBinItem.code).like(like_value))
                    | (func.lower(LyRecycleBinItem.name).like(like_value))
                    | (func.lower(LyRecycleBinItem.entity_type).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(LyRecycleBinItem.deleted_at.desc(), LyRecycleBinItem.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return RecycleBinListData(items=[self._to_item(row) for row in rows], total=total, page=page, page_size=page_size)

    def move_master_data_to_trash(self, *, row: LyMasterDataRecord, actor: str) -> LyRecycleBinItem:
        item = LyRecycleBinItem(
            module="master_data",
            entity_type=str(row.entity_type),
            entity_path=ENTITY_TYPE_TO_PATH.get(str(row.entity_type)),
            original_id=int(row.id),
            company=str(row.company),
            code=str(row.code),
            name=str(row.name),
            snapshot=self._snapshot_master_data(row),
            details={"table": "ly_master_data_record"},
            deleted_by=actor,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def move_style_dictionary_to_trash(self, *, row: LyStyleDictionary, actor: str) -> LyRecycleBinItem:
        item = LyRecycleBinItem(
            module="style_master",
            entity_type="style_dictionary",
            entity_path="dictionaries",
            original_id=int(row.id),
            company=str(row.company),
            code=str(row.code),
            name=str(row.name),
            snapshot=self._snapshot_style_dictionary(row),
            details={"table": "ly_style_dictionary", "dict_type": str(row.dict_type)},
            deleted_by=actor,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def move_sample_tracking_node_to_trash(self, *, row: LySampleTrackingNode, actor: str, company: str) -> LyRecycleBinItem:
        item = LyRecycleBinItem(
            module="sample",
            entity_type="sample_tracking_node",
            entity_path="tracking-templates/nodes",
            original_id=int(row.id),
            company=company,
            code=str(row.id),
            name=str(row.name),
            snapshot=self._snapshot_sample_tracking_node(row, company=company),
            details={"table": "ly_sample_tracking_node", "template_id": int(row.template_id)},
            deleted_by=actor,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def move_production_followup_node_to_trash(self, *, row: LyProductionFollowupTemplateNode, actor: str) -> LyRecycleBinItem:
        item = LyRecycleBinItem(
            module="production",
            entity_type="production_followup_node",
            entity_path="followup-templates/nodes",
            original_id=int(row.id),
            company=str(row.company),
            code=str(row.id),
            name=str(row.node_name),
            snapshot=self._snapshot_production_followup_node(row),
            details={"table": "ly_production_followup_template_node", "template_id": int(row.template_id)},
            deleted_by=actor,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def restore(self, *, item_id: int, actor: str) -> RecycleBinItem:
        item = self._get_deleted_item(item_id)
        try:
            if item.module == "master_data":
                self._restore_master_data(item, actor=actor)
            elif item.module == "style_master" and item.entity_type == "style_dictionary":
                self._restore_style_dictionary(item, actor=actor)
            elif item.module == "sample" and item.entity_type == "sample_tracking_node":
                self._restore_sample_tracking_node(item, actor=actor)
            elif item.module == "production" and item.entity_type == "production_followup_node":
                self._restore_production_followup_node(item, actor=actor)
            else:
                raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="当前回收站记录暂不支持恢复")
            item.status = "restored"
            item.restored_by = actor
            item.restored_at = datetime.now(UTC)
            item.version = int(item.version or 0) + 1
            self.session.flush()
        except BusinessException:
            raise
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        return self._to_item(item)

    def purge(self, *, item_id: int) -> RecycleBinItem:
        item = self._get_deleted_item(item_id)
        payload = self._to_item(item)
        try:
            self.session.delete(item)
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        return payload

    def _restore_master_data(self, item: LyRecycleBinItem, *, actor: str) -> None:
        snapshot = dict(item.snapshot or {})
        original_id = int(snapshot.get("id") or item.original_id)
        entity_type = self._require_text(snapshot.get("entity_type") or item.entity_type, "entity_type")
        company = self._require_text(snapshot.get("company") or item.company, "company")
        code = self._require_text(snapshot.get("code") or item.code, "code")
        existing_id = self.session.query(LyMasterDataRecord).filter(LyMasterDataRecord.id == original_id).first()
        if existing_id is not None:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="原始 id 已被占用，无法恢复")
        existing_code = (
            self.session.query(LyMasterDataRecord)
            .filter(
                LyMasterDataRecord.entity_type == entity_type,
                LyMasterDataRecord.company == company,
                LyMasterDataRecord.code == code,
            )
            .first()
        )
        if existing_code is not None:
            raise BusinessException(code=MASTER_DATA_CONFLICT, message=f"{code} 已存在，无法恢复")
        self.session.add(
            LyMasterDataRecord(
                id=original_id,
                entity_type=entity_type,
                company=company,
                code=code,
                name=self._require_text(snapshot.get("name") or item.name, "name"),
                status=self._require_text(snapshot.get("status") or "active", "status"),
                payload=self._clean_json(snapshot.get("payload") or {}),
                version=int(snapshot.get("version") or 1),
                created_by=self._require_text(snapshot.get("created_by") or actor, "created_by"),
                created_at=self._parse_datetime(snapshot.get("created_at")) or datetime.now(UTC),
                updated_by=actor,
                updated_at=datetime.now(UTC),
                deactivated_by=self._optional_text(snapshot.get("deactivated_by")),
                deactivated_at=self._parse_datetime(snapshot.get("deactivated_at")),
                deactivate_reason=self._optional_text(snapshot.get("deactivate_reason")),
            )
        )

    def _restore_style_dictionary(self, item: LyRecycleBinItem, *, actor: str) -> None:
        snapshot = dict(item.snapshot or {})
        original_id = int(snapshot.get("id") or item.original_id)
        company = self._require_text(snapshot.get("company") or item.company, "company")
        dict_type = self._require_text(snapshot.get("dict_type") or (item.details or {}).get("dict_type"), "dict_type")
        code = self._require_text(snapshot.get("code") or item.code, "code")
        existing_id = self.session.query(LyStyleDictionary).filter(LyStyleDictionary.id == original_id).first()
        if existing_id is not None:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="原始 id 已被占用，无法恢复")
        existing_code = (
            self.session.query(LyStyleDictionary)
            .filter(
                LyStyleDictionary.dict_type == dict_type,
                LyStyleDictionary.company == company,
                LyStyleDictionary.code == code,
            )
            .first()
        )
        if existing_code is not None:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message=f"{dict_type}:{code} 已存在，无法恢复")
        self.session.add(
            LyStyleDictionary(
                id=original_id,
                company=company,
                dict_type=dict_type,
                code=code,
                name=self._require_text(snapshot.get("name") or item.name, "name"),
                status=self._require_text(snapshot.get("status") or "active", "status"),
                sort_no=int(snapshot.get("sort_no") or 10),
                version=int(snapshot.get("version") or 1),
                created_by=self._require_text(snapshot.get("created_by") or actor, "created_by"),
                created_at=self._parse_datetime(snapshot.get("created_at")) or datetime.now(UTC),
                updated_by=actor,
                updated_at=datetime.now(UTC),
                deactivated_by=self._optional_text(snapshot.get("deactivated_by")),
                deactivated_at=self._parse_datetime(snapshot.get("deactivated_at")),
                deactivate_reason=self._optional_text(snapshot.get("deactivate_reason")),
            )
        )

    def _restore_sample_tracking_node(self, item: LyRecycleBinItem, *, actor: str) -> None:
        snapshot = dict(item.snapshot or {})
        original_id = int(snapshot.get("id") or item.original_id)
        template_id = int(snapshot.get("template_id") or (item.details or {}).get("template_id") or 0)
        if not template_id:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="template_id 不能为空，无法恢复")
        existing_id = self.session.query(LySampleTrackingNode).filter(LySampleTrackingNode.id == original_id).first()
        if existing_id is not None:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="原始 id 已被占用，无法恢复")
        template = self.session.query(LySampleTrackingTemplate).filter(LySampleTrackingTemplate.id == template_id).first()
        if template is None:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="原模板不存在，无法恢复")
        self.session.add(
            LySampleTrackingNode(
                id=original_id,
                template_id=template_id,
                name=self._require_text(snapshot.get("name") or item.name, "name"),
                role=self._require_text(snapshot.get("role") or "", "role"),
                lead_time=str(snapshot.get("lead_time") or ""),
                status=self._require_text(snapshot.get("status") or "required", "status"),
                gate=str(snapshot.get("gate") or ""),
                output=str(snapshot.get("output") or ""),
                reminder=str(snapshot.get("reminder") or ""),
                sequence_no=int(snapshot.get("sequence_no") or 10),
                created_by=actor,
                updated_by=actor,
            )
        )
        template.updated_by = actor
        template.version = int(template.version or 0) + 1

    def _restore_production_followup_node(self, item: LyRecycleBinItem, *, actor: str) -> None:
        snapshot = dict(item.snapshot or {})
        original_id = int(snapshot.get("id") or item.original_id)
        template_id = int(snapshot.get("template_id") or (item.details or {}).get("template_id") or 0)
        company = self._require_text(snapshot.get("company") or item.company, "company")
        if not template_id:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="template_id 不能为空，无法恢复")
        existing_id = self.session.query(LyProductionFollowupTemplateNode).filter(LyProductionFollowupTemplateNode.id == original_id).first()
        if existing_id is not None:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="原始 id 已被占用，无法恢复")
        template = (
            self.session.query(LyProductionFollowupTemplate)
            .filter(LyProductionFollowupTemplate.id == template_id, LyProductionFollowupTemplate.company == company)
            .first()
        )
        if template is None:
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message="原模板不存在，无法恢复")
        self.session.add(
            LyProductionFollowupTemplateNode(
                id=original_id,
                template_id=template_id,
                company=company,
                node_name=self._require_text(snapshot.get("node_name") or item.name, "node_name"),
                owner=str(snapshot.get("owner") or ""),
                lead_time_hours=int(snapshot.get("lead_time_hours") or 0),
                status=self._require_text(snapshot.get("status") or "required", "status"),
                gate=str(snapshot.get("gate") or ""),
                output=str(snapshot.get("output") or ""),
                reminder=str(snapshot.get("reminder") or ""),
                sequence_no=int(snapshot.get("sequence_no") or 10),
                created_by=actor,
                updated_by=actor,
            )
        )
        template.updated_by = actor

    def _get_deleted_item(self, item_id: int) -> LyRecycleBinItem:
        row = self.session.query(LyRecycleBinItem).filter(LyRecycleBinItem.id == int(item_id), LyRecycleBinItem.status == "deleted").first()
        if row is None:
            raise BusinessException(code=RECYCLE_BIN_NOT_FOUND, message="回收站记录不存在或已处理")
        return row

    @staticmethod
    def _snapshot_master_data(row: LyMasterDataRecord) -> dict[str, Any]:
        return RecycleBinService._clean_json(
            {
                "id": int(row.id),
                "entity_type": row.entity_type,
                "company": row.company,
                "code": row.code,
                "name": row.name,
                "status": row.status,
                "payload": row.payload or {},
                "version": int(row.version or 1),
                "created_by": row.created_by,
                "created_at": row.created_at,
                "updated_by": row.updated_by,
                "updated_at": row.updated_at,
                "deactivated_by": row.deactivated_by,
                "deactivated_at": row.deactivated_at,
                "deactivate_reason": row.deactivate_reason,
            }
        )

    @staticmethod
    def _snapshot_style_dictionary(row: LyStyleDictionary) -> dict[str, Any]:
        return RecycleBinService._clean_json(
            {
                "id": int(row.id),
                "company": row.company,
                "dict_type": row.dict_type,
                "code": row.code,
                "name": row.name,
                "status": row.status,
                "sort_no": int(row.sort_no or 10),
                "version": int(row.version or 1),
                "created_by": row.created_by,
                "created_at": row.created_at,
                "updated_by": row.updated_by,
                "updated_at": row.updated_at,
                "deactivated_by": row.deactivated_by,
                "deactivated_at": row.deactivated_at,
                "deactivate_reason": row.deactivate_reason,
            }
        )

    @staticmethod
    def _snapshot_sample_tracking_node(row: LySampleTrackingNode, *, company: str) -> dict[str, Any]:
        return RecycleBinService._clean_json(
            {
                "id": int(row.id),
                "company": company,
                "template_id": int(row.template_id),
                "name": row.name,
                "role": row.role,
                "lead_time": row.lead_time,
                "status": row.status,
                "gate": row.gate,
                "output": row.output,
                "reminder": row.reminder,
                "sequence_no": int(row.sequence_no or 10),
            }
        )

    @staticmethod
    def _snapshot_production_followup_node(row: LyProductionFollowupTemplateNode) -> dict[str, Any]:
        return RecycleBinService._clean_json(
            {
                "id": int(row.id),
                "company": row.company,
                "template_id": int(row.template_id),
                "node_name": row.node_name,
                "owner": row.owner,
                "lead_time_hours": int(row.lead_time_hours or 0),
                "status": row.status,
                "gate": row.gate,
                "output": row.output,
                "reminder": row.reminder,
                "sequence_no": int(row.sequence_no or 10),
            }
        )

    @staticmethod
    def _clean_json(value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

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
            raise BusinessException(code=RECYCLE_BIN_CONFLICT, message=f"{field_name} 不能为空，无法恢复")
        return text

    @staticmethod
    def _to_item(row: LyRecycleBinItem) -> RecycleBinItem:
        return RecycleBinItem(
            id=int(row.id),
            module=str(row.module),
            entity_type=str(row.entity_type),
            entity_path=row.entity_path,
            original_id=int(row.original_id),
            company=row.company,
            code=row.code,
            name=row.name,
            status=str(row.status),  # type: ignore[arg-type]
            snapshot=dict(row.snapshot or {}),
            details=dict(row.details or {}),
            deleted_by=str(row.deleted_by),
            deleted_at=row.deleted_at,
            restored_by=row.restored_by,
            restored_at=row.restored_at,
        )
