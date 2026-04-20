"""Pydantic schemas for quality outbox worker and status APIs (TASK-030D)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class QualityOutboxWorkerRunOnceRequest(BaseModel):
    """Internal run-once request payload for quality outbox worker."""

    batch_size: int = Field(default=20, ge=1, le=200)
    dry_run: bool = False


class QualityOutboxWorkerRunOnceData(BaseModel):
    """Internal run-once response payload for quality outbox worker."""

    dry_run: bool
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int


class QualityOutboxStatusData(BaseModel):
    """Read-only outbox status payload for one quality inspection."""

    inspection_id: int
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    stock_entry_name: str | None = None
