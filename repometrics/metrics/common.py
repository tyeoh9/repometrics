from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

DEFAULT_EXCLUDES = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}


def gitignore_patterns(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return []
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--others", "-i", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0:
            return []
        patterns = []
        for line in out.stdout.splitlines():
            line = line.strip()
            if line:
                patterns.append(line)
        return patterns
    except OSError:
        return []


def _is_ignored(rel_path: str, patterns: list[str]) -> bool:
    if rel_path.startswith(".git/"):
        return True
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def walk_files(root: Path) -> list[Path]:
    patterns = gitignore_patterns(root)
    files: list[Path] = []
    for path in root.rglob("*"):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel == ".":
            continue
        parts = rel.split("/")
        if any(part in DEFAULT_EXCLUDES for part in parts):
            continue
        if _is_ignored(rel, patterns):
            continue
        if path.is_symlink():
            continue
        if path.is_file():
            files.append(path)
    return files


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(1024)
            return b"\x00" in chunk
    except OSError:
        return False
