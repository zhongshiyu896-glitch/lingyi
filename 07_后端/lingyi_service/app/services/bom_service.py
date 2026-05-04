"""Business service for BOM module (TASK-001)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple

from sqlalchemy import and_
from sqlalchemy import func
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
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import is_default_bom_unique_conflict
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.schemas.bom import BomActivateData
from app.schemas.bom import BomCreateRequest
from app.schemas.bom import BomDeactivateData
from app.schemas.bom import BomDetailData
from app.schemas.bom import BomExplodeData
from app.schemas.bom import BomExplodeRequest
from app.schemas.bom import BomHeader
from app.schemas.bom import BomMaterialGalleryData
from app.schemas.bom import BomMaterialGalleryItem
from app.schemas.bom import BomMaterialGalleryQuery
from app.schemas.bom import BomPurchaseOrderData
from app.schemas.bom import BomPurchaseOrderItem
from app.schemas.bom import BomPurchaseOrderQuery
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
        self._validate_item_exists(item_code=payload.item_code, code=BOM_ITEM_NOT_FOUND)
        self._validate_items(payload.bom_items)
        self._validate_operations(payload.operations)

        bom_no = self._build_bom_no(item_code=payload.item_code, version_no=payload.version_no)
        try:
            exists = self.session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if exists:
            raise BomBusinessError(code=BOM_DEFAULT_CONFLICT, message="BOM 编号冲突")

        try:
            bom = LyApparelBom(
                bom_no=bom_no,
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
            if query.item_code:
                sql = sql.filter(LyApparelBom.item_code == query.item_code)
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

        self._validate_items(payload.bom_items)
        self._validate_operations(payload.operations)

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

        # 锁定同 item_code 的 BOM 集合，避免并发 set-default 导致默认值竞争。
        try:
            same_item_rows = (
                self.session.query(LyApparelBom)
                .filter(LyApparelBom.item_code == bom.item_code)
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

        grouped: Dict[Tuple[str, str, str, str], Decimal] = {}
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
                str(row.size or ""),
                str(row.uom),
            )
            grouped[key] = self._round(grouped.get(key, Decimal("0")) + final_qty)
            total_material_qty = self._round(total_material_qty + final_qty)

        material_requirements = [
            ExplodedMaterialItem(
                material_item_code=k[0],
                color=k[1] or None,
                size=k[2] or None,
                uom=k[3],
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
            raise DatabaseReadFailed() from None
        raise BomBusinessError(code=code, message="物料不存在")

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
        for item in bom_items:
            row = LyApparelBomItem(
                bom_id=bom_id,
                material_item_code=item.material_item_code,
                color=item.color,
                size=item.size,
                qty_per_piece=item.qty_per_piece,
                loss_rate=item.loss_rate,
                uom=item.uom,
                remark=item.remark,
            )
            self.session.add(row)

    def _replace_operations(self, bom_id: int, operations: Iterable[BomOperationPayload]) -> None:
        self.session.query(LyBomOperation).filter(LyBomOperation.bom_id == bom_id).delete()
        for op in operations:
            row = LyBomOperation(
                bom_id=bom_id,
                process_name=op.process_name,
                sequence_no=op.sequence_no,
                is_subcontract=op.is_subcontract,
                wage_rate=op.wage_rate,
                subcontract_cost_per_piece=op.subcontract_cost_per_piece,
                remark=op.remark,
            )
            self.session.add(row)

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
