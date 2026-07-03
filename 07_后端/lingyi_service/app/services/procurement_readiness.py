"""Shared read-only procurement readiness derivation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


PROCUREMENT_STATUS_LABELS: dict[str, str] = {
    "not_calculated": "未算料",
    "pending_purchase": "待采购",
    "purchasing": "采购中",
    "ordered_pending_inbound": "已下单待入库",
    "partial_inbound": "部分入库",
    "ready": "已齐料",
    "inbound_exception": "入库异常",
}


@dataclass(slots=True)
class ProcurementRequirementSnapshot:
    """Normalized procurement facts for one material requirement row."""

    status: str
    net_required_qty: Decimal
    purchased_qty: Decimal
    received_qty: Decimal
    purchase_no: str


@dataclass(slots=True)
class ProcurementReadinessSummary:
    """Plan or order level derived procurement readiness."""

    procurement_status: str
    procurement_status_label: str
    purchase_status: str
    material_ready: bool
    pending_requirement_count: int


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def normalize_requirement_snapshot(row: Any) -> ProcurementRequirementSnapshot:
    """Normalize ORM rows, SQL rows, or dicts into one shape."""

    if isinstance(row, dict):
        getter = row.get
    else:
        getter = lambda key, default=None: getattr(row, key, default)

    return ProcurementRequirementSnapshot(
        status=str(getter("status", "") or "").strip().lower(),
        net_required_qty=_decimal(getter("net_required_qty", 0)),
        purchased_qty=_decimal(getter("purchased_qty", 0)),
        received_qty=_decimal(getter("received_qty", 0)),
        purchase_no=str(getter("purchase_no", "") or "").strip(),
    )


def derive_procurement_readiness_status(
    *,
    snapshot_count: int,
    shortage_qty_total: Decimal | int | str,
    requirement_rows: list[Any],
) -> ProcurementReadinessSummary:
    """Derive the single read-only procurement status used by production and dashboard views."""

    rows: list[ProcurementRequirementSnapshot] = []
    for row in requirement_rows:
        snapshot = normalize_requirement_snapshot(row)
        if snapshot.status not in {"cancelled", "canceled"}:
            rows.append(snapshot)
    shortage = _decimal(shortage_qty_total)
    active_count = len(rows)

    if int(snapshot_count or 0) <= 0 and active_count == 0:
        procurement_status = "not_calculated"
    elif active_count == 0:
        procurement_status = "ready" if shortage <= Decimal("0") else "pending_purchase"
    elif any(row.status == "completed" and row.received_qty < row.net_required_qty for row in rows):
        procurement_status = "inbound_exception"
    elif any(row.received_qty > row.purchased_qty and row.purchased_qty > Decimal("0") for row in rows):
        procurement_status = "inbound_exception"
    elif all(row.received_qty >= row.net_required_qty for row in rows):
        procurement_status = "ready"
    elif any(row.received_qty > Decimal("0") for row in rows):
        procurement_status = "partial_inbound"
    elif rows and all(row.purchase_no or row.purchased_qty >= row.net_required_qty for row in rows):
        procurement_status = "ordered_pending_inbound"
    elif any(row.purchase_no or row.purchased_qty > Decimal("0") for row in rows):
        procurement_status = "purchasing"
    else:
        procurement_status = "pending_purchase"

    purchase_status = {
        "not_calculated": "not_calculated",
        "pending_purchase": "pending_purchase",
        "ready": "ready",
        "inbound_exception": "purchasing",
        "partial_inbound": "purchasing",
        "ordered_pending_inbound": "purchasing",
        "purchasing": "purchasing",
    }[procurement_status]

    return ProcurementReadinessSummary(
        procurement_status=procurement_status,
        procurement_status_label=PROCUREMENT_STATUS_LABELS[procurement_status],
        purchase_status=purchase_status,
        material_ready=procurement_status == "ready",
        pending_requirement_count=0 if procurement_status == "ready" else active_count,
    )
