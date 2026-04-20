"""ERPNext read adapter for quality source validation under fail-closed policy."""

from __future__ import annotations

import json
from typing import Any
from urllib import parse
from urllib import request as urllib_request

from fastapi import Request

from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import QUALITY_INVALID_SOURCE
from app.core.error_codes import QUALITY_SOURCE_UNAVAILABLE
from app.core.error_codes import message_of
from app.core.exceptions import BusinessException
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_fail_closed_adapter import map_erpnext_exception
from app.services.erpnext_fail_closed_adapter import normalize_erpnext_response
from app.services.erpnext_fail_closed_adapter import require_submitted_doc


class ERPNextQualityAdapter:
    """Read ERPNext resources for quality source validation."""

    def __init__(self, request_obj: Request | None = None, base_url: str = ""):
        self.request_obj = request_obj
        self.base_url = base_url.strip().rstrip("/")

    def require_resource(self, *, doctype: str, name: str, require_submitted: bool) -> dict[str, Any]:
        if not self.base_url:
            raise BusinessException(code=QUALITY_SOURCE_UNAVAILABLE, message=message_of(QUALITY_SOURCE_UNAVAILABLE))
        headers = self._build_headers()
        if not headers:
            raise BusinessException(code=QUALITY_SOURCE_UNAVAILABLE, message="ERPNext 质量来源校验缺少鉴权上下文")
        fields = parse.quote(
            json.dumps(
                [
                    "name",
                    "company",
                    "docstatus",
                    "disabled",
                    "status",
                    "supplier",
                    "item_code",
                    "items",
                ],
                separators=(",", ":"),
            ),
            safe="",
        )
        path = f"/api/resource/{parse.quote(doctype)}/{parse.quote(name, safe='')}?fields={fields}"
        req = urllib_request.Request(url=f"{self.base_url}{path}", method="GET", headers=headers)
        try:
            with urllib_request.urlopen(req, timeout=5) as response:
                body = response.read().decode("utf-8")
            payload = json.loads(body)
            normalized = normalize_erpnext_response(payload, doctype=doctype, resource_name=name)
            if require_submitted:
                normalized = require_submitted_doc(normalized)
            if not isinstance(normalized.data, dict):
                raise TypeError("normalized data is not dict")
            data = dict(normalized.data)
            if self._truthy_disabled(data.get("disabled")):
                raise BusinessException(code=QUALITY_INVALID_SOURCE, message=f"{doctype} 已禁用")
            return data
        except BusinessException:
            raise
        except ERPNextAdapterException as exc:
            raise BusinessException(code=self._quality_code_for_erpnext(exc), message=exc.safe_message) from exc
        except Exception as exc:
            mapped = map_erpnext_exception(exc, doctype=doctype, resource_name=name)
            raise BusinessException(code=self._quality_code_for_erpnext(mapped), message=mapped.safe_message) from exc

    def _build_headers(self) -> dict[str, str] | None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.request_obj is not None:
            authorization = self.request_obj.headers.get("Authorization")
            cookie = self.request_obj.headers.get("Cookie")
            if authorization:
                headers["Authorization"] = authorization
            if cookie:
                headers["Cookie"] = cookie
        if "Authorization" not in headers and "Cookie" not in headers:
            return None
        return headers

    @staticmethod
    def _truthy_disabled(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes"}

    @staticmethod
    def _quality_code_for_erpnext(exc: ERPNextAdapterException) -> str:
        if exc.error_code == EXTERNAL_SERVICE_UNAVAILABLE:
            return QUALITY_SOURCE_UNAVAILABLE
        return QUALITY_INVALID_SOURCE

