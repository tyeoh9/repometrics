from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.metrics.dependencies import analyze


def test_dependencies_counts_edges_and_cycles(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("import pkg.b\n", encoding="utf-8")
    (pkg / "b.py").write_text("from pkg import a\n", encoding="utf-8")
    (pkg / "isolated.py").write_text("x = 1\n", encoding="utf-8")

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.status == "ok"
    assert result.metrics is not None
    assert result.metrics.total_nodes >= 3
    assert result.metrics.total_edges >= 2
    assert result.metrics.cycle_count >= 1
    assert result.metrics.isolated_modules >= 1


def test_dependencies_marks_partial_on_parse_error(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("import math\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("def nope(:\n", encoding="utf-8")

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.status == "partial"
    assert result.metrics is not None
    assert result.warnings
    assert "bad.py" in result.warnings[0]


def test_dependencies_resolves_relative_imports_in_package_init(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from . import util\n", encoding="utf-8")
    (pkg / "util.py").write_text("VALUE = 1\n", encoding="utf-8")

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.status == "ok"
    assert result.metrics is not None
    assert result.metrics.total_edges >= 1
    assert result.metrics.most_imported_module == "pkg.util"
