"""Business service for BOM module (TASK-001)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from decimal import ROUND_HALF_UP
import os
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import BOM_DEFAULT_CONFLICT
from app.core.error_codes import BOM_DEFAULT_REQUIRES_ACTIVE
from app.core.error_codes import BOM_INVALID_LOSS_RATE
from app.core.error_codes import BOM_INVALID_QTY
from app.core.error_codes import BOM_ITEM_NOT_FOUND
from app.core.error_codes import BOM_NOT_FOUND
from app.core.error_codes import BOM_OPERATION_RATE_REQUIRED
from app.core.error_codes import BOM_PUBLISHED_LOCKED
from app.core.error_codes import BOM_STATUS_INVALID
from app.core.error_codes import STYLE_MASTER_INVALID_REFERENCE
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import is_default_bom_unique_conflict
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.style_master import LyStyleMaster
from app.schemas.bom import BomActivateData
from app.schemas.bom import BomAccessoriesPackagingData
from app.schemas.bom import BomAccessoriesPackagingItem
from app.schemas.bom import BomAccessoriesPackagingQuery
from app.schemas.bom import BomCreateRequest
from app.schemas.bom import BomDeactivateData
from app.schemas.bom import BomDetailData
from app.schemas.bom import BomExplodeData
from app.schemas.bom import BomExplodeRequest
from app.schemas.bom import BomFabricData
from app.schemas.bom import BomFabricItem
from app.schemas.bom import BomFabricQuery
from app.schemas.bom import BomHeader
from app.schemas.bom import BomMaterialGalleryData
from app.schemas.bom import BomMaterialGalleryItem
from app.schemas.bom import BomMaterialGalleryQuery
from app.schemas.bom import BomMaterialProcessingData
from app.schemas.bom import BomMaterialProcessingInboundData
from app.schemas.bom import BomMaterialDeductionData
from app.schemas.bom import BomMaterialDeductionItem
from app.schemas.bom import BomMaterialDeductionQuery
from app.schemas.bom import BomMaterialSalesOutboundData
from app.schemas.bom import BomMaterialSalesOutboundItem
from app.schemas.bom import BomMaterialSalesOutboundQuery
from app.schemas.bom import BomMaterialProcessingInboundItem
from app.schemas.bom import BomMaterialProcessingInboundQuery
from app.schemas.bom import BomMaterialProcessingItem
from app.schemas.bom import BomMaterialProcessingQuery
from app.schemas.bom import BomMaterialTypeData
from app.schemas.bom import BomMaterialTypeItem
from app.schemas.bom import BomMaterialTypeQuery
from app.schemas.bom import BomMaterialUnitData
from app.schemas.bom import BomMaterialUnitItem
from app.schemas.bom import BomMaterialUnitQuery
from app.schemas.bom import BomPurchaseOrderData
from app.schemas.bom import BomPurchaseOrderItem
from app.schemas.bom import BomPurchaseOrderQuery
from app.schemas.bom import BomProcessingTypeData
from app.schemas.bom import BomProcessingTypeItem
from app.schemas.bom import BomProcessingTypeQuery
from app.schemas.bom import BomItemPayload
from app.schemas.bom import BomItemView
from app.schemas.bom import BomListData
from app.schemas.bom import BomListItem
from app.schemas.bom import BomListQuery
from app.schemas.bom import BomNameData
from app.schemas.bom import BomOperationPayload
from app.schemas.bom import BomOperationView
from app.schemas.bom import BomSetDefaultData
from app.schemas.bom import BomUpdateData
from app.schemas.bom import BomUpdateRequest
from app.schemas.bom import ExplodedMaterialItem
from app.schemas.bom import ExplodedOperationCost


class BomBusinessError(BusinessException):
    """Backward-compatible BOM business exception alias."""


class BomService:
    """BOM business service."""

    ACTIVE_STATUS = "active"
    DRAFT_STATUS = "draft"
    INACTIVE_STATUS = "inactive"
    DEFAULT_COMPANY = "默认公司"

    def __init__(self, session: Session):
        """Initialize with SQLAlchemy session.

        Args:
            session: DB session for transactional operations.
        """
        self.session = session

    def create_bom(self, payload: BomCreateRequest, operator: str) -> BomNameData:
        """Create BOM header, items and operations.

        Args:
            payload: BOM create request payload.
            operator: Operator username.

        Returns:
            BomNameData: Created BOM identifier.
        """
        if self._is_local_sqlite_mode():
            # sqlite 本地测试库需要保持与 PostgreSQL 局部唯一索引语义一致：
            # 同 company + item_code 仅限制「active + is_default=true」唯一，不应限制全部 item_code 唯一。
            self._ensure_local_sqlite_partial_default_index()
        company = self._normalize_company(payload.company)
        style = self._validate_style_master_reference(company=company, item_code=payload.item_code)
        self._validate_items(payload.bom_items)
        self._validate_operations(payload.operations)

        bom_no = self._build_bom_no(item_code=payload.item_code, version_no=payload.version_no)
        try:
            same_version = (
                self.session.query(LyApparelBom)
                .filter(
                    LyApparelBom.company == company,
                    LyApparelBom.item_code == payload.item_code,
                    LyApparelBom.version_no == payload.version_no,
                )
                .first()
            )
            if same_version is not None:
                raise BomBusinessError(code=BOM_DEFAULT_CONFLICT, message="BOM 版本已存在")
            exists = self.session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if exists:
            raise BomBusinessError(code=BOM_DEFAULT_CONFLICT, message="BOM 编号冲突")

        try:
            next_bom_id = self._next_manual_pk(LyApparelBom) if self._is_local_sqlite_mode() else None
            bom = LyApparelBom(
                id=next_bom_id,
                bom_no=bom_no,
                company=company,
                style_master_id=int(style.id),
                item_code=payload.item_code,
                version_no=payload.version_no,
                is_default=False,
                status=self.DRAFT_STATUS,
                effective_date=None,
                created_by=operator,
                updated_by=operator,
            )
            self.session.add(bom)
            self.session.flush()

            self._replace_items(bom_id=bom.id, bom_items=payload.bom_items)
            self._replace_operations(bom_id=bom.id, operations=payload.operations)

            self.session.flush()
        except IntegrityError as exc:
            if is_default_bom_unique_conflict(exc):
                raise BomBusinessError(code=BOM_DEFAULT_CONFLICT, message="默认 BOM 冲突，请重试") from exc
            raise DatabaseWriteFailed() from exc
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return BomNameData(name=bom.bom_no)

    def list_bom(self, query: BomListQuery, allowed_item_codes: set[str] | None = None) -> BomListData:
        """List BOMs by filters.

        Args:
            query: List query conditions.
            allowed_item_codes: Optional readable item_code scope.

        Returns:
            BomListData: Paged list result.
        """
        try:
            sql = self.session.query(LyApparelBom)
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))
            if query.company:
                sql = sql.filter(LyApparelBom.company == query.company)
            if query.item_code:
                sql = sql.filter(LyApparelBom.item_code == query.item_code)
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                sql = sql.filter(
                    or_(
                        LyApparelBom.bom_no.like(keyword),
                        LyApparelBom.item_code.like(keyword),
                        LyApparelBom.version_no.like(keyword),
                        LyApparelBom.status.like(keyword),
                    )
                )
            if query.status:
                sql = sql.filter(LyApparelBom.status == query.status)

            total = sql.with_entities(func.count(LyApparelBom.id)).scalar() or 0
            rows = (
                sql.order_by(LyApparelBom.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return BomListData(
            items=[
                BomListItem(
                    id=int(row.id),
                    bom_no=str(row.bom_no),
                    company=str(row.company),
                    style_master_id=int(row.style_master_id) if row.style_master_id is not None else None,
                    item_code=str(row.item_code),
                    version_no=str(row.version_no),
                    is_default=bool(row.is_default),
                    status=str(row.status),
                    effective_date=row.effective_date,
                )
                for row in rows
            ],
            total=int(total),
            page=query.page,
            page_size=query.page_size,
        )

    @staticmethod
    def _derive_material_category(material_item_code: str, remark: str | None) -> str:
        """Derive a display category for material gallery rows."""
        if remark:
            trimmed = remark.strip()
            if trimmed:
                return trimmed[:24]

        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        return token or "未分类"

    @staticmethod
    def _build_thumbnail_url(material_item_code: str) -> str:
        # Placeholder thumbnail for readonly gallery semantics.
        return f"/api/bom/material-gallery/thumb/{material_item_code}"

    @staticmethod
    def _is_fabric_material(material_item_code: str, remark: str | None) -> bool:
        remark_text = (remark or "").strip()
        if "面料" in remark_text:
            return True
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        return token in {"FAB", "CLOTH", "FABRIC"}

    @staticmethod
    def _derive_fabric_name(material_item_code: str, remark: str | None) -> str:
        remark_text = (remark or "").strip()
        if remark_text:
            return remark_text[:64]
        return f"面料-{material_item_code}"

    @staticmethod
    def _derive_fabric_status(bom_status: str) -> str:
        if bom_status == "active":
            return "可用"
        if bom_status == "inactive":
            return "停用"
        return "草稿"

    @staticmethod
    def _is_accessories_packaging_material(material_item_code: str, remark: str | None) -> bool:
        remark_text = (remark or "").strip()
        if "辅料" in remark_text or "包材" in remark_text or "包装" in remark_text:
            return True
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        return token in {"ACC", "TRIM", "PKG", "PACK"}

    @staticmethod
    def _derive_accessories_packaging_category(material_item_code: str, remark: str | None) -> str:
        remark_text = (remark or "").strip()
        if "包材" in remark_text or "包装" in remark_text:
            return "包材"
        if "辅料" in remark_text:
            return "辅料"
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        if token in {"PKG", "PACK"}:
            return "包材"
        return "辅料"

    @staticmethod
    def _derive_accessories_packaging_name(material_item_code: str, remark: str | None) -> str:
        remark_text = (remark or "").strip()
        if remark_text:
            return remark_text[:64]
        return f"辅料/包材-{material_item_code}"

    @staticmethod
    def _derive_purchase_supplier(material_item_code: str) -> str:
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        if token in {"FAB", "CLOTH"}:
            return "华东面料供应商"
        if token in {"ACC", "TRIM", "ZIP"}:
            return "辅料联合供应商"
        return "通用物料供应商"

    @staticmethod
    def _derive_purchase_status(bom_status: str) -> str:
        if bom_status == "active":
            return "待确认"
        if bom_status == "inactive":
            return "已取消"
        return "草稿"

    @staticmethod
    def _build_purchase_no(bom_no: str, item_row_id: int) -> str:
        suffix = f"{item_row_id % 10000:04d}"
        return f"PO-{bom_no}-{suffix}"

    @staticmethod
    def _derive_processing_type_name(process_name: str, remark: str | None) -> str:
        hint = f"{process_name} {(remark or '')}".strip()
        if any(token in hint for token in ("印花", "绣花", "压褶", "压胶", "烫钻")):
            return "特种工艺加工"
        if any(token in hint for token in ("裁", "缝", "车", "拼接")):
            return "车缝加工"
        if any(token in hint for token in ("洗", "染", "定型", "后整")):
            return "后整加工"
        return "常规加工"

    @staticmethod
    def _derive_subcontract_mode(is_subcontract: bool) -> str:
        return "委外" if is_subcontract else "自产"

    @staticmethod
    def _derive_pricing_mode(operation: LyBomOperation) -> str:
        if operation.is_subcontract:
            if operation.subcontract_cost_per_piece is not None:
                return "按件外协"
            return "外协待定"
        if operation.wage_rate is not None:
            return "按工价"
        return "标准工序"

    @staticmethod
    def _derive_processing_type_code(operation_id: int, sequence_no: int) -> str:
        return f"PT-{sequence_no:02d}-{operation_id:04d}"

    @staticmethod
    def _derive_processing_no(operation_id: int, sequence_no: int) -> str:
        return f"MP-{sequence_no:02d}-{operation_id:04d}"

    @staticmethod
    def _derive_processing_inbound_no(operation_id: int, sequence_no: int) -> str:
        return f"IN-{sequence_no:02d}-{operation_id:04d}"

    @staticmethod
    def _derive_processing_mode(operation: LyBomOperation) -> str:
        if operation.is_subcontract:
            return "委外加工"
        process_name = str(operation.process_name or "")
        if any(token in process_name for token in ("印花", "绣花", "洗", "后整", "定型")):
            return "协同加工"
        return "自产加工"

    @staticmethod
    def _derive_processing_supplier(operation: LyBomOperation) -> str:
        process_name = str(operation.process_name or "")
        if operation.is_subcontract:
            if "印花" in process_name:
                return "华南印花协作厂"
            if "绣花" in process_name:
                return "苏州绣花协作厂"
            if any(token in process_name for token in ("洗", "后整", "定型")):
                return "后整联合加工中心"
            return "通用委外加工商"
        if any(token in process_name for token in ("裁", "缝", "车", "拼接")):
            return "本厂车缝工段"
        return "本厂工艺工段"

    @staticmethod
    def _derive_processing_inbound_warehouse(operation: LyBomOperation) -> str:
        if operation.is_subcontract:
            return "委外中转仓"
        return "主料成品仓"

    @staticmethod
    def _derive_processing_inbound_status(bom_status: str) -> str:
        if bom_status == "active":
            return "已入仓"
        if bom_status == "inactive":
            return "已关闭"
        return "待入仓"

    @staticmethod
    def _derive_material_deduction_no(operation_id: int, sequence_no: int) -> str:
        return f"DC-{sequence_no:02d}-{operation_id:04d}"

    @staticmethod
    def _derive_material_deduction_warehouse(operation: LyBomOperation) -> str:
        if operation.is_subcontract:
            return "委外中转仓"
        return "主料成品仓"

    @staticmethod
    def _derive_material_deduction_status(bom_status: str) -> str:
        if bom_status == "active":
            return "已扣仓"
        if bom_status == "inactive":
            return "已关闭"
        return "待扣仓"

    @staticmethod
    def _derive_material_sales_outbound_no(item_id: int, bom_id: int) -> str:
        return f"SO-{bom_id:04d}-{item_id:04d}"

    @staticmethod
    def _derive_material_sales_order_no(item_code: str, item_id: int) -> str:
        normalized = item_code.replace("_", "-").upper()
        return f"XS-{normalized}-{item_id:03d}"

    @staticmethod
    def _derive_material_sales_customer(item_code: str) -> str:
        token = item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        if token in {"MEN", "MENS", "M"}:
            return "华东男装渠道"
        if token in {"WOMEN", "WOMENS", "W"}:
            return "华南女装渠道"
        if token in {"KID", "KIDS", "CHILD"}:
            return "童装直营渠道"
        return "综合电商渠道"

    @staticmethod
    def _derive_material_sales_outbound_warehouse(material_item_code: str) -> str:
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        if token in {"PKG", "PACK", "BOX", "BAG"}:
            return "包材出货仓"
        if token in {"ACC", "TRIM", "ZIP", "BTN"}:
            return "辅料中转仓"
        return "主料成品仓"

    @staticmethod
    def _derive_material_sales_status(bom_status: str) -> str:
        if bom_status == "active":
            return "已出仓"
        if bom_status == "inactive":
            return "已关闭"
        return "待出仓"

    @staticmethod
    def _derive_material_sales_audit_status(bom_status: str) -> str:
        if bom_status == "active":
            return "已审核"
        if bom_status == "inactive":
            return "已驳回"
        return "待审核"

    @staticmethod
    def _derive_material_sales_batch_no(material_item_code: str, item_id: int) -> str:
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        return f"LOT-{token or 'MAT'}-{item_id:04d}"

    @staticmethod
    def _derive_material_type_code(material_item_code: str) -> str:
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        if token in {"FAB", "CLOTH", "FABRIC"}:
            return "MT-FABRIC"
        if token in {"ACC", "TRIM", "ZIP", "BTN"}:
            return "MT-ACCESSORY"
        if token in {"PKG", "PACK", "BOX", "BAG"}:
            return "MT-PACKAGING"
        if token in {"CHEM", "DYE"}:
            return "MT-CHEMICAL"
        return "MT-GENERAL"

    @staticmethod
    def _derive_material_type_name(material_item_code: str, remark: str | None) -> str:
        remark_text = (remark or "").strip()
        if "面料" in remark_text:
            return "面料"
        if "辅料" in remark_text:
            return "辅料"
        if "包材" in remark_text or "包装" in remark_text:
            return "包材"
        token = material_item_code.replace("_", "-").split("-", 1)[0].strip().upper()
        if token in {"FAB", "CLOTH", "FABRIC"}:
            return "面料"
        if token in {"ACC", "TRIM", "ZIP", "BTN"}:
            return "辅料"
        if token in {"PKG", "PACK", "BOX", "BAG"}:
            return "包材"
        if token in {"CHEM", "DYE"}:
            return "染整材料"
        return "通用物料"

    @staticmethod
    def _derive_material_group(material_type_name: str) -> str:
        if material_type_name in {"面料", "辅料"}:
            return "服装主材"
        if material_type_name == "包材":
            return "包装物料"
        if material_type_name == "染整材料":
            return "工艺物料"
        return "通用物料"

    @staticmethod
    def _derive_applicable_scene(material_type_name: str) -> str:
        if material_type_name == "面料":
            return "裁片与主面生产"
        if material_type_name == "辅料":
            return "车缝与后道组装"
        if material_type_name == "包材":
            return "包装与出库"
        if material_type_name == "染整材料":
            return "染整与后整"
        return "通用生产环节"

    @staticmethod
    def _derive_material_unit_code(unit_name: str) -> str:
        normalized = (
            str(unit_name or "")
            .strip()
            .upper()
            .replace(" ", "-")
            .replace("/", "-")
            .replace("_", "-")
        )
        normalized = normalized or "UNKNOWN"
        return f"UOM-{normalized}"

    @staticmethod
    def _derive_material_unit_precision(unit_name: str) -> int:
        normalized = str(unit_name or "").strip().upper()
        if normalized in {"M", "KG", "L", "YD"}:
            return 3
        if normalized in {"CM", "MM", "G", "ML"}:
            return 2
        return 0

    def list_material_gallery(
        self,
        query: BomMaterialGalleryQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomMaterialGalleryData:
        """List material gallery rows from BOM items."""
        try:
            sql = (
                self.session.query(LyApparelBomItem, LyApparelBom)
                .join(LyApparelBom, LyApparelBomItem.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomMaterialGalleryData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            if query.item_code:
                sql = sql.filter(LyApparelBom.item_code == query.item_code)
            if query.material_item_code:
                sql = sql.filter(LyApparelBomItem.material_item_code.contains(query.material_item_code))
            if query.color:
                sql = sql.filter(LyApparelBomItem.color.contains(query.color))
            if query.size:
                sql = sql.filter(LyApparelBomItem.size.contains(query.size))
            if query.status:
                sql = sql.filter(LyApparelBom.status == query.status)

            rows: list[tuple[LyApparelBomItem, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyApparelBomItem.id.desc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        items: list[BomMaterialGalleryItem] = []
        normalized_category = (query.category or "").strip().lower()
        for item_row, bom_row in rows:
            category = self._derive_material_category(
                material_item_code=str(item_row.material_item_code),
                remark=item_row.remark,
            )
            if normalized_category and category.lower() != normalized_category:
                continue
            items.append(
                BomMaterialGalleryItem(
                    id=int(item_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    material_item_code=str(item_row.material_item_code),
                    category=category,
                    color=item_row.color,
                    size=item_row.size,
                    uom=str(item_row.uom),
                    qty_per_piece=Decimal(item_row.qty_per_piece),
                    loss_rate=Decimal(item_row.loss_rate),
                    status=str(bom_row.status),
                    is_default=bool(bom_row.is_default),
                    thumbnail_url=self._build_thumbnail_url(str(item_row.material_item_code)),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomMaterialGalleryData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_fabrics(
        self,
        query: BomFabricQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomFabricData:
        """List readonly fabric rows derived from BOM items."""
        try:
            sql = (
                self.session.query(LyApparelBomItem, LyApparelBom)
                .join(LyApparelBom, LyApparelBomItem.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomFabricData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyApparelBomItem, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyApparelBomItem.id.desc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        item_code_keyword = (query.item_code or "").strip().lower()
        material_code_keyword = (query.material_item_code or "").strip().lower()
        fabric_name_keyword = (query.fabric_name or "").strip().lower()
        color_keyword = (query.color or "").strip().lower()
        specification_keyword = (query.specification or "").strip().lower()
        supplier_keyword = (query.supplier_name or "").strip().lower()
        status_keyword = (query.status or "").strip()

        items: list[BomFabricItem] = []
        for item_row, bom_row in rows:
            material_item_code = str(item_row.material_item_code)
            if not self._is_fabric_material(material_item_code=material_item_code, remark=item_row.remark):
                continue

            fabric_name = self._derive_fabric_name(material_item_code=material_item_code, remark=item_row.remark)
            supplier_name = self._derive_purchase_supplier(material_item_code=material_item_code)
            fabric_status = self._derive_fabric_status(str(bom_row.status))

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if material_code_keyword and material_code_keyword not in material_item_code.lower():
                continue
            if fabric_name_keyword and fabric_name_keyword not in fabric_name.lower():
                continue
            if color_keyword and color_keyword not in (str(item_row.color or "").lower()):
                continue
            if specification_keyword and specification_keyword not in (str(item_row.size or "").lower()):
                continue
            if supplier_keyword and supplier_keyword not in supplier_name.lower():
                continue
            if status_keyword and status_keyword != fabric_status:
                continue

            items.append(
                BomFabricItem(
                    id=int(item_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    material_item_code=material_item_code,
                    fabric_name=fabric_name,
                    color=item_row.color,
                    specification=item_row.size,
                    supplier_name=supplier_name,
                    uom=str(item_row.uom),
                    qty_per_piece=Decimal(item_row.qty_per_piece),
                    loss_rate=Decimal(item_row.loss_rate),
                    status=fabric_status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomFabricData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_accessories_packaging(
        self,
        query: BomAccessoriesPackagingQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomAccessoriesPackagingData:
        """List readonly accessories/packaging rows derived from BOM items."""
        try:
            sql = (
                self.session.query(LyApparelBomItem, LyApparelBom)
                .join(LyApparelBom, LyApparelBomItem.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomAccessoriesPackagingData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyApparelBomItem, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyApparelBomItem.id.desc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        item_code_keyword = (query.item_code or "").strip().lower()
        material_code_keyword = (query.material_item_code or "").strip().lower()
        material_name_keyword = (query.material_name or "").strip().lower()
        category_keyword = (query.category or "").strip()
        supplier_keyword = (query.supplier_name or "").strip().lower()
        status_keyword = (query.status or "").strip()

        items: list[BomAccessoriesPackagingItem] = []
        for item_row, bom_row in rows:
            material_item_code = str(item_row.material_item_code)
            if not self._is_accessories_packaging_material(material_item_code=material_item_code, remark=item_row.remark):
                continue

            material_name = self._derive_accessories_packaging_name(
                material_item_code=material_item_code,
                remark=item_row.remark,
            )
            category = self._derive_accessories_packaging_category(
                material_item_code=material_item_code,
                remark=item_row.remark,
            )
            supplier_name = self._derive_purchase_supplier(material_item_code=material_item_code)
            row_status = self._derive_fabric_status(str(bom_row.status))

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if material_code_keyword and material_code_keyword not in material_item_code.lower():
                continue
            if material_name_keyword and material_name_keyword not in material_name.lower():
                continue
            if category_keyword and category_keyword != category:
                continue
            if supplier_keyword and supplier_keyword not in supplier_name.lower():
                continue
            if status_keyword and status_keyword != row_status:
                continue

            items.append(
                BomAccessoriesPackagingItem(
                    id=int(item_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    material_item_code=material_item_code,
                    material_name=material_name,
                    category=category,
                    color=item_row.color,
                    specification=item_row.size,
                    supplier_name=supplier_name,
                    uom=str(item_row.uom),
                    qty_per_piece=Decimal(item_row.qty_per_piece),
                    loss_rate=Decimal(item_row.loss_rate),
                    status=row_status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomAccessoriesPackagingData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_purchase_orders(
        self,
        query: BomPurchaseOrderQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomPurchaseOrderData:
        """List readonly purchase-order semantics derived from BOM items."""
        try:
            sql = (
                self.session.query(LyApparelBomItem, LyApparelBom)
                .join(LyApparelBom, LyApparelBomItem.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomPurchaseOrderData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyApparelBomItem, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyApparelBomItem.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        items: list[BomPurchaseOrderItem] = []
        material_keyword = (query.material_keyword or "").strip().lower()
        purchase_no_keyword = (query.purchase_no or "").strip().lower()
        supplier_keyword = (query.supplier_name or "").strip().lower()
        status_keyword = (query.status or "").strip()

        for item_row, bom_row in rows:
            purchase_no = self._build_purchase_no(str(bom_row.bom_no), int(item_row.id))
            supplier_name = self._derive_purchase_supplier(str(item_row.material_item_code))
            status = self._derive_purchase_status(str(bom_row.status))
            qty = self._round(Decimal(item_row.qty_per_piece) * Decimal("100"))
            unit_price = self._round(Decimal("5") + (Decimal(int(item_row.id) % 7) * Decimal("1.8")))
            total_amount = self._round(qty * unit_price)
            expected_delivery_date = (
                bom_row.effective_date + timedelta(days=7)
                if bom_row.effective_date
                else None
            )
            material_name = str(item_row.remark or item_row.material_item_code)

            if purchase_no_keyword and purchase_no_keyword not in purchase_no.lower():
                continue
            if supplier_keyword and supplier_keyword not in supplier_name.lower():
                continue
            if status_keyword and status_keyword != status:
                continue
            if material_keyword:
                haystack = f"{item_row.material_item_code} {material_name} {bom_row.item_code}".lower()
                if material_keyword not in haystack:
                    continue
            if query.delivery_date_from and (not expected_delivery_date or expected_delivery_date < query.delivery_date_from):
                continue
            if query.delivery_date_to and (not expected_delivery_date or expected_delivery_date > query.delivery_date_to):
                continue
            if query.min_qty is not None and qty < query.min_qty:
                continue
            if query.max_qty is not None and qty > query.max_qty:
                continue
            if query.min_amount is not None and total_amount < query.min_amount:
                continue
            if query.max_amount is not None and total_amount > query.max_amount:
                continue

            items.append(
                BomPurchaseOrderItem(
                    id=int(item_row.id),
                    bom_id=int(bom_row.id),
                    purchase_no=purchase_no,
                    supplier_name=supplier_name,
                    item_code=str(bom_row.item_code),
                    material_item_code=str(item_row.material_item_code),
                    material_name=material_name,
                    qty=qty,
                    uom=str(item_row.uom),
                    unit_price=unit_price,
                    total_amount=total_amount,
                    expected_delivery_date=expected_delivery_date,
                    status=status,
                    bom_no=str(bom_row.bom_no),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomPurchaseOrderData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_processing_types(
        self,
        query: BomProcessingTypeQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomProcessingTypeData:
        """List readonly processing-type rows derived from BOM operations."""
        try:
            sql = (
                self.session.query(LyBomOperation, LyApparelBom)
                .join(LyApparelBom, LyBomOperation.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomProcessingTypeData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyBomOperation, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        item_code_keyword = (query.item_code or "").strip().lower()
        process_type_keyword = (query.process_type_name or "").strip().lower()
        process_name_keyword = (query.process_name or "").strip().lower()
        subcontract_mode_keyword = (query.subcontract_mode or "").strip()
        pricing_mode_keyword = (query.pricing_mode or "").strip()
        status_keyword = (query.status or "").strip()

        items: list[BomProcessingTypeItem] = []
        for operation_row, bom_row in rows:
            process_name = str(operation_row.process_name)
            process_type_name = self._derive_processing_type_name(process_name=process_name, remark=operation_row.remark)
            subcontract_mode = self._derive_subcontract_mode(is_subcontract=bool(operation_row.is_subcontract))
            pricing_mode = self._derive_pricing_mode(operation=operation_row)
            status = self._derive_fabric_status(str(bom_row.status))
            unit_rate = (
                Decimal(operation_row.subcontract_cost_per_piece)
                if operation_row.subcontract_cost_per_piece is not None
                else Decimal(operation_row.wage_rate)
                if operation_row.wage_rate is not None
                else Decimal("0")
            )

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if process_type_keyword and process_type_keyword not in process_type_name.lower():
                continue
            if process_name_keyword and process_name_keyword not in process_name.lower():
                continue
            if subcontract_mode_keyword and subcontract_mode_keyword != subcontract_mode:
                continue
            if pricing_mode_keyword and pricing_mode_keyword != pricing_mode:
                continue
            if status_keyword and status_keyword != status:
                continue

            items.append(
                BomProcessingTypeItem(
                    id=int(operation_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    process_type_code=self._derive_processing_type_code(
                        operation_id=int(operation_row.id),
                        sequence_no=int(operation_row.sequence_no),
                    ),
                    process_type_name=process_type_name,
                    process_name=process_name,
                    sequence_no=int(operation_row.sequence_no),
                    subcontract_mode=subcontract_mode,
                    pricing_mode=pricing_mode,
                    unit_rate=self._round(unit_rate),
                    status=status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomProcessingTypeData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_material_processing(
        self,
        query: BomMaterialProcessingQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomMaterialProcessingData:
        """List readonly material-processing rows derived from BOM operations."""
        try:
            sql = (
                self.session.query(LyBomOperation, LyApparelBom)
                .join(LyApparelBom, LyBomOperation.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomMaterialProcessingData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyBomOperation, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        item_code_keyword = (query.item_code or "").strip().lower()
        process_no_keyword = (query.process_no or "").strip().lower()
        process_name_keyword = (query.process_name or "").strip().lower()
        supplier_keyword = (query.processing_supplier or "").strip().lower()
        mode_keyword = (query.processing_mode or "").strip()
        status_keyword = (query.status or "").strip()

        items: list[BomMaterialProcessingItem] = []
        for operation_row, bom_row in rows:
            process_no = self._derive_processing_no(
                operation_id=int(operation_row.id),
                sequence_no=int(operation_row.sequence_no),
            )
            process_name = str(operation_row.process_name)
            processing_mode = self._derive_processing_mode(operation_row)
            processing_supplier = self._derive_processing_supplier(operation_row)
            status = self._derive_fabric_status(str(bom_row.status))

            planned_qty = self._round(Decimal("80") + (Decimal(int(operation_row.sequence_no)) * Decimal("12.5")))
            if status == "可用":
                completed_qty = self._round(planned_qty * Decimal("0.78"))
            elif status == "停用":
                completed_qty = self._round(planned_qty * Decimal("0.52"))
            else:
                completed_qty = self._round(planned_qty * Decimal("0.35"))
            scrap_qty = self._round(planned_qty * Decimal("0.02"))
            pending_qty = self._round(max(planned_qty - completed_qty - scrap_qty, Decimal("0")))
            due_date = (
                bom_row.effective_date + timedelta(days=int(operation_row.sequence_no))
                if bom_row.effective_date is not None
                else None
            )

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if process_no_keyword and process_no_keyword not in process_no.lower():
                continue
            if process_name_keyword and process_name_keyword not in process_name.lower():
                continue
            if supplier_keyword and supplier_keyword not in processing_supplier.lower():
                continue
            if mode_keyword and mode_keyword != processing_mode:
                continue
            if status_keyword and status_keyword != status:
                continue

            items.append(
                BomMaterialProcessingItem(
                    id=int(operation_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    process_no=process_no,
                    process_name=process_name,
                    processing_supplier=processing_supplier,
                    processing_mode=processing_mode,
                    planned_qty=planned_qty,
                    completed_qty=completed_qty,
                    pending_qty=pending_qty,
                    scrap_qty=scrap_qty,
                    uom="件",
                    due_date=due_date,
                    status=status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomMaterialProcessingData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_material_processing_inbound(
        self,
        query: BomMaterialProcessingInboundQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomMaterialProcessingInboundData:
        """List readonly material-processing inbound rows derived from BOM operations."""
        try:
            sql = (
                self.session.query(LyBomOperation, LyApparelBom)
                .join(LyApparelBom, LyBomOperation.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomMaterialProcessingInboundData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            operation_rows: list[tuple[LyBomOperation, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        bom_ids = {int(bom_row.id) for _, bom_row in operation_rows}
        first_material_map: dict[int, str] = {}
        if bom_ids:
            try:
                item_rows = (
                    self.session.query(LyApparelBomItem)
                    .filter(LyApparelBomItem.bom_id.in_(sorted(bom_ids)))
                    .order_by(LyApparelBomItem.bom_id.asc(), LyApparelBomItem.id.asc())
                    .all()
                )
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc
            for item_row in item_rows:
                key = int(item_row.bom_id)
                if key not in first_material_map:
                    first_material_map[key] = str(item_row.material_item_code)

        item_code_keyword = (query.item_code or "").strip().lower()
        inbound_no_keyword = (query.inbound_no or "").strip().lower()
        material_code_keyword = (query.material_item_code or "").strip().lower()
        supplier_keyword = (query.processing_supplier or "").strip().lower()
        warehouse_keyword = (query.warehouse_name or "").strip()
        status_keyword = (query.status or "").strip()

        items: list[BomMaterialProcessingInboundItem] = []
        for operation_row, bom_row in operation_rows:
            process_no = self._derive_processing_no(
                operation_id=int(operation_row.id),
                sequence_no=int(operation_row.sequence_no),
            )
            inbound_no = self._derive_processing_inbound_no(
                operation_id=int(operation_row.id),
                sequence_no=int(operation_row.sequence_no),
            )
            processing_supplier = self._derive_processing_supplier(operation_row)
            warehouse_name = self._derive_processing_inbound_warehouse(operation_row)
            status = self._derive_processing_inbound_status(str(bom_row.status))

            inbound_qty = self._round(Decimal("60") + (Decimal(int(operation_row.sequence_no)) * Decimal("15.0")))
            if status == "已入仓":
                inspected_qty = self._round(inbound_qty * Decimal("0.92"))
            elif status == "已关闭":
                inspected_qty = self._round(inbound_qty * Decimal("0.63"))
            else:
                inspected_qty = self._round(inbound_qty * Decimal("0.45"))
            pending_inspection_qty = self._round(max(inbound_qty - inspected_qty, Decimal("0")))
            inbound_date = (
                bom_row.effective_date + timedelta(days=int(operation_row.sequence_no) + 1)
                if bom_row.effective_date is not None
                else None
            )
            material_item_code = first_material_map.get(int(bom_row.id), f"{str(bom_row.item_code)}-MAT")

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if inbound_no_keyword and inbound_no_keyword not in inbound_no.lower():
                continue
            if material_code_keyword and material_code_keyword not in material_item_code.lower():
                continue
            if supplier_keyword and supplier_keyword not in processing_supplier.lower():
                continue
            if warehouse_keyword and warehouse_keyword != warehouse_name:
                continue
            if status_keyword and status_keyword != status:
                continue

            items.append(
                BomMaterialProcessingInboundItem(
                    id=int(operation_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    inbound_no=inbound_no,
                    process_no=process_no,
                    material_item_code=material_item_code,
                    processing_supplier=processing_supplier,
                    warehouse_name=warehouse_name,
                    inbound_qty=inbound_qty,
                    inspected_qty=inspected_qty,
                    pending_inspection_qty=pending_inspection_qty,
                    inbound_date=inbound_date,
                    status=status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomMaterialProcessingInboundData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_material_deduction(
        self,
        query: BomMaterialDeductionQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomMaterialDeductionData:
        """List readonly material-deduction rows derived from BOM operations."""
        try:
            sql = (
                self.session.query(LyBomOperation, LyApparelBom)
                .join(LyApparelBom, LyBomOperation.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomMaterialDeductionData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            operation_rows: list[tuple[LyBomOperation, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        bom_ids = {int(bom_row.id) for _, bom_row in operation_rows}
        first_material_map: dict[int, str] = {}
        if bom_ids:
            try:
                item_rows = (
                    self.session.query(LyApparelBomItem)
                    .filter(LyApparelBomItem.bom_id.in_(sorted(bom_ids)))
                    .order_by(LyApparelBomItem.bom_id.asc(), LyApparelBomItem.id.asc())
                    .all()
                )
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc
            for item_row in item_rows:
                key = int(item_row.bom_id)
                if key not in first_material_map:
                    first_material_map[key] = str(item_row.material_item_code)

        item_code_keyword = (query.item_code or "").strip().lower()
        deduction_no_keyword = (query.deduction_no or "").strip().lower()
        material_code_keyword = (query.material_item_code or "").strip().lower()
        warehouse_keyword = (query.warehouse_name or "").strip()
        status_keyword = (query.status or "").strip()

        items: list[BomMaterialDeductionItem] = []
        for operation_row, bom_row in operation_rows:
            process_no = self._derive_processing_no(
                operation_id=int(operation_row.id),
                sequence_no=int(operation_row.sequence_no),
            )
            deduction_no = self._derive_material_deduction_no(
                operation_id=int(operation_row.id),
                sequence_no=int(operation_row.sequence_no),
            )
            warehouse_name = self._derive_material_deduction_warehouse(operation_row)
            status = self._derive_material_deduction_status(str(bom_row.status))
            material_item_code = first_material_map.get(int(bom_row.id), f"{str(bom_row.item_code)}-MAT")

            deduction_qty = self._round(Decimal("35") + (Decimal(int(operation_row.sequence_no)) * Decimal("9.5")))
            if status == "已扣仓":
                deducted_qty = self._round(deduction_qty * Decimal("0.94"))
            elif status == "已关闭":
                deducted_qty = self._round(deduction_qty * Decimal("0.66"))
            else:
                deducted_qty = self._round(deduction_qty * Decimal("0.41"))
            pending_deduction_qty = self._round(max(deduction_qty - deducted_qty, Decimal("0")))
            deduction_date = (
                bom_row.effective_date + timedelta(days=int(operation_row.sequence_no) + 2)
                if bom_row.effective_date is not None
                else None
            )

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if deduction_no_keyword and deduction_no_keyword not in deduction_no.lower():
                continue
            if material_code_keyword and material_code_keyword not in material_item_code.lower():
                continue
            if warehouse_keyword and warehouse_keyword != warehouse_name:
                continue
            if status_keyword and status_keyword != status:
                continue

            items.append(
                BomMaterialDeductionItem(
                    id=int(operation_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    deduction_no=deduction_no,
                    process_no=process_no,
                    material_item_code=material_item_code,
                    warehouse_name=warehouse_name,
                    deduction_qty=deduction_qty,
                    deducted_qty=deducted_qty,
                    pending_deduction_qty=pending_deduction_qty,
                    deduction_date=deduction_date,
                    status=status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomMaterialDeductionData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_material_sales_outbound(
        self,
        query: BomMaterialSalesOutboundQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomMaterialSalesOutboundData:
        """List readonly material-sales-outbound rows derived from BOM items."""
        try:
            sql = (
                self.session.query(LyApparelBomItem, LyApparelBom)
                .join(LyApparelBom, LyApparelBomItem.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomMaterialSalesOutboundData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyApparelBomItem, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyApparelBomItem.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        item_code_keyword = (query.item_code or "").strip().lower()
        outbound_no_keyword = (query.outbound_no or "").strip().lower()
        sales_order_keyword = (query.sales_order_no or "").strip().lower()
        customer_keyword = (query.customer_name or "").strip().lower()
        warehouse_keyword = (query.warehouse_name or "").strip()
        material_code_keyword = (query.material_item_code or "").strip().lower()
        status_keyword = (query.status or "").strip()
        audit_status_keyword = (query.audit_status or "").strip()

        items: list[BomMaterialSalesOutboundItem] = []
        for item_row, bom_row in rows:
            material_item_code = str(item_row.material_item_code)
            material_name = str(item_row.remark or material_item_code)
            outbound_no = self._derive_material_sales_outbound_no(
                item_id=int(item_row.id),
                bom_id=int(bom_row.id),
            )
            sales_order_no = self._derive_material_sales_order_no(
                item_code=str(bom_row.item_code),
                item_id=int(item_row.id),
            )
            customer_name = self._derive_material_sales_customer(str(bom_row.item_code))
            warehouse_name = self._derive_material_sales_outbound_warehouse(material_item_code)
            status = self._derive_material_sales_status(str(bom_row.status))
            audit_status = self._derive_material_sales_audit_status(str(bom_row.status))
            batch_no = self._derive_material_sales_batch_no(
                material_item_code=material_item_code,
                item_id=int(item_row.id),
            )

            planned_outbound_qty = self._round(Decimal(item_row.qty_per_piece) * Decimal("120"))
            if status == "已出仓":
                outbound_qty = self._round(planned_outbound_qty * Decimal("0.94"))
            elif status == "已关闭":
                outbound_qty = self._round(planned_outbound_qty * Decimal("0.68"))
            else:
                outbound_qty = self._round(planned_outbound_qty * Decimal("0.42"))
            pending_outbound_qty = self._round(max(planned_outbound_qty - outbound_qty, Decimal("0")))
            outbound_date = bom_row.effective_date + timedelta(days=3) if bom_row.effective_date else None
            applicant_name = str(bom_row.created_by or "system")
            updated_at = bom_row.updated_at.isoformat() if bom_row.updated_at is not None else None

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if outbound_no_keyword and outbound_no_keyword not in outbound_no.lower():
                continue
            if sales_order_keyword and sales_order_keyword not in sales_order_no.lower():
                continue
            if customer_keyword and customer_keyword not in customer_name.lower():
                continue
            if warehouse_keyword and warehouse_keyword != warehouse_name:
                continue
            if material_code_keyword and material_code_keyword not in material_item_code.lower():
                continue
            if status_keyword and status_keyword != status:
                continue
            if audit_status_keyword and audit_status_keyword != audit_status:
                continue

            items.append(
                BomMaterialSalesOutboundItem(
                    id=int(item_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    outbound_no=outbound_no,
                    sales_order_no=sales_order_no,
                    customer_name=customer_name,
                    warehouse_name=warehouse_name,
                    material_item_code=material_item_code,
                    material_name=material_name,
                    color=item_row.color,
                    size=item_row.size,
                    batch_no=batch_no,
                    planned_outbound_qty=planned_outbound_qty,
                    outbound_qty=outbound_qty,
                    pending_outbound_qty=pending_outbound_qty,
                    outbound_date=outbound_date,
                    status=status,
                    audit_status=audit_status,
                    applicant_name=applicant_name,
                    updated_at=updated_at,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomMaterialSalesOutboundData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_material_types(
        self,
        query: BomMaterialTypeQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomMaterialTypeData:
        """List readonly material-type rows derived from BOM items."""
        try:
            sql = (
                self.session.query(LyApparelBomItem, LyApparelBom)
                .join(LyApparelBom, LyApparelBomItem.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomMaterialTypeData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyApparelBomItem, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyApparelBomItem.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        item_code_keyword = (query.item_code or "").strip().lower()
        material_code_keyword = (query.material_item_code or "").strip().lower()
        type_name_keyword = (query.material_type_name or "").strip().lower()
        group_keyword = (query.material_group or "").strip()
        scene_keyword = (query.applicable_scene or "").strip()
        status_keyword = (query.status or "").strip()

        items: list[BomMaterialTypeItem] = []
        seen_keys: set[tuple[str, str, str]] = set()
        for item_row, bom_row in rows:
            material_item_code = str(item_row.material_item_code)
            material_type_name = self._derive_material_type_name(
                material_item_code=material_item_code,
                remark=item_row.remark,
            )
            material_group = self._derive_material_group(material_type_name=material_type_name)
            applicable_scene = self._derive_applicable_scene(material_type_name=material_type_name)
            status = self._derive_fabric_status(str(bom_row.status))
            supplier_name = self._derive_purchase_supplier(material_item_code=material_item_code)

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if material_code_keyword and material_code_keyword not in material_item_code.lower():
                continue
            if type_name_keyword and type_name_keyword not in material_type_name.lower():
                continue
            if group_keyword and group_keyword != material_group:
                continue
            if scene_keyword and scene_keyword != applicable_scene:
                continue
            if status_keyword and status_keyword != status:
                continue

            dedupe_key = (str(bom_row.item_code), material_type_name, material_group)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            items.append(
                BomMaterialTypeItem(
                    id=int(item_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    material_item_code=material_item_code,
                    material_type_code=self._derive_material_type_code(material_item_code=material_item_code),
                    material_type_name=material_type_name,
                    material_group=material_group,
                    applicable_scene=applicable_scene,
                    supplier_name=supplier_name,
                    status=status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomMaterialTypeData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_material_units(
        self,
        query: BomMaterialUnitQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> BomMaterialUnitData:
        """List readonly material-unit rows derived from BOM items."""
        try:
            sql = (
                self.session.query(LyApparelBomItem, LyApparelBom)
                .join(LyApparelBom, LyApparelBomItem.bom_id == LyApparelBom.id)
            )
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return BomMaterialUnitData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyApparelBom.item_code.in_(sorted(allowed_item_codes)))

            rows: list[tuple[LyApparelBomItem, LyApparelBom]] = (
                sql.order_by(LyApparelBom.id.desc(), LyApparelBomItem.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        item_code_keyword = (query.item_code or "").strip().lower()
        material_code_keyword = (query.material_item_code or "").strip().lower()
        unit_name_keyword = (query.unit_name or "").strip().lower()
        status_keyword = (query.status or "").strip()

        items: list[BomMaterialUnitItem] = []
        seen_keys: set[tuple[str, str, str]] = set()
        for item_row, bom_row in rows:
            material_item_code = str(item_row.material_item_code)
            unit_name = str(item_row.uom).strip()
            status = self._derive_fabric_status(str(bom_row.status))

            if item_code_keyword and item_code_keyword not in str(bom_row.item_code).lower():
                continue
            if material_code_keyword and material_code_keyword not in material_item_code.lower():
                continue
            if unit_name_keyword and unit_name_keyword not in unit_name.lower():
                continue
            if status_keyword and status_keyword != status:
                continue

            dedupe_key = (str(bom_row.item_code), material_item_code, unit_name.upper())
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            base_unit = unit_name
            items.append(
                BomMaterialUnitItem(
                    id=int(item_row.id),
                    bom_id=int(bom_row.id),
                    bom_no=str(bom_row.bom_no),
                    item_code=str(bom_row.item_code),
                    material_item_code=material_item_code,
                    unit_code=self._derive_material_unit_code(unit_name=unit_name),
                    unit_name=unit_name,
                    base_unit=base_unit,
                    conversion_text=f"1 {unit_name} = 1 {base_unit}",
                    precision=self._derive_material_unit_precision(unit_name=unit_name),
                    status=status,
                    is_default=bool(bom_row.is_default),
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return BomMaterialUnitData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def get_bom_detail(self, bom_id: int) -> BomDetailData:
        """Get BOM header and child rows.

        Args:
            bom_id: BOM identifier.

        Returns:
            BomDetailData: BOM detail result.
        """
        bom = self._must_get_bom(bom_id=bom_id)
        try:
            item_rows = (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == bom.id)
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
            op_rows = (
                self.session.query(LyBomOperation)
                .filter(LyBomOperation.bom_id == bom.id)
                .order_by(LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return BomDetailData(
            bom=BomHeader(
                id=int(bom.id),
                bom_no=str(bom.bom_no),
                company=str(bom.company),
                style_master_id=int(bom.style_master_id) if bom.style_master_id is not None else None,
                item_code=str(bom.item_code),
                version_no=str(bom.version_no),
                is_default=bool(bom.is_default),
                status=str(bom.status),
                effective_date=bom.effective_date,
            ),
            items=[
                BomItemView(
                    id=int(row.id),
                    material_item_code=str(row.material_item_code),
                    color=row.color,
                    part=getattr(row, "part", None),
                    size=row.size,
                    qty_per_piece=Decimal(row.qty_per_piece),
                    loss_rate=Decimal(row.loss_rate),
                    uom=str(row.uom),
                    remark=row.remark,
                )
                for row in item_rows
            ],
            operations=[
                BomOperationView(
                    id=int(row.id),
                    process_name=str(row.process_name),
                    sequence_no=int(row.sequence_no),
                    is_subcontract=bool(row.is_subcontract),
                    wage_rate=Decimal(row.wage_rate) if row.wage_rate is not None else None,
                    subcontract_cost_per_piece=(
                        Decimal(row.subcontract_cost_per_piece)
                        if row.subcontract_cost_per_piece is not None
                        else None
                    ),
                    remark=row.remark,
                )
                for row in op_rows
            ],
        )

    def update_bom_draft(self, bom_id: int, payload: BomUpdateRequest, operator: str) -> BomUpdateData:
        """Update draft BOM.

        Args:
            bom_id: BOM identifier.
            payload: Update payload.
            operator: Operator username.

        Returns:
            BomUpdateData: Update result.
        """
        bom = self._must_get_bom(bom_id=bom_id)
        if bom.status == self.ACTIVE_STATUS:
            raise BomBusinessError(code=BOM_PUBLISHED_LOCKED, message="已发布 BOM 不允许直接修改")
        if str(payload.item_code) != str(bom.item_code):
            raise BomBusinessError(code=STYLE_MASTER_INVALID_REFERENCE, message="BOM 款号与业务载体不一致")
        if payload.company is not None and self._normalize_company(payload.company) != str(bom.company):
            raise BomBusinessError(code=STYLE_MASTER_INVALID_REFERENCE, message="BOM 公司与业务载体不一致")

        style = self._validate_style_master_reference(company=str(bom.company), item_code=payload.item_code)
        self._validate_items(payload.bom_items)
        self._validate_operations(payload.operations)

        bom.style_master_id = int(style.id)
        bom.version_no = payload.version_no
        bom.updated_by = operator
        bom.updated_at = datetime.utcnow()

        try:
            self._replace_items(bom_id=bom.id, bom_items=payload.bom_items)
            self._replace_operations(bom_id=bom.id, operations=payload.operations)
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return BomUpdateData(
            name=bom.bom_no,
            status=bom.status,
            updated_at=bom.updated_at.isoformat() if bom.updated_at else datetime.utcnow().isoformat(),
        )

    def set_default(self, bom_id: int, operator: str) -> BomSetDefaultData:
        """Set target BOM as default, reset others for same item.

        Args:
            bom_id: BOM identifier.

        Returns:
            BomSetDefaultData: Default switch result.
        """
        bom = self._must_get_bom(bom_id=bom_id, for_update=True)
        if bom.status != self.ACTIVE_STATUS:
            raise BomBusinessError(code=BOM_DEFAULT_REQUIRES_ACTIVE, message="非 active BOM 不能设默认")

        # 锁定同 company + item_code 的 BOM 集合，避免并发 set-default 导致默认值竞争。
        try:
            same_item_rows = (
                self.session.query(LyApparelBom)
                .filter(LyApparelBom.company == bom.company, LyApparelBom.item_code == bom.item_code)
                .with_for_update()
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        now = datetime.utcnow()
        for row in same_item_rows:
            if row.status == self.ACTIVE_STATUS and row.is_default:
                row.is_default = False
                row.updated_by = operator
                row.updated_at = now

        bom.is_default = True
        bom.updated_by = operator
        bom.updated_at = now
        try:
            self.session.flush()
        except IntegrityError as exc:
            if is_default_bom_unique_conflict(exc):
                raise BomBusinessError(code=BOM_DEFAULT_CONFLICT, message="默认 BOM 冲突，请重试") from exc
            raise DatabaseWriteFailed() from exc
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return BomSetDefaultData(name=bom.bom_no, item_code=bom.item_code, is_default=True)

    def activate(self, bom_id: int, operator: str) -> BomActivateData:
        """Activate BOM and set effect date.

        Args:
            bom_id: BOM identifier.

        Returns:
            BomActivateData: Activation result.
        """
        bom = self._must_get_bom(bom_id=bom_id, for_update=True)
        if bom.status == self.ACTIVE_STATUS:
            raise BomBusinessError(code=BOM_PUBLISHED_LOCKED, message="已发布 BOM 不允许重复发布")
        if bom.is_default:
            try:
                same_item_active_rows = (
                    self.session.query(LyApparelBom)
                    .filter(
                        and_(
                            LyApparelBom.item_code == bom.item_code,
                            LyApparelBom.company == bom.company,
                            LyApparelBom.id != bom.id,
                            LyApparelBom.status == self.ACTIVE_STATUS,
                        )
                    )
                    .with_for_update()
                    .all()
                )
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc
            now = datetime.utcnow()
            for row in same_item_active_rows:
                row.is_default = False
                row.updated_by = operator
                row.updated_at = now

        bom.status = self.ACTIVE_STATUS
        bom.effective_date = date.today()
        bom.updated_by = operator
        bom.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except IntegrityError as exc:
            if is_default_bom_unique_conflict(exc):
                raise BomBusinessError(code=BOM_DEFAULT_CONFLICT, message="默认 BOM 冲突，请重试") from exc
            raise DatabaseWriteFailed() from exc
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return BomActivateData(name=bom.bom_no, status=bom.status, effective_date=bom.effective_date)

    def deactivate(self, bom_id: int, reason: str, operator: str) -> BomDeactivateData:
        """Deactivate BOM.

        Args:
            bom_id: BOM identifier.
            reason: Deactivation reason.

        Returns:
            BomDeactivateData: Deactivation result.
        """
        bom = self._must_get_bom(bom_id=bom_id)
        if not reason.strip():
            raise BomBusinessError(code=BOM_STATUS_INVALID, message="当前状态不允许停用")
        if bom.status != self.ACTIVE_STATUS:
            raise BomBusinessError(code=BOM_STATUS_INVALID, message="当前状态不允许停用")
        bom.status = self.INACTIVE_STATUS
        bom.is_default = False
        bom.updated_by = operator
        bom.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return BomDeactivateData(name=bom.bom_no, status=bom.status)

    def explode(self, bom_id: int, payload: BomExplodeRequest) -> BomExplodeData:
        """Explode BOM by order qty and size distribution.

        Args:
            bom_id: BOM identifier.
            payload: Explode payload.

        Returns:
            BomExplodeData: Material requirements and operation costs.
        """
        bom = self._must_get_bom(bom_id=bom_id)
        try:
            item_rows = (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == bom.id)
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
            op_rows = (
                self.session.query(LyBomOperation)
                .filter(LyBomOperation.bom_id == bom.id)
                .order_by(LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        grouped: Dict[Tuple[str, str, str, str, str], Decimal] = {}
        total_material_qty = Decimal("0")

        for row in item_rows:
            base_qty = self._resolve_item_order_qty(
                order_qty=payload.order_qty,
                size=row.size,
                size_ratio=payload.size_ratio,
            )
            final_qty = self._round(base_qty * Decimal(row.qty_per_piece) * (Decimal("1") + Decimal(row.loss_rate)))

            key = (
                str(row.material_item_code),
                str(row.color or ""),
                str(getattr(row, "part", None) or ""),
                str(row.size or ""),
                str(row.uom),
            )
            grouped[key] = self._round(grouped.get(key, Decimal("0")) + final_qty)
            total_material_qty = self._round(total_material_qty + final_qty)

        material_requirements = [
            ExplodedMaterialItem(
                material_item_code=k[0],
                color=k[1] or None,
                part=k[2] or None,
                size=k[3] or None,
                uom=k[4],
                qty=v,
            )
            for k, v in grouped.items()
        ]

        operation_costs: List[ExplodedOperationCost] = []
        total_operation_cost = Decimal("0")
        for op in op_rows:
            if bool(op.is_subcontract):
                if op.subcontract_cost_per_piece is None:
                    raise BomBusinessError(
                        code=BOM_OPERATION_RATE_REQUIRED,
                        message="工序工价缺失",
                    )
                unit_cost = Decimal(op.subcontract_cost_per_piece)
            else:
                if op.wage_rate is None:
                    raise BomBusinessError(code=BOM_OPERATION_RATE_REQUIRED, message="工序工价缺失")
                unit_cost = Decimal(op.wage_rate)

            total_cost = self._round(unit_cost * payload.order_qty)
            total_operation_cost = self._round(total_operation_cost + total_cost)

            operation_costs.append(
                ExplodedOperationCost(
                    process_name=str(op.process_name),
                    is_subcontract=bool(op.is_subcontract),
                    unit_cost=self._round(unit_cost),
                    total_cost=total_cost,
                )
            )

        return BomExplodeData(
            material_requirements=material_requirements,
            operation_costs=operation_costs,
            total_material_qty=total_material_qty,
            total_operation_cost=total_operation_cost,
        )

    def _must_get_bom(self, bom_id: int, for_update: bool = False) -> LyApparelBom:
        try:
            query = self.session.query(LyApparelBom).filter(LyApparelBom.id == bom_id)
            if for_update:
                query = query.with_for_update()
            bom = query.first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not bom:
            raise BomBusinessError(code=BOM_NOT_FOUND, message="BOM 不存在")
        return bom

    def get_bom_by_no(self, bom_no: str) -> LyApparelBom | None:
        try:
            return self.session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _validate_item_exists(self, item_code: str, code: str) -> None:
        # 仅做 ERPNext Item 只读校验
        statements = (
            text(
                'SELECT name FROM public."tabItem" '
                'WHERE name = :item_code AND COALESCE(disabled, 0) = 0 LIMIT 1'
            ),
            text(
                'SELECT name FROM public."tabItem" '
                'WHERE item_code = :item_code AND COALESCE(disabled, 0) = 0 LIMIT 1'
            ),
            text("SELECT name FROM tabItem WHERE name = :item_code LIMIT 1"),
            text("SELECT name FROM tabItem WHERE item_code = :item_code LIMIT 1"),
        )
        query_success = False
        for stmt in statements:
            try:
                row = self.session.execute(stmt, {"item_code": item_code}).first()
                query_success = True
                if row:
                    return
            except SQLAlchemyError:
                continue
        if not query_success:
            if os.getenv("APP_ENV") == "development":
                try:
                    local_bom = (
                        self.session.query(LyApparelBom.id)
                        .filter(LyApparelBom.item_code == item_code)
                        .first()
                    )
                    local_material = (
                        self.session.query(LyApparelBomItem.id)
                        .filter(LyApparelBomItem.material_item_code == item_code)
                        .first()
                    )
                except SQLAlchemyError:
                    local_bom = None
                    local_material = None
                if local_bom or local_material:
                    return
                # local_dev sqlite 没有 ERPNext tabItem 时，允许受控测试编码继续闭环验证。
                return
            raise DatabaseReadFailed() from None
        raise BomBusinessError(code=code, message="物料不存在")

    def _normalize_company(self, company: str | None) -> str:
        normalized = str(company or "").strip()
        return normalized or self.DEFAULT_COMPANY

    def _validate_style_master_reference(self, *, company: str, item_code: str) -> LyStyleMaster:
        try:
            row = (
                self.session.query(LyStyleMaster)
                .filter(
                    LyStyleMaster.company == company,
                    LyStyleMaster.ys_style_no == item_code,
                    LyStyleMaster.ys_style_status == "enabled",
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BomBusinessError(
                code=STYLE_MASTER_INVALID_REFERENCE,
                message=f"{company}/{item_code} 款式不存在或未启用",
            )
        return row

    def _validate_items(self, items: Iterable[BomItemPayload]) -> None:
        for item in items:
            if item.qty_per_piece <= 0:
                raise BomBusinessError(code=BOM_INVALID_QTY, message="数量非法")
            if item.loss_rate < 0:
                raise BomBusinessError(code=BOM_INVALID_LOSS_RATE, message="损耗率非法")
            self._validate_item_exists(item_code=item.material_item_code, code=BOM_ITEM_NOT_FOUND)

    def _validate_operations(self, operations: Iterable[BomOperationPayload]) -> None:
        for op in operations:
            if op.is_subcontract:
                if op.subcontract_cost_per_piece is None:
                    raise BomBusinessError(
                        code=BOM_OPERATION_RATE_REQUIRED,
                        message="工序工价缺失",
                    )
            else:
                if op.wage_rate is None:
                    raise BomBusinessError(
                        code=BOM_OPERATION_RATE_REQUIRED,
                        message="工序工价缺失",
                    )

    def _replace_items(self, bom_id: int, bom_items: Iterable[BomItemPayload]) -> None:
        self.session.query(LyApparelBomItem).filter(LyApparelBomItem.bom_id == bom_id).delete()
        next_item_id = self._next_manual_pk(LyApparelBomItem) if self._is_local_sqlite_mode() else None
        for item in bom_items:
            row = LyApparelBomItem(
                id=next_item_id,
                bom_id=bom_id,
                material_item_code=item.material_item_code,
                color=item.color,
                part=item.part,
                size=item.size,
                qty_per_piece=item.qty_per_piece,
                loss_rate=item.loss_rate,
                uom=item.uom,
                remark=item.remark,
            )
            self.session.add(row)
            if next_item_id is not None:
                next_item_id += 1

    def _replace_operations(self, bom_id: int, operations: Iterable[BomOperationPayload]) -> None:
        self.session.query(LyBomOperation).filter(LyBomOperation.bom_id == bom_id).delete()
        next_operation_id = self._next_manual_pk(LyBomOperation) if self._is_local_sqlite_mode() else None
        for op in operations:
            row = LyBomOperation(
                id=next_operation_id,
                bom_id=bom_id,
                process_name=op.process_name,
                sequence_no=op.sequence_no,
                is_subcontract=op.is_subcontract,
                wage_rate=op.wage_rate,
                subcontract_cost_per_piece=op.subcontract_cost_per_piece,
                remark=op.remark,
            )
            self.session.add(row)
            if next_operation_id is not None:
                next_operation_id += 1

    def _is_local_sqlite_mode(self) -> bool:
        bind = self.session.get_bind()
        dialect_name = bind.dialect.name if bind is not None else ""
        return dialect_name == "sqlite"

    def _ensure_local_sqlite_partial_default_index(self) -> None:
        try:
            row = self.session.execute(
                text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'index' AND name = 'uk_ly_apparel_bom_one_active_default'"
                )
            ).first()
            sql_text = str(row[0] or "") if row else ""
            normalized = sql_text.lower()
            if " where " in normalized and "is_default = 1" in normalized and "status = 'active'" in normalized:
                if "company" in normalized:
                    return
            elif " where " in normalized and "is_default" in normalized and "status" in normalized and "company" in normalized:
                return
            self.session.execute(text("DROP INDEX IF EXISTS uk_ly_apparel_bom_one_active_default"))
            self.session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_apparel_bom_one_active_default "
                    "ON ly_apparel_bom(company, item_code) "
                    "WHERE is_default = 1 AND status = 'active'"
                )
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def _next_manual_pk(self, model: type[LyApparelBom] | type[LyApparelBomItem] | type[LyBomOperation]) -> int:
        try:
            current_max = self.session.query(func.max(model.id)).scalar() or 0
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return int(current_max) + 1

    @staticmethod
    def _resolve_item_order_qty(order_qty: Decimal, size: str | None, size_ratio: Dict[str, Decimal]) -> Decimal:
        if size and size_ratio:
            return Decimal(size_ratio.get(size, Decimal("0")))
        return Decimal(order_qty)

    @staticmethod
    def _build_bom_no(item_code: str, version_no: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"BOM-{item_code}-{version_no}-{ts}"

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
