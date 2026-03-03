from __future__ import annotations

from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.metrics.common import walk_files
from repometrics.models import CategoryResult, StructureMetrics


def _non_empty_loc(path: Path) -> int:
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except (OSError, UnicodeDecodeError):
        return 0


def _depth(root: Path, path: Path) -> int:
    rel_parts = path.relative_to(root).parts
    return max(len(rel_parts) - 1, 0)


def analyze(path: Path, config: ScanConfig) -> CategoryResult[StructureMetrics]:
    del config
    all_files = walk_files(path)
    py_files = [file_path for file_path in all_files if file_path.suffix == ".py"]

    depths = [_depth(path, file_path) for file_path in py_files]
    total_py = len(py_files)
    max_depth = max(depths) if depths else 0
    avg_depth = (sum(depths) / total_py) if total_py else 0.0

    largest_file_loc = 0
    largest_file_path = ""
    files_gt_500 = 0
    files_gt_1000 = 0
    total_python_loc = 0
    for file_path in py_files:
        loc = _non_empty_loc(file_path)
        total_python_loc += loc
        if loc > largest_file_loc:
            largest_file_loc = loc
            largest_file_path = str(file_path.relative_to(path))
        if loc > 500:
            files_gt_500 += 1
        if loc > 1000:
            files_gt_1000 += 1

    empty_dirs = 0
    for dir_path in path.rglob("*"):
        if not dir_path.is_dir() or dir_path.is_symlink():
            continue
        try:
            relative = dir_path.relative_to(path)
        except ValueError:
            continue
        if relative == Path("."):
            continue
        try:
            next(dir_path.iterdir())
        except StopIteration:
            empty_dirs += 1
        except OSError:
            continue

    metrics = StructureMetrics(
        total_py_files=total_py,
        max_depth=max_depth,
        avg_depth=avg_depth,
        files_gt_500_loc=files_gt_500,
        files_gt_1000_loc=files_gt_1000,
        largest_file_path=largest_file_path,
        largest_file_loc=largest_file_loc,
        empty_dirs=empty_dirs,
        total_python_loc=total_python_loc,
    )
    return CategoryResult(status="ok", metrics=metrics)
