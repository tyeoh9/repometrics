from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.metrics.hygiene import analyze


def test_hygiene_strict_test_name_counts_as_match(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_service.py").write_text("def test_run():\n    assert True\n", encoding="utf-8")

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.status == "ok"
    assert result.metrics is not None
    assert result.metrics.modules_without_matching_test_count == 0
    assert result.metrics.test_file_count == 1


def test_hygiene_fuzzy_match_emits_warning_without_confirmation(tmp_path: Path) -> None:
    (tmp_path / "billing_service.py").write_text(
        "def bill():\n    return 'ok'\n", encoding="utf-8"
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "billing-service.integration.py").write_text(
        "def billing_check():\n    assert True\n", encoding="utf-8"
    )

    result = analyze(tmp_path, ScanConfig(days=30, confirm_test_matches=False))

    assert result.status == "partial"
    assert result.metrics is not None
    assert result.metrics.modules_without_matching_test_count == 1
    assert result.warnings
    assert "ambiguous test match suggestion" in result.warnings[0]


def test_hygiene_non_interactive_confirm_flag_warns(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "service.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "service.integration.py").write_text("def test_it():\n    assert True\n", encoding="utf-8")

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    result = analyze(tmp_path, ScanConfig(days=30, confirm_test_matches=True))

    assert result.status == "partial"
    assert result.warnings
    assert "non-interactive mode" in result.warnings[0]


def test_hygiene_fuzzy_uses_distinct_test_files(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "auth_service.py").write_text("def auth():\n    return 1\n", encoding="utf-8")
    (tmp_path / "billing_service.py").write_text("def bill():\n    return 1\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "service.integration.py").write_text("def test_service():\n    assert True\n", encoding="utf-8")
    monkeypatch.setattr("repometrics.metrics.hygiene._similarity", lambda _a, _b: 1.0)

    result = analyze(tmp_path, ScanConfig(days=30, confirm_test_matches=False))

    assert result.status == "partial"
    assert result.metrics is not None
    assert result.metrics.modules_without_matching_test_count == 2
    assert len(result.warnings) == 1
