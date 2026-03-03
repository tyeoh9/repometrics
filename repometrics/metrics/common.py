from __future__ import annotations

import subprocess
from pathlib import Path

DEFAULT_EXCLUDES = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}


def _git_context(root: Path) -> tuple[Path, Path] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return None
        repo_root = Path(proc.stdout.strip()).resolve()
        scan_root = root.resolve()
        rel_scan_root = scan_root.relative_to(repo_root)
        return repo_root, rel_scan_root
    except (OSError, ValueError):
        return None


def _git_scoped_files(root: Path) -> list[Path] | None:
    context = _git_context(root)
    if context is None:
        return None

    repo_root, rel_scan_root = context
    cmd = ["git", "-C", str(repo_root), "ls-files", "-co", "--exclude-standard", "-z"]
    if str(rel_scan_root) != ".":
        cmd.extend(["--", rel_scan_root.as_posix()])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=False,
        check=False,
    )
    if proc.returncode != 0:
        return None

    files: list[Path] = []
    for raw in proc.stdout.split(b"\x00"):
        if not raw:
            continue
        rel_repo_path = Path(raw.decode("utf-8"))
        abs_path = repo_root / rel_repo_path
        parts = rel_repo_path.parts
        if any(part in DEFAULT_EXCLUDES for part in parts):
            continue
        if abs_path.is_symlink() or not abs_path.is_file():
            continue
        try:
            abs_path.relative_to(root.resolve())
        except ValueError:
            continue
        files.append(abs_path)
    return files


def _fallback_files(root: Path) -> list[Path]:
    files: list[Path] = []
    root_resolved = root.resolve()
    for path in root_resolved.rglob("*"):
        parts = path.relative_to(root_resolved).parts
        if not parts:
            continue
        if any(part in DEFAULT_EXCLUDES for part in parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        files.append(path)
    return files


def walk_files(root: Path) -> list[Path]:
    scoped = _git_scoped_files(root)
    if scoped is not None:
        return scoped
    return _fallback_files(root)


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(1024)
            return b"\x00" in chunk
    except OSError:
        return False
