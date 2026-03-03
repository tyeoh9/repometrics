from __future__ import annotations

import re
import sys
from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.metrics.common import is_binary, walk_files
from repometrics.models import BinaryFile, CategoryResult, HygieneMetrics

_TOKENS_TO_IGNORE = {"test", "tests", "spec", "unit", "integration", "it", "e2e"}
_TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX)\b", flags=re.IGNORECASE)


def _is_test_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if path.suffix != ".py":
        return False
    return any(part == "tests" for part in rel.parts) or path.name.startswith("test_")


def _normalize_stem(stem: str) -> set[str]:
    tokens = set(re.split(r"[^a-zA-Z0-9]+", stem.lower()))
    return {token for token in tokens if token and token not in _TOKENS_TO_IGNORE}


def _similarity(module_stem: str, test_stem: str) -> float:
    module_tokens = _normalize_stem(module_stem)
    test_tokens = _normalize_stem(test_stem)
    if not module_tokens or not test_tokens:
        return 0.0
    overlap = len(module_tokens.intersection(test_tokens))
    union = len(module_tokens.union(test_tokens))
    jaccard = overlap / union if union else 0.0
    prefix_bonus = 0.15 if test_stem.startswith(module_stem) else 0.0
    suffix_bonus = 0.15 if test_stem.endswith(module_stem) else 0.0
    return jaccard + prefix_bonus + suffix_bonus


def _confirm_match(module: Path, candidate: Path) -> bool:
    if not sys.stdin.isatty():
        return False
    prompt = f"Use test match {candidate} for module {module}? [y/N]: "
    answer = input(prompt).strip().lower()
    return answer in {"y", "yes"}


def analyze(path: Path, config: ScanConfig) -> CategoryResult[HygieneMetrics]:
    files = walk_files(path)
    warnings: list[str] = []

    py_files = [file_path for file_path in files if file_path.suffix == ".py"]
    test_files = [file_path for file_path in py_files if _is_test_file(file_path, path)]
    code_files = [file_path for file_path in py_files if file_path not in test_files]

    basename_groups: dict[str, set[str]] = {}
    for file_path in code_files:
        basename_groups.setdefault(file_path.name, set()).add(str(file_path.parent))
    duplicate_basenames_count = sum(
        1 for directories in basename_groups.values() if len(directories) > 1
    )

    todo_markers_count = 0
    for file_path in files:
        if is_binary(file_path):
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        todo_markers_count += len(_TODO_PATTERN.findall(text))

    matched_modules: set[Path] = set()
    test_name_set = {test.name for test in test_files}
    for code_path in code_files:
        if f"test_{code_path.stem}.py" in test_name_set:
            matched_modules.add(code_path)

    fuzzy_candidates = [test for test in test_files if not test.name.startswith("test_")]
    for code_path in code_files:
        if code_path in matched_modules:
            continue
        scored = sorted(
            (
                (_similarity(code_path.stem, test.stem), test)
                for test in fuzzy_candidates
            ),
            key=lambda item: (-item[0], str(item[1])),
        )
        if not scored or scored[0][0] < 0.6:
            continue
        best_score, best_test = scored[0]
        if config.confirm_test_matches and _confirm_match(code_path, best_test):
            matched_modules.add(code_path)
            continue
        warnings.append(
            "hygiene: ambiguous test match suggestion "
            f"{best_test.relative_to(path)} -> {code_path.relative_to(path)} "
            f"(score={best_score:.2f}); rerun with --confirm-test-matches"
        )

    modules_without_matching_test_count = len(code_files) - len(matched_modules)
    test_to_code_ratio = len(test_files) / len(code_files) if code_files else 0.0

    binaries: list[BinaryFile] = []
    for file_path in files:
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        if size <= 1_000_000:
            continue
        if is_binary(file_path):
            binaries.append(BinaryFile(path=str(file_path.relative_to(path)), size_bytes=size))
    binaries.sort(key=lambda item: (-item.size_bytes, item.path))

    total_python_loc = 0
    for file_path in py_files:
        try:
            total_python_loc += sum(
                1 for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()
            )
        except (OSError, UnicodeDecodeError):
            continue

    metrics = HygieneMetrics(
        duplicate_basenames_count=duplicate_basenames_count,
        todo_markers_count=todo_markers_count,
        test_to_code_ratio=test_to_code_ratio,
        modules_without_matching_test_count=modules_without_matching_test_count,
        large_binary_files_count=len(binaries),
        large_binary_files_top10=binaries[:10],
        code_file_count=len(code_files),
        test_file_count=len(test_files),
        total_python_loc=total_python_loc,
    )
    status = "partial" if warnings else "ok"
    return CategoryResult(status=status, metrics=metrics, warnings=warnings)
