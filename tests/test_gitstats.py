import subprocess
from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.metrics.gitstats import analyze


def test_gitstats_unavailable_outside_git(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('ok')\n", encoding="utf-8")

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.status == "unavailable"
    assert result.metrics is None
    assert result.warnings


def test_gitstats_collects_commit_stats(tmp_path: Path) -> None:
    file_path = tmp_path / "main.py"
    file_path.write_text("print('v1')\n", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "main.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-m", "c1"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    file_path.write_text("print('v2')\nprint('extra')\n", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-m", "c2"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.status == "ok"
    assert result.metrics is not None
    assert result.metrics.total_commits >= 2
    assert result.metrics.largest_commit_loc_changed >= 1
    assert result.metrics.hotspots_top10
    assert result.metrics.hotspots_top10[0].path == "main.py"
