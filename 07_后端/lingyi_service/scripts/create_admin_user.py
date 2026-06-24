"""Create or update the single FastAPI admin login account.

Usage:
  LINGYI_DB_URL=... LINGYI_ADMIN_PASSWORD='...' ./.venv/bin/python scripts/create_admin_user.py --username admin

If LINGYI_ADMIN_PASSWORD is not set, the command prompts for the password.
"""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.auth import make_admin_password_hash
from app.models.auth import AuthBase
from app.models.auth import LyAuthAdminUser


def _engine_execution_options(database_url: str) -> dict[str, object]:
    if database_url.strip().lower().startswith("sqlite"):
        return {"schema_translate_map": {"ly_schema": None, "public": None}}
    return {}


def _read_password(env_name: str) -> str:
    password = os.getenv(env_name, "")
    if password:
        return password
    first = getpass.getpass("Admin password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise ValueError("passwords do not match")
    return first


def _parse_roles(raw_roles: str) -> list[str]:
    roles = sorted({role.strip() for role in raw_roles.split(",") if role.strip()})
    if not roles:
        raise ValueError("at least one role is required")
    return roles


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/update Lingyi FastAPI admin login account")
    parser.add_argument("--username", default="admin", help="admin username")
    parser.add_argument("--roles", default="System Manager", help="comma-separated roles")
    parser.add_argument("--password-env", default="LINGYI_ADMIN_PASSWORD", help="environment variable containing the password")
    parser.add_argument("--update", action="store_true", help="update an existing account instead of failing")
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        raise ValueError("username must not be empty")
    password = _read_password(args.password_env)
    roles = _parse_roles(args.roles)
    password_hash = make_admin_password_hash(password)

    database_url = os.getenv("LINGYI_DB_URL", "sqlite:///./lingyi_service.db")
    engine = create_engine(database_url, future=True, execution_options=_engine_execution_options(database_url))
    AuthBase.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with SessionLocal() as session:
        existing = session.query(LyAuthAdminUser).filter(LyAuthAdminUser.username == username).one_or_none()
        if existing is not None and not args.update:
            print(f"admin account already exists: {username}; pass --update to rotate password", file=sys.stderr)
            return 2
        try:
            if existing is None:
                existing = LyAuthAdminUser(
                    username=username,
                    password_hash=password_hash,
                    roles=roles,
                    status="active",
                    is_service_account=False,
                )
                session.add(existing)
                action = "created"
            else:
                existing.password_hash = password_hash
                existing.roles = roles
                existing.status = "active"
                existing.is_service_account = False
                action = "updated"
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

    print(f"admin account {action}: {username} roles={','.join(roles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
