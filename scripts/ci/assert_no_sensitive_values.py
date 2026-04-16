#!/usr/bin/env python3
"""Conservative credential-shape scanner for CI reports and changed text files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
TOKEN_PATTERN = re.compile(
    r"(?i)(password|passwd|token|secret|authorization|cookie|dsn)\s*[:=]\s*['\"]?([^'\"\s]{8,})"
)
URI_PATTERN = re.compile(r"(?i)(postgresql|mysql|mongodb)(?:\+\w+)?://[^\s:@]+:[^\s@]+@")
SECRET_REFERENCE_PATTERN = re.compile(r"\$\{\{\s*secrets\.[A-Za-z0-9_]+\s*\}\}")
REDACTED_VALUE_PATTERN = re.compile(r"(?i)^(\*{3,}|<redacted>|\[redacted\])$")


def is_placeholder_value(value: str) -> bool:
    """Allow references to platform secret placeholders, never literal credentials."""

    return bool("${{" in value or SECRET_REFERENCE_PATTERN.search(value) or REDACTED_VALUE_PATTERN.search(value))


def iter_files(paths: list[Path]):
    for item in paths:
        if not item.exists():
            continue
        if item.is_dir():
            for child in item.rglob("*"):
                if any(part in SKIP_DIRS for part in child.parts):
                    continue
                if child.is_file():
                    yield child
        elif item.is_file():
            if not any(part in SKIP_DIRS for part in item.parts):
                yield item


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def main() -> int:
    targets = [Path(arg) for arg in sys.argv[1:]] or [Path(".")]
    findings: list[str] = []
    for path in iter_files(targets):
        text = read_text(path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            token_findings = [
                match
                for match in TOKEN_PATTERN.finditer(line)
                if not is_placeholder_value(match.group(2))
            ]
            uri_findings = [
                match
                for match in URI_PATTERN.finditer(line)
                if not is_placeholder_value(match.group(0))
            ]
            if token_findings or uri_findings:
                findings.append(f"{path}:{line_no}: credential-shaped value detected")
    if findings:
        print("Sensitive scan failed:", file=sys.stderr)
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    print("Sensitive scan passed: no credential-shaped values detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
