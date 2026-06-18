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
    ) -> MasterDataListData:
        normalized_entity_type = self._normalize_entity_type(entity_type)
        try:
            query = self.session.query(LyMasterDataRecord).filter(
                LyMasterDataRecord.entity_type == normalized_entity_type,
            )
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
                    LyMasterDataRecord.status.asc(),
                    LyMasterDataRecord.updated_at.desc(),
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
        code = self._require_text(payload.code, "code")
        name = self._require_text(payload.name, "name")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(
            operation="create",
            entity_type=normalized_entity_type,
            company=company,
            code=code,
            name=name,
            payload=payload.payload,
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
                payload=self._clean_payload(payload.payload),
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
        try:
            row.code = next_code
            row.name = next_name
            row.payload = next_payload
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
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
