"""Read-only dev seed pagination for productized frontend handoff routes."""

from __future__ import annotations

from typing import Any

from app.data.frontend_readiness_seed import GAP_LIST_ROWS

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _parse_page(value: Any, *, default: int = DEFAULT_PAGE) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 1 else default


def _parse_page_size(value: Any, *, default: int = DEFAULT_PAGE_SIZE) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if parsed < 1 or parsed > MAX_PAGE_SIZE:
        return default
    return parsed


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _row_matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    for field, expected in filters.items():
        normalized_expected = _scope_text(expected)
        if normalized_expected is None:
            continue
        if _scope_text(row.get(field)) != normalized_expected:
            return False
    return True


def dev_seed_page_for_user(
    *,
    seed_key: str,
    current_user: Any,
    page: Any,
    page_size: Any,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a standard page from seed rows only for dev-header users."""
    normalized_page = _parse_page(page)
    normalized_page_size = _parse_page_size(page_size)
    rows = list(GAP_LIST_ROWS.get(seed_key, [])) if getattr(current_user, "source", None) == "dev_header" else []
    if filters:
        rows = [row for row in rows if _row_matches(row, filters)]
    total = len(rows)
    start = (normalized_page - 1) * normalized_page_size
    end = start + normalized_page_size
    return {
        "items": rows[start:end],
        "total": total,
        "page": normalized_page,
        "page_size": normalized_page_size,
    }
