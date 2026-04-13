"""Repository helpers for workshop Job Card sync outbox scheduling."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseReadFailed
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.services.service_account_policy import ServiceAccountResourcePolicy


class WorkshopJobCardSyncOutboxRepository:
    """Query helpers for due outbox rows with service-account resource scope."""

    def __init__(self, session: Session):
        self.session = session

    def list_due_for_service_account(
        self,
        *,
        policy: ServiceAccountResourcePolicy,
        limit: int,
        now: datetime | None = None,
    ) -> list[YsWorkshopJobCardSyncOutbox]:
        """List due rows that match the service-account `company/item_code` scope.

        NOTE:
        Resource filters are applied in SQL before ordering and limit to avoid head-of-line blocking.
        """
        if limit <= 0:
            return []
        if not policy.allowed_companies or not policy.allowed_items:
            return []

        moment = now or datetime.utcnow()
        query = (
            self.session.query(YsWorkshopJobCardSyncOutbox)
            .filter(
                YsWorkshopJobCardSyncOutbox.status.in_(["pending", "failed"]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= moment,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
                YsWorkshopJobCardSyncOutbox.company.in_(sorted(policy.allowed_companies)),
                YsWorkshopJobCardSyncOutbox.item_code.in_(sorted(policy.allowed_items)),
            )
            .order_by(YsWorkshopJobCardSyncOutbox.id.asc())
            .limit(limit)
        )
        try:
            return query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def count_due_for_service_account(
        self,
        *,
        policy: ServiceAccountResourcePolicy,
        now: datetime | None = None,
    ) -> int:
        """Count due rows that match current service-account scope."""
        if not policy.allowed_companies or not policy.allowed_items:
            return 0

        moment = now or datetime.utcnow()
        query = (
            self.session.query(func.count(YsWorkshopJobCardSyncOutbox.id))
            .filter(
                YsWorkshopJobCardSyncOutbox.status.in_(["pending", "failed"]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= moment,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
                YsWorkshopJobCardSyncOutbox.company.in_(sorted(policy.allowed_companies)),
                YsWorkshopJobCardSyncOutbox.item_code.in_(sorted(policy.allowed_items)),
            )
        )
        try:
            return int(query.scalar() or 0)
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def count_due_forbidden_for_service_account(
        self,
        *,
        policy: ServiceAccountResourcePolicy,
        now: datetime | None = None,
    ) -> int:
        """Count due rows with explicit scope that are outside current service-account scope."""
        if not policy.allowed_companies or not policy.allowed_items:
            return 0

        moment = now or datetime.utcnow()
        has_scope = and_(
            YsWorkshopJobCardSyncOutbox.company.isnot(None),
            YsWorkshopJobCardSyncOutbox.company != "",
            YsWorkshopJobCardSyncOutbox.item_code.isnot(None),
            YsWorkshopJobCardSyncOutbox.item_code != "",
        )
        forbidden_scope = or_(
            YsWorkshopJobCardSyncOutbox.company.notin_(sorted(policy.allowed_companies)),
            YsWorkshopJobCardSyncOutbox.item_code.notin_(sorted(policy.allowed_items)),
        )

        query = (
            self.session.query(func.count(YsWorkshopJobCardSyncOutbox.id))
            .filter(
                YsWorkshopJobCardSyncOutbox.status.in_(["pending", "failed"]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= moment,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
                has_scope,
                forbidden_scope,
            )
        )
        try:
            return int(query.scalar() or 0)
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def list_due_forbidden_for_service_account(
        self,
        *,
        policy: ServiceAccountResourcePolicy,
        limit: int | None = None,
        now: datetime | None = None,
    ) -> list[YsWorkshopJobCardSyncOutbox]:
        """List due rows with explicit scope that are outside current service-account scope."""
        if limit is not None and limit <= 0:
            return []
        if not policy.allowed_companies or not policy.allowed_items:
            return []

        moment = now or datetime.utcnow()
        has_scope = and_(
            YsWorkshopJobCardSyncOutbox.company.isnot(None),
            YsWorkshopJobCardSyncOutbox.company != "",
            YsWorkshopJobCardSyncOutbox.item_code.isnot(None),
            YsWorkshopJobCardSyncOutbox.item_code != "",
        )
        forbidden_scope = or_(
            YsWorkshopJobCardSyncOutbox.company.notin_(sorted(policy.allowed_companies)),
            YsWorkshopJobCardSyncOutbox.item_code.notin_(sorted(policy.allowed_items)),
        )
        query = (
            self.session.query(YsWorkshopJobCardSyncOutbox)
            .filter(
                YsWorkshopJobCardSyncOutbox.status.in_(["pending", "failed"]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= moment,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
                has_scope,
                forbidden_scope,
            )
            .order_by(YsWorkshopJobCardSyncOutbox.id.asc())
        )
        if limit is not None:
            query = query.limit(limit)
        try:
            return query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def list_due_missing_scope(
        self,
        *,
        now: datetime | None = None,
    ) -> list[YsWorkshopJobCardSyncOutbox]:
        """List due rows missing company/item_code scope."""
        moment = now or datetime.utcnow()
        missing_scope = or_(
            YsWorkshopJobCardSyncOutbox.company.is_(None),
            YsWorkshopJobCardSyncOutbox.company == "",
            YsWorkshopJobCardSyncOutbox.item_code.is_(None),
            YsWorkshopJobCardSyncOutbox.item_code == "",
        )
        query = (
            self.session.query(YsWorkshopJobCardSyncOutbox)
            .filter(
                YsWorkshopJobCardSyncOutbox.status.in_(["pending", "failed"]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= moment,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
                missing_scope,
            )
            .order_by(YsWorkshopJobCardSyncOutbox.id.asc())
        )
        try:
            return query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def count_due_missing_scope(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        """Count due rows missing required resource scope."""
        moment = now or datetime.utcnow()
        missing_scope = or_(
            YsWorkshopJobCardSyncOutbox.company.is_(None),
            YsWorkshopJobCardSyncOutbox.company == "",
            YsWorkshopJobCardSyncOutbox.item_code.is_(None),
            YsWorkshopJobCardSyncOutbox.item_code == "",
        )
        query = (
            self.session.query(func.count(YsWorkshopJobCardSyncOutbox.id))
            .filter(
                YsWorkshopJobCardSyncOutbox.status.in_(["pending", "failed"]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= moment,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
                missing_scope,
            )
        )
        try:
            return int(query.scalar() or 0)
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
