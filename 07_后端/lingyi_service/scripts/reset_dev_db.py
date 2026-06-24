#!/usr/bin/env python3
"""Reset a local/development Lingyi database to an empty schema.

This is intentionally a development-only tool. It refuses production app
environments, refuses remote database hosts, checks that port 8000 is not in
use, recreates the schema, and then delegates admin creation to
scripts/create_admin_user.py so passwords are never hard-coded here.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_LOCAL_DEV_DATABASE_URL = "sqlite:///./lingyi_service.local.db"
PRODUCTION_MARKERS = (
    "prod",
    "production",
    "rds.amazonaws.com",
    "amazonaws.com",
    "cloudsql",
    "supabase",
    "neon.tech",
    "render.com",
    "railway.app",
    "aliyuncs.com",
    "postgres.database.azure.com",
    "database.windows.net",
)
LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}


class ResetSafetyError(RuntimeError):
    """Raised when a requested reset is not safe."""


@dataclass(frozen=True)
class DatabaseTarget:
    raw_url: str
    source: str
    app_env: str
    url: URL
    kind: str
    sqlite_path: Path | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset the Lingyi local/dev database to empty tables")
    parser.add_argument("--database-url", help="database URL override; defaults to LINGYI_DB_URL/DATABASE_URL/local_dev")
    parser.add_argument("--app-env", help="APP_ENV override used for safety checks")
    parser.add_argument("--yes", action="store_true", help="skip the interactive RESET confirmation")
    parser.add_argument("--dry-run", action="store_true", help="print checks/actions without deleting or creating data")
    parser.add_argument("--with-seed", action="store_true", help="load local development seed data after rebuilding tables")
    parser.add_argument("--clean-uploads", action="store_true", help="delete files below uploaded_files/")
    parser.add_argument("--port", type=int, default=8000, help="backend port that must be stopped before reset")
    parser.add_argument("--admin-username", default="admin", help="admin username to create/update")
    parser.add_argument("--admin-roles", default="System Manager", help="comma-separated admin roles")
    parser.add_argument(
        "--admin-password-env",
        default="LINGYI_ADMIN_PASSWORD",
        help="environment variable consumed by scripts/create_admin_user.py",
    )
    return parser.parse_args()


def resolve_database_target(args: argparse.Namespace) -> DatabaseTarget:
    if args.database_url:
        raw_url = args.database_url.strip()
        source = "--database-url"
    elif os.getenv("LINGYI_DB_URL", "").strip():
        raw_url = os.environ["LINGYI_DB_URL"].strip()
        source = "LINGYI_DB_URL"
    elif os.getenv("DATABASE_URL", "").strip():
        raw_url = os.environ["DATABASE_URL"].strip()
        source = "DATABASE_URL"
    else:
        raw_url = DEFAULT_LOCAL_DEV_DATABASE_URL
        source = "app/local_dev default"

    app_env = (args.app_env or os.getenv("APP_ENV", "development")).strip() or "development"
    try:
        url = make_url(raw_url)
    except Exception as exc:  # pragma: no cover - make_url keeps detail in exc
        raise ResetSafetyError(f"invalid database URL from {source}: {exc}") from exc

    backend = url.get_backend_name().lower()
    if backend.startswith("sqlite"):
        sqlite_path = resolve_sqlite_path(url)
        return DatabaseTarget(raw_url=raw_url, source=source, app_env=app_env, url=url, kind="sqlite", sqlite_path=sqlite_path)
    if backend.startswith("postgresql") or backend.startswith("postgres"):
        return DatabaseTarget(raw_url=raw_url, source=source, app_env=app_env, url=url, kind="postgres")
    raise ResetSafetyError(f"unsupported database backend for dev reset: {backend}")


def resolve_sqlite_path(url: URL) -> Path:
    database = url.database
    if not database or database == ":memory:":
        raise ResetSafetyError("refusing to reset sqlite memory/empty database")
    path = Path(database)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_safe_target(target: DatabaseTarget) -> None:
    if target.app_env.strip().lower() == "production":
        raise ResetSafetyError("APP_ENV=production; refusing to reset any database")

    raw_lower = target.raw_url.lower()
    if any(marker in raw_lower for marker in PRODUCTION_MARKERS):
        raise ResetSafetyError("database URL contains a production marker; refusing to reset")

    if target.kind == "sqlite":
        assert_safe_sqlite_target(target)
        return
    assert_safe_postgres_target(target)


def assert_safe_sqlite_target(target: DatabaseTarget) -> None:
    assert target.sqlite_path is not None
    allowed_roots = [PROJECT_ROOT.resolve(), Path("/tmp").resolve(), Path("/private/tmp").resolve()]
    if not any(is_relative_to(target.sqlite_path, root) for root in allowed_roots):
        raise ResetSafetyError(f"sqlite path is outside the service project/tmp roots: {target.sqlite_path}")
    name_lower = target.sqlite_path.name.lower()
    if any(marker in name_lower for marker in ("prod", "production")):
        raise ResetSafetyError(f"sqlite file name looks production-like: {target.sqlite_path.name}")


def assert_safe_postgres_target(target: DatabaseTarget) -> None:
    host = target.url.host or ""
    database = target.url.database or ""
    if host not in LOCAL_HOSTS:
        raise ResetSafetyError(f"postgres host is not local/dev: {host}")
    if any(marker in database.lower() for marker in ("prod", "production")):
        raise ResetSafetyError(f"postgres database name looks production-like: {database}")


def print_target_summary(target: DatabaseTarget, args: argparse.Namespace) -> None:
    print("reset_dev_db target:")
    print(f"  app_env: {target.app_env}")
    print(f"  database_url: {target.raw_url}")
    print(f"  database_url_source: {target.source}")
    print(f"  database_kind: {target.kind}")
    if target.sqlite_path is not None:
        print(f"  sqlite_path: {target.sqlite_path}")
    if target.kind == "postgres":
        print(f"  postgres_host: {target.url.host or '(local socket)'}")
        print(f"  postgres_database: {target.url.database}")
    print(f"  with_seed: {str(args.with_seed).lower()}")
    print(f"  clean_uploads: {str(args.clean_uploads).lower()}")
    print(f"  admin_username: {args.admin_username}")


def port_is_open(port: int) -> bool:
    for host in ("127.0.0.1", "localhost"):
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            continue
    return False


def assert_backend_stopped(port: int, dry_run: bool) -> None:
    if not port_is_open(port):
        print(f"port_check: ok, {port} is not listening")
        return
    message = f"port_check: blocked, {port} is listening; stop the backend before reset"
    if dry_run:
        print(message)
        return
    raise ResetSafetyError(message)


def confirm_reset(args: argparse.Namespace) -> None:
    if args.dry_run:
        print("confirmation: dry-run, no destructive action")
        return
    if args.yes:
        print("confirmation: --yes supplied")
        return
    if not sys.stdin.isatty():
        raise ResetSafetyError("non-interactive shell; pass --yes after reviewing the printed target")
    typed = input("Type RESET to delete this dev database and rebuild empty tables: ").strip()
    if typed != "RESET":
        raise ResetSafetyError("confirmation did not match RESET; aborted")


def engine_options(target: DatabaseTarget) -> dict[str, object]:
    if target.kind == "sqlite":
        return {"schema_translate_map": {"ly_schema": None, "public": None}}
    return {}


def create_target_engine(target: DatabaseTarget):
    return create_engine(target.raw_url, future=True, execution_options=engine_options(target))


def reset_sqlite_files(target: DatabaseTarget, dry_run: bool) -> list[str]:
    assert target.sqlite_path is not None
    deleted: list[str] = []
    for path in (
        target.sqlite_path,
        Path(f"{target.sqlite_path}-wal"),
        Path(f"{target.sqlite_path}-shm"),
        Path(f"{target.sqlite_path}-journal"),
    ):
        if path.exists():
            deleted.append(str(path))
            if not dry_run:
                path.unlink()
    print("sqlite_delete:")
    if deleted:
        for path in deleted:
            print(f"  {path}")
    else:
        print("  no existing sqlite files")
    return deleted


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def reset_postgres_schema(target: DatabaseTarget, dry_run: bool) -> list[str]:
    actions = ["drop schema ly_schema cascade", "create schema ly_schema"]
    engine = create_target_engine(target)
    try:
        if dry_run:
            inspector = inspect(engine)
            public_tables = inspector.get_table_names(schema="public")
            actions.extend([f"drop public table {name}" for name in public_tables])
            return actions
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS ly_schema CASCADE"))
            conn.execute(text("CREATE SCHEMA ly_schema"))
            inspector = inspect(conn)
            for table_name in inspector.get_table_names(schema="public"):
                if table_name == "spatial_ref_sys":
                    continue
                conn.execute(text(f"DROP TABLE IF EXISTS public.{quote_identifier(table_name)} CASCADE"))
                actions.append(f"drop public table {table_name}")
    finally:
        engine.dispose()
    print("postgres_reset:")
    for action in actions:
        print(f"  {action}")
    return actions


def rebuild_schema(target: DatabaseTarget, dry_run: bool) -> str:
    alembic_ini = PROJECT_ROOT / "alembic.ini"
    alembic_env = PROJECT_ROOT / "migrations" / "env.py"
    if alembic_ini.exists() and alembic_env.exists():
        if dry_run:
            print(f"migration: would run alembic upgrade head using {alembic_ini}")
            return "alembic upgrade head"
        env = os.environ.copy()
        env["LINGYI_DB_URL"] = target.raw_url
        subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
        )
        print("migration: alembic upgrade head")
        return "alembic upgrade head"

    if dry_run:
        print("migration: alembic config missing; would create tables from SQLAlchemy model metadata")
        return "sqlalchemy metadata create_all"
    create_tables_from_models(target)
    print("migration: alembic config missing; created tables from SQLAlchemy model metadata")
    return "sqlalchemy metadata create_all"


def create_tables_from_models(target: DatabaseTarget) -> None:
    os.environ["LINGYI_DB_URL"] = target.raw_url
    engine = create_target_engine(target)
    try:
        if target.kind == "postgres":
            with engine.begin() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS ly_schema"))

        from app.models.audit import Base as AuditBase
        from app.models.auth import AuthBase
        from app.models.bom import Base as BomBase
        from app.models.bom import LyApparelBom
        from app.models.factory_statement import Base as FactoryStatementBase
        from app.models.finance_approval import Base as FinanceApprovalBase
        from app.models.master_data import Base as MasterDataBase
        from app.models.material_purchase import Base as MaterialPurchaseBase
        from app.models.production import Base as ProductionBase
        from app.models.quality import Base as QualityBase
        import app.models.quality_outbox  # noqa: F401
        from app.models.sample import Base as SampleBase
        from app.models.sales_order import Base as SalesOrderBase
        from app.models.style_master import Base as StyleMasterBase
        from app.models.style_profit import Base as StyleProfitBase
        from app.models.subcontract import Base as SubcontractBase
        import app.models.warehouse  # noqa: F401
        from app.models.workshop import Base as WorkshopBase

        metadatas = [
            AuthBase.metadata,
            AuditBase.metadata,
            BomBase.metadata,
            ProductionBase.metadata,
            FactoryStatementBase.metadata,
            FinanceApprovalBase.metadata,
            MasterDataBase.metadata,
            MaterialPurchaseBase.metadata,
            SampleBase.metadata,
            SalesOrderBase.metadata,
            StyleMasterBase.metadata,
            QualityBase.metadata,
            StyleProfitBase.metadata,
            WorkshopBase.metadata,
        ]
        for metadata in metadatas:
            metadata.create_all(bind=engine)

        if "ly_schema.ly_apparel_bom" not in SubcontractBase.metadata.tables:
            LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=engine)
    finally:
        engine.dispose()


def run_optional_seed(target: DatabaseTarget, dry_run: bool) -> None:
    if dry_run:
        print("seed: would load local_dev seed data")
        return
    if target.kind != "sqlite":
        raise ResetSafetyError("--with-seed is only supported for sqlite local_dev databases")
    os.environ["LINGYI_DB_URL"] = target.raw_url
    os.environ["APP_ENV"] = "development"
    import app.local_dev  # noqa: F401

    print("seed: loaded app.local_dev seed data")


def recreate_admin(target: DatabaseTarget, args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"admin: would run scripts/create_admin_user.py for {args.admin_username}")
        return
    if not os.getenv(args.admin_password_env, "") and not sys.stdin.isatty():
        raise ResetSafetyError(
            f"{args.admin_password_env} is not set and stdin is non-interactive; "
            "set the env var or run interactively"
        )
    env = os.environ.copy()
    env["LINGYI_DB_URL"] = target.raw_url
    env["APP_ENV"] = target.app_env
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "create_admin_user.py"),
            "--username",
            args.admin_username,
            "--roles",
            args.admin_roles,
            "--password-env",
            args.admin_password_env,
            "--update",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )
    print(f"admin: recreated {args.admin_username}")


def clean_uploads(dry_run: bool) -> list[str]:
    upload_root = PROJECT_ROOT / "uploaded_files"
    removed: list[str] = []
    if not upload_root.exists():
        print(f"uploads: {upload_root} does not exist")
        return removed
    for child in sorted(upload_root.iterdir(), key=lambda path: path.name):
        removed.append(str(child))
        if dry_run:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    print("uploads_clean:")
    if removed:
        for path in removed:
            print(f"  {path}")
    else:
        print("  no files")
    return removed


def count_business_rows(target: DatabaseTarget) -> int:
    engine = create_target_engine(target)
    excluded = {"ly_auth_admin_user", "alembic_version"}
    total = 0
    try:
        inspector = inspect(engine)
        schema = None if target.kind == "sqlite" else "ly_schema"
        for table_name in inspector.get_table_names(schema=schema):
            if table_name in excluded:
                continue
            table_ref = quote_identifier(table_name)
            if schema:
                table_ref = f"{quote_identifier(schema)}.{table_ref}"
            with engine.connect() as conn:
                total += int(conn.execute(text(f"SELECT COUNT(*) FROM {table_ref}")).scalar_one())
    finally:
        engine.dispose()
    return total


def main() -> int:
    args = parse_args()
    try:
        target = resolve_database_target(args)
        print_target_summary(target, args)
        assert_safe_target(target)
        print("safety: ok")
        assert_backend_stopped(args.port, args.dry_run)
        confirm_reset(args)

        if target.kind == "sqlite":
            reset_sqlite_files(target, args.dry_run)
        else:
            reset_postgres_schema(target, args.dry_run)

        rebuild_schema(target, args.dry_run)
        if args.with_seed:
            run_optional_seed(target, args.dry_run)
        recreate_admin(target, args)
        if args.clean_uploads:
            clean_uploads(args.dry_run)

        if args.dry_run:
            print("result: dry-run complete; database was not modified")
        else:
            print(f"business_rows_after_reset: {count_business_rows(target)}")
            print("result: reset complete")
        return 0
    except ResetSafetyError as exc:
        print(f"reset_dev_db refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
