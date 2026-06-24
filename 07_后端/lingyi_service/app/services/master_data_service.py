"""Service layer for FastAPI-native master data writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
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
from app.core.error_codes import MASTER_DATA_CONFLICT
from app.core.error_codes import MASTER_DATA_IDEMPOTENCY_CONFLICT
from app.core.error_codes import MASTER_DATA_INVALID_TYPE
from app.core.error_codes import MASTER_DATA_NOT_FOUND
from app.core.exceptions import BusinessException
from app.models.master_data import LyMasterDataIdempotency
from app.models.master_data import LyMasterDataRecord
from app.schemas.master_data import MasterDataCreateRequest
from app.schemas.master_data import MasterDataDeactivateRequest
from app.schemas.master_data import MasterDataItem
from app.schemas.master_data import MasterDataListData
from app.schemas.master_data import MasterDataUpdateRequest

ENTITY_PATH_TO_TYPE = {
    "customers": "customer",
    "suppliers": "supplier",
    "factories": "factory",
    "warehouses": "warehouse",
    "materials": "material",
    "sample-types": "sample_type",
    "common-addresses": "common_address",
    "trade-terms": "trade_term",
    "invoice-types": "invoice_type",
    "cost-types": "cost_type",
    "size-sorts": "size_sort",
    "distribution-channels": "distribution_channel",
    "bank-accounts": "bank_account",
}
ENTITY_TYPES = set(ENTITY_PATH_TO_TYPE.values())
WAREHOUSE_LOCATION_KINDS = {"warehouse", "area"}
MATERIAL_SUPPLIER_BOUND_KINDS = {"fabric", "accessory"}
ENTITY_CODE_PREFIXES = {
    "customer": "CUST",
    "supplier": "SUP",
    "factory": "FAC",
    "warehouse": "WH",
    "material": "MAT",
    "sample_type": "ST",
    "common_address": "ADDR",
    "trade_term": "TERM",
    "invoice_type": "INV",
    "cost_type": "COST",
    "size_sort": "SIZE",
    "distribution_channel": "CHAN",
    "bank_account": "BANK",
}
MATERIAL_KIND_CODE_PREFIXES = {
    "fabric": "FAB",
    "accessory": "ACC",
    "gallery": "PIC",
    "processing": "PROC",
    "category": "MT",
    "unit": "MU",
}


@dataclass(frozen=True)
class MasterDataMutationResult:
    """Mutation result plus audit snapshots."""

    item: MasterDataItem
    before: dict[str, Any] | None
    after: dict[str, Any]
    idempotent: bool = False


class MasterDataService:
    """Read/write FastAPI-native master data records."""

    def __init__(self, session: Session):
        self.session = session

    @classmethod
    def entity_type_from_path(cls, entity_path: str) -> str:
        entity_type = ENTITY_PATH_TO_TYPE.get(str(entity_path or "").strip())
        if not entity_type:
            raise BusinessException(code=MASTER_DATA_INVALID_TYPE, message="主数据类型非法")
        return entity_type

    def list_records(
        self,
        *,
        entity_type: str,
        company: str | None,
        keyword: str | None,
        disabled: bool | None,
        page: int,
        page_size: int,
        allowed_companies: set[str] | None = None,
        allowed_customers: set[str] | None = None,
        allowed_items: set[str] | None = None,
    ) -> MasterDataListData:
        normalized_entity_type = self._normalize_entity_type(entity_type)
        try:
            query = self.session.query(LyMasterDataRecord).filter(
                LyMasterDataRecord.entity_type == normalized_entity_type,
            )
            if allowed_companies is not None:
                if not allowed_companies:
                    return MasterDataListData(items=[], total=0, page=page, page_size=page_size)
                query = query.filter(LyMasterDataRecord.company.in_(sorted(allowed_companies)))
            if normalized_entity_type == "customer" and allowed_customers is not None:
                if not allowed_customers:
                    return MasterDataListData(items=[], total=0, page=page, page_size=page_size)
                query = query.filter(LyMasterDataRecord.code.in_(sorted(allowed_customers)))
            if normalized_entity_type == "material" and allowed_items is not None:
                if not allowed_items:
                    return MasterDataListData(items=[], total=0, page=page, page_size=page_size)
                query = query.filter(LyMasterDataRecord.code.in_(sorted(allowed_items)))
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyMasterDataRecord.company == normalized_company)
            if disabled is not None:
                query = query.filter(LyMasterDataRecord.status == ("inactive" if disabled else "active"))
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyMasterDataRecord.code).like(like_value))
                    | (func.lower(LyMasterDataRecord.name).like(like_value))
                    | (func.lower(LyMasterDataRecord.company).like(like_value))
                )

            total = int(query.count())
            offset = max(page - 1, 0) * page_size
            rows = (
                query.order_by(
                    LyMasterDataRecord.created_at.desc(),
                    LyMasterDataRecord.id.desc(),
                )
                .offset(offset)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return MasterDataListData(
            items=[self._to_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_record(
        self,
        *,
        entity_type: str,
        payload: MasterDataCreateRequest,
        actor: str,
    ) -> MasterDataMutationResult:
        normalized_entity_type = self._normalize_entity_type(entity_type)
        company = self._require_text(payload.company, "company")
        requested_code = self._optional_text(payload.code)
        name = self._require_text(payload.name, "name")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        next_payload = self._clean_payload(payload.payload)
        if normalized_entity_type in {"customer", "supplier"}:
            next_payload = self._normalize_contact_payload(payload=next_payload)
        request_hash = self._request_hash(
            operation="create",
            entity_type=normalized_entity_type,
            company=company,
            requested_code=requested_code,
            name=name,
            payload=next_payload,
        )
        existing_idem = self._get_idempotency(
            entity_type=normalized_entity_type,
            company=company,
            idempotency_key=idempotency_key,
        )
        if existing_idem is not None:
            self._ensure_same_idempotency(existing_idem, operation="create", request_hash=request_hash)
            row = self._get_record_by_id(existing_idem.record_id)
            after = self._snapshot(row)
            return MasterDataMutationResult(item=self._to_item(row), before=after, after=after, idempotent=True)

        code = requested_code or self._next_code(entity_type=normalized_entity_type, company=company, payload=next_payload)
        next_payload = self._sync_code_payload(entity_type=normalized_entity_type, code=code, payload=next_payload)
        if normalized_entity_type == "warehouse":
            next_payload = self._normalize_warehouse_payload(
                company=company,
                code=code,
                payload=next_payload,
                current_record_id=None,
            )
        if normalized_entity_type == "material":
            next_payload = self._normalize_material_payload(
                company=company,
                payload=next_payload,
            )

        active_conflict = self._get_record_by_code(
            entity_type=normalized_entity_type,
            company=company,
            code=code,
        )
        if active_conflict is not None and active_conflict.status == "active":
            raise BusinessException(code=MASTER_DATA_CONFLICT, message=f"{code} 已存在启用中的主数据")

        try:
            row = LyMasterDataRecord(
                entity_type=normalized_entity_type,
                company=company,
                code=code,
                name=name,
                status="active",
                payload=next_payload,
                version=1,
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type=normalized_entity_type,
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
        after = self._snapshot(row)
        return MasterDataMutationResult(item=self._to_item(row), before=None, after=after)

    def update_record(
        self,
        *,
        entity_type: str,
        record_id: int,
        payload: MasterDataUpdateRequest,
        actor: str,
    ) -> MasterDataMutationResult:
        normalized_entity_type = self._normalize_entity_type(entity_type)
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_record_for_mutation(entity_type=normalized_entity_type, record_id=record_id, company=company)
        next_code = self._optional_text(payload.code) or row.code
        next_name = self._optional_text(payload.name) or row.name
        next_payload = self._clean_payload(payload.payload) if payload.payload is not None else dict(row.payload or {})
        if normalized_entity_type in {"customer", "supplier"}:
            next_payload = self._normalize_contact_payload(payload=next_payload)
        if normalized_entity_type == "warehouse":
            next_payload = self._normalize_warehouse_payload(
                company=company,
                code=next_code,
                payload=next_payload,
                current_record_id=int(row.id),
            )
        if normalized_entity_type == "material":
            next_payload = self._normalize_material_payload(
                company=company,
                payload=next_payload,
            )
        request_hash = self._request_hash(
            operation="update",
            entity_type=normalized_entity_type,
            company=company,
            record_id=record_id,
            code=next_code,
            name=next_name,
            payload=next_payload,
        )
        existing_idem = self._get_idempotency(
            entity_type=normalized_entity_type,
            company=company,
            idempotency_key=idempotency_key,
        )
        if existing_idem is not None:
            self._ensure_same_idempotency(existing_idem, operation="update", request_hash=request_hash)
            idempotent_row = self._get_record_by_id(existing_idem.record_id)
            after = self._snapshot(idempotent_row)
            return MasterDataMutationResult(
                item=self._to_item(idempotent_row),
                before=after,
                after=after,
                idempotent=True,
            )

        if next_code != row.code:
            conflict = self._get_record_by_code(
                entity_type=normalized_entity_type,
                company=company,
                code=next_code,
            )
            if conflict is not None and int(conflict.id) != int(row.id):
                raise BusinessException(code=MASTER_DATA_CONFLICT, message=f"{next_code} 已存在")

        before = self._snapshot(row)
        old_code = str(row.code)
        try:
            row.code = next_code
            row.name = next_name
            row.payload = next_payload
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            if normalized_entity_type == "warehouse" and next_code != old_code:
                self._rename_warehouse_parent_references(
                    company=company,
                    old_code=old_code,
                    new_code=next_code,
                    actor=actor,
                )
            self._insert_idempotency(
                entity_type=normalized_entity_type,
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
        after = self._snapshot(row)
        return MasterDataMutationResult(item=self._to_item(row), before=before, after=after)

    def deactivate_record(
        self,
        *,
        entity_type: str,
        record_id: int,
        payload: MasterDataDeactivateRequest,
        actor: str,
    ) -> MasterDataMutationResult:
        normalized_entity_type = self._normalize_entity_type(entity_type)
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        reason = self._require_text(payload.reason, "reason")
        row = self._get_record_for_mutation(entity_type=normalized_entity_type, record_id=record_id, company=company)
        if normalized_entity_type == "warehouse" and self._has_active_warehouse_children(company=company, parent_code=str(row.code)):
            raise BusinessException(code=MASTER_DATA_CONFLICT, message="存在启用中的仓库子级，不能停用父级")
        request_hash = self._request_hash(
            operation="deactivate",
            entity_type=normalized_entity_type,
            company=company,
            record_id=record_id,
            reason=reason,
        )
        existing_idem = self._get_idempotency(
            entity_type=normalized_entity_type,
            company=company,
            idempotency_key=idempotency_key,
        )
        if existing_idem is not None:
            self._ensure_same_idempotency(existing_idem, operation="deactivate", request_hash=request_hash)
            idempotent_row = self._get_record_by_id(existing_idem.record_id)
            after = self._snapshot(idempotent_row)
            return MasterDataMutationResult(
                item=self._to_item(idempotent_row),
                before=after,
                after=after,
                idempotent=True,
            )

        before = self._snapshot(row)
        try:
            if row.status != "inactive":
                row.status = "inactive"
                row.deactivated_by = actor
                row.deactivated_at = datetime.now(UTC)
                row.deactivate_reason = reason
                row.updated_by = actor
                row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type=normalized_entity_type,
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
        after = self._snapshot(row)
        return MasterDataMutationResult(item=self._to_item(row), before=before, after=after)

    def get_record_for_permission(self, *, entity_type: str, record_id: int, company: str | None = None) -> MasterDataItem:
        normalized_entity_type = self._normalize_entity_type(entity_type)
        query = self.session.query(LyMasterDataRecord).filter(
            LyMasterDataRecord.id == record_id,
            LyMasterDataRecord.entity_type == normalized_entity_type,
        )
        normalized_company = self._optional_text(company)
        if normalized_company:
            query = query.filter(LyMasterDataRecord.company == normalized_company)
        row = query.first()
        if row is None:
            raise BusinessException(code=MASTER_DATA_NOT_FOUND, message="主数据不存在或 company 不匹配")
        return self._to_item(row)

    @classmethod
    def _normalize_entity_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ENTITY_TYPES:
            raise BusinessException(code=MASTER_DATA_INVALID_TYPE, message="主数据类型非法")
        return normalized

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
            raise BusinessException(code=MASTER_DATA_CONFLICT, message=f"{field_name} 不能为空")
        return text

    @staticmethod
    def _clean_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
        if not payload:
            return {}
        return json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))

    @classmethod
    def _split_material_colors(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return list(dict.fromkeys(text for item in value if (text := cls._optional_text(item)) is not None))
        text = cls._optional_text(value)
        if text is None:
            return []
        separators = "、,，/／;；\n\r"
        parts: list[str] = []
        current = []
        for char in text:
            if char in separators:
                part = cls._optional_text("".join(current))
                if part is not None:
                    parts.append(part)
                current = []
                continue
            current.append(char)
        part = cls._optional_text("".join(current))
        if part is not None:
            parts.append(part)
        return list(dict.fromkeys(parts))

    def _next_code(self, *, entity_type: str, company: str, payload: dict[str, Any]) -> str:
        prefix = self._code_prefix(entity_type=entity_type, payload=payload)
        existing_codes = {
            str(row[0])
            for row in self.session.query(LyMasterDataRecord.code)
            .filter(
                LyMasterDataRecord.entity_type == entity_type,
                LyMasterDataRecord.company == company,
                LyMasterDataRecord.code.like(f"{prefix}-%"),
            )
            .all()
        }
        next_number = len(existing_codes) + 1
        while next_number < 1_000_000:
            candidate = f"{prefix}-{next_number:06d}"
            if candidate not in existing_codes:
                return candidate
            next_number += 1
        raise BusinessException(code=MASTER_DATA_CONFLICT, message=f"{prefix} 自动编码已用尽")

    def _code_prefix(self, *, entity_type: str, payload: dict[str, Any]) -> str:
        if entity_type == "material":
            material_kind = (
                self._optional_text(payload.get("material_kind"))
                or self._optional_text(payload.get("materialKind"))
                or ""
            )
            return MATERIAL_KIND_CODE_PREFIXES.get(material_kind, ENTITY_CODE_PREFIXES["material"])
        return ENTITY_CODE_PREFIXES.get(entity_type, "MD")

    def _sync_code_payload(self, *, entity_type: str, code: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if entity_type != "material":
            return self._clean_payload(normalized)

        self._fill_payload_text(normalized, "material_item_code", code)
        material_kind = (
            self._optional_text(normalized.get("material_kind"))
            or self._optional_text(normalized.get("materialKind"))
            or ""
        )
        if material_kind == "processing":
            self._fill_payload_text(normalized, "process_type_code", code)
        elif material_kind == "category":
            self._fill_payload_text(normalized, "material_type_code", code)
        elif material_kind == "unit":
            self._fill_payload_text(normalized, "unit_code", code)
        return self._clean_payload(normalized)

    def _fill_payload_text(self, payload: dict[str, Any], key: str, value: str) -> None:
        if self._optional_text(payload.get(key)) is None:
            payload[key] = value

    @classmethod
    def _normalize_contact_payload(cls, *, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        contact_person = (
            cls._optional_text(normalized.get("contactPerson"))
            or cls._optional_text(normalized.get("contact_person"))
            or cls._optional_text(normalized.get("contact"))
        )
        phone = (
            cls._optional_text(normalized.get("phone"))
            or cls._optional_text(normalized.get("contact_phone"))
            or cls._optional_text(normalized.get("contactPhone"))
            or cls._optional_text(normalized.get("telephone"))
            or cls._optional_text(normalized.get("tel"))
        )
        wechat = (
            cls._optional_text(normalized.get("wechat"))
            or cls._optional_text(normalized.get("weixin"))
            or cls._optional_text(normalized.get("weChat"))
        )

        for key in ("contactPerson", "contact_person", "contact"):
            if contact_person:
                normalized[key] = contact_person
            else:
                normalized.pop(key, None)
        if phone:
            normalized["phone"] = phone
        else:
            normalized.pop("phone", None)
        if wechat:
            normalized["wechat"] = wechat
        else:
            normalized.pop("wechat", None)

        for alias in ("contact_phone", "contactPhone", "telephone", "tel", "weixin", "weChat"):
            normalized.pop(alias, None)
        return cls._clean_payload(normalized)

    def _normalize_warehouse_payload(
        self,
        *,
        company: str,
        code: str,
        payload: dict[str, Any],
        current_record_id: int | None,
    ) -> dict[str, Any]:
        normalized = dict(payload)
        parent_code = self._optional_text(normalized.get("parent_code")) or self._optional_text(normalized.get("parentCode"))
        location_kind = (
            self._optional_text(normalized.get("location_kind"))
            or self._optional_text(normalized.get("locationKind"))
            or ("area" if parent_code else "warehouse")
        )
        if location_kind not in WAREHOUSE_LOCATION_KINDS:
            raise BusinessException(code=MASTER_DATA_CONFLICT, message="仓库节点类型必须是 warehouse 或 area")
        if parent_code:
            if parent_code == code:
                raise BusinessException(code=MASTER_DATA_CONFLICT, message="仓库父级不能指向自身")
            parent = self._get_record_by_code(entity_type="warehouse", company=company, code=parent_code)
            if parent is None or parent.status != "active":
                raise BusinessException(code=MASTER_DATA_CONFLICT, message="父级仓库不存在或已停用")
            if current_record_id is not None:
                self._ensure_no_warehouse_parent_cycle(
                    company=company,
                    current_record_id=current_record_id,
                    parent=parent,
                )
            normalized["parent_code"] = parent_code
        else:
            normalized.pop("parent_code", None)
        normalized.pop("parentCode", None)
        normalized.pop("locationKind", None)
        normalized["location_kind"] = location_kind
        manager = self._optional_text(normalized.get("manager"))
        if manager:
            normalized["manager"] = manager
        else:
            normalized.pop("manager", None)
        return self._clean_payload(normalized)

    def _normalize_material_payload(
        self,
        *,
        company: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(payload)
        colors = self._split_material_colors(normalized.get("colors") or normalized.get("color_specs") or normalized.get("colorSpecs"))
        if not colors:
            colors = self._split_material_colors(normalized.get("color"))
        if colors:
            normalized["colors"] = colors
            normalized["color"] = "、".join(colors)
            normalized.pop("color_specs", None)
            normalized.pop("colorSpecs", None)
        material_kind = (
            self._optional_text(normalized.get("material_kind"))
            or self._optional_text(normalized.get("materialKind"))
            or ""
        )
        if material_kind not in MATERIAL_SUPPLIER_BOUND_KINDS:
            return self._clean_payload(normalized)

        supplier_name = self._optional_text(normalized.get("supplier_name")) or self._optional_text(normalized.get("supplierName"))
        supplier_code = self._optional_text(normalized.get("supplier_code")) or self._optional_text(normalized.get("supplierCode"))
        supplier = self._get_active_supplier_by_code_or_name(company=company, value=supplier_code) if supplier_code else None
        if supplier is None and supplier_name:
            supplier = self._get_active_supplier_by_code_or_name(company=company, value=supplier_name)
        if supplier is None:
            supplier_value = supplier_code or supplier_name or "空"
            raise BusinessException(code=MASTER_DATA_CONFLICT, message=f"供应商主数据未启用或不存在：{supplier_value}")

        normalized["supplier_name"] = str(supplier.name)
        normalized["supplier_code"] = str(supplier.code)
        normalized.pop("supplierName", None)
        normalized.pop("supplierCode", None)

        unit_code = self._optional_text(normalized.get("unit_code")) or self._optional_text(normalized.get("unitCode"))
        unit_name = (
            self._optional_text(normalized.get("uom"))
            or self._optional_text(normalized.get("base_unit"))
            or self._optional_text(normalized.get("baseUnit"))
            or self._optional_text(normalized.get("unit_name"))
            or self._optional_text(normalized.get("unitName"))
        )
        unit = self._get_active_material_unit_by_code_or_name(company=company, value=unit_code) if unit_code else None
        if unit is None and unit_name:
            unit = self._get_active_material_unit_by_code_or_name(company=company, value=unit_name)
        if unit is None:
            unit_value = unit_code or unit_name or "空"
            raise BusinessException(code=MASTER_DATA_CONFLICT, message=f"物料单位主数据未启用或不存在：{unit_value}")
        normalized["uom"] = str(unit.name)
        normalized["unit_code"] = str(unit.code)
        normalized.pop("unitCode", None)
        normalized.pop("baseUnit", None)
        normalized.pop("unitName", None)
        return self._clean_payload(normalized)

    def _ensure_no_warehouse_parent_cycle(
        self,
        *,
        company: str,
        current_record_id: int,
        parent: LyMasterDataRecord,
    ) -> None:
        seen_codes: set[str] = set()
        current_parent: LyMasterDataRecord | None = parent
        while current_parent is not None:
            if int(current_parent.id) == int(current_record_id):
                raise BusinessException(code=MASTER_DATA_CONFLICT, message="仓库父级不能形成循环")
            parent_code = self._optional_text(dict(current_parent.payload or {}).get("parent_code")) or self._optional_text(
                dict(current_parent.payload or {}).get("parentCode")
            )
            if not parent_code or parent_code in seen_codes:
                return
            seen_codes.add(parent_code)
            current_parent = self._get_record_by_code(entity_type="warehouse", company=company, code=parent_code)

    def _rename_warehouse_parent_references(
        self,
        *,
        company: str,
        old_code: str,
        new_code: str,
        actor: str,
    ) -> None:
        child_rows = (
            self.session.query(LyMasterDataRecord)
            .filter(
                LyMasterDataRecord.entity_type == "warehouse",
                LyMasterDataRecord.company == company,
            )
            .all()
        )
        for child in child_rows:
            child_payload = dict(child.payload or {})
            parent_code = self._optional_text(child_payload.get("parent_code")) or self._optional_text(child_payload.get("parentCode"))
            if parent_code != old_code:
                continue
            child_payload["parent_code"] = new_code
            child_payload.pop("parentCode", None)
            child.payload = self._clean_payload(child_payload)
            child.updated_by = actor
            child.updated_at = datetime.now(UTC)
            child.version = int(child.version or 0) + 1

    def _has_active_warehouse_children(self, *, company: str, parent_code: str) -> bool:
        rows = (
            self.session.query(LyMasterDataRecord)
            .filter(
                LyMasterDataRecord.entity_type == "warehouse",
                LyMasterDataRecord.company == company,
                LyMasterDataRecord.status == "active",
            )
            .all()
        )
        return any(
            (
                self._optional_text(dict(row.payload or {}).get("parent_code"))
                or self._optional_text(dict(row.payload or {}).get("parentCode"))
            )
            == parent_code
            for row in rows
        )

    @classmethod
    def _request_hash(cls, **payload: Any) -> str:
        normalized = cls._clean_payload(payload)
        raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_record_by_id(self, record_id: int) -> LyMasterDataRecord:
        row = self.session.query(LyMasterDataRecord).filter(LyMasterDataRecord.id == record_id).first()
        if row is None:
            raise BusinessException(code=MASTER_DATA_NOT_FOUND, message="主数据不存在")
        return row

    def _get_record_for_mutation(self, *, entity_type: str, record_id: int, company: str) -> LyMasterDataRecord:
        row = (
            self.session.query(LyMasterDataRecord)
            .filter(
                LyMasterDataRecord.id == record_id,
                LyMasterDataRecord.entity_type == entity_type,
                LyMasterDataRecord.company == company,
            )
            .first()
        )
        if row is None:
            raise BusinessException(code=MASTER_DATA_NOT_FOUND, message="主数据不存在或 company 不匹配")
        return row

    def _get_record_by_code(self, *, entity_type: str, company: str, code: str) -> LyMasterDataRecord | None:
        return (
            self.session.query(LyMasterDataRecord)
            .filter(
                LyMasterDataRecord.entity_type == entity_type,
                LyMasterDataRecord.company == company,
                LyMasterDataRecord.code == code,
            )
            .first()
        )

    def _get_active_supplier_by_code_or_name(self, *, company: str, value: str | None) -> LyMasterDataRecord | None:
        normalized = self._optional_text(value)
        if normalized is None:
            return None
        return (
            self.session.query(LyMasterDataRecord)
            .filter(
                LyMasterDataRecord.entity_type == "supplier",
                LyMasterDataRecord.company == company,
                LyMasterDataRecord.status == "active",
                (LyMasterDataRecord.code == normalized) | (LyMasterDataRecord.name == normalized),
            )
            .first()
        )

    def _get_active_material_unit_by_code_or_name(self, *, company: str, value: str | None) -> LyMasterDataRecord | None:
        normalized = self._optional_text(value)
        if normalized is None:
            return None
        candidates = (
            self.session.query(LyMasterDataRecord)
            .filter(
                LyMasterDataRecord.entity_type == "material",
                LyMasterDataRecord.company == company,
                LyMasterDataRecord.status == "active",
                (LyMasterDataRecord.code == normalized) | (LyMasterDataRecord.name == normalized),
            )
            .all()
        )
        for row in candidates:
            payload = dict(row.payload or {})
            material_kind = (
                self._optional_text(payload.get("material_kind"))
                or self._optional_text(payload.get("materialKind"))
                or ""
            )
            if material_kind == "unit":
                return row
        return None

    def _get_idempotency(
        self,
        *,
        entity_type: str,
        company: str,
        idempotency_key: str,
    ) -> LyMasterDataIdempotency | None:
        return (
            self.session.query(LyMasterDataIdempotency)
            .filter(
                LyMasterDataIdempotency.entity_type == entity_type,
                LyMasterDataIdempotency.company == company,
                LyMasterDataIdempotency.idempotency_key == idempotency_key,
            )
            .first()
        )

    @staticmethod
    def _ensure_same_idempotency(row: LyMasterDataIdempotency, *, operation: str, request_hash: str) -> None:
        if row.operation != operation or row.request_hash != request_hash:
            raise BusinessException(code=MASTER_DATA_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

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
            LyMasterDataIdempotency(
                entity_type=entity_type,
                company=company,
                idempotency_key=idempotency_key,
                operation=operation,
                request_hash=request_hash,
                record_id=record_id,
                created_by=actor,
            )
        )

    @classmethod
    def _snapshot(cls, row: LyMasterDataRecord) -> dict[str, Any]:
        return {
            "id": int(row.id),
            "entity_type": row.entity_type,
            "company": row.company,
            "code": row.code,
            "name": row.name,
            "status": row.status,
            "payload": cls._clean_payload(dict(row.payload or {})),
            "version": int(row.version or 0),
            "created_by": row.created_by,
            "updated_by": row.updated_by,
            "deactivated_by": row.deactivated_by,
            "deactivate_reason": row.deactivate_reason,
        }

    @classmethod
    def _to_item(cls, row: LyMasterDataRecord) -> MasterDataItem:
        return MasterDataItem(
            id=int(row.id),
            entity_type=row.entity_type,
            code=row.code,
            name=row.name,
            company=row.company,
            status=row.status,
            disabled=row.status != "active",
            payload=cls._clean_payload(dict(row.payload or {})),
            version=int(row.version or 0),
            created_by=row.created_by,
            created_at=row.created_at,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
            deactivated_by=row.deactivated_by,
            deactivated_at=row.deactivated_at,
            deactivate_reason=row.deactivate_reason,
        )
