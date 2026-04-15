"""Permission constants and static fallback mapping.

注意：
- static 角色映射仅为 Sprint 1 临时方案，生产前必须切换为 ERPNext 权限来源。
"""

from __future__ import annotations

import json
import os
from typing import Iterable

AUTH_UNAUTHORIZED_CODE = "AUTH_UNAUTHORIZED"
AUTH_FORBIDDEN_CODE = "AUTH_FORBIDDEN"
PERMISSION_SOURCE_UNAVAILABLE_CODE = "PERMISSION_SOURCE_UNAVAILABLE"

BOM_CREATE = "bom:create"
BOM_UPDATE = "bom:update"
BOM_PUBLISH = "bom:publish"
BOM_SUBMIT = "bom:submit"
BOM_DEACTIVATE = "bom:deactivate"
BOM_CANCEL = "bom:cancel"
BOM_SET_DEFAULT = "bom:set_default"
BOM_READ = "bom:read"

WORKSHOP_READ = "workshop:read"
WORKSHOP_TICKET_REGISTER = "workshop:ticket_register"
WORKSHOP_TICKET_REVERSAL = "workshop:ticket_reversal"
WORKSHOP_TICKET_BATCH = "workshop:ticket_batch"
WORKSHOP_WAGE_READ = "workshop:wage_read"
WORKSHOP_WAGE_RATE_READ = "workshop:wage_rate_read"
WORKSHOP_WAGE_RATE_READ_ALL = "workshop:wage_rate_read_all"
WORKSHOP_WAGE_RATE_MANAGE = "workshop:wage_rate_manage"
WORKSHOP_WAGE_RATE_MANAGE_ALL = "workshop:wage_rate_manage_all"
WORKSHOP_JOB_CARD_SYNC = "workshop:job_card_sync"
WORKSHOP_JOB_CARD_SYNC_WORKER = "workshop:job_card_sync_worker"

SUBCONTRACT_READ = "subcontract:read"
SUBCONTRACT_CREATE = "subcontract:create"
SUBCONTRACT_ISSUE_MATERIAL = "subcontract:issue_material"
SUBCONTRACT_RECEIVE = "subcontract:receive"
SUBCONTRACT_INSPECT = "subcontract:inspect"
SUBCONTRACT_CANCEL = "subcontract:cancel"
SUBCONTRACT_STOCK_SYNC_RETRY = "subcontract:stock_sync_retry"
SUBCONTRACT_STOCK_SYNC_WORKER = "subcontract:stock_sync_worker"
SUBCONTRACT_SETTLEMENT_READ = "subcontract:settlement_read"
SUBCONTRACT_SETTLEMENT_LOCK = "subcontract:settlement_lock"
SUBCONTRACT_SETTLEMENT_RELEASE = "subcontract:settlement_release"

PRODUCTION_READ = "production:read"
PRODUCTION_PLAN_CREATE = "production:plan_create"
PRODUCTION_MATERIAL_CHECK = "production:material_check"
PRODUCTION_WORK_ORDER_CREATE = "production:work_order_create"
PRODUCTION_JOB_CARD_SYNC = "production:job_card_sync"
PRODUCTION_WORK_ORDER_WORKER = "production:work_order_worker"

STYLE_PROFIT_READ = "style_profit:read"
STYLE_PROFIT_SNAPSHOT_CREATE = "style_profit:snapshot_create"
FACTORY_STATEMENT_READ = "factory_statement:read"
FACTORY_STATEMENT_CREATE = "factory_statement:create"
FACTORY_STATEMENT_CONFIRM = "factory_statement:confirm"
FACTORY_STATEMENT_CANCEL = "factory_statement:cancel"
FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE = "factory_statement:payable_draft_create"
FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER = "factory_statement:payable_draft_worker"

ALL_BOM_ACTIONS = {
    BOM_READ,
    BOM_CREATE,
    BOM_UPDATE,
    BOM_PUBLISH,
    BOM_SUBMIT,
    BOM_DEACTIVATE,
    BOM_CANCEL,
    BOM_SET_DEFAULT,
}

ALL_WORKSHOP_ACTIONS = {
    WORKSHOP_READ,
    WORKSHOP_TICKET_REGISTER,
    WORKSHOP_TICKET_REVERSAL,
    WORKSHOP_TICKET_BATCH,
    WORKSHOP_WAGE_READ,
    WORKSHOP_WAGE_RATE_READ,
    WORKSHOP_WAGE_RATE_READ_ALL,
    WORKSHOP_WAGE_RATE_MANAGE,
    WORKSHOP_WAGE_RATE_MANAGE_ALL,
    WORKSHOP_JOB_CARD_SYNC,
    WORKSHOP_JOB_CARD_SYNC_WORKER,
}

ALL_SUBCONTRACT_ACTIONS = {
    SUBCONTRACT_READ,
    SUBCONTRACT_CREATE,
    SUBCONTRACT_ISSUE_MATERIAL,
    SUBCONTRACT_RECEIVE,
    SUBCONTRACT_INSPECT,
    SUBCONTRACT_CANCEL,
    SUBCONTRACT_STOCK_SYNC_RETRY,
    SUBCONTRACT_STOCK_SYNC_WORKER,
    SUBCONTRACT_SETTLEMENT_READ,
    SUBCONTRACT_SETTLEMENT_LOCK,
    SUBCONTRACT_SETTLEMENT_RELEASE,
}

ALL_PRODUCTION_ACTIONS = {
    PRODUCTION_READ,
    PRODUCTION_PLAN_CREATE,
    PRODUCTION_MATERIAL_CHECK,
    PRODUCTION_WORK_ORDER_CREATE,
    PRODUCTION_JOB_CARD_SYNC,
    PRODUCTION_WORK_ORDER_WORKER,
}

ALL_STYLE_PROFIT_ACTIONS = {
    STYLE_PROFIT_READ,
    STYLE_PROFIT_SNAPSHOT_CREATE,
}

ALL_FACTORY_STATEMENT_ACTIONS = {
    FACTORY_STATEMENT_READ,
    FACTORY_STATEMENT_CREATE,
    FACTORY_STATEMENT_CONFIRM,
    FACTORY_STATEMENT_CANCEL,
    FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE,
    FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER,
}

# 动作别名兼容：保留历史 publish/deactivate，同时支持 submit/cancel。
ACTION_ALIAS_TO_CANONICAL = {
    BOM_SUBMIT: BOM_PUBLISH,
    BOM_CANCEL: BOM_DEACTIVATE,
}

# 临时方案，生产前替换：static role -> action mapping
DEFAULT_STATIC_ROLE_ACTIONS: dict[str, set[str]] = {
    "System Manager": set(
        ALL_BOM_ACTIONS
        | ALL_WORKSHOP_ACTIONS
        | ALL_SUBCONTRACT_ACTIONS
        | ALL_PRODUCTION_ACTIONS
        | ALL_STYLE_PROFIT_ACTIONS
        | ALL_FACTORY_STATEMENT_ACTIONS
    ),
    "LY Integration Service": {
        WORKSHOP_READ,
        WORKSHOP_JOB_CARD_SYNC,
        WORKSHOP_JOB_CARD_SYNC_WORKER,
        SUBCONTRACT_STOCK_SYNC_WORKER,
        PRODUCTION_WORK_ORDER_WORKER,
        PRODUCTION_READ,
        PRODUCTION_JOB_CARD_SYNC,
        FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER,
    },
    "BOM Manager": set(ALL_BOM_ACTIONS),
    "BOM Editor": {BOM_READ, BOM_CREATE, BOM_UPDATE},
    "BOM Publisher": {BOM_READ, BOM_PUBLISH, BOM_SUBMIT, BOM_SET_DEFAULT, BOM_DEACTIVATE, BOM_CANCEL},
    "Workshop Manager": set(ALL_WORKSHOP_ACTIONS - {WORKSHOP_JOB_CARD_SYNC_WORKER}),
    "Workshop Clerk": {WORKSHOP_READ, WORKSHOP_TICKET_REGISTER, WORKSHOP_TICKET_REVERSAL, WORKSHOP_TICKET_BATCH},
    "Workshop Wage Clerk": {WORKSHOP_READ, WORKSHOP_WAGE_READ, WORKSHOP_WAGE_RATE_READ, WORKSHOP_WAGE_RATE_MANAGE},
    "Workshop Sync Operator": {WORKSHOP_READ, WORKSHOP_JOB_CARD_SYNC},
    "Subcontract Operator": {
        SUBCONTRACT_READ,
        SUBCONTRACT_CREATE,
        SUBCONTRACT_ISSUE_MATERIAL,
        SUBCONTRACT_RECEIVE,
    },
    "Subcontract Inspector": {
        SUBCONTRACT_READ,
        SUBCONTRACT_INSPECT,
    },
    "Subcontract Viewer": {
        SUBCONTRACT_READ,
    },
    "Production Manager": {
        PRODUCTION_READ,
        PRODUCTION_PLAN_CREATE,
        PRODUCTION_MATERIAL_CHECK,
        PRODUCTION_WORK_ORDER_CREATE,
        PRODUCTION_JOB_CARD_SYNC,
        STYLE_PROFIT_READ,
    },
    "Finance Manager": {
        STYLE_PROFIT_READ,
        STYLE_PROFIT_SNAPSHOT_CREATE,
        FACTORY_STATEMENT_READ,
        FACTORY_STATEMENT_CREATE,
        FACTORY_STATEMENT_CONFIRM,
        FACTORY_STATEMENT_CANCEL,
        FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE,
    },
    "Sales Manager": {
        STYLE_PROFIT_READ,
    },
    "Subcontract Manager": {
        SUBCONTRACT_READ,
        SUBCONTRACT_CREATE,
        SUBCONTRACT_ISSUE_MATERIAL,
        SUBCONTRACT_RECEIVE,
        SUBCONTRACT_INSPECT,
        SUBCONTRACT_CANCEL,
        SUBCONTRACT_STOCK_SYNC_RETRY,
        SUBCONTRACT_SETTLEMENT_READ,
        SUBCONTRACT_SETTLEMENT_LOCK,
        SUBCONTRACT_SETTLEMENT_RELEASE,
        FACTORY_STATEMENT_READ,
        FACTORY_STATEMENT_CREATE,
        FACTORY_STATEMENT_CONFIRM,
        FACTORY_STATEMENT_CANCEL,
        FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE,
    },
    "Viewer": {BOM_READ},
}


def get_permission_source() -> str:
    """Return permission source: static or erpnext."""
    value = os.getenv("LINGYI_PERMISSION_SOURCE", "static").strip().lower()
    if value not in {"static", "erpnext"}:
        return "static"
    return value


def get_static_actions_for_roles(roles: Iterable[str]) -> set[str]:
    """Resolve action set from temporary static role mapping."""
    role_actions = dict(DEFAULT_STATIC_ROLE_ACTIONS)
    role_actions.update(_load_custom_role_actions())

    actions: set[str] = set()
    for role in roles:
        role_name = role.strip()
        if not role_name:
            continue
        if ":" in role_name:
            actions.add(role_name)
        actions.update(role_actions.get(role_name, set()))
    return normalize_actions(actions)


def normalize_actions(actions: Iterable[str]) -> set[str]:
    """Normalize action aliases to canonical action codes."""
    normalized = {item.strip() for item in actions if item and item.strip()}
    for alias, canonical in ACTION_ALIAS_TO_CANONICAL.items():
        if alias in normalized:
            normalized.add(canonical)
    return normalized


def _load_custom_role_actions() -> dict[str, set[str]]:
    """Load optional static role map from env (temporary for Sprint 1)."""
    raw = os.getenv("LINGYI_ROLE_ACTIONS_JSON", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}

    parsed: dict[str, set[str]] = {}
    for role, actions in payload.items():
        if not isinstance(role, str):
            continue
        if not isinstance(actions, list):
            continue
        parsed[role.strip()] = {str(item).strip() for item in actions if str(item).strip()}
    return parsed
