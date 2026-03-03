import subprocess
from pathlib import Path

from repometrics.scanner import scan
from repometrics.scoring import compute


def test_scan_marks_dependencies_partial_on_syntax_error(tmp_path: Path) -> None:
    (tmp_path / "good.py").write_text("import good\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("def nope(:\n", encoding="utf-8")

    report = scan(tmp_path, days=30)

    assert report.dependencies.status == "partial"
    assert report.dependencies.warnings
    assert "bad.py" in report.dependencies.warnings[0]
    assert report.warnings


def test_scan_non_git_reweights_final_score(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    report = scan(tmp_path, days=30)
    score = compute(report)

    assert report.git.status == "unavailable"
    assert "git" not in score.category_scores
    assert score.weights_used == {
        "structure": 37.5,
        "dependencies": 37.5,
        "hygiene": 25.0,
    }


def test_scan_git_repo_reports_git_metrics(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "main.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    report = scan(tmp_path, days=30)

    assert report.git.status == "ok"
    assert report.git.metrics is not None
    assert report.git.metrics.total_commits >= 1
