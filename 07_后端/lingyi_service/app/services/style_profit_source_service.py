"""Source mapping skeleton for style profit report (TASK-005C/TASK-005C1).

This service intentionally focuses on source locating/mapping only.
Profit aggregation is deferred to TASK-005D.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
import hashlib
import json
from typing import Any
from typing import Iterable

from sqlalchemy.orm import Session

from app.schemas.style_profit import StyleProfitMaterialSourceDTO
from app.schemas.style_profit import StyleProfitMaterialSourceResolutionDTO
from app.schemas.style_profit import StyleProfitRevenueSourceDTO


class StyleProfitSourceService:
    """Resolve ERPNext/local source rows into normalized mapping DTOs."""

    _HASH_KEYS = (
        "company",
        "item_code",
        "sales_order",
        "from_date",
        "to_date",
        "revenue_mode",
        "include_provisional_subcontract",
        "formula_version",
        "work_order",
        "allowed_material_item_codes",
        "sales_invoice_rows",
        "sales_order_rows",
        "bom_material_rows",
        "bom_operation_rows",
        "stock_ledger_rows",
        "purchase_receipt_rows",
        "workshop_ticket_rows",
        "subcontract_rows",
    )
    _VOLATILE_HASH_KEYS = {
        "created_at",
        "updated_at",
        "operator",
        "request_id",
        "snapshot_no",
        "audit_id",
        "id",
    }
    _SENSITIVE_KEYS = {
        "authorization",
        "cookie",
        "token",
        "password",
        "secret",
    }
    _STATUS_ALLOWED_WITHOUT_DOCSTATUS: dict[str, set[str]] = {
        "sales invoice": {"paid", "unpaid", "overdue", "partly paid"},
        "sales order": {"to deliver and bill", "to bill", "to deliver", "completed"},
    }
    _STATUS_NOT_SUBMITTED = {
        "draft",
        "cancelled",
        "canceled",
        "closed",
        "void",
        "return",
    }
    _STATUS_UNKNOWN = {"", "unknown"}
    _STATUS_REJECTED = _STATUS_NOT_SUBMITTED | _STATUS_UNKNOWN
    _DOCSTATUS_REQUIRED_DOCTYPES = {
        "stock ledger entry",
        "stock entry",
        "purchase receipt",
    }
    _SLE_REASONS = {
        "status_untrusted": "SLE_STATUS_UNTRUSTED",
        "scope_untrusted": "SLE_SCOPE_UNTRUSTED",
        "material_not_in_bom": "SLE_MATERIAL_NOT_IN_BOM",
        "cancelled": "SLE_CANCELLED",
        "draft_or_unsubmitted": "SLE_DRAFT_OR_UNSUBMITTED",
    }

    def __init__(self, session: Session | None = None):
        self.session = session

    @classmethod
    def build_snapshot_request_hash(cls, payload: dict[str, Any]) -> str:
        """Build stable request hash without volatile runtime fields."""
        canonical: dict[str, Any] = {}
        for key in cls._HASH_KEYS:
            canonical[key] = cls._canonicalize_for_hash(payload.get(key))

        encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def resolve_revenue_sources(
        self,
        *,
        company: str,
        sales_order: str,
        item_code: str,
        sales_invoice_rows: Iterable[dict[str, Any]] | None = None,
        sales_order_rows: Iterable[dict[str, Any]] | None = None,
    ) -> list[StyleProfitRevenueSourceDTO]:
        """Resolve revenue rows with Sales Invoice priority and SO fallback."""
        normalized_company = self._normalize_text(company)
        normalized_order = self._normalize_text(sales_order)
        normalized_item = self._normalize_text(item_code)

        invoice_sources = self._build_revenue_rows(
            rows=sales_invoice_rows or [],
            expected_company=normalized_company,
            expected_order=normalized_order,
            expected_item=normalized_item,
            source_type="Sales Invoice",
            revenue_status="actual",
        )
        if invoice_sources:
            return invoice_sources

        return self._build_revenue_rows(
            rows=sales_order_rows or [],
            expected_company=normalized_company,
            expected_order=normalized_order,
            expected_item=normalized_item,
            source_type="Sales Order",
            revenue_status="estimated",
        )

    def resolve_material_cost_sources(
        self,
        *,
        company: str,
        sales_order: str,
        style_item_code: str | None = None,
        item_code: str | None = None,
        stock_ledger_rows: Iterable[dict[str, Any]],
        purchase_receipt_rows: Iterable[dict[str, Any]] | None = None,
        work_order: str | None = None,
        allowed_material_item_codes: set[str] | None = None,
    ) -> StyleProfitMaterialSourceResolutionDTO:
        """Resolve SLE material sources with include/exclude/unresolved buckets."""
        normalized_company = self._normalize_text(company)
        normalized_order = self._normalize_text(sales_order)
        normalized_work_order = self._normalize_text(work_order)
        normalized_style_item = self._normalize_text(style_item_code or item_code)
        allowed_materials = {
            self._normalize_text(code)
            for code in (allowed_material_item_codes or set())
            if self._normalize_text(code)
        }

        mapped: list[StyleProfitMaterialSourceDTO] = []
        unresolved: list[StyleProfitMaterialSourceDTO] = []
        excluded: list[StyleProfitMaterialSourceDTO] = []
        references: list[StyleProfitMaterialSourceDTO] = []
        actual_material_cost = Decimal("0")

        for row in stock_ledger_rows:
            dto = self._build_material_source_row(
                row=row,
                company=normalized_company,
                style_item_code=normalized_style_item,
            )
            source_doctype = dto.source_doctype
            sle_like = self._is_sle_like_doctype(source_doctype)

            if source_doctype == "Purchase Receipt":
                dto.mapping_status = "excluded"
                dto.include_in_profit = False
                dto.unresolved_reason = "purchase_receipt_reference_only"
                excluded.append(dto)
                references.append(dto)
                continue

            submitted, rejected_reason = self._submission_gate(row, source_doctype=source_doctype)
            if not submitted:
                dto.mapping_status = "unresolved"
                dto.include_in_profit = False
                dto.unresolved_reason = (
                    self._normalize_material_reason(rejected_reason, sle_like=sle_like)
                    if sle_like
                    else rejected_reason
                )
                if dto.source_status in {"", "unknown"}:
                    dto.source_status = "unknown"
                unresolved.append(dto)
                continue
            if dto.source_status == "unknown":
                dto.mapping_status = "unresolved"
                dto.include_in_profit = False
                dto.unresolved_reason = (
                    self._SLE_REASONS["status_untrusted"] if sle_like else "source_status_unknown"
                )
                unresolved.append(dto)
                continue

            row_company = self._normalize_text(row.get("company"))
            if row_company and row_company != normalized_company:
                dto.mapping_status = "unresolved"
                dto.include_in_profit = False
                dto.unresolved_reason = (
                    self._SLE_REASONS["scope_untrusted"] if sle_like else "company_mismatch"
                )
                unresolved.append(dto)
                continue

            row_order = self._normalize_text(
                row.get("sales_order") or row.get("custom_ly_sales_order")
            )
            row_work_order = self._normalize_text(
                row.get("work_order") or row.get("custom_ly_work_order")
            )
            row_job_card = self._normalize_text(
                row.get("job_card") or row.get("custom_ly_job_card")
            )
            row_plan_id = row.get("production_plan_id", row.get("custom_ly_production_plan"))

            if normalized_order and row_order and row_order != normalized_order:
                dto.mapping_status = "unresolved"
                dto.include_in_profit = False
                dto.unresolved_reason = (
                    self._SLE_REASONS["scope_untrusted"] if sle_like else "sales_order_mismatch"
                )
                unresolved.append(dto)
                continue
            if normalized_work_order and row_work_order and row_work_order != normalized_work_order:
                dto.mapping_status = "unresolved"
                dto.include_in_profit = False
                dto.unresolved_reason = (
                    self._SLE_REASONS["scope_untrusted"] if sle_like else "work_order_mismatch"
                )
                unresolved.append(dto)
                continue

            source_item = self._normalize_text(dto.source_item_code)
            if allowed_materials:
                if source_item not in allowed_materials:
                    dto.mapping_status = "unresolved"
                    dto.include_in_profit = False
                    dto.unresolved_reason = (
                        self._SLE_REASONS["material_not_in_bom"] if sle_like else "material_item_not_in_bom"
                    )
                    unresolved.append(dto)
                    continue
            else:
                dto.mapping_status = "unresolved"
                dto.include_in_profit = False
                dto.unresolved_reason = (
                    self._SLE_REASONS["material_not_in_bom"] if sle_like else "material_item_not_in_bom"
                )
                unresolved.append(dto)
                continue

            bridge_match = self._is_material_scope_trusted(
                expected_company=normalized_company,
                expected_item_code=normalized_style_item,
                expected_sales_order=normalized_order,
                expected_work_order=normalized_work_order,
                row_order=row_order,
                row_work_order=row_work_order,
                row_plan_id=row_plan_id,
                row_job_card=row_job_card,
                row_voucher_type=self._normalize_text(row.get("voucher_type")),
                row_voucher_no=self._normalize_text(row.get("voucher_no")),
            )

            if bridge_match:
                dto.mapping_status = "mapped"
                dto.include_in_profit = True
                dto.unresolved_reason = None
                mapped.append(dto)
                actual_material_cost += dto.amount
                continue

            dto.mapping_status = "unresolved"
            dto.include_in_profit = False
            dto.unresolved_reason = (
                self._SLE_REASONS["scope_untrusted"] if sle_like else "unable_to_link_order_or_material_scope"
            )
            unresolved.append(dto)

        if purchase_receipt_rows:
            for row in purchase_receipt_rows:
                dto = self._build_material_source_row(
                    row=row,
                    company=normalized_company,
                    style_item_code=normalized_style_item,
                )
                dto.source_doctype = "Purchase Receipt"
                dto.mapping_status = "excluded"
                dto.include_in_profit = False
                dto.unresolved_reason = "purchase_receipt_reference_only"
                references.append(dto)

        return StyleProfitMaterialSourceResolutionDTO(
            actual_material_cost=actual_material_cost,
            mapped_sources=mapped,
            unresolved_sources=unresolved,
            excluded_sources=excluded,
            reference_sources=references,
        )

    def _build_revenue_rows(
        self,
        *,
        rows: Iterable[dict[str, Any]],
        expected_company: str,
        expected_order: str,
        expected_item: str,
        source_type: str,
        revenue_status: str,
    ) -> list[StyleProfitRevenueSourceDTO]:
        if not expected_order:
            return []

        collected: list[StyleProfitRevenueSourceDTO] = []
        seen_keys: set[tuple[str, str]] = set()

        for row in rows:
            if not self._is_submitted(row, source_doctype=source_type):
                continue

            row_company = self._normalize_text(row.get("company"))
            row_order = self._normalize_text(row.get("sales_order"))
            row_item = self._normalize_text(row.get("item_code"))
            if row_company and row_company != expected_company:
                continue
            if not row_order or row_order != expected_order:
                continue
            if row_item and row_item != expected_item:
                continue

            source_name = self._normalize_text(row.get("name") or row.get("parent"))
            source_line_no = self._normalize_text(
                row.get("line_no") or row.get("line_id") or row.get("detail_id") or row.get("idx") or row.get("name")
            )
            if not source_name:
                continue
            key = (source_name, source_line_no)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            amount = self._to_decimal(
                row.get("base_net_amount", row.get("base_amount", row.get("amount", "0")))
            )
            qty = self._to_decimal(row.get("qty", "0"))
            rate = self._to_decimal(row.get("rate", "0"))
            collected.append(
                StyleProfitRevenueSourceDTO(
                    source_type=source_type,
                    source_name=source_name,
                    source_line_no=source_line_no,
                    item_code=expected_item,
                    qty=qty,
                    unit_rate=rate,
                    amount=amount,
                    revenue_status=revenue_status,
                    source_status=self._resolve_revenue_source_status(row),
                )
            )

        collected.sort(key=lambda row: (row.source_name, row.source_line_no))
        return collected

    def _build_material_source_row(
        self,
        *,
        row: dict[str, Any],
        company: str,
        style_item_code: str,
    ) -> StyleProfitMaterialSourceDTO:
        source_doctype = self._normalize_text(row.get("voucher_type")) or "Stock Ledger Entry"
        source_name = self._normalize_text(row.get("voucher_no")) or "UNKNOWN"
        source_line_no = self._normalize_text(row.get("line_no") or row.get("line_id") or row.get("idx") or row.get("name"))
        source_item_code = self._normalize_text(row.get("item_code"))
        stock_value_difference = self._to_decimal(row.get("stock_value_difference", "0"))
        posting_date = self._to_date(row.get("posting_date"))
        status_label = self._normalize_text(row.get("status")).lower() or "unknown"

        return StyleProfitMaterialSourceDTO(
            source_system="erpnext",
            source_doctype=source_doctype,
            source_status=status_label,
            source_name=source_name,
            source_line_no=source_line_no,
            company=company,
            style_item_code=style_item_code,
            source_item_code=source_item_code,
            sales_order=self._none_if_empty(row.get("sales_order")),
            production_plan_id=self._to_int_or_none(row.get("production_plan_id")),
            work_order=self._none_if_empty(row.get("work_order")),
            job_card=self._none_if_empty(row.get("job_card")),
            detail_id=None,
            snapshot_id=None,
            source_type=source_doctype,
            warehouse=self._none_if_empty(row.get("warehouse")),
            posting_date=posting_date,
            qty=self._to_decimal(row.get("actual_qty", "0")),
            unit_rate=self._to_decimal(row.get("valuation_rate", row.get("incoming_rate", row.get("rate", "0")))),
            currency=self._none_if_empty(row.get("currency")),
            stock_value_difference=stock_value_difference,
            amount_basis="abs_stock_value_difference",
            amount=abs(stock_value_difference),
            include_in_profit=False,
            mapping_status="unresolved",
            unresolved_reason=None,
            raw_ref=self._sanitize_raw_ref(row),
        )

    @classmethod
    def _sanitize_raw_ref(cls, row: dict[str, Any]) -> dict[str, Any]:
        """Keep only trace-safe fields, explicitly dropping sensitive keys."""
        allowed_keys = {
            "voucher_type",
            "voucher_no",
            "item_code",
            "warehouse",
            "actual_qty",
            "valuation_rate",
            "incoming_rate",
            "rate",
            "stock_value_difference",
            "posting_date",
            "company",
            "sales_order",
            "work_order",
            "job_card",
            "production_plan_id",
            "docstatus",
            "status",
            "is_cancelled",
            "line_no",
            "line_id",
            "idx",
            "name",
            "currency",
        }
        sanitized: dict[str, Any] = {}
        for key, value in row.items():
            key_text = str(key)
            lowered = key_text.lower()
            if any(sensitive in lowered for sensitive in cls._SENSITIVE_KEYS):
                continue
            if "sql" in lowered:
                continue
            if key_text not in allowed_keys:
                continue
            sanitized[key_text] = cls._canonicalize(value)
        return sanitized

    @classmethod
    def _submission_gate(
        cls,
        row: dict[str, Any],
        *,
        source_doctype: str | None = None,
    ) -> tuple[bool, str]:
        canonical_doctype = cls._canonical_doctype(
            source_doctype
            or row.get("source_doctype")
            or row.get("doctype")
            or row.get("voucher_type")
        )
        status = cls._normalize_text(row.get("status")).lower()

        if canonical_doctype in {"stock ledger entry", "stock entry"}:
            if row.get("docstatus") is None:
                return False, cls._SLE_REASONS["status_untrusted"]
            if row.get("status") is None or status in cls._STATUS_UNKNOWN:
                return False, cls._SLE_REASONS["status_untrusted"]
            if row.get("is_cancelled") is not None and cls._is_cancelled_true(row.get("is_cancelled")):
                return False, cls._SLE_REASONS["cancelled"]
            try:
                if int(row.get("docstatus")) != 1:
                    return False, cls._SLE_REASONS["draft_or_unsubmitted"]
            except Exception:
                return False, cls._SLE_REASONS["status_untrusted"]
            if status in {"cancelled", "canceled", "void", "return"}:
                return False, cls._SLE_REASONS["cancelled"]
            if status in cls._STATUS_NOT_SUBMITTED:
                return False, cls._SLE_REASONS["draft_or_unsubmitted"]
            return True, "submitted"

        is_cancelled = row.get("is_cancelled")
        if bool(is_cancelled):
            return False, "not_submitted_or_cancelled"

        docstatus = row.get("docstatus")
        if docstatus is not None:
            try:
                if int(docstatus) != 1:
                    return False, "not_submitted_or_cancelled"
            except Exception:
                return False, "source_status_unknown"
            return True, "submitted"

        if not canonical_doctype:
            return False, "source_status_unknown"

        if status in cls._STATUS_NOT_SUBMITTED:
            return False, "not_submitted_or_cancelled"
        if status in cls._STATUS_UNKNOWN:
            return False, "source_status_unknown"

        if canonical_doctype in cls._DOCSTATUS_REQUIRED_DOCTYPES:
            return False, "source_status_unknown"

        allowed_statuses = cls._STATUS_ALLOWED_WITHOUT_DOCSTATUS.get(canonical_doctype)
        if allowed_statuses and status in allowed_statuses:
            return True, "submitted"
        if status in cls._STATUS_REJECTED:
            return False, "not_submitted_or_cancelled"
        return False, "source_status_unknown"

    @classmethod
    def _is_submitted(cls, row: dict[str, Any], source_doctype: str | None = None) -> bool:
        return cls._submission_gate(row, source_doctype=source_doctype)[0]

    @classmethod
    def _canonical_doctype(cls, source_doctype: Any) -> str:
        value = cls._normalize_text(source_doctype).lower()
        return value

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip()

    @classmethod
    def _none_if_empty(cls, value: Any) -> str | None:
        normalized = cls._normalize_text(value)
        return normalized if normalized else None

    @classmethod
    def _canonicalize(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: cls._canonicalize(v) for k, v in sorted(value.items())}
        if isinstance(value, list):
            return [cls._canonicalize(v) for v in value]
        if isinstance(value, bool):
            return value
        if isinstance(value, Decimal):
            return cls._normalize_decimal_text(value)
        if isinstance(value, (int, float)):
            return cls._normalize_decimal_text(value)
        if isinstance(value, str):
            stripped = value.strip()
            try:
                return cls._normalize_decimal_text(Decimal(stripped))
            except (InvalidOperation, ValueError):
                return stripped
        return value

    @classmethod
    def _canonicalize_for_hash(cls, value: Any) -> Any:
        if isinstance(value, dict):
            canonical: dict[str, Any] = {}
            for key in sorted(value.keys()):
                key_text = str(key)
                if cls._should_drop_hash_key(key_text):
                    continue
                canonical[key_text] = cls._canonicalize_for_hash(value[key])
            return canonical
        if isinstance(value, list):
            normalized = [cls._canonicalize_for_hash(v) for v in value]
            return sorted(
                normalized,
                key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            )
        return cls._canonicalize(value)

    @classmethod
    def _should_drop_hash_key(cls, key: str) -> bool:
        lowered = key.lower().strip()
        if lowered in cls._VOLATILE_HASH_KEYS:
            return True
        return any(sensitive in lowered for sensitive in cls._SENSITIVE_KEYS)

    @classmethod
    def _resolve_revenue_source_status(cls, row: dict[str, Any]) -> str:
        status = cls._normalize_text(row.get("status")).lower()
        if status:
            return status
        docstatus = row.get("docstatus")
        try:
            if docstatus is not None and int(docstatus) == 1:
                return "submitted"
        except Exception:
            return "unknown"
        return "unknown"

    @classmethod
    def _is_sle_like_doctype(cls, source_doctype: str) -> bool:
        return cls._canonical_doctype(source_doctype) in {"stock ledger entry", "stock entry"}

    @classmethod
    def _normalize_material_reason(cls, reason: str, *, sle_like: bool) -> str:
        if not sle_like:
            return reason
        if reason in cls._SLE_REASONS.values():
            return reason
        if reason in {"source_status_unknown"}:
            return cls._SLE_REASONS["status_untrusted"]
        if reason in {"not_submitted_or_cancelled"}:
            return cls._SLE_REASONS["draft_or_unsubmitted"]
        if reason in {"material_item_not_in_bom"}:
            return cls._SLE_REASONS["material_not_in_bom"]
        if reason in {
            "company_mismatch",
            "sales_order_mismatch",
            "work_order_mismatch",
            "unable_to_link_order_or_material_scope",
        }:
            return cls._SLE_REASONS["scope_untrusted"]
        return cls._SLE_REASONS["status_untrusted"]

    @classmethod
    def _is_cancelled_true(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        text = cls._normalize_text(value).lower()
        return text in {"1", "true", "yes", "y"}

    def _is_material_scope_trusted(
        self,
        *,
        expected_company: str,
        expected_item_code: str,
        expected_sales_order: str,
        expected_work_order: str,
        row_order: str,
        row_work_order: str,
        row_plan_id: Any,
        row_job_card: str,
        row_voucher_type: str,
        row_voucher_no: str,
    ) -> bool:
        if expected_sales_order and row_order and row_order == expected_sales_order:
            return True
        if expected_work_order and row_work_order and row_work_order == expected_work_order:
            return True
        if (
            expected_work_order
            and self._canonical_doctype(row_voucher_type) == "work order"
            and row_voucher_no
            and row_voucher_no == expected_work_order
        ):
            return True

        if self.session is None:
            return False

        try:
            from app.models.production import LyProductionJobCardLink
            from app.models.production import LyProductionPlan
            from app.models.production import LyProductionWorkOrderLink
        except Exception:
            return False

        if row_plan_id not in (None, ""):
            try:
                plan_id = int(str(row_plan_id).strip())
                plan = (
                    self.session.query(LyProductionPlan)
                    .filter(LyProductionPlan.id == plan_id)
                    .one_or_none()
                )
                if (
                    plan is not None
                    and self._normalize_text(plan.company) == expected_company
                    and self._normalize_text(plan.item_code) == expected_item_code
                    and self._normalize_text(plan.sales_order) == expected_sales_order
                ):
                    return True
            except Exception:
                pass

        if row_job_card:
            try:
                link = (
                    self.session.query(LyProductionJobCardLink)
                    .filter(LyProductionJobCardLink.job_card == row_job_card)
                    .order_by(LyProductionJobCardLink.id.desc())
                    .first()
                )
                if link is not None:
                    plan = (
                        self.session.query(LyProductionPlan)
                        .filter(LyProductionPlan.id == link.plan_id)
                        .one_or_none()
                    )
                    if (
                        plan is not None
                        and self._normalize_text(plan.company) == expected_company
                        and self._normalize_text(plan.item_code) == expected_item_code
                        and self._normalize_text(plan.sales_order) == expected_sales_order
                    ):
                        return True
            except Exception:
                pass

        if row_work_order:
            try:
                link = (
                    self.session.query(LyProductionWorkOrderLink)
                    .filter(LyProductionWorkOrderLink.work_order == row_work_order)
                    .order_by(LyProductionWorkOrderLink.id.desc())
                    .first()
                )
                if link is not None:
                    plan = (
                        self.session.query(LyProductionPlan)
                        .filter(LyProductionPlan.id == link.plan_id)
                        .one_or_none()
                    )
                    if (
                        plan is not None
                        and self._normalize_text(plan.company) == expected_company
                        and self._normalize_text(plan.item_code) == expected_item_code
                        and self._normalize_text(plan.sales_order) == expected_sales_order
                    ):
                        return True
            except Exception:
                pass

        return False

    @staticmethod
    def _normalize_decimal_text(value: Decimal | int | float) -> str:
        decimal_value = Decimal(str(value))
        normalized = format(decimal_value, "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        if normalized in {"-0", ""}:
            normalized = "0"
        return normalized

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @staticmethod
    def _to_date(value: Any) -> date | None:
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
            except ValueError:
                try:
                    return datetime.strptime(raw, "%Y-%m-%d").date()
                except ValueError:
                    return None
        return None

    @staticmethod
    def _to_int_or_none(value: Any) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except Exception:
            return None
