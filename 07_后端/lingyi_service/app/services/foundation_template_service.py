"""Service layer for foundation template writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import hashlib
import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import BOM_TEMPLATE_CONFLICT
from app.core.error_codes import BOM_TEMPLATE_IDEMPOTENCY_CONFLICT
from app.core.error_codes import BOM_TEMPLATE_INVALID_TYPE
from app.core.error_codes import BOM_TEMPLATE_NOT_FOUND
from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.exceptions import BusinessException
from app.models.bom import LyFoundationTemplate
from app.models.bom import LyFoundationTemplateIdempotency
from app.models.bom import LyFoundationTemplateNode
from app.schemas.bom import FoundationTemplateCreateRequest
from app.schemas.bom import FoundationTemplateDeactivateRequest
from app.schemas.bom import FoundationTemplateItem
from app.schemas.bom import FoundationTemplateListData
from app.schemas.bom import FoundationTemplateNodeCreateRequest
from app.schemas.bom import FoundationTemplateNodeDeactivateRequest
from app.schemas.bom import FoundationTemplateNodeItem
from app.schemas.bom import FoundationTemplateNodeUpdateRequest
from app.schemas.bom import FoundationTemplateUpdateRequest

TEMPLATE_PATH_TO_TYPE = {
    "process-requirement-templates": "workmanship",
    "size-chart-templates": "size_spec",
}
TEMPLATE_TYPES = set(TEMPLATE_PATH_TO_TYPE.values())
ACTIVE_STATUS = "active"
INACTIVE_STATUS = "inactive"
TEMPLATE_CODE_PREFIXES = {
    "workmanship": "WK-TPL",
    "size_spec": "SZ-TPL",
}
NODE_CODE_PREFIXES = {
    "workmanship": "WK-NODE",
    "size_spec": "SZ-NODE",
}


@dataclass(frozen=True)
class FoundationTemplateMutationResult:
    """Mutation result plus audit snapshots."""

    item: FoundationTemplateItem | FoundationTemplateNodeItem
    before: dict[str, Any] | None
    after: dict[str, Any]
    idempotent: bool = False


class FoundationTemplateService:
    """Read/write foundation templates with idempotency."""

    def __init__(self, session: Session):
        self.session = session

    @classmethod
    def template_type_from_path(cls, template_path: str) -> str:
        template_type = TEMPLATE_PATH_TO_TYPE.get(str(template_path or "").strip())
        if not template_type:
            raise BusinessException(code=BOM_TEMPLATE_INVALID_TYPE, message="模板类型非法")
        return template_type

    def list_templates(
        self,
        *,
        template_type: str,
        company: str | None,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> FoundationTemplateListData:
        normalized_type = self._normalize_template_type(template_type)
        try:
            query = self.session.query(LyFoundationTemplate).filter(
                LyFoundationTemplate.template_type == normalized_type,
            )
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyFoundationTemplate.company == normalized_company)
            normalized_status = self._optional_status(status)
            if normalized_status:
                query = query.filter(LyFoundationTemplate.status == normalized_status)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyFoundationTemplate.template_code).like(like_value))
                    | (func.lower(LyFoundationTemplate.name).like(like_value))
                    | (func.lower(LyFoundationTemplate.scene).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(
                    LyFoundationTemplate.created_at.desc(),
                    LyFoundationTemplate.id.desc(),
                )
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return FoundationTemplateListData(
            items=[self._to_template_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_template(
        self,
        *,
        template_type: str,
        payload: FoundationTemplateCreateRequest,
        actor: str,
    ) -> FoundationTemplateMutationResult:
        normalized_type = self._normalize_template_type(template_type)
        company = self._require_text(payload.company, "company")
        requested_template_code = self._optional_text(payload.template_code)
        name = self._require_text(payload.name, "name")
        scene = self._optional_text(payload.scene) or "业务配置"
        next_status = self._optional_status(payload.status) or ACTIVE_STATUS
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(
            operation="create",
            template_type=normalized_type,
            company=company,
            requested_template_code=requested_template_code,
            name=name,
            scene=scene,
            status=next_status,
        )
        existing = self._get_idempotency(
            entity_type="template",
            company=company,
            template_type=normalized_type,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._ensure_same_idempotency(existing, operation="create", request_hash=request_hash)
            row = self._get_template_by_id(existing.record_id)
            after = self._snapshot_template(row)
            return FoundationTemplateMutationResult(item=self._to_template_item(row), before=after, after=after, idempotent=True)

        template_code = requested_template_code or self._next_template_code(company=company, template_type=normalized_type)
        if self._get_template_by_code(company=company, template_type=normalized_type, template_code=template_code) is not None:
            raise BusinessException(code=BOM_TEMPLATE_CONFLICT, message=f"{template_code} 已存在")

        try:
            row = LyFoundationTemplate(
                company=company,
                template_type=normalized_type,
                template_code=template_code,
                name=name,
                scene=scene,
                status=next_status,
                version=1,
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
            self._insert_idempotency(
                entity_type="template",
                company=company,
                template_type=normalized_type,
                idempotency_key=idempotency_key,
                operation="create",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_template(row)
        return FoundationTemplateMutationResult(item=self._to_template_item(row), before=None, after=after)

    def update_template(
        self,
        *,
        template_type: str,
        template_id: int,
        payload: FoundationTemplateUpdateRequest,
        actor: str,
    ) -> FoundationTemplateMutationResult:
        normalized_type = self._normalize_template_type(template_type)
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_template_for_mutation(template_id=template_id, company=company, template_type=normalized_type)
        next_code = self._optional_text(payload.template_code) or row.template_code
        next_name = self._optional_text(payload.name) or row.name
        next_scene = self._optional_text(payload.scene) or row.scene
        next_status = self._optional_status(payload.status) or row.status
        request_hash = self._request_hash(
            operation="update",
            template_type=normalized_type,
            template_id=template_id,
            company=company,
            template_code=next_code,
            name=next_name,
            scene=next_scene,
            status=next_status,
        )
        existing = self._get_idempotency(
            entity_type="template",
            company=company,
            template_type=normalized_type,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._ensure_same_idempotency(existing, operation="update", request_hash=request_hash)
            idem_row = self._get_template_by_id(existing.record_id)
            after = self._snapshot_template(idem_row)
            return FoundationTemplateMutationResult(item=self._to_template_item(idem_row), before=after, after=after, idempotent=True)
        if next_code != row.template_code:
            conflict = self._get_template_by_code(company=company, template_type=normalized_type, template_code=next_code)
            if conflict is not None and int(conflict.id) != int(row.id):
                raise BusinessException(code=BOM_TEMPLATE_CONFLICT, message=f"{next_code} 已存在")

        before = self._snapshot_template(row)
        try:
            now = datetime.now(UTC)
            row.template_code = next_code
            row.name = next_name
            row.scene = next_scene
            row.status = next_status
            row.version = int(row.version or 0) + 1
            row.updated_by = actor
            row.updated_at = now
            self._insert_idempotency(
                entity_type="template",
                company=company,
                template_type=normalized_type,
                idempotency_key=idempotency_key,
                operation="update",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_template(row)
        return FoundationTemplateMutationResult(item=self._to_template_item(row), before=before, after=after)

    def deactivate_template(
        self,
        *,
        template_type: str,
        template_id: int,
        payload: FoundationTemplateDeactivateRequest,
        actor: str,
    ) -> FoundationTemplateMutationResult:
        normalized_type = self._normalize_template_type(template_type)
        company = self._require_text(payload.company, "company")
        reason = self._require_text(payload.reason, "reason")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        row = self._get_template_for_mutation(template_id=template_id, company=company, template_type=normalized_type)
        request_hash = self._request_hash(
            operation="deactivate",
            template_type=normalized_type,
            template_id=template_id,
            company=company,
            reason=reason,
        )
        existing = self._get_idempotency(
            entity_type="template",
            company=company,
            template_type=normalized_type,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._ensure_same_idempotency(existing, operation="deactivate", request_hash=request_hash)
            idem_row = self._get_template_by_id(existing.record_id)
            after = self._snapshot_template(idem_row)
            return FoundationTemplateMutationResult(item=self._to_template_item(idem_row), before=after, after=after, idempotent=True)

        before = self._snapshot_template(row)
        try:
            now = datetime.now(UTC)
            row.status = INACTIVE_STATUS
            row.deactivated_by = actor
            row.deactivated_at = now
            row.deactivate_reason = reason
            row.updated_by = actor
            row.updated_at = now
            row.version = int(row.version or 0) + 1
            self._insert_idempotency(
                entity_type="template",
                company=company,
                template_type=normalized_type,
                idempotency_key=idempotency_key,
                operation="deactivate",
                request_hash=request_hash,
                record_id=int(row.id),
                actor=actor,
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_template(row)
        return FoundationTemplateMutationResult(item=self._to_template_item(row), before=before, after=after)

    def create_node(
        self,
        *,
        template_type: str,
        template_id: int,
        payload: FoundationTemplateNodeCreateRequest,
        actor: str,
    ) -> FoundationTemplateMutationResult:
        normalized_type = self._normalize_template_type(template_type)
        company = self._require_text(payload.company, "company")
        template = self._get_template_for_mutation(template_id=template_id, company=company, template_type=normalized_type)
        requested_code = self._optional_text(payload.code)
        name = self._require_text(payload.name, "name")
        node_type = self._require_text(payload.node_type, "node_type")
        owner = self._optional_text(payload.owner) or "业务"
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(
            operation="create_node",
            template_type=normalized_type,
            template_id=template_id,
            company=company,
            requested_code=requested_code,
            name=name,
            node_type=node_type,
            required=bool(payload.required),
            sort_no=int(payload.sort_no),
            owner=owner,
        )
        existing = self._get_idempotency(
            entity_type="node",
            company=company,
            template_type=normalized_type,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._ensure_same_idempotency(existing, operation="create_node", request_hash=request_hash)
            node = self._get_node_by_id(existing.record_id)
            after = self._snapshot_node(node)
            return FoundationTemplateMutationResult(item=self._to_node_item(node), before=after, after=after, idempotent=True)

        code = requested_code or self._next_node_code(template_id=int(template.id), template_type=normalized_type)
        if self._get_node_by_code(template_id=int(template.id), code=code) is not None:
            raise BusinessException(code=BOM_TEMPLATE_CONFLICT, message=f"{code} 已存在")

        try:
            node = LyFoundationTemplateNode(
                template_id=int(template.id),
                code=code,
                name=name,
                node_type=node_type,
                required=bool(payload.required),
                status=ACTIVE_STATUS,
                sort_no=int(payload.sort_no),
                owner=owner,
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(node)
            template.updated_by = actor
            template.updated_at = datetime.now(UTC)
            self.session.flush()
            self._insert_idempotency(
                entity_type="node",
                company=company,
                template_type=normalized_type,
                idempotency_key=idempotency_key,
                operation="create_node",
                request_hash=request_hash,
                record_id=int(node.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_node(node)
        return FoundationTemplateMutationResult(item=self._to_node_item(node), before=None, after=after)

    def update_node(
        self,
        *,
        template_type: str,
        template_id: int,
        node_id: int,
        payload: FoundationTemplateNodeUpdateRequest,
        actor: str,
    ) -> FoundationTemplateMutationResult:
        normalized_type = self._normalize_template_type(template_type)
        company = self._require_text(payload.company, "company")
        template = self._get_template_for_mutation(template_id=template_id, company=company, template_type=normalized_type)
        node = self._get_node_for_mutation(node_id=node_id, template_id=int(template.id))
        next_code = self._optional_text(payload.code) or node.code
        next_name = self._optional_text(payload.name) or node.name
        next_node_type = self._optional_text(payload.node_type) or node.node_type
        next_required = bool(node.required if payload.required is None else payload.required)
        next_status = self._optional_status(payload.status) or node.status
        next_sort_no = int(node.sort_no if payload.sort_no is None else payload.sort_no)
        next_owner = self._optional_text(payload.owner) or node.owner
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(
            operation="update_node",
            template_type=normalized_type,
            template_id=template_id,
            node_id=node_id,
            company=company,
            code=next_code,
            name=next_name,
            node_type=next_node_type,
            required=next_required,
            status=next_status,
            sort_no=next_sort_no,
            owner=next_owner,
        )
        existing = self._get_idempotency(
            entity_type="node",
            company=company,
            template_type=normalized_type,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._ensure_same_idempotency(existing, operation="update_node", request_hash=request_hash)
            idem_node = self._get_node_by_id(existing.record_id)
            after = self._snapshot_node(idem_node)
            return FoundationTemplateMutationResult(item=self._to_node_item(idem_node), before=after, after=after, idempotent=True)
        if next_code != node.code:
            conflict = self._get_node_by_code(template_id=int(template.id), code=next_code)
            if conflict is not None and int(conflict.id) != int(node.id):
                raise BusinessException(code=BOM_TEMPLATE_CONFLICT, message=f"{next_code} 已存在")

        before = self._snapshot_node(node)
        try:
            now = datetime.now(UTC)
            node.code = next_code
            node.name = next_name
            node.node_type = next_node_type
            node.required = next_required
            node.status = next_status
            node.sort_no = next_sort_no
            node.owner = next_owner
            node.updated_by = actor
            node.updated_at = now
            template.updated_by = actor
            template.updated_at = now
            self._insert_idempotency(
                entity_type="node",
                company=company,
                template_type=normalized_type,
                idempotency_key=idempotency_key,
                operation="update_node",
                request_hash=request_hash,
                record_id=int(node.id),
                actor=actor,
            )
            self.session.flush()
        except (IntegrityError, SQLAlchemyError) as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_node(node)
        return FoundationTemplateMutationResult(item=self._to_node_item(node), before=before, after=after)

    def deactivate_node(
        self,
        *,
        template_type: str,
        template_id: int,
        node_id: int,
        payload: FoundationTemplateNodeDeactivateRequest,
        actor: str,
    ) -> FoundationTemplateMutationResult:
        normalized_type = self._normalize_template_type(template_type)
        company = self._require_text(payload.company, "company")
        template = self._get_template_for_mutation(template_id=template_id, company=company, template_type=normalized_type)
        node = self._get_node_for_mutation(node_id=node_id, template_id=int(template.id))
        reason = self._require_text(payload.reason, "reason")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(
            operation="deactivate_node",
            template_type=normalized_type,
            template_id=template_id,
            node_id=node_id,
            company=company,
            reason=reason,
        )
        existing = self._get_idempotency(
            entity_type="node",
            company=company,
            template_type=normalized_type,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._ensure_same_idempotency(existing, operation="deactivate_node", request_hash=request_hash)
            idem_node = self._get_node_by_id(existing.record_id)
            after = self._snapshot_node(idem_node)
            return FoundationTemplateMutationResult(item=self._to_node_item(idem_node), before=after, after=after, idempotent=True)

        before = self._snapshot_node(node)
        try:
            now = datetime.now(UTC)
            node.status = INACTIVE_STATUS
            node.updated_by = actor
            node.updated_at = now
            template.updated_by = actor
            template.updated_at = now
            self._insert_idempotency(
                entity_type="node",
                company=company,
                template_type=normalized_type,
                idempotency_key=idempotency_key,
                operation="deactivate_node",
                request_hash=request_hash,
                record_id=int(node.id),
                actor=actor,
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        after = self._snapshot_node(node)
        return FoundationTemplateMutationResult(item=self._to_node_item(node), before=before, after=after)

    def _normalize_template_type(self, template_type: str) -> str:
        value = self._require_text(template_type, "template_type")
        if value not in TEMPLATE_TYPES:
            raise BusinessException(code=BOM_TEMPLATE_INVALID_TYPE, message="模板类型非法")
        return value

    def _optional_status(self, status: str | None) -> str | None:
        value = self._optional_text(status)
        if not value:
            return None
        lowered = value.lower()
        if lowered in {ACTIVE_STATUS, "enabled", "启用"}:
            return ACTIVE_STATUS
        if lowered in {INACTIVE_STATUS, "disabled", "停用"}:
            return INACTIVE_STATUS
        raise BusinessException(code=BOM_TEMPLATE_INVALID_TYPE, message="模板状态非法")

    def _get_template_by_id(self, template_id: int) -> LyFoundationTemplate:
        row = self.session.query(LyFoundationTemplate).filter(LyFoundationTemplate.id == int(template_id)).first()
        if row is None:
            raise BusinessException(code=BOM_TEMPLATE_NOT_FOUND, message="模板不存在")
        return row

    def _get_template_for_mutation(self, *, template_id: int, company: str, template_type: str) -> LyFoundationTemplate:
        row = (
            self.session.query(LyFoundationTemplate)
            .filter(
                LyFoundationTemplate.id == int(template_id),
                LyFoundationTemplate.company == company,
                LyFoundationTemplate.template_type == template_type,
            )
            .first()
        )
        if row is None:
            raise BusinessException(code=BOM_TEMPLATE_NOT_FOUND, message="模板不存在")
        return row

    def _get_template_by_code(self, *, company: str, template_type: str, template_code: str) -> LyFoundationTemplate | None:
        return (
            self.session.query(LyFoundationTemplate)
            .filter(
                LyFoundationTemplate.company == company,
                LyFoundationTemplate.template_type == template_type,
                LyFoundationTemplate.template_code == template_code,
            )
            .first()
        )

    def _get_node_by_id(self, node_id: int) -> LyFoundationTemplateNode:
        row = self.session.query(LyFoundationTemplateNode).filter(LyFoundationTemplateNode.id == int(node_id)).first()
        if row is None:
            raise BusinessException(code=BOM_TEMPLATE_NOT_FOUND, message="模板节点不存在")
        return row

    def _get_node_for_mutation(self, *, node_id: int, template_id: int) -> LyFoundationTemplateNode:
        row = (
            self.session.query(LyFoundationTemplateNode)
            .filter(LyFoundationTemplateNode.id == int(node_id), LyFoundationTemplateNode.template_id == int(template_id))
            .first()
        )
        if row is None:
            raise BusinessException(code=BOM_TEMPLATE_NOT_FOUND, message="模板节点不存在")
        return row

    def _get_node_by_code(self, *, template_id: int, code: str) -> LyFoundationTemplateNode | None:
        return (
            self.session.query(LyFoundationTemplateNode)
            .filter(LyFoundationTemplateNode.template_id == int(template_id), LyFoundationTemplateNode.code == code)
            .first()
        )

    def _next_template_code(self, *, company: str, template_type: str) -> str:
        prefix = TEMPLATE_CODE_PREFIXES.get(template_type, "TPL")
        existing_codes = {
            str(row[0])
            for row in self.session.query(LyFoundationTemplate.template_code)
            .filter(
                LyFoundationTemplate.company == company,
                LyFoundationTemplate.template_type == template_type,
                LyFoundationTemplate.template_code.like(f"{prefix}-%"),
            )
            .all()
        }
        return self._next_prefixed_code(prefix=prefix, existing_codes=existing_codes)

    def _next_node_code(self, *, template_id: int, template_type: str) -> str:
        prefix = NODE_CODE_PREFIXES.get(template_type, "NODE")
        existing_codes = {
            str(row[0])
            for row in self.session.query(LyFoundationTemplateNode.code)
            .filter(
                LyFoundationTemplateNode.template_id == int(template_id),
                LyFoundationTemplateNode.code.like(f"{prefix}-%"),
            )
            .all()
        }
        return self._next_prefixed_code(prefix=prefix, existing_codes=existing_codes)

    @staticmethod
    def _next_prefixed_code(*, prefix: str, existing_codes: set[str]) -> str:
        next_number = len(existing_codes) + 1
        while next_number < 1_000_000:
            candidate = f"{prefix}-{next_number:06d}"
            if candidate not in existing_codes:
                return candidate
            next_number += 1
        raise BusinessException(code=BOM_TEMPLATE_CONFLICT, message=f"{prefix} 自动编码已用尽")

    def _get_idempotency(
        self,
        *,
        entity_type: str,
        company: str,
        template_type: str,
        idempotency_key: str,
    ) -> LyFoundationTemplateIdempotency | None:
        return (
            self.session.query(LyFoundationTemplateIdempotency)
            .filter(
                LyFoundationTemplateIdempotency.entity_type == entity_type,
                LyFoundationTemplateIdempotency.company == company,
                LyFoundationTemplateIdempotency.template_type == template_type,
                LyFoundationTemplateIdempotency.idempotency_key == idempotency_key,
            )
            .first()
        )

    def _insert_idempotency(
        self,
        *,
        entity_type: str,
        company: str,
        template_type: str,
        idempotency_key: str,
        operation: str,
        request_hash: str,
        record_id: int,
        actor: str,
    ) -> None:
        self.session.add(
            LyFoundationTemplateIdempotency(
                entity_type=entity_type,
                company=company,
                template_type=template_type,
                idempotency_key=idempotency_key,
                operation=operation,
                request_hash=request_hash,
                record_id=record_id,
                created_by=actor,
            )
        )

    def _ensure_same_idempotency(self, row: LyFoundationTemplateIdempotency, *, operation: str, request_hash: str) -> None:
        if row.operation != operation or row.request_hash != request_hash:
            raise BusinessException(code=BOM_TEMPLATE_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

    def _to_template_item(self, row: LyFoundationTemplate) -> FoundationTemplateItem:
        nodes = sorted(row.nodes or [], key=lambda item: (int(item.sort_no or 0), int(item.id or 0)))
        return FoundationTemplateItem(
            id=int(row.id),
            company=row.company,
            template_type=row.template_type,
            template_code=row.template_code,
            name=row.name,
            scene=row.scene,
            status=row.status,
            version=int(row.version or 1),
            created_by=row.created_by,
            created_at=self._datetime_text(row.created_at),
            updated_at=self._datetime_text(row.updated_at) if row.updated_at else None,
            nodes=[self._to_node_item(node) for node in nodes],
        )

    def _to_node_item(self, row: LyFoundationTemplateNode) -> FoundationTemplateNodeItem:
        return FoundationTemplateNodeItem(
            id=int(row.id),
            template_id=int(row.template_id),
            code=row.code,
            name=row.name,
            node_type=row.node_type,
            required=bool(row.required),
            status=row.status,
            sort_no=int(row.sort_no or 0),
            owner=row.owner,
            created_by=row.created_by,
            created_at=self._datetime_text(row.created_at),
            updated_at=self._datetime_text(row.updated_at) if row.updated_at else None,
        )

    def _snapshot_template(self, row: LyFoundationTemplate) -> dict[str, Any]:
        return self._to_template_item(row).model_dump()

    def _snapshot_node(self, row: LyFoundationTemplateNode) -> dict[str, Any]:
        return self._to_node_item(row).model_dump()

    @staticmethod
    def _datetime_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _request_hash(**payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _require_text(self, value: Any, field: str) -> str:
        text = self._optional_text(value)
        if not text:
            raise BusinessException(code=BOM_TEMPLATE_INVALID_TYPE, message=f"{field} 不能为空")
        return text
