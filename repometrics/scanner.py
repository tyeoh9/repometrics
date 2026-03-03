from __future__ import annotations

from datetime import datetime
from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.metrics import dependencies, gitstats, hygiene, structure
from repometrics.models import RepoMetricsReport


def scan(path: Path, days: int, confirm_test_matches: bool = False) -> RepoMetricsReport:
    config = ScanConfig(days=days, confirm_test_matches=confirm_test_matches)
    root = path.resolve()

    structure_result = structure.analyze(root, config)
    dependencies_result = dependencies.analyze(root, config)
    git_result = gitstats.analyze(root, config)
    hygiene_result = hygiene.analyze(root, config)

    warnings: list[str] = []
    errors: list[str] = []
    for result in (structure_result, dependencies_result, git_result, hygiene_result):
        warnings.extend(result.warnings)
        errors.extend(result.errors)

    return RepoMetricsReport(
        schema_version="1.0",
        path=str(root),
        days=days,
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        structure=structure_result,
        dependencies=dependencies_result,
        git=git_result,
        hygiene=hygiene_result,
        warnings=warnings,
        errors=errors,
    )
