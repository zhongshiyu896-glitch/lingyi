"""Export backend route inventory and frontend page connection matrix.

This tool is intentionally read-only for application code and frontend sources.
It imports the FastAPI app in test mode, classifies routes, and writes backend
contract artifacts under ``contracts/``.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args, get_origin

from fastapi.routing import APIRoute

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
DEFAULT_FRONTEND_REGISTRY = Path("/Users/hh/Desktop/lingyi-frontend-1to1/src/page-registry.ts")
CONTRACT_FIELD_PATH = BACKEND_ROOT / "contracts" / "frontend_readiness_field_contract.json"

READ_METHODS = {"GET"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIPPED_METHODS = {"HEAD", "OPTIONS"}
DEV_ONLY_NOTE = "dev/test only; 生产环境必须关闭"
FLOW_STUB_NOTE = "readiness flow 回执桩; 不得当作真实写接口"


@dataclass(frozen=True)
class PageDefinitionSnapshot:
    index: int
    module: str
    title: str
    route: str
    template: str
    data_kind: str
    contract_schemas: list[str]
    field_gaps: list[str]
    actions: list[str]
    filters: list[str]
    api_path: str | None


def _set_import_env(app_env: str = "test") -> None:
    os.environ["APP_ENV"] = app_env
    os.environ.setdefault("LINGYI_ALLOW_DEV_AUTH", "true")
    os.environ.setdefault("LINGYI_ERPNEXT_BASE_URL", "")
    os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext" if app_env == "production" else "static"
    os.environ.setdefault("LINGYI_DB_URL", "sqlite+pysqlite:///:memory:")


def load_app_for_env(app_env: str = "test"):
    """Reload app.main with deterministic environment and return its app."""
    _set_import_env(app_env)
    import app.main as main_module

    return importlib.reload(main_module).app


def _load_readiness_maps() -> tuple[set[str], set[str]]:
    from app.routers.frontend_readiness import ALL_READINESS_ENDPOINTS
    from app.routers.frontend_readiness import WRITE_READINESS_ENDPOINTS

    return set(ALL_READINESS_ENDPOINTS), set(WRITE_READINESS_ENDPOINTS)


def _load_field_contract() -> dict[str, list[str]]:
    if not CONTRACT_FIELD_PATH.exists():
        return {}
    payload = json.loads(CONTRACT_FIELD_PATH.read_text(encoding="utf-8"))
    endpoints = payload.get("endpoints", {})
    if not isinstance(endpoints, dict):
        return {}
    return {str(key): list(value) for key, value in endpoints.items() if isinstance(value, list)}


def _iter_routes(app) -> Iterable[APIRoute]:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api/"):
            yield route


def first_route_for(app, *, method: str, path: str) -> APIRoute | None:
    """Return the first exact route registered for a method/path pair."""
    normalized_method = method.upper()
    for route in _iter_routes(app):
        if route.path == path and normalized_method in (route.methods or set()):
            return route
    return None


def _query_params(route: APIRoute) -> list[str]:
    return [param.name for param in route.dependant.query_params]


def _path_params(route: APIRoute) -> list[str]:
    return [param.name for param in route.dependant.path_params]


def _body_params(route: APIRoute) -> list[str]:
    return [param.name for param in route.dependant.body_params]


def _model_field_names(annotation: Any, *, prefix: str = "", depth: int = 0) -> list[str]:
    if annotation is None or depth > 3:
        return []
    origin = get_origin(annotation)
    if origin in {list, tuple, set, frozenset}:
        args = get_args(annotation)
        return _model_field_names(args[0], prefix=prefix, depth=depth + 1) if args else []
    model_fields = getattr(annotation, "model_fields", None)
    if not model_fields:
        return []
    names: list[str] = []
    for name, field in model_fields.items():
        field_name = f"{prefix}{name}" if prefix else name
        names.append(field_name)
        nested = _model_field_names(getattr(field, "annotation", None), prefix=f"{field_name}.", depth=depth + 1)
        names.extend(nested)
    return names


def _response_fields(route: APIRoute, field_contract: dict[str, list[str]], method: str) -> list[str]:
    contract_key = f"{method} {route.path}"
    if contract_key in field_contract:
        return field_contract[contract_key]
    fields = _model_field_names(route.response_model)
    if fields:
        return fields[:80]
    return []


def _route_class(route: APIRoute, method: str, readiness_paths: set[str], readiness_flow_paths: set[str]) -> tuple[str, str]:
    path = route.path
    endpoint_module = getattr(route.endpoint, "__module__", "")
    if path in readiness_flow_paths or "/readiness/" in path:
        return "C", FLOW_STUB_NOTE
    if path in readiness_paths and endpoint_module == "app.routers.frontend_readiness":
        return "B", DEV_ONLY_NOTE
    if "/internal/" in path:
        return "D", "内部 worker/运维接口; 不给前端页面直接接入"
    if path.endswith("/diagnostic") or "/diagnostic/" in path:
        return "D", "诊断接口; 运维排障用途"
    if path.startswith("/api/local-dev/"):
        return "D", "local-dev 运行时接口; 主 app 不挂载"
    if path.startswith("/api/auth/"):
        return "A", "认证/会话真实接口"
    if method in WRITE_METHODS:
        return "A", "真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等"
    return "A", "真实业务只读接口候选"


def _frontend_connect_status(route_class: str, method: str) -> str:
    if route_class == "B":
        return "temporary_dev_only"
    if route_class == "C":
        return "do_not_connect_as_write"
    if route_class == "D":
        return "not_for_page_direct_use"
    if method in WRITE_METHODS:
        return "needs_dedicated_write_task"
    return "candidate"


def _requires_login(path: str) -> bool:
    return path not in {"/api/auth/login", "/api/auth/logout"} and not path.startswith("/api/auth/local-profiles")


def _is_known_business_write(route_class: str, method: str, path: str) -> bool:
    if route_class != "A" or method not in WRITE_METHODS:
        return False
    if path.startswith("/api/auth/"):
        return False
    if "/diagnostic" in path or "/internal/" in path:
        return False
    return True


def _is_paginated(query_params: list[str], response_fields: list[str]) -> bool:
    field_set = set(response_fields)
    return {"items", "total", "page", "page_size"}.issubset(field_set) or {"page", "page_size"}.issubset(query_params)


def build_route_catalog(app) -> list[dict[str, Any]]:
    readiness_paths, readiness_flow_paths = _load_readiness_maps()
    field_contract = _load_field_contract()
    route_order = {id(route): index for index, route in enumerate(_iter_routes(app))}
    duplicate_counter: Counter[tuple[str, str]] = Counter()
    for route in _iter_routes(app):
        for method in sorted((route.methods or set()) - SKIPPED_METHODS):
            duplicate_counter[(method, route.path)] += 1

    rows: list[dict[str, Any]] = []
    for route in _iter_routes(app):
        for method in sorted((route.methods or set()) - SKIPPED_METHODS):
            query_params = _query_params(route)
            response_fields = _response_fields(route, field_contract, method)
            route_class, risk_note = _route_class(route, method, readiness_paths, readiness_flow_paths)
            rows.append(
                {
                    "class": route_class,
                    "method": method,
                    "path": route.path,
                    "name": route.name,
                    "tags": list(route.tags),
                    "endpoint_module": getattr(route.endpoint, "__module__", ""),
                    "request_params": {
                        "path": _path_params(route),
                        "query": query_params,
                        "body": _body_params(route),
                    },
                    "response_fields": response_fields,
                    "is_paginated": _is_paginated(query_params, response_fields),
                    "requires_login": _requires_login(route.path),
                    "is_real_write_db": _is_known_business_write(route_class, method, route.path),
                    "frontend_connect_status": _frontend_connect_status(route_class, method),
                    "risk_note": risk_note,
                    "duplicate_method_path_count": duplicate_counter[(method, route.path)],
                    "registered_order": route_order[id(route)],
                }
            )
    return sorted(rows, key=lambda item: (item["path"], item["method"], item["registered_order"]))


def _split_top_level_args(text: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escape = False
    for index, char in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
            continue
        if char in "([{":
            depth += 1
            continue
        if char in ")]}":
            depth -= 1
            continue
        if char == "," and depth == 0:
            args.append(text[start:index].strip())
            start = index + 1
    tail = text[start:].strip()
    if tail:
        args.append(tail)
    return args


def _literal_string(value: str) -> str:
    value = value.strip()
    try:
        return str(ast.literal_eval(value))
    except (SyntaxError, ValueError):
        return value.strip("'\"`")


def _string_array(value: str) -> list[str]:
    return [_literal_string(match.group(0)) for match in re.finditer(r"'(?:\\'|[^'])*'|\"(?:\\\"|[^\"])*\"", value)]


def _field_gaps(value: str) -> list[str]:
    gaps: list[str] = []
    for match in re.finditer(r"gap\((.*?)\)", value):
        args = _split_top_level_args(match.group(1))
        if not args:
            continue
        schema = _literal_string(args[0])
        note = _literal_string(args[1]) if len(args) > 1 else f"contract 缺少 {schema} schema"
        gaps.append(f"{schema}: {note}")
    return gaps


def parse_frontend_page_registry_text(text: str) -> list[PageDefinitionSnapshot]:
    pages: list[PageDefinitionSnapshot] = []
    for match in re.finditer(r"page\((.*?)\),", text, flags=re.DOTALL):
        args = _split_top_level_args(match.group(1))
        if len(args) < 11:
            continue
        try:
            index = int(args[0])
        except ValueError:
            continue
        pages.append(
            PageDefinitionSnapshot(
                index=index,
                module=_literal_string(args[1]),
                title=_literal_string(args[2]),
                route=_literal_string(args[3]),
                template=_literal_string(args[4]),
                data_kind=_literal_string(args[6]),
                contract_schemas=_string_array(args[7]),
                field_gaps=_field_gaps(args[8]),
                actions=_string_array(args[9]),
                filters=_string_array(args[10]),
                api_path=_literal_string(args[11]) if len(args) >= 12 else None,
            )
        )
    return sorted(pages, key=lambda page: page.index)


def parse_frontend_page_registry(path: Path) -> list[PageDefinitionSnapshot]:
    if not path.exists():
        return []
    return parse_frontend_page_registry_text(path.read_text(encoding="utf-8"))


def _normalize_api_path(api_path: str | None) -> str | None:
    if not api_path:
        return None
    normalized = api_path.replace("<company>", "LY-FRONTEND-DEV").strip()
    return normalized.split("?", 1)[0].rstrip("/") or "/"


def build_page_matrix(pages: list[PageDefinitionSnapshot], route_catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog_paths = {(row["method"], row["path"].rstrip("/") or "/"): row for row in route_catalog}
    rows: list[dict[str, Any]] = []
    for page in pages:
        normalized_path = _normalize_api_path(page.api_path)
        route_row = catalog_paths.get(("GET", normalized_path)) if normalized_path else None
        if route_row is None and page.api_path:
            status = "api_path_not_found_in_backend"
            backend_class = None
        elif route_row is None:
            status = "missing_api_path"
            backend_class = None
        elif route_row["class"] == "A":
            status = "real_backend_route"
            backend_class = route_row["class"]
        elif route_row["class"] == "B":
            status = "dev_readiness_only"
            backend_class = route_row["class"]
        else:
            status = "not_frontend_direct"
            backend_class = route_row["class"]
        rows.append(
            {
                "index": page.index,
                "module": page.module,
                "page": page.title,
                "page_route": page.route,
                "template": page.template,
                "data_kind": page.data_kind,
                "api_path": page.api_path,
                "backend_status": status,
                "backend_class": backend_class,
                "contract_schemas": page.contract_schemas,
                "field_gaps": page.field_gaps,
                "priority": _page_priority(status, page),
            }
        )
    return rows


def _page_priority(status: str, page: PageDefinitionSnapshot) -> str:
    if status == "real_backend_route" and page.template in {"config_list", "list_table_filter", "report_table", "dashboard"}:
        return "P1_first_readonly_connect"
    if status in {"dev_readiness_only", "api_path_not_found_in_backend"}:
        return "P2_backend_alignment_needed"
    if status == "missing_api_path":
        return "P3_needs_product_contract"
    return "P4_hold"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_route_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["class"] for row in rows)
    lines = [
        "# 后端接口资产分类清单",
        "",
        "来源：FastAPI `app.routes` 自动导出；readiness/stub 以 `app/routers/frontend_readiness.py` 为准。",
        "",
        f"- A 类真实业务接口：{counts.get('A', 0)}",
        f"- B 类 dev/test readiness 只读接口：{counts.get('B', 0)}",
        f"- C 类 readiness flow 回执桩：{counts.get('C', 0)}",
        f"- D 类内部/诊断/不建议前端直连接口：{counts.get('D', 0)}",
        "",
        "| 类别 | Method | Path | 分页 | 登录 | 真实写库 | 前端接入状态 | 响应字段摘要 | 风险说明 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        fields = ", ".join(row["response_fields"][:12])
        if len(row["response_fields"]) > 12:
            fields += ", ..."
        lines.append(
            "| {class_} | {method} | `{path_}` | {paginated} | {login} | {write_db} | {status} | {fields} | {note} |".format(
                class_=row["class"],
                method=row["method"],
                path_=row["path"],
                paginated="是" if row["is_paginated"] else "否",
                login="是" if row["requires_login"] else "否",
                write_db="是" if row["is_real_write_db"] else "否",
                status=row["frontend_connect_status"],
                fields=fields or "-",
                note=row["risk_note"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_page_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["backend_status"] for row in rows)
    lines = [
        "# 前端页面到后端接口接入矩阵",
        "",
        f"来源：只读解析 `{DEFAULT_FRONTEND_REGISTRY}`；不修改前端文件。",
        "",
        f"- 真实后端可接：{counts.get('real_backend_route', 0)}",
        f"- dev readiness only：{counts.get('dev_readiness_only', 0)}",
        f"- apiPath 未命中后端：{counts.get('api_path_not_found_in_backend', 0)}",
        f"- 未声明 apiPath：{counts.get('missing_api_path', 0)}",
        "",
        "| 优先级 | 模块 | 页面 | 前端路由 | apiPath | 后端状态 | 契约/缺口 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        gaps = "; ".join(row["field_gaps"]) or ", ".join(row["contract_schemas"]) or "-"
        lines.append(
            f"| {row['priority']} | {row['module']} | {row['page']} | `{row['page_route']}` | "
            f"`{row['api_path'] or ''}` | {row['backend_status']} | {gaps} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_protocol_markdown(path: Path) -> None:
    lines = [
        "# 后端统一协议与权限基础规范",
        "",
        "本文件对应 `FastAPI后端长期开发单_20260616` 任务3，记录当前后端统一口径和后续硬门禁。",
        "",
        "## 响应信封",
        "",
        "- 成功：`{\"code\":\"0\",\"message\":\"success\",\"data\":...}`。",
        "- 失败：`{\"code\":错误码,\"message\":错误说明,\"data\":{} 或 null}`；可附带 `request_id`，但不得替换既有信封。",
        "- 当前仓库仍使用既有错误码，如 `AUTH_UNAUTHORIZED` / `AUTH_FORBIDDEN`；开发单建议的新错误码需要单独迁移任务，不能在本轮破坏既有前端/测试。",
        "",
        "## 分页",
        "",
        "- 标准列表：`{\"items\":[],\"total\":0,\"page\":1,\"page_size\":20}`。",
        "- 默认 `page=1`，`page_size=20`；readiness 端口上限 100，非法或超上限回落默认值。",
        "",
        "## 权限",
        "",
        "- 开发/测试联调用 `X-LY-Dev-User` 与 `X-LY-Dev-Roles`，生产必须关闭 dev header。",
        "- 业务接口必须后端鉴权，前端隐藏按钮不能替代接口权限。",
        "- readiness/stub 只能在 development/dev/local/test 挂载，生产 route table 不应出现对应路径。",
        "",
        "## 接入规则",
        "",
        "- A 类真实 GET 接口可进入前端只读接入候选。",
        "- A 类写接口必须经单独任务验证真实落库、权限、审计、幂等/冲突处理后才可接。",
        "- B 类 readiness 只读接口只作为临时联调辅助。",
        "- C 类 readiness flow 回执桩不得当作真实写接口。",
        "- D 类内部/诊断接口不得给页面直连。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_assets(*, frontend_registry: Path = DEFAULT_FRONTEND_REGISTRY, contracts_dir: Path | None = None) -> dict[str, Any]:
    app = load_app_for_env("test")
    contracts_dir = contracts_dir or BACKEND_ROOT / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    route_catalog = build_route_catalog(app)
    pages = parse_frontend_page_registry(frontend_registry)
    page_matrix = build_page_matrix(pages, route_catalog)

    route_json = contracts_dir / "backend_interface_asset_catalog.json"
    route_md = contracts_dir / "backend_interface_asset_catalog.md"
    page_json = contracts_dir / "frontend_backend_page_matrix.json"
    page_md = contracts_dir / "frontend_backend_page_matrix.md"
    protocol_md = contracts_dir / "backend_api_protocol_baseline.md"

    _write_json(route_json, {"source": "FastAPI app.routes", "routes": route_catalog})
    _write_route_markdown(route_md, route_catalog)
    _write_json(
        page_json,
        {
            "source": str(frontend_registry),
            "frontend_readonly": True,
            "pages": page_matrix,
        },
    )
    _write_page_markdown(page_md, page_matrix)
    _write_protocol_markdown(protocol_md)
    return {
        "route_count": len(route_catalog),
        "page_count": len(page_matrix),
        "files": [str(route_json), str(route_md), str(page_json), str(page_md), str(protocol_md)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend-registry", type=Path, default=DEFAULT_FRONTEND_REGISTRY)
    parser.add_argument("--contracts-dir", type=Path, default=BACKEND_ROOT / "contracts")
    args = parser.parse_args()
    result = export_assets(frontend_registry=args.frontend_registry, contracts_dir=args.contracts_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
