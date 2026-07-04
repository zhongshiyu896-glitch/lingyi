"""Build a local-only deployment rehearsal package for Stage 4.

The script never starts services, opens ports, or writes outside the selected
output directory. It copies build artifacts and writes operator templates so a
real deployment can be performed later after explicit approval.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONTEND_ROOT = Path("/Users/hh/Desktop/lingyi-frontend-1to1")
DEFAULT_OUTPUT_PARENT = Path("/Users/hh/Desktop")
FORBIDDEN_REMOTE_MARKERS = ("192.168.8.175",)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"[stage4] run: {' '.join(command)} (cwd={cwd})")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _copytree(src: Path, dst: Path) -> None:
    def _ignore(_directory: str, names: list[str]) -> set[str]:
        ignored = {"__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"}
        ignored.update(name for name in names if name.endswith((".pyc", ".pyo", ".db", ".sqlite", ".sqlite3")))
        return ignored

    shutil.copytree(src, dst, ignore=_ignore)


def _copy_backend(output_root: Path, *, include_uploads: bool) -> dict[str, str]:
    backend_root = output_root / "backend"
    backend_root.mkdir(parents=True, exist_ok=True)
    for directory in ("app", "migrations", "scripts"):
        _copytree(PROJECT_ROOT / directory, backend_root / directory)
    for filename in ("README.md", "requirements.txt", "requirements-dev.txt", "pytest.ini"):
        source = PROJECT_ROOT / filename
        if source.exists():
            shutil.copy2(source, backend_root / filename)

    runtime_root = output_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    db_source = PROJECT_ROOT / "lingyi_service.b.db"
    if db_source.exists():
        shutil.copy2(db_source, runtime_root / "lingyi_service.b.db")

    uploads_source = PROJECT_ROOT / "uploaded_files"
    if include_uploads and uploads_source.exists():
        _copytree(uploads_source, runtime_root / "uploaded_files")
        uploads_state = "copied"
    elif uploads_source.exists():
        (runtime_root / "uploaded_files").mkdir(exist_ok=True)
        uploads_state = "placeholder"
    else:
        uploads_state = "missing"

    return {
        "backend_root": str(backend_root),
        "runtime_root": str(runtime_root),
        "db_state": "copied" if db_source.exists() else "missing",
        "uploads_state": uploads_state,
    }


def _copy_frontend(frontend_root: Path, output_root: Path) -> dict[str, str]:
    dist_source = frontend_root / "dist"
    if not dist_source.exists():
        raise FileNotFoundError(f"frontend dist not found after build: {dist_source}")
    frontend_target = output_root / "frontend"
    frontend_target.mkdir(parents=True, exist_ok=True)
    _copytree(dist_source, frontend_target / "dist")
    shutil.copy2(frontend_root / "package.json", frontend_target / "package.json")
    return {"frontend_root": str(frontend_target), "dist_state": "copied"}


def _write_templates(output_root: Path) -> None:
    env_dir = output_root / "env"
    systemd_dir = output_root / "systemd"
    nginx_dir = output_root / "nginx"
    env_dir.mkdir(parents=True, exist_ok=True)
    systemd_dir.mkdir(parents=True, exist_ok=True)
    nginx_dir.mkdir(parents=True, exist_ok=True)

    (env_dir / "lingyi.env.example").write_text(
        "\n".join(
            [
                "APP_ENV=production",
                "LINGYI_PERMISSION_SOURCE=fastapi",
                "LINGYI_ALLOW_DEV_AUTH=false",
                "LINGYI_DB_URL=sqlite:////opt/lingyi/runtime/lingyi_service.db",
                "LINGYI_LOCAL_SESSION_SECRET=REPLACE_WITH_LONG_RANDOM_SECRET",
                "LINGYI_ADMIN_PASSWORD=SET_ONLY_WHEN_CREATING_ADMIN",
                "LINGYI_AUTH_HARDENING_ENABLED=true",
                "LINGYI_AUTH_RATE_LIMIT_ENABLED=true",
                "LINGYI_AUTH_LOGIN_MAX_FAILURES=5",
                "LINGYI_AUTH_LOGIN_WINDOW_SECONDS=300",
                "LINGYI_AUTH_LOGIN_LOCK_SECONDS=900",
                "LINGYI_AUTH_SESSION_MAX_AGE_SECONDS=3600",
                "LINGYI_AUTH_STRONG_PASSWORD_ENABLED=true",
                "LINGYI_AUTH_STRONG_PASSWORD_MIN_LENGTH=12",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (systemd_dir / "lingyi-backend.service").write_text(
        "\n".join(
            [
                "[Unit]",
                "Description=Lingyi FastAPI backend",
                "After=network.target",
                "",
                "[Service]",
                "WorkingDirectory=/opt/lingyi/backend",
                "EnvironmentFile=/opt/lingyi/env/lingyi.env",
                "ExecStart=/opt/lingyi/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000",
                "Restart=always",
                "RestartSec=5",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (nginx_dir / "lingyi.conf").write_text(
        "\n".join(
            [
                "server {",
                "    listen 80;",
                "    server_name example.com;",
                "    return 301 https://$host$request_uri;",
                "}",
                "",
                "server {",
                "    listen 443 ssl http2;",
                "    server_name example.com;",
                "    root /opt/lingyi/frontend/dist;",
                "    index index.html;",
                "",
                "    location /api/ {",
                "        proxy_pass http://127.0.0.1:8000;",
                "        proxy_set_header Host $host;",
                "        proxy_set_header X-Forwarded-Proto https;",
                "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
                "    }",
                "",
                "    location / {",
                "        try_files $uri $uri/ /index.html;",
                "    }",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (output_root / "RUNBOOK.md").write_text(
        "\n".join(
            [
                "# Lingyi Stage 4 Local Deployment Rehearsal",
                "",
                "This package is a local dry run only. It is not a deployed server.",
                "",
                "## Real deployment checklist",
                "",
                "1. Copy backend, frontend, runtime, env, systemd, and nginx folders to /opt/lingyi.",
                "2. Create /opt/lingyi/backend/.venv and install requirements.txt.",
                "3. Copy env/lingyi.env.example to env/lingyi.env and replace every placeholder.",
                "4. Run migrations or reset only against an approved empty production database.",
                "5. Create or rotate the admin user with scripts/create_admin_user.py.",
                "6. Install the systemd service and nginx config.",
                "7. Enable HTTPS certificate automation before exposing port 443.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _assert_local_only(frontend_root: Path, output_root: Path) -> None:
    values = [str(frontend_root), str(output_root)]
    values.extend(f"{key}={value}" for key, value in os.environ.items() if key.startswith(("LINGYI_", "VITE_LINGYI_")))
    combined = "\n".join(values)
    for marker in FORBIDDEN_REMOTE_MARKERS:
        if marker in combined:
            raise RuntimeError(f"forbidden remote marker present in rehearsal inputs: {marker}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local-only Lingyi deployment rehearsal package")
    parser.add_argument("--frontend-root", type=Path, default=DEFAULT_FRONTEND_ROOT)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--include-uploads", action="store_true", help="copy uploaded_files into the rehearsal runtime")
    parser.add_argument("--skip-frontend-build", action="store_true", help="reuse existing frontend dist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frontend_root = args.frontend_root.expanduser().resolve()
    output_root = (args.output_root or DEFAULT_OUTPUT_PARENT / f"lingyi_stage4_deploy_dry_run_{_timestamp()}").expanduser().resolve()
    _assert_local_only(frontend_root, output_root)

    if not frontend_root.exists():
        raise FileNotFoundError(f"frontend root not found: {frontend_root}")

    if output_root.exists():
        raise FileExistsError(f"output root already exists: {output_root}")
    output_root.mkdir(parents=True)

    if not args.skip_frontend_build:
        _run(["npm", "run", "build"], cwd=frontend_root)
    _run([sys.executable, "-m", "compileall", "-q", "app", "scripts", "migrations"], cwd=PROJECT_ROOT)
    _run([sys.executable, "scripts/reset_dev_db.py", "--database-url", "sqlite:///./stage4_rehearsal.db", "--dry-run"], cwd=PROJECT_ROOT)

    backend_summary = _copy_backend(output_root, include_uploads=args.include_uploads)
    frontend_summary = _copy_frontend(frontend_root, output_root)
    _write_templates(output_root)

    summary = {
        "status": "ok",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "frontend_source": str(frontend_root),
        "output_root": str(output_root),
        "local_only": True,
        "started_services": False,
        "opened_ports": [],
        "backend": backend_summary,
        "frontend": frontend_summary,
    }
    (output_root / "stage4_deploy_dry_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
