"""FastAPI-native local image upload routes."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC
from datetime import datetime
import hashlib
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import Request
from fastapi import UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import UPLOAD_INVALID_FILE
from app.core.exceptions import AppException
from app.core.exceptions import BusinessException
from app.core.permissions import MASTER_DATA_MANAGE
from app.core.permissions import STYLE_MASTER_MANAGE
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
ALLOWED_UPLOAD_SCOPES = {"material", "style_gallery"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def upload_root_dir() -> Path:
    """Return configured local upload root."""
    return Path(os.getenv("LINGYI_UPLOAD_DIR", "uploaded_files")).resolve()


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _err(exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message, "data": None})


def _require_scope(scope: str) -> str:
    normalized = str(scope or "").strip().lower()
    if normalized not in ALLOWED_UPLOAD_SCOPES:
        raise BusinessException(code=UPLOAD_INVALID_FILE, message="上传 scope 必须是 material 或 style_gallery")
    return normalized


def _require_image_file(file: UploadFile) -> str:
    content_type = str(file.content_type or "").split(";")[0].strip().lower()
    suffix = ALLOWED_IMAGE_CONTENT_TYPES.get(content_type)
    if not suffix:
        raise BusinessException(code=UPLOAD_INVALID_FILE, message="仅支持 jpg/png/webp/gif 图片")
    filename = str(file.filename or "").strip()
    if not filename:
        raise BusinessException(code=UPLOAD_INVALID_FILE, message="文件名不能为空")
    return suffix


def _require_valid_image_payload(*, content: bytes, suffix: str) -> None:
    if suffix == ".jpg":
        if not (content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9")):
            raise BusinessException(code=UPLOAD_INVALID_FILE, message="图片内容与格式不匹配")
        return
    if suffix == ".png":
        if not (content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 33 and content[12:16] == b"IHDR"):
            raise BusinessException(code=UPLOAD_INVALID_FILE, message="图片内容与格式不匹配")
        return
    if suffix == ".gif":
        if not (content.startswith(b"GIF87a") or content.startswith(b"GIF89a")):
            raise BusinessException(code=UPLOAD_INVALID_FILE, message="图片内容与格式不匹配")
        return
    if suffix == ".webp":
        if not (content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP"):
            raise BusinessException(code=UPLOAD_INVALID_FILE, message="图片内容与格式不匹配")
        return
    raise BusinessException(code=UPLOAD_INVALID_FILE, message="仅支持 jpg/png/webp/gif 图片")


def _require_upload_permission(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    scope: str,
) -> None:
    if scope == "material":
        PermissionService(session=session).require_action(
            current_user=current_user,
            request_obj=request,
            action=MASTER_DATA_MANAGE,
            module="master_data",
            resource_type="material",
        )
        return
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=STYLE_MASTER_MANAGE,
        module="style_master",
        resource_type="STYLE_GALLERY",
    )


def _audit_success(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    scope: str,
    data: dict[str, Any],
) -> None:
    AuditService(session).record_success(
        module="uploads",
        action="upload_image",
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=scope.upper(),
        resource_id=None,
        resource_no=str(data.get("stored_filename") or ""),
        before_data=None,
        after_data=data,
        context=AuditContext.from_request(request),
    )
    session.commit()


def _audit_failure(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    scope: str,
    filename: str | None,
    error_code: str,
) -> None:
    try:
        session.rollback()
    except Exception:
        pass
    AuditService(session).record_failure(
        module="uploads",
        action="upload_image",
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=scope.upper() if scope else "UNKNOWN",
        resource_id=None,
        resource_no=filename,
        before_data=None,
        after_data=None,
        error_code=error_code,
        context=AuditContext.from_request(request),
    )
    session.commit()


@router.post("/images")
async def upload_image(
    request: Request,
    scope: str = Form(...),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    normalized_scope = ""
    stored_path: Path | None = None
    try:
        normalized_scope = _require_scope(scope)
        _require_upload_permission(session=session, request=request, current_user=current_user, scope=normalized_scope)
        suffix = _require_image_file(file)
        day = datetime.now(UTC).strftime("%Y%m%d")
        relative_dir = Path("images") / normalized_scope / day
        target_dir = upload_root_dir() / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        size = 0
        content = bytearray()
        stored_filename = f"{uuid4().hex}{suffix}"
        stored_path = target_dir / stored_filename
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise BusinessException(code=UPLOAD_INVALID_FILE, message="图片大小不能超过 5MB")
            digest.update(chunk)
            content.extend(chunk)
        if size <= 0:
            raise BusinessException(code=UPLOAD_INVALID_FILE, message="图片文件不能为空")
        _require_valid_image_payload(content=bytes(content), suffix=suffix)

        with stored_path.open("wb") as handle:
            handle.write(content)

        relative_path = relative_dir / stored_filename
        url = "/" + str(Path("uploads") / relative_path).replace(os.sep, "/")
        data = {
            "scope": normalized_scope,
            "url": url,
            "thumbnail_url": url,
            "stored_filename": stored_filename,
            "original_filename": str(file.filename or ""),
            "content_type": str(file.content_type or ""),
            "size": size,
            "sha256": digest.hexdigest(),
        }
        _audit_success(session=session, request=request, current_user=current_user, scope=normalized_scope, data=data)
        return _ok(data)
    except AppException as exc:
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        _audit_failure(
            session=session,
            request=request,
            current_user=current_user,
            scope=normalized_scope,
            filename=str(file.filename or "") or None,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        error = BusinessException(code=DATABASE_WRITE_FAILED)
        _audit_failure(
            session=session,
            request=request,
            current_user=current_user,
            scope=normalized_scope,
            filename=str(file.filename or "") or None,
            error_code=error.code,
        )
        return _err(error)
    finally:
        await file.close()
