"""Service layer for FastAPI-native style master data."""

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
from app.core.error_codes import STYLE_MASTER_CONFLICT
from app.core.error_codes import STYLE_MASTER_IDEMPOTENCY_CONFLICT
from app.core.error_codes import STYLE_MASTER_INVALID_REFERENCE
from app.core.error_codes import STYLE_MASTER_INVALID_STATUS
from app.core.error_codes import STYLE_MASTER_NOT_FOUND
from app.core.exceptions import BusinessException
from app.models.style_master import LyStyleDictionary
from app.models.style_master import LyStyleMaster
from app.models.style_master import LyStyleMasterIdempotency
from app.schemas.style_master import StyleDictionaryCreateRequest
from app.schemas.style_master import StyleDictionaryItem
from app.schemas.style_master import StyleDictionaryListData
from app.schemas.style_master import StyleDictionaryUpdateRequest
from app.schemas.style_master import StyleMasterCreateRequest
from app.schemas.style_master import StyleMasterItem
from app.schemas.style_master import StyleMasterListData
from app.schemas.style_master import StyleMasterUpdateRequest

STYLE_STATUSES = {"draft", "enabled", "disabled"}
DICTIONARY_TYPES = {"season", "year", "brand", "color", "size"}
DICTIONARY_STATUSES = {"active", "inactive"}


@dataclass(frozen=True)
class StyleMasterMutationResult:
    """Mutation output plus audit snapshots."""

    item: StyleMasterItem | StyleDictionaryItem
    before: dict[str, Any] | None
    after: dict[str, Any]
    resource_type: str
    resource_id: int
    resource_no: str
    idempotent: bool = False


class StyleMasterService:
    """Read and mutate style masters and their minimal dictionaries."""

    def __init__(self, session: Session):
        self.session = session

    def list_styles(
        self,
        *,
        company: str | None,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> StyleMasterListData:
        try:
            query = self.session.query(LyStyleMaster)
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyStyleMaster.company == normalized_company)
            normalized_status = self._optional_text(status)
            if normalized_status and normalized_status != "all":
                query = query.filter(LyStyleMaster.ys_style_status == self._normalize_style_status(normalized_status))
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyStyleMaster.ys_style_no).like(like_value))
                    | (func.lower(LyStyleMaster.ys_style_name_cn).like(like_value))
                    | (func.lower(LyStyleMaster.ys_brand).like(like_value))
                    | (func.lower(LyStyleMaster.ys_year).like(like_value))
                    | (func.lower(LyStyleMaster.ys_season).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(
                    LyStyleMaster.ys_style_status.asc(),
                    LyStyleMaster.updated_at.desc(),
                    LyStyleMaster.id.desc(),
                )
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return StyleMasterListData(items=[self._style_item(row) for row in rows], total=total, page=page, page_size=page_size)

    def create_style(self, *, payload: StyleMasterCreateRequest, actor: str) -> StyleMasterMutationResult:
        company = self._require_text(payload.company, "company")
        style_no = self._require_text(payload.ys_style_no, "ys_style_no")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        style_values = self._style_values_from_create(payload)
        self._ensure_dictionary_refs(company=company, ys_season=payload.ys_season, ys_year=payload.ys_year, ys_brand=payload.ys_brand)
        self._normalize_style_pair_refs(company=company, values=style_values)
        request_hash = self._request_hash(operation="create", entity_type="style", company=company, values=style_values)
        idem = self._get_idempotency(entity_type="style", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create", request_hash=request_hash)
            row = self._get_style_by_id(idem.record_id)
            after = self._snapshot_style(row)
            return self._style_result(row=row, before=after, after=after, idempotent=True)

        if self._get_style_by_no(company=company, style_no=style_no):
            raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"{style_no} 已存在")

        try:
            row = LyStyleMaster(
                company=company,
                ys_style_no=style_no,
                ys_style_name_cn=style_values["ys_style_name_cn"],
                ys_season=style_values["ys_season"],
                ys_year=style_values["ys_year"],
                ys_brand=style_values["ys_brand"],
                ys_style_status=style_values["ys_style_status"],
                colors=style_values["colors"],
                sizes=style_values["sizes"],
                version=1,
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="style",
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
        after = self._snapshot_style(row)
        return self._style_result(row=row, before=None, after=after)

    def update_style(self, *, style_id: int, payload: StyleMasterUpdateRequest, actor: str) -> StyleMasterMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_style_for_mutation(style_id=style_id, company=company)
        values = self._style_values_from_update(row=row, payload=payload)
        self._ensure_dictionary_refs(company=company, ys_season=values["ys_season"], ys_year=values["ys_year"], ys_brand=values["ys_brand"])
        self._normalize_style_pair_refs(company=company, values=values)
        request_hash = self._request_hash(operation="update", entity_type="style", company=company, style_id=style_id, values=values)
        idem = self._get_idempotency(entity_type="style", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="update", request_hash=request_hash)
            idem_row = self._get_style_by_id(idem.record_id)
            after = self._snapshot_style(idem_row)
            return self._style_result(row=idem_row, before=after, after=after, idempotent=True)

        if values["ys_style_no"] != row.ys_style_no:
            conflict = self._get_style_by_no(company=company, style_no=values["ys_style_no"])
            if conflict and int(conflict.id) != int(row.id):
                raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"{values['ys_style_no']} 已存在")

        before = self._snapshot_style(row)
        try:
            for key, value in values.items():
                setattr(row, key, value)
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="style",
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
        after = self._snapshot_style(row)
        return self._style_result(row=row, before=before, after=after)

    def deactivate_style(
        self,
        *,
        style_id: int,
        company: str,
        idempotency_key: str,
        reason: str,
        actor: str,
    ) -> StyleMasterMutationResult:
        company = self._require_text(company, "company")
        idempotency_key = self._require_text(idempotency_key, "idempotency_key")
        reason = self._require_text(reason, "reason")
        row = self._get_style_for_mutation(style_id=style_id, company=company, allow_disabled=True)
        request_hash = self._request_hash(operation="deactivate", entity_type="style", company=company, style_id=style_id, reason=reason)
        idem = self._get_idempotency(entity_type="style", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="deactivate", request_hash=request_hash)
            idem_row = self._get_style_by_id(idem.record_id)
            after = self._snapshot_style(idem_row)
            return self._style_result(row=idem_row, before=after, after=after, idempotent=True)

        before = self._snapshot_style(row)
        try:
            row.ys_style_status = "disabled"
            row.disabled_by = actor
            row.disabled_at = datetime.now(UTC)
            row.disable_reason = reason
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="style",
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
        after = self._snapshot_style(row)
        return self._style_result(row=row, before=before, after=after)

    def list_dictionaries(
        self,
        *,
        company: str | None,
        dict_type: str | None,
        keyword: str | None,
        disabled: bool | None,
        page: int,
        page_size: int,
    ) -> StyleDictionaryListData:
        try:
            query = self.session.query(LyStyleDictionary)
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyStyleDictionary.company == normalized_company)
            normalized_type = self._optional_text(dict_type)
            if normalized_type:
                query = query.filter(LyStyleDictionary.dict_type == self._normalize_dictionary_type(normalized_type))
            if disabled is not None:
                query = query.filter(LyStyleDictionary.status == ("inactive" if disabled else "active"))
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyStyleDictionary.code).like(like_value))
                    | (func.lower(LyStyleDictionary.name).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(
                    LyStyleDictionary.dict_type.asc(),
                    LyStyleDictionary.status.asc(),
                    LyStyleDictionary.sort_no.asc(),
                    LyStyleDictionary.id.asc(),
                )
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return StyleDictionaryListData(items=[self._dictionary_item(row) for row in rows], total=total, page=page, page_size=page_size)

    def create_dictionary(self, *, payload: StyleDictionaryCreateRequest, actor: str) -> StyleMasterMutationResult:
        company = self._require_text(payload.company, "company")
        dict_type = self._normalize_dictionary_type(payload.dict_type)
        code = self._require_text(payload.code, "code")
        values = {
            "dict_type": dict_type,
            "code": code,
            "name": self._require_text(payload.name, "name"),
            "sort_no": int(payload.sort_no),
        }
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(operation="create", entity_type="dictionary", company=company, values=values)
        idem = self._get_idempotency(entity_type="dictionary", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create", request_hash=request_hash)
            row = self._get_dictionary_by_id(idem.record_id)
            after = self._snapshot_dictionary(row)
            return self._dictionary_result(row=row, before=after, after=after, idempotent=True)

        if self._get_dictionary_by_code(company=company, dict_type=dict_type, code=code):
            raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"{dict_type}:{code} 已存在")
        try:
            row = LyStyleDictionary(
                company=company,
                dict_type=dict_type,
                code=code,
                name=values["name"],
                status="active",
                sort_no=values["sort_no"],
                version=1,
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="dictionary",
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
        after = self._snapshot_dictionary(row)
        return self._dictionary_result(row=row, before=None, after=after)

    def update_dictionary(self, *, dictionary_id: int, payload: StyleDictionaryUpdateRequest, actor: str) -> StyleMasterMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_dictionary_for_mutation(dictionary_id=dictionary_id, company=company)
        values = {
            "code": self._optional_text(payload.code) or row.code,
            "name": self._optional_text(payload.name) or row.name,
            "sort_no": int(payload.sort_no if payload.sort_no is not None else row.sort_no),
            "status": self._normalize_dictionary_status(payload.status or row.status),
        }
        request_hash = self._request_hash(operation="update", entity_type="dictionary", company=company, dictionary_id=dictionary_id, values=values)
        idem = self._get_idempotency(entity_type="dictionary", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="update", request_hash=request_hash)
            idem_row = self._get_dictionary_by_id(idem.record_id)
            after = self._snapshot_dictionary(idem_row)
            return self._dictionary_result(row=idem_row, before=after, after=after, idempotent=True)

        if values["code"] != row.code:
            conflict = self._get_dictionary_by_code(company=company, dict_type=row.dict_type, code=values["code"])
            if conflict and int(conflict.id) != int(row.id):
                raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"{row.dict_type}:{values['code']} 已存在")
        before = self._snapshot_dictionary(row)
        try:
            row.code = values["code"]
            row.name = values["name"]
            row.sort_no = values["sort_no"]
            row.status = values["status"]
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="dictionary",
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
        after = self._snapshot_dictionary(row)
        return self._dictionary_result(row=row, before=before, after=after)

    def deactivate_dictionary(
        self,
        *,
        dictionary_id: int,
        company: str,
        idempotency_key: str,
        reason: str,
        actor: str,
    ) -> StyleMasterMutationResult:
        company = self._require_text(company, "company")
        idempotency_key = self._require_text(idempotency_key, "idempotency_key")
        reason = self._require_text(reason, "reason")
        row = self._get_dictionary_for_mutation(dictionary_id=dictionary_id, company=company, allow_inactive=True)
        request_hash = self._request_hash(operation="deactivate", entity_type="dictionary", company=company, dictionary_id=dictionary_id, reason=reason)
        idem = self._get_idempotency(entity_type="dictionary", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="deactivate", request_hash=request_hash)
            idem_row = self._get_dictionary_by_id(idem.record_id)
            after = self._snapshot_dictionary(idem_row)
            return self._dictionary_result(row=idem_row, before=after, after=after, idempotent=True)
        before = self._snapshot_dictionary(row)
        try:
            row.status = "inactive"
            row.deactivated_by = actor
            row.deactivated_at = datetime.now(UTC)
            row.deactivate_reason = reason
            row.updated_by = actor
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="dictionary",
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
        after = self._snapshot_dictionary(row)
        return self._dictionary_result(row=row, before=before, after=after)

    def _ensure_dictionary_refs(self, *, company: str, ys_season: str, ys_year: str, ys_brand: str) -> None:
        refs = {
            "season": self._require_text(ys_season, "ys_season"),
            "year": self._require_text(ys_year, "ys_year"),
            "brand": self._require_text(ys_brand, "ys_brand"),
        }
        for dict_type, code in refs.items():
            row = self._get_dictionary_by_code(company=company, dict_type=dict_type, code=code)
            if row is None or row.status != "active":
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"{dict_type}:{code} 字典不存在或已停用")

    def _normalize_style_pair_refs(self, *, company: str, values: dict[str, Any]) -> None:
        values["colors"] = self._normalize_pair_dictionary_refs(
            company=company,
            dict_type="color",
            items=values["colors"],
            code_key="ys_color_code",
            name_key="ys_color_name",
        )
        values["sizes"] = self._normalize_pair_dictionary_refs(
            company=company,
            dict_type="size",
            items=values["sizes"],
            code_key="ys_size_code",
            name_key="ys_size_name",
        )

    def _normalize_pair_dictionary_refs(
        self,
        *,
        company: str,
        dict_type: str,
        items: list[dict[str, Any]],
        code_key: str,
        name_key: str,
    ) -> list[dict[str, str]]:
        if not items:
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"{dict_type} 字典引用不能为空")
        normalized_items: list[dict[str, str]] = []
        seen_codes: set[str] = set()
        for item in items:
            code = self._require_text(item.get(code_key), code_key)
            if code in seen_codes:
                raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"{dict_type}:{code} 重复")
            row = self._get_dictionary_by_code(company=company, dict_type=dict_type, code=code)
            if row is None or row.status != "active":
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"{dict_type}:{code} 字典不存在或已停用")
            normalized_items.append({code_key: code, name_key: self._require_text(row.name, "name")})
            seen_codes.add(code)
        return normalized_items

    def _style_values_from_create(self, payload: StyleMasterCreateRequest) -> dict[str, Any]:
        return {
            "ys_style_no": self._require_text(payload.ys_style_no, "ys_style_no"),
            "ys_style_name_cn": self._require_text(payload.ys_style_name_cn, "ys_style_name_cn"),
            "ys_season": self._require_text(payload.ys_season, "ys_season"),
            "ys_year": self._require_text(payload.ys_year, "ys_year"),
            "ys_brand": self._require_text(payload.ys_brand, "ys_brand"),
            "ys_style_status": self._normalize_style_status(payload.ys_style_status),
            "colors": [item.model_dump(mode="json") for item in payload.colors],
            "sizes": [item.model_dump(mode="json") for item in payload.sizes],
        }

    def _style_values_from_update(self, *, row: LyStyleMaster, payload: StyleMasterUpdateRequest) -> dict[str, Any]:
        if row.ys_style_status == "disabled":
            raise BusinessException(code=STYLE_MASTER_INVALID_STATUS, message="停用款式不允许编辑")
        return {
            "ys_style_no": self._optional_text(payload.ys_style_no) or row.ys_style_no,
            "ys_style_name_cn": self._optional_text(payload.ys_style_name_cn) or row.ys_style_name_cn,
            "ys_season": self._optional_text(payload.ys_season) or row.ys_season,
            "ys_year": self._optional_text(payload.ys_year) or row.ys_year,
            "ys_brand": self._optional_text(payload.ys_brand) or row.ys_brand,
            "ys_style_status": self._normalize_style_status(payload.ys_style_status or row.ys_style_status),
            "colors": [item.model_dump(mode="json") for item in payload.colors] if payload.colors is not None else list(row.colors or []),
            "sizes": [item.model_dump(mode="json") for item in payload.sizes] if payload.sizes is not None else list(row.sizes or []),
        }

    def _get_style_for_mutation(self, *, style_id: int, company: str, allow_disabled: bool = False) -> LyStyleMaster:
        row = self.session.query(LyStyleMaster).filter(LyStyleMaster.id == int(style_id), LyStyleMaster.company == company).first()
        if row is None:
            raise BusinessException(code=STYLE_MASTER_NOT_FOUND)
        if not allow_disabled and row.ys_style_status == "disabled":
            raise BusinessException(code=STYLE_MASTER_INVALID_STATUS, message="款式已停用")
        return row

    def _get_dictionary_for_mutation(self, *, dictionary_id: int, company: str, allow_inactive: bool = False) -> LyStyleDictionary:
        row = self.session.query(LyStyleDictionary).filter(LyStyleDictionary.id == int(dictionary_id), LyStyleDictionary.company == company).first()
        if row is None:
            raise BusinessException(code=STYLE_MASTER_NOT_FOUND)
        if not allow_inactive and row.status == "inactive":
            raise BusinessException(code=STYLE_MASTER_INVALID_STATUS, message="字典已停用")
        return row

    def _get_style_by_id(self, style_id: int) -> LyStyleMaster:
        row = self.session.query(LyStyleMaster).filter(LyStyleMaster.id == int(style_id)).first()
        if row is None:
            raise BusinessException(code=STYLE_MASTER_NOT_FOUND)
        return row

    def _get_dictionary_by_id(self, dictionary_id: int) -> LyStyleDictionary:
        row = self.session.query(LyStyleDictionary).filter(LyStyleDictionary.id == int(dictionary_id)).first()
        if row is None:
            raise BusinessException(code=STYLE_MASTER_NOT_FOUND)
        return row

    def _get_style_by_no(self, *, company: str, style_no: str) -> LyStyleMaster | None:
        return self.session.query(LyStyleMaster).filter(LyStyleMaster.company == company, LyStyleMaster.ys_style_no == style_no).first()

    def _get_dictionary_by_code(self, *, company: str, dict_type: str, code: str) -> LyStyleDictionary | None:
        return (
            self.session.query(LyStyleDictionary)
            .filter(
                LyStyleDictionary.company == company,
                LyStyleDictionary.dict_type == dict_type,
                LyStyleDictionary.code == code,
            )
            .first()
        )

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
            LyStyleMasterIdempotency(
                entity_type=entity_type,
                company=company,
                idempotency_key=idempotency_key,
                operation=operation,
                request_hash=request_hash,
                record_id=record_id,
                created_by=actor,
            )
        )

    def _get_idempotency(self, *, entity_type: str, company: str, idempotency_key: str) -> LyStyleMasterIdempotency | None:
        return (
            self.session.query(LyStyleMasterIdempotency)
            .filter(
                LyStyleMasterIdempotency.entity_type == entity_type,
                LyStyleMasterIdempotency.company == company,
                LyStyleMasterIdempotency.idempotency_key == idempotency_key,
            )
            .first()
        )

    def _ensure_same_idempotency(self, row: LyStyleMasterIdempotency, *, operation: str, request_hash: str) -> None:
        if row.operation != operation or row.request_hash != request_hash:
            raise BusinessException(code=STYLE_MASTER_IDEMPOTENCY_CONFLICT)

    def _style_result(
        self,
        *,
        row: LyStyleMaster,
        before: dict[str, Any] | None,
        after: dict[str, Any],
        idempotent: bool = False,
    ) -> StyleMasterMutationResult:
        return StyleMasterMutationResult(
            item=self._style_item(row),
            before=before,
            after=after,
            resource_type="STYLE_MASTER",
            resource_id=int(row.id),
            resource_no=str(row.ys_style_no),
            idempotent=idempotent,
        )

    def _dictionary_result(
        self,
        *,
        row: LyStyleDictionary,
        before: dict[str, Any] | None,
        after: dict[str, Any],
        idempotent: bool = False,
    ) -> StyleMasterMutationResult:
        return StyleMasterMutationResult(
            item=self._dictionary_item(row),
            before=before,
            after=after,
            resource_type="STYLE_DICTIONARY",
            resource_id=int(row.id),
            resource_no=f"{row.dict_type}:{row.code}",
            idempotent=idempotent,
        )

    def _style_item(self, row: LyStyleMaster) -> StyleMasterItem:
        return StyleMasterItem(
            id=int(row.id),
            company=row.company,
            ys_style_no=row.ys_style_no,
            ys_style_name_cn=row.ys_style_name_cn,
            ys_season=row.ys_season,
            ys_year=row.ys_year,
            ys_brand=row.ys_brand,
            ys_style_status=self._normalize_style_status(row.ys_style_status),
            colors=list(row.colors or []),
            sizes=list(row.sizes or []),
            version=int(row.version or 1),
            created_by=row.created_by,
            created_at=row.created_at,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
            disabled_by=row.disabled_by,
            disabled_at=row.disabled_at,
            disable_reason=row.disable_reason,
        )

    def _dictionary_item(self, row: LyStyleDictionary) -> StyleDictionaryItem:
        status = self._normalize_dictionary_status(row.status)
        return StyleDictionaryItem(
            id=int(row.id),
            company=row.company,
            dict_type=self._normalize_dictionary_type(row.dict_type),
            code=row.code,
            name=row.name,
            status=status,
            disabled=status == "inactive",
            sort_no=int(row.sort_no or 0),
            version=int(row.version or 1),
            created_by=row.created_by,
            created_at=row.created_at,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
            deactivated_by=row.deactivated_by,
            deactivated_at=row.deactivated_at,
            deactivate_reason=row.deactivate_reason,
        )

    def _snapshot_style(self, row: LyStyleMaster) -> dict[str, Any]:
        return self._style_item(row).model_dump(mode="json")

    def _snapshot_dictionary(self, row: LyStyleDictionary) -> dict[str, Any]:
        return self._dictionary_item(row).model_dump(mode="json")

    def _normalize_style_status(self, value: str) -> str:
        normalized = self._require_text(value, "ys_style_status")
        if normalized not in STYLE_STATUSES:
            raise BusinessException(code=STYLE_MASTER_INVALID_STATUS, message="款式状态非法")
        return normalized

    def _normalize_dictionary_type(self, value: str) -> str:
        normalized = self._require_text(value, "dict_type")
        if normalized not in DICTIONARY_TYPES:
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message="字典类型非法")
        return normalized

    def _normalize_dictionary_status(self, value: str) -> str:
        normalized = self._require_text(value, "status")
        if normalized not in DICTIONARY_STATUSES:
            raise BusinessException(code=STYLE_MASTER_INVALID_STATUS, message="字典状态非法")
        return normalized

    def _request_hash(self, **payload: Any) -> str:
        dumped = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    def _require_text(self, value: Any, field: str) -> str:
        stripped = self._optional_text(value)
        if not stripped:
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"{field} 不能为空")
        return stripped
