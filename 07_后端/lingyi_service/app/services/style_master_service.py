"""Service layer for FastAPI-native style master data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
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
from app.core.error_codes import BOM_NOT_FOUND
from app.core.error_codes import STYLE_MASTER_CONFLICT
from app.core.error_codes import STYLE_MASTER_IDEMPOTENCY_CONFLICT
from app.core.error_codes import STYLE_MASTER_INVALID_REFERENCE
from app.core.error_codes import STYLE_MASTER_INVALID_STATUS
from app.core.error_codes import STYLE_MASTER_NOT_FOUND
from app.core.exceptions import BusinessException
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyApparelBomWriteOperation
from app.models.bom import LyBomOperation
from app.models.master_data import LyMasterDataRecord
from app.models.style_master import LyStyleDictionary
from app.models.style_master import LyStyleGallery
from app.models.style_master import LyStyleMaster
from app.models.style_master import LyStyleMasterIdempotency
from app.models.style_master import LyStyleSku
from app.schemas.style_master import StyleDictionaryCreateRequest
from app.schemas.style_master import StyleDictionaryItem
from app.schemas.style_master import StyleDictionaryListData
from app.schemas.style_master import StyleDictionaryUpdateRequest
from app.schemas.style_master import StyleGalleryCreateRequest
from app.schemas.style_master import StyleGalleryItem
from app.schemas.style_master import StyleGalleryListData
from app.schemas.style_master import StyleGalleryUpdateRequest
from app.schemas.style_master import StyleMaterialBomData
from app.schemas.style_master import StyleMaterialBomExplodeData
from app.schemas.style_master import StyleMaterialBomHeader
from app.schemas.style_master import StyleMaterialBomItem
from app.schemas.style_master import StyleMaterialBomOperation
from app.schemas.style_master import StyleMaterialBomRequirementItem
from app.schemas.style_master import StyleMaterialBomUpsertRequest
from app.schemas.style_master import StyleMasterCreateRequest
from app.schemas.style_master import StyleMasterItem
from app.schemas.style_master import StyleMasterListData
from app.schemas.style_master import StyleMasterUpdateRequest
from app.schemas.style_master import StyleSkuItem
from app.schemas.style_master import StyleSkuListData
from app.schemas.style_master import StyleSkuUpsertRequest
from app.services.recycle_bin_service import RecycleBinService

STYLE_STATUSES = {"draft", "enabled", "disabled"}
DICTIONARY_TYPES = {"season", "year", "brand", "color", "size"}
DICTIONARY_STATUSES = {"active", "inactive"}
DICTIONARY_CODE_PREFIXES = {
    "season": "SEA",
    "year": "YEAR",
    "brand": "BRAND",
    "color": "COLOR",
    "size": "SIZE",
}
GALLERY_IMAGE_TYPES = {"main", "detail", "color", "process", "other"}
STYLE_GALLERY_UPLOAD_PREFIX = "/uploads/images/style_gallery/"


@dataclass(frozen=True)
class StyleMasterMutationResult:
    """Mutation output plus audit snapshots."""

    item: Any
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
        style_id: int | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> StyleMasterListData:
        try:
            query = self.session.query(LyStyleMaster)
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyStyleMaster.company == normalized_company)
            if style_id is not None:
                query = query.filter(LyStyleMaster.id == int(style_id))
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
                    LyStyleMaster.created_at.desc(),
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
        summaries = self._style_gallery_summaries([int(row.id) for row in rows])
        sku_counts = self._style_sku_counts([int(row.id) for row in rows])
        return StyleMasterListData(
            items=[
                self._style_item(
                    row,
                    gallery_summary=summaries.get(int(row.id)),
                    sku_count=sku_counts.get(int(row.id), 0),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_style_gallery(
        self,
        *,
        company: str | None,
        keyword: str | None,
        style_id: int | None,
        image_type: str | None,
        is_primary: bool | None,
        page: int,
        page_size: int,
    ) -> StyleGalleryListData:
        try:
            query = (
                self.session.query(LyStyleGallery, LyStyleMaster)
                .join(LyStyleMaster, LyStyleMaster.id == LyStyleGallery.style_master_id)
                .filter(LyStyleGallery.status == "active")
            )
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyStyleGallery.company == normalized_company)
            if style_id:
                query = query.filter(LyStyleGallery.style_master_id == int(style_id))
            normalized_type = self._optional_text(image_type)
            if normalized_type and normalized_type != "all":
                query = query.filter(LyStyleGallery.image_type == self._normalize_gallery_image_type(normalized_type))
            if is_primary is not None:
                query = query.filter(LyStyleGallery.is_primary.is_(bool(is_primary)))
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyStyleMaster.ys_style_no).like(like_value))
                    | (func.lower(LyStyleMaster.ys_style_name_cn).like(like_value))
                    | (func.lower(LyStyleMaster.ys_brand).like(like_value))
                    | (func.lower(LyStyleGallery.image_name).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(
                    LyStyleGallery.created_at.desc(),
                    LyStyleGallery.id.desc(),
                )
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return StyleGalleryListData(
            items=[self._gallery_item(row=gallery, style=style) for gallery, style in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_style_gallery(self, *, payload: StyleGalleryCreateRequest, actor: str) -> StyleMasterMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        style = self._get_style_for_read(style_id=payload.style_master_id, company=company)
        image_url = self._normalize_style_gallery_upload_url(payload.image_url, "image_url")
        image_type = self._normalize_gallery_image_type(payload.image_type)
        thumbnail_url = (
            self._normalize_style_gallery_upload_url(payload.thumbnail_url, "thumbnail_url")
            if self._optional_text(payload.thumbnail_url)
            else image_url
        )
        values = {
            "style_master_id": int(style.id),
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "image_name": self._optional_text(payload.image_name),
            "image_type": image_type,
            "is_primary": bool(payload.is_primary),
        }
        request_hash = self._request_hash(operation="create", entity_type="gallery", company=company, values=values)
        idem = self._get_idempotency(entity_type="gallery", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create", request_hash=request_hash)
            row = self._get_gallery_by_id(idem.record_id)
            idem_style = self._get_style_for_read(style_id=int(row.style_master_id), company=str(row.company))
            after = self._snapshot_gallery(row=row, style=idem_style)
            return self._gallery_result(row=row, style=idem_style, before=after, after=after, idempotent=True)
        now = datetime.now(UTC)
        try:
            if payload.is_primary:
                self._clear_other_primary_gallery(company=company, style_master_id=int(style.id))
            row = LyStyleGallery(
                company=company,
                style_master_id=values["style_master_id"],
                image_url=values["image_url"],
                thumbnail_url=values["thumbnail_url"],
                image_name=values["image_name"],
                image_type=values["image_type"],
                is_primary=values["is_primary"],
                status="active",
                created_by=actor,
                updated_by=actor,
                updated_at=now,
            )
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="gallery",
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
        after = self._snapshot_gallery(row=row, style=style)
        return self._gallery_result(row=row, style=style, before=None, after=after)

    def update_style_gallery(
        self,
        *,
        gallery_id: int,
        payload: StyleGalleryUpdateRequest,
        actor: str,
    ) -> StyleMasterMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_gallery_for_mutation(gallery_id=gallery_id, company=company)
        style = self._get_style_for_read(style_id=int(row.style_master_id), company=company)
        image_url = (
            self._normalize_style_gallery_upload_url(payload.image_url, "image_url")
            if payload.image_url is not None
            else str(row.image_url)
        )
        thumbnail_url = (
            self._normalize_style_gallery_upload_url(payload.thumbnail_url, "thumbnail_url")
            if self._optional_text(payload.thumbnail_url)
            else (
                image_url
                if payload.thumbnail_url is not None
                else str(row.thumbnail_url or row.image_url)
            )
        )
        values = {
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "image_name": self._optional_text(payload.image_name) if payload.image_name is not None else row.image_name,
            "image_type": self._normalize_gallery_image_type(payload.image_type or str(row.image_type)),
            "is_primary": bool(payload.is_primary) if payload.is_primary is not None else bool(row.is_primary),
        }
        request_hash = self._request_hash(operation="update", entity_type="gallery", company=company, gallery_id=gallery_id, values=values)
        idem = self._get_idempotency(entity_type="gallery", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="update", request_hash=request_hash)
            idem_row = self._get_gallery_by_id(idem.record_id)
            idem_style = self._get_style_for_read(style_id=int(idem_row.style_master_id), company=str(idem_row.company))
            after = self._snapshot_gallery(row=idem_row, style=idem_style)
            return self._gallery_result(row=idem_row, style=idem_style, before=after, after=after, idempotent=True)
        before = self._snapshot_gallery(row=row, style=style)
        try:
            row.image_url = values["image_url"]
            row.thumbnail_url = values["thumbnail_url"]
            row.image_name = values["image_name"]
            row.image_type = values["image_type"]
            if payload.is_primary is not None:
                if payload.is_primary:
                    self._clear_other_primary_gallery(company=company, style_master_id=int(row.style_master_id), exclude_gallery_id=int(row.id))
                row.is_primary = values["is_primary"]
            row.updated_by = actor
            row.updated_at = datetime.now(UTC)
            self._insert_idempotency(
                entity_type="gallery",
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
        after = self._snapshot_gallery(row=row, style=style)
        return self._gallery_result(row=row, style=style, before=before, after=after)

    def deactivate_style_gallery(
        self,
        *,
        gallery_id: int,
        company: str,
        idempotency_key: str,
        reason: str,
        actor: str,
    ) -> StyleMasterMutationResult:
        company = self._require_text(company, "company")
        idempotency_key = self._require_text(idempotency_key, "idempotency_key")
        reason = self._require_text(reason, "reason")
        request_hash = self._request_hash(operation="deactivate", entity_type="gallery", company=company, gallery_id=gallery_id, reason=reason)
        idem = self._get_idempotency(entity_type="gallery", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="deactivate", request_hash=request_hash)
            idem_row = self._get_gallery_by_id(idem.record_id)
            idem_style = self._get_style_for_read(style_id=int(idem_row.style_master_id), company=str(idem_row.company))
            after = self._snapshot_gallery(row=idem_row, style=idem_style)
            return self._gallery_result(row=idem_row, style=idem_style, before=after, after=after, idempotent=True)
        row = self._get_gallery_for_mutation(gallery_id=gallery_id, company=company)
        style = self._get_style_for_read(style_id=int(row.style_master_id), company=company)
        before = self._snapshot_gallery(row=row, style=style)
        try:
            row.status = "inactive"
            row.is_primary = False
            row.deactivated_by = actor
            row.deactivated_at = datetime.now(UTC)
            row.deactivate_reason = reason
            row.updated_by = actor
            row.updated_at = datetime.now(UTC)
            self._insert_idempotency(
                entity_type="gallery",
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
        after = self._snapshot_gallery(row=row, style=style)
        return self._gallery_result(row=row, style=style, before=before, after=after)

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
            self._sync_style_bom_item_code(style_id=int(row.id), company=company, item_code=str(values["ys_style_no"]), actor=actor)
            self._sync_style_sku_style_no(style_id=int(row.id), company=company, item_code=str(values["ys_style_no"]), actor=actor)
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

    def list_style_skus(self, *, style_id: int, company: str | None) -> StyleSkuListData:
        """Return the style color-size SKU matrix."""
        normalized_company = self._require_text(company, "company")
        style = self._get_style_for_read(style_id=style_id, company=normalized_company)
        return self._style_sku_list_data(style=style)

    def upsert_style_skus(
        self,
        *,
        style_id: int,
        payload: StyleSkuUpsertRequest,
        actor: str,
    ) -> StyleMasterMutationResult:
        """Create or replace the style color-size SKU matrix."""
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        style = self._get_style_for_mutation(style_id=style_id, company=company)
        if str(style.ys_style_status) == "disabled":
            raise BusinessException(code=STYLE_MASTER_INVALID_STATUS, message="停用款式不允许维护 SKU 矩阵")
        normalized_items = self._normalize_sku_payload(style=style, items=payload.items)
        request_hash = self._request_hash(
            operation="style_sku_upsert",
            entity_type="sku",
            company=company,
            style_id=style_id,
            values=normalized_items,
        )
        idem = self._get_idempotency(entity_type="sku", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="update", request_hash=request_hash)
            data = self._style_sku_list_data(style=style)
            return StyleMasterMutationResult(
                item=data,
                before=data.model_dump(mode="json"),
                after=data.model_dump(mode="json"),
                resource_type="STYLE_SKU",
                resource_id=int(style.id),
                resource_no=str(style.ys_style_no),
                idempotent=True,
            )

        before = self._style_sku_list_data(style=style).model_dump(mode="json")
        now = datetime.now(UTC)
        try:
            existing_rows = (
                self.session.query(LyStyleSku)
                .filter(LyStyleSku.company == company, LyStyleSku.style_master_id == int(style.id))
                .all()
            )
            existing_by_pair = {(str(row.color_code), str(row.size_code)): row for row in existing_rows}
            active_pairs: set[tuple[str, str]] = set()
            for item in normalized_items:
                pair = (item["color_code"], item["size_code"])
                active_pairs.add(pair)
                row = existing_by_pair.get(pair)
                if row is None:
                    row = LyStyleSku(
                        company=company,
                        style_master_id=int(style.id),
                        ys_style_no=str(style.ys_style_no),
                        color_code=item["color_code"],
                        color_name=item["color_name"],
                        size_code=item["size_code"],
                        size_name=item["size_name"],
                        sku_code=item["sku_code"],
                        barcode=item["barcode"],
                        status=item["status"],
                        sort_no=item["sort_no"],
                        created_by=actor,
                        updated_by=actor,
                        updated_at=now,
                    )
                    self.session.add(row)
                else:
                    row.ys_style_no = str(style.ys_style_no)
                    row.color_name = item["color_name"]
                    row.size_name = item["size_name"]
                    row.sku_code = item["sku_code"]
                    row.barcode = item["barcode"]
                    row.status = item["status"]
                    row.sort_no = item["sort_no"]
                    row.updated_by = actor
                    row.updated_at = now
            for pair, row in existing_by_pair.items():
                if pair not in active_pairs:
                    row.ys_style_no = str(style.ys_style_no)
                    row.status = "inactive"
                    row.updated_by = actor
                    row.updated_at = now
            self._insert_idempotency(
                entity_type="sku",
                company=company,
                idempotency_key=idempotency_key,
                operation="update",
                request_hash=request_hash,
                record_id=int(style.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._style_sku_list_data(style=style).model_dump(mode="json")
        return StyleMasterMutationResult(
            item=self._style_sku_list_data(style=style),
            before=before,
            after=after,
            resource_type="STYLE_SKU",
            resource_id=int(style.id),
            resource_no=str(style.ys_style_no),
        )

    def get_style_material_bom(self, *, style_id: int, company: str | None) -> StyleMaterialBomData:
        """Return the current material BOM snapshot for a style."""
        normalized_company = self._require_text(company, "company")
        style = self._get_style_for_read(style_id=style_id, company=normalized_company)
        bom = self._find_style_material_bom(style=style)
        if bom is None:
            return StyleMaterialBomData(bom=None, items=[])
        return self._style_material_bom_data(style=style, bom=bom)

    def upsert_style_material_bom(
        self,
        *,
        style_id: int,
        payload: StyleMaterialBomUpsertRequest,
        actor: str,
    ) -> StyleMasterMutationResult:
        """Create or replace the style material BOM lines."""
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        style = self._get_style_for_mutation(style_id=style_id, company=company)
        if str(style.ys_style_status) == "disabled":
            raise BusinessException(code=STYLE_MASTER_INVALID_STATUS, message="停用款式不允许维护用料 BOM")
        payload_items = [item.model_dump(mode="json") for item in payload.items]
        payload_operations = [item.model_dump(mode="json") for item in payload.operations] if payload.operations is not None else None
        request_hash = self._request_hash(
            operation="style_material_bom_upsert",
            company=company,
            style_id=style_id,
            item_code=str(style.ys_style_no),
            version_no=payload.version_no,
            items=payload_items,
            operations=payload_operations,
        )
        idem = self._get_bom_operation(company=company, operation="style_material_bom_upsert", idempotency_key=idempotency_key)
        if idem:
            if idem.request_hash != request_hash:
                raise BusinessException(code=STYLE_MASTER_IDEMPOTENCY_CONFLICT)
            bom = self._must_get_style_bom_by_id(int(idem.bom_id))
            data = self._style_material_bom_data(style=style, bom=bom)
            return StyleMasterMutationResult(
                item=data,
                before=data.model_dump(mode="json"),
                after=data.model_dump(mode="json"),
                resource_type="STYLE_MATERIAL_BOM",
                resource_id=int(bom.id),
                resource_no=str(bom.bom_no),
                idempotent=True,
            )

        self._ensure_unique_style_material_bom_items(items=payload.items)
        self._ensure_style_bom_materials_active(company=company, items=payload.items)
        if payload.operations is not None:
            self._ensure_style_material_bom_operations(operations=payload.operations)
        existing = self._find_style_material_bom(style=style)
        before = self._style_material_bom_data(style=style, bom=existing).model_dump(mode="json") if existing else None
        now = datetime.now(UTC)
        try:
            bom = existing
            if bom is None:
                bom = LyApparelBom(
                    id=self._next_id(LyApparelBom),
                    bom_no=self._next_material_bom_no(item_code=str(style.ys_style_no), version_no=payload.version_no),
                    company=company,
                    style_master_id=int(style.id),
                    item_code=str(style.ys_style_no),
                    version_no=str(payload.version_no),
                    is_default=True,
                    status="active",
                    effective_date=now.date(),
                    created_by=actor,
                    updated_by=actor,
                )
                self.session.add(bom)
                self.session.flush()
            else:
                bom.company = company
                bom.style_master_id = int(style.id)
                bom.item_code = str(style.ys_style_no)
                bom.version_no = str(payload.version_no)
                bom.is_default = True
                bom.status = "active"
                bom.effective_date = bom.effective_date or now.date()
                bom.updated_by = actor
                bom.updated_at = now

            self.session.query(LyApparelBomItem).filter(LyApparelBomItem.bom_id == int(bom.id)).delete()
            next_item_id = self._next_id(LyApparelBomItem)
            for item in payload.items:
                self.session.add(
                    LyApparelBomItem(
                        id=next_item_id,
                        bom_id=int(bom.id),
                        material_item_code=item.material_item_code.strip(),
                        color=self._optional_text(item.color),
                        size=self._optional_text(item.size),
                        part=self._optional_text(item.part),
                        qty_per_piece=item.qty_per_piece,
                        usage_count=item.usage_count,
                        spec_by_size=self._bom_spec_by_size(item.spec_by_size),
                        loss_rate=item.loss_rate,
                        uom=item.uom.strip(),
                        remark=self._optional_text(item.remark),
                    )
                )
                next_item_id += 1
            if payload.operations is not None:
                self.session.query(LyBomOperation).filter(LyBomOperation.bom_id == int(bom.id)).delete()
                next_operation_id = self._next_id(LyBomOperation)
                for operation in payload.operations:
                    self.session.add(
                        LyBomOperation(
                            id=next_operation_id,
                            bom_id=int(bom.id),
                            process_name=operation.process_name.strip(),
                            sequence_no=int(operation.sequence_no),
                            is_subcontract=bool(operation.is_subcontract),
                            wage_rate=operation.wage_rate,
                            subcontract_cost_per_piece=operation.subcontract_cost_per_piece,
                            remark=self._optional_text(operation.remark),
                        )
                    )
                    next_operation_id += 1
            self.session.flush()
            data = self._style_material_bom_data(style=style, bom=bom)
            self.session.add(
                LyApparelBomWriteOperation(
                    bom_id=int(bom.id),
                    company=company,
                    operation="style_material_bom_upsert",
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_json=json.dumps(data.model_dump(mode="json"), ensure_ascii=False, default=str),
                    created_by=actor,
                )
            )
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        return StyleMasterMutationResult(
            item=data,
            before=before,
            after=data.model_dump(mode="json"),
            resource_type="STYLE_MATERIAL_BOM",
            resource_id=int(data.bom.id) if data.bom else int(style.id),
            resource_no=data.bom.bom_no if data.bom else str(style.ys_style_no),
        )

    def explode_style_material_bom(self, *, style_id: int, company: str | None, order_qty: Decimal) -> StyleMaterialBomExplodeData:
        """Calculate material requirements from the style material BOM."""
        normalized_company = self._require_text(company, "company")
        style = self._get_style_for_read(style_id=style_id, company=normalized_company)
        bom = self._find_style_material_bom(style=style)
        if bom is None:
            raise BusinessException(code=BOM_NOT_FOUND, message="该款式未维护用料 BOM")
        data = self._style_material_bom_data(style=style, bom=bom)
        if not data.items:
            raise BusinessException(code=BOM_NOT_FOUND, message="该款式用料 BOM 未维护明细")
        items: list[StyleMaterialBomRequirementItem] = []
        total = Decimal("0")
        for item in data.items:
            usage_count = Decimal(str(item.usage_count or 1))
            required_qty = (
                Decimal(str(order_qty)) * item.qty_per_piece * usage_count * (Decimal("1") + item.loss_rate)
            ).quantize(Decimal("0.000001"))
            total += required_qty
            items.append(
                StyleMaterialBomRequirementItem(
                    material_item_code=item.material_item_code,
                    color=item.color,
                    size=item.size,
                    part=item.part,
                    uom=item.uom,
                    qty_per_piece=item.qty_per_piece,
                    usage_count=usage_count,
                    spec_by_size=item.spec_by_size,
                    loss_rate=item.loss_rate,
                    required_qty=required_qty,
                )
            )
        return StyleMaterialBomExplodeData(
            style_master_id=int(style.id),
            item_code=str(style.ys_style_no),
            order_qty=Decimal(str(order_qty)),
            items=items,
            total_required_qty=total.quantize(Decimal("0.000001")),
        )

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
                    LyStyleDictionary.created_at.desc(),
                    LyStyleDictionary.id.desc(),
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
        requested_code = self._optional_text(payload.code)
        values_for_hash = {
            "dict_type": dict_type,
            "code": requested_code,
            "name": self._require_text(payload.name, "name"),
            "sort_no": int(payload.sort_no),
        }
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(operation="create", entity_type="dictionary", company=company, values=values_for_hash)
        idem = self._get_idempotency(entity_type="dictionary", company=company, idempotency_key=idempotency_key)
        if idem:
            self._ensure_same_idempotency(idem, operation="create", request_hash=request_hash)
            row = self._get_dictionary_by_id(idem.record_id)
            after = self._snapshot_dictionary(row)
            return self._dictionary_result(row=row, before=after, after=after, idempotent=True)

        code = requested_code or self._next_dictionary_code(company=company, dict_type=dict_type)
        values = {**values_for_hash, "code": code}
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

    def delete_dictionary(
        self,
        *,
        dictionary_id: int,
        company: str,
        actor: str,
    ) -> StyleMasterMutationResult:
        company = self._require_text(company, "company")
        row = self._get_dictionary_for_mutation(dictionary_id=dictionary_id, company=company, allow_inactive=True)
        reference_no = self._referencing_style_no(row)
        if reference_no:
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"字典 {row.dict_type}:{row.code} 已被款式 {reference_no} 引用，不能删除")

        before = self._snapshot_dictionary(row)
        try:
            RecycleBinService(self.session).move_style_dictionary_to_trash(row=row, actor=actor)
            self.session.query(LyStyleMasterIdempotency).filter(
                LyStyleMasterIdempotency.entity_type == "dictionary",
                LyStyleMasterIdempotency.record_id == int(row.id),
            ).delete(synchronize_session=False)
            self.session.delete(row)
            self.session.flush()
        except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        after = {
            "id": int(before["id"]),
            "company": before["company"],
            "dict_type": before["dict_type"],
            "code": before["code"],
            "name": before["name"],
            "deleted": True,
        }
        return StyleMasterMutationResult(
            item=after,
            before=before,
            after=after,
            resource_type="STYLE_DICTIONARY",
            resource_id=int(before["id"]),
            resource_no=f"{before['dict_type']}:{before['code']}",
        )

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

    def _get_style_for_read(self, *, style_id: int, company: str) -> LyStyleMaster:
        row = self.session.query(LyStyleMaster).filter(LyStyleMaster.id == int(style_id), LyStyleMaster.company == company).first()
        if row is None:
            raise BusinessException(code=STYLE_MASTER_NOT_FOUND)
        return row

    def _get_gallery_for_mutation(self, *, gallery_id: int, company: str) -> LyStyleGallery:
        row = (
            self.session.query(LyStyleGallery)
            .filter(
                LyStyleGallery.id == int(gallery_id),
                LyStyleGallery.company == company,
                LyStyleGallery.status == "active",
            )
            .first()
        )
        if row is None:
            raise BusinessException(code=STYLE_MASTER_NOT_FOUND, message="款式图库记录不存在或已停用")
        return row

    def _clear_other_primary_gallery(self, *, company: str, style_master_id: int, exclude_gallery_id: int | None = None) -> None:
        query = self.session.query(LyStyleGallery).filter(
            LyStyleGallery.company == company,
            LyStyleGallery.style_master_id == int(style_master_id),
            LyStyleGallery.status == "active",
            LyStyleGallery.is_primary.is_(True),
        )
        if exclude_gallery_id is not None:
            query = query.filter(LyStyleGallery.id != int(exclude_gallery_id))
        for row in query.all():
            row.is_primary = False

    def _style_gallery_summaries(self, style_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not style_ids:
            return {}
        try:
            rows = (
                self.session.query(LyStyleGallery)
                .filter(
                    LyStyleGallery.style_master_id.in_(style_ids),
                    LyStyleGallery.status == "active",
                )
                .order_by(LyStyleGallery.is_primary.desc(), LyStyleGallery.updated_at.desc(), LyStyleGallery.id.desc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        summaries: dict[int, dict[str, Any]] = {
            int(style_id): {"gallery_count": 0, "primary_image_url": None, "primary_thumbnail_url": None}
            for style_id in style_ids
        }
        for row in rows:
            style_id = int(row.style_master_id)
            summary = summaries.setdefault(style_id, {"gallery_count": 0, "primary_image_url": None, "primary_thumbnail_url": None})
            summary["gallery_count"] = int(summary["gallery_count"] or 0) + 1
            if bool(row.is_primary) and not summary["primary_image_url"]:
                summary["primary_image_url"] = row.image_url
                summary["primary_thumbnail_url"] = row.thumbnail_url or row.image_url
        return summaries

    def _style_sku_counts(self, style_ids: list[int]) -> dict[int, int]:
        if not style_ids:
            return {}
        try:
            rows = (
                self.session.query(LyStyleSku.style_master_id, func.count(LyStyleSku.id))
                .filter(LyStyleSku.style_master_id.in_(style_ids), LyStyleSku.status == "active")
                .group_by(LyStyleSku.style_master_id)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return {int(style_id): int(count or 0) for style_id, count in rows}

    def _style_sku_list_data(self, *, style: LyStyleMaster) -> StyleSkuListData:
        try:
            rows = (
                self.session.query(LyStyleSku)
                .filter(LyStyleSku.company == style.company, LyStyleSku.style_master_id == int(style.id))
                .order_by(LyStyleSku.status.asc(), LyStyleSku.sort_no.asc(), LyStyleSku.color_code.asc(), LyStyleSku.size_code.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return StyleSkuListData(
            style_master_id=int(style.id),
            ys_style_no=str(style.ys_style_no),
            items=[self._sku_item(row) for row in rows],
            total=len(rows),
        )

    def _normalize_sku_payload(self, *, style: LyStyleMaster, items: list[Any]) -> list[dict[str, Any]]:
        colors = {
            self._require_text(row.get("ys_color_code"), "ys_color_code"): self._require_text(row.get("ys_color_name"), "ys_color_name")
            for row in list(style.colors or [])
        }
        sizes = {
            self._require_text(row.get("ys_size_code"), "ys_size_code"): self._require_text(row.get("ys_size_name"), "ys_size_name")
            for row in list(style.sizes or [])
        }
        if not colors or not sizes:
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message="款式缺少颜色或尺码，无法维护 SKU 矩阵")
        normalized: list[dict[str, Any]] = []
        seen_pairs: set[tuple[str, str]] = set()
        seen_sku_codes: set[str] = set()
        for index, item in enumerate(items, start=1):
            color_code = self._require_text(item.color_code, "color_code")
            size_code = self._require_text(item.size_code, "size_code")
            if color_code not in colors:
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"颜色 {color_code} 不在当前款式颜色中")
            if size_code not in sizes:
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"尺码 {size_code} 不在当前款式尺码中")
            pair = (color_code, size_code)
            if pair in seen_pairs:
                raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"SKU 款色码重复: {color_code}/{size_code}")
            sku_code = self._require_text(item.sku_code, "sku_code")
            if sku_code in seen_sku_codes:
                raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"SKU 编码重复: {sku_code}")
            status = self._require_text(item.status, "status")
            if status not in {"active", "inactive"}:
                raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message=f"SKU 状态非法: {status}")
            normalized.append(
                {
                    "color_code": color_code,
                    "color_name": self._optional_text(item.color_name) or colors[color_code],
                    "size_code": size_code,
                    "size_name": self._optional_text(item.size_name) or sizes[size_code],
                    "sku_code": sku_code,
                    "barcode": self._optional_text(item.barcode),
                    "status": status,
                    "sort_no": int(item.sort_no if item.sort_no is not None else index * 10),
                }
            )
            seen_pairs.add(pair)
            seen_sku_codes.add(sku_code)
        return normalized

    def _find_style_material_bom(self, *, style: LyStyleMaster) -> LyApparelBom | None:
        return (
            self.session.query(LyApparelBom)
            .filter(
                LyApparelBom.company == style.company,
                LyApparelBom.style_master_id == int(style.id),
            )
            .order_by(
                LyApparelBom.is_default.desc(),
                LyApparelBom.status.asc(),
                LyApparelBom.id.desc(),
            )
            .first()
        )

    def _must_get_style_bom_by_id(self, bom_id: int) -> LyApparelBom:
        row = self.session.query(LyApparelBom).filter(LyApparelBom.id == int(bom_id)).first()
        if row is None:
            raise BusinessException(code=BOM_NOT_FOUND, message="BOM 不存在")
        return row

    def _ensure_style_bom_materials_active(self, *, company: str, items: list[Any]) -> None:
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

    def _ensure_unique_style_material_bom_items(self, *, items: list[Any]) -> None:
        seen: set[tuple[str, str, str, str]] = set()
        for item in items:
            material_code = self._require_text(getattr(item, "material_item_code", ""), "material_item_code")
            color = self._optional_text(getattr(item, "color", None)) or ""
            size = self._optional_text(getattr(item, "size", None)) or ""
            part = self._optional_text(getattr(item, "part", None)) or ""
            key = (material_code.lower(), color.lower(), size.lower(), part.lower())
            if key in seen:
                raise BusinessException(
                    code=STYLE_MASTER_CONFLICT,
                    message=(
                        "款用料 BOM 行重复: "
                        f"{material_code} / {color or '全部颜色'} / {size or '全部尺码'} / {part or '未填部位'}"
                    ),
                )
            seen.add(key)

    def _ensure_style_material_bom_operations(self, *, operations: list[Any]) -> None:
        seen_sequences: set[int] = set()
        for operation in operations:
            process_name = self._require_text(getattr(operation, "process_name", ""), "process_name")
            sequence_no = int(getattr(operation, "sequence_no", 0))
            if sequence_no in seen_sequences:
                raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"工序序号重复: {sequence_no}")
            seen_sequences.add(sequence_no)
            if bool(getattr(operation, "is_subcontract", False)):
                unit_cost = getattr(operation, "subcontract_cost_per_piece", None)
                if unit_cost is None or Decimal(str(unit_cost)) <= 0:
                    raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"工序工价缺失: {process_name}")
            else:
                wage_rate = getattr(operation, "wage_rate", None)
                if wage_rate is None or Decimal(str(wage_rate)) <= 0:
                    raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"工序工价缺失: {process_name}")

    def _material_name_lookup(self, *, company: str, material_codes: list[str]) -> dict[str, str]:
        codes = [code for code in dict.fromkeys(material_codes) if code]
        if not codes:
            return {}
        try:
            rows = (
                self.session.query(LyMasterDataRecord.code, LyMasterDataRecord.name)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == company,
                    LyMasterDataRecord.code.in_(codes),
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return {str(row.code): self._optional_text(row.name) or str(row.code) for row in rows}

    def _style_material_bom_data(self, *, style: LyStyleMaster, bom: LyApparelBom) -> StyleMaterialBomData:
        items = (
            self.session.query(LyApparelBomItem)
            .filter(LyApparelBomItem.bom_id == int(bom.id))
            .order_by(LyApparelBomItem.id.asc())
            .all()
        )
        operations = (
            self.session.query(LyBomOperation)
            .filter(LyBomOperation.bom_id == int(bom.id))
            .order_by(LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc())
            .all()
        )
        material_names = self._material_name_lookup(
            company=str(bom.company),
            material_codes=[str(item.material_item_code) for item in items],
        )
        return StyleMaterialBomData(
            bom=StyleMaterialBomHeader(
                id=int(bom.id),
                bom_no=str(bom.bom_no),
                company=str(bom.company),
                style_master_id=int(style.id),
                item_code=str(bom.item_code),
                version_no=str(bom.version_no),
                is_default=bool(bom.is_default),
                status=str(bom.status),
                updated_at=bom.updated_at,
            ),
            items=[
                StyleMaterialBomItem(
                    id=int(item.id),
                    material_item_code=str(item.material_item_code),
                    material_name=material_names.get(str(item.material_item_code)),
                    color=item.color,
                    size=getattr(item, "size", None),
                    part=getattr(item, "part", None),
                    qty_per_piece=Decimal(str(item.qty_per_piece)),
                    usage_count=Decimal(str(getattr(item, "usage_count", 1) or 1)),
                    spec_by_size=self._bom_spec_by_size(getattr(item, "spec_by_size", None)),
                    loss_rate=Decimal(str(item.loss_rate or 0)),
                    uom=str(item.uom),
                    remark=item.remark,
                )
                for item in items
            ],
            operations=[
                StyleMaterialBomOperation(
                    id=int(operation.id),
                    process_name=str(operation.process_name),
                    sequence_no=int(operation.sequence_no),
                    is_subcontract=bool(operation.is_subcontract),
                    wage_rate=Decimal(str(operation.wage_rate)) if operation.wage_rate is not None else None,
                    subcontract_cost_per_piece=(
                        Decimal(str(operation.subcontract_cost_per_piece))
                        if operation.subcontract_cost_per_piece is not None
                        else None
                    ),
                    remark=operation.remark,
                )
                for operation in operations
            ],
        )

    def _get_bom_operation(self, *, company: str, operation: str, idempotency_key: str) -> LyApparelBomWriteOperation | None:
        return (
            self.session.query(LyApparelBomWriteOperation)
            .filter(
                LyApparelBomWriteOperation.company == company,
                LyApparelBomWriteOperation.operation == operation,
                LyApparelBomWriteOperation.idempotency_key == idempotency_key,
            )
            .first()
        )

    def _sync_style_bom_item_code(self, *, style_id: int, company: str, item_code: str, actor: str) -> None:
        now = datetime.now(UTC)
        try:
            rows = (
                self.session.query(LyApparelBom)
                .filter(LyApparelBom.company == company, LyApparelBom.style_master_id == int(style_id))
                .all()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_bom_table_error(exc):
                return
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        for bom in rows:
            bom.item_code = item_code
            bom.updated_by = actor
            bom.updated_at = now

    def _sync_style_sku_style_no(self, *, style_id: int, company: str, item_code: str, actor: str) -> None:
        now = datetime.now(UTC)
        try:
            rows = (
                self.session.query(LyStyleSku)
                .filter(LyStyleSku.company == company, LyStyleSku.style_master_id == int(style_id))
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        for row in rows:
            row.ys_style_no = item_code
            row.updated_by = actor
            row.updated_at = now

    @staticmethod
    def _next_material_bom_no(*, item_code: str, version_no: str) -> str:
        token = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"BOM-{item_code}-{version_no}-{token}"

    @staticmethod
    def _is_missing_bom_table_error(exc: BaseException) -> bool:
        message = str(exc).lower()
        return "ly_apparel_bom" in message and ("no such table" in message or "does not exist" in message)

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

    def _get_gallery_by_id(self, gallery_id: int) -> LyStyleGallery:
        row = self.session.query(LyStyleGallery).filter(LyStyleGallery.id == int(gallery_id)).first()
        if row is None:
            raise BusinessException(code=STYLE_MASTER_NOT_FOUND, message="款式图库记录不存在")
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

    def _referencing_style_no(self, row: LyStyleDictionary) -> str | None:
        styles = self.session.query(LyStyleMaster).filter(LyStyleMaster.company == row.company).all()
        for style in styles:
            if row.dict_type == "season" and style.ys_season == row.code:
                return str(style.ys_style_no)
            if row.dict_type == "year" and style.ys_year == row.code:
                return str(style.ys_style_no)
            if row.dict_type == "brand" and style.ys_brand == row.code:
                return str(style.ys_style_no)
            if row.dict_type == "color" and self._style_pair_contains(style.colors, "ys_color_code", row.code):
                return str(style.ys_style_no)
            if row.dict_type == "size" and self._style_pair_contains(style.sizes, "ys_size_code", row.code):
                return str(style.ys_style_no)
        return None

    @staticmethod
    def _style_pair_contains(items: Any, code_key: str, code: str) -> bool:
        if not isinstance(items, list):
            return False
        return any(isinstance(item, dict) and str(item.get(code_key) or "") == code for item in items)

    @classmethod
    def _bom_spec_by_size(cls, value: Any) -> dict[str, str]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                return {}
        else:
            parsed = value
        if not isinstance(parsed, dict):
            return {}
        result: dict[str, str] = {}
        for key, spec in parsed.items():
            size = cls._optional_text(key)
            text = cls._optional_text(spec)
            if size and text:
                result[size] = text
        return result

    def _next_dictionary_code(self, *, company: str, dict_type: str) -> str:
        prefix = DICTIONARY_CODE_PREFIXES[self._normalize_dictionary_type(dict_type)]
        existing_codes = {
            str(row[0])
            for row in self.session.query(LyStyleDictionary.code)
            .filter(
                LyStyleDictionary.company == company,
                LyStyleDictionary.dict_type == dict_type,
                LyStyleDictionary.code.like(f"{prefix}-%"),
            )
            .all()
        }
        next_number = len(existing_codes) + 1
        while next_number < 1_000_000:
            candidate = f"{prefix}-{next_number:06d}"
            if candidate not in existing_codes:
                return candidate
            next_number += 1
        raise BusinessException(code=STYLE_MASTER_CONFLICT, message=f"{prefix} 自动编码已用尽")

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

    def _gallery_result(
        self,
        *,
        row: LyStyleGallery,
        style: LyStyleMaster,
        before: dict[str, Any] | None,
        after: dict[str, Any],
        idempotent: bool = False,
    ) -> StyleMasterMutationResult:
        return StyleMasterMutationResult(
            item=self._gallery_item(row=row, style=style),
            before=before,
            after=after,
            resource_type="STYLE_GALLERY",
            resource_id=int(row.id),
            resource_no=str(style.ys_style_no),
            idempotent=idempotent,
        )

    def _style_item(
        self,
        row: LyStyleMaster,
        gallery_summary: dict[str, Any] | None = None,
        sku_count: int | None = None,
    ) -> StyleMasterItem:
        gallery_summary = gallery_summary or {}
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
            primary_image_url=gallery_summary.get("primary_image_url"),
            primary_thumbnail_url=gallery_summary.get("primary_thumbnail_url"),
            gallery_count=int(gallery_summary.get("gallery_count") or 0),
            sku_count=int(sku_count or 0),
            version=int(row.version or 1),
            created_by=row.created_by,
            created_at=row.created_at,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
            disabled_by=row.disabled_by,
            disabled_at=row.disabled_at,
            disable_reason=row.disable_reason,
        )

    def _gallery_item(self, *, row: LyStyleGallery, style: LyStyleMaster | None = None) -> StyleGalleryItem:
        style = style or self._get_style_for_read(style_id=int(row.style_master_id), company=str(row.company))
        return StyleGalleryItem(
            id=int(row.id),
            company=str(row.company),
            style_master_id=int(row.style_master_id),
            ys_style_no=str(style.ys_style_no),
            ys_style_name_cn=str(style.ys_style_name_cn),
            image_url=str(row.image_url),
            thumbnail_url=row.thumbnail_url or row.image_url,
            image_name=row.image_name,
            image_type=self._normalize_gallery_image_type(str(row.image_type)),
            is_primary=bool(row.is_primary),
            designer=style.updated_by or style.created_by,
            style_type=style.ys_brand,
            created_by=str(row.created_by),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _sku_item(self, row: LyStyleSku) -> StyleSkuItem:
        return StyleSkuItem(
            id=int(row.id),
            company=str(row.company),
            style_master_id=int(row.style_master_id),
            ys_style_no=str(row.ys_style_no),
            color_code=str(row.color_code),
            color_name=str(row.color_name),
            size_code=str(row.size_code),
            size_name=str(row.size_name),
            sku_code=str(row.sku_code),
            barcode=row.barcode,
            status=row.status,
            sort_no=int(row.sort_no or 0),
            created_by=str(row.created_by),
            created_at=row.created_at,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
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

    def _snapshot_gallery(self, *, row: LyStyleGallery, style: LyStyleMaster | None = None) -> dict[str, Any]:
        return self._gallery_item(row=row, style=style).model_dump(mode="json")

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

    def _normalize_gallery_image_type(self, value: str) -> str:
        normalized = self._require_text(value, "image_type")
        if normalized not in GALLERY_IMAGE_TYPES:
            raise BusinessException(code=STYLE_MASTER_INVALID_REFERENCE, message="图片类型非法")
        return normalized

    def _normalize_style_gallery_upload_url(self, value: str | None, field_name: str) -> str:
        normalized = self._require_text(value, field_name)
        if (
            not normalized.startswith(STYLE_GALLERY_UPLOAD_PREFIX)
            or ".." in normalized
            or "\\" in normalized
        ):
            raise BusinessException(
                code=STYLE_MASTER_INVALID_REFERENCE,
                message=f"{field_name} 必须来自款式图库图片上传",
            )
        return normalized

    def _request_hash(self, **payload: Any) -> str:
        dumped = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def _next_id(self, model: type[Any]) -> int:
        current = self.session.query(func.max(model.id)).scalar()
        return int(current or 0) + 1

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
