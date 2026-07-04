"""Create and verify a local Lingyi database/uploads backup.

This script is intentionally local-only. Restore verification writes into a
temporary directory below the selected backup root and never replaces the live
database or uploads directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP_ROOT = Path("/Users/hh/Desktop/领意_本地备份/stage4_db_uploads")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_stats(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"files": 0, "bytes": 0}
    files = 0
    total_bytes = 0
    for item in path.rglob("*"):
        if item.is_file():
            files += 1
            total_bytes += item.stat().st_size
    return {"files": files, "bytes": total_bytes}


def _sqlite_integrity_check(db_path: Path) -> str:
    with sqlite3.connect(str(db_path)) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "missing-result"


def _archive_uploads(source_dir: Path, target_tar: Path) -> dict[str, int | str]:
    stats = _directory_stats(source_dir)
    if not source_dir.exists():
        return {**stats, "state": "missing"}
    with tarfile.open(target_tar, "w:gz") as tar:
        tar.add(source_dir, arcname="uploaded_files")
    return {**stats, "state": "archived", "archive_sha256": _sha256(target_tar)}


def _restore_check(snapshot_dir: Path, manifest: dict[str, object]) -> dict[str, object]:
    restored: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="restore_check_", dir=snapshot_dir.parent) as tmp:
        tmp_root = Path(tmp)
        db_backup = snapshot_dir / "lingyi_service.b.db"
        if db_backup.exists():
            restored_db = tmp_root / "lingyi_service.restore.db"
            shutil.copy2(db_backup, restored_db)
            restored["db_sha256_matches"] = _sha256(restored_db) == manifest["db"]["sha256"]  # type: ignore[index]
            restored["db_integrity_check"] = _sqlite_integrity_check(restored_db)
        uploads_archive = snapshot_dir / "uploaded_files.tar.gz"
        if uploads_archive.exists():
            with tarfile.open(uploads_archive, "r:gz") as tar:
                tar.extractall(tmp_root)
            restored["uploads_files"] = _directory_stats(tmp_root / "uploaded_files")["files"]
            restored["uploads_archive_sha256_matches"] = _sha256(uploads_archive) == manifest["uploads"].get("archive_sha256")  # type: ignore[index]
    restored["state"] = "verified"
    return restored


def _apply_retention(backup_root: Path, retain: int) -> list[str]:
    if retain <= 0 or not backup_root.exists():
        return []
    snapshots = sorted([path for path in backup_root.iterdir() if path.is_dir() and path.name.startswith("snapshot_")])
    to_delete = snapshots[:-retain]
    deleted: list[str] = []
    for path in to_delete:
        shutil.rmtree(path)
        deleted.append(str(path))
    return deleted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and verify Lingyi local backup")
    parser.add_argument("--db-path", type=Path, default=PROJECT_ROOT / "lingyi_service.b.db")
    parser.add_argument("--uploads-dir", type=Path, default=PROJECT_ROOT / "uploaded_files")
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    parser.add_argument("--retain", type=int, default=14, help="number of snapshot_* directories to keep")
    parser.add_argument("--restore-check", action="store_true", help="verify backup by restoring into a temporary directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = args.db_path.expanduser().resolve()
    uploads_dir = args.uploads_dir.expanduser().resolve()
    backup_root = args.backup_root.expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")

    backup_root.mkdir(parents=True, exist_ok=True)
    snapshot_dir = backup_root / f"snapshot_{_timestamp()}"
    if snapshot_dir.exists():
        raise FileExistsError(snapshot_dir)
    snapshot_dir.mkdir()

    db_backup = snapshot_dir / db_path.name
    shutil.copy2(db_path, db_backup)
    manifest: dict[str, object] = {
        "status": "ok",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "db_path": str(db_path),
            "uploads_dir": str(uploads_dir),
        },
        "snapshot_dir": str(snapshot_dir),
        "db": {
            "filename": db_backup.name,
            "bytes": db_backup.stat().st_size,
            "sha256": _sha256(db_backup),
            "integrity_check": _sqlite_integrity_check(db_backup),
        },
        "uploads": _archive_uploads(uploads_dir, snapshot_dir / "uploaded_files.tar.gz"),
    }
    if args.restore_check:
        manifest["restore_check"] = _restore_check(snapshot_dir, manifest)
    manifest["retention_deleted"] = _apply_retention(backup_root, args.retain)

    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
