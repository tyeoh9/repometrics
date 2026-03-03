import subprocess
from pathlib import Path

from repometrics.metrics.common import walk_files


def test_walk_files_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (tmp_path / "tracked.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("print('nope')\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", ".gitignore", "tracked.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    files = {p.relative_to(tmp_path).as_posix() for p in walk_files(tmp_path)}
    assert "tracked.py" in files
    assert "ignored.py" not in files


def test_walk_files_fallback_outside_git(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"x")

    files = {p.relative_to(tmp_path).as_posix() for p in walk_files(tmp_path)}
    assert files == {"a.py", "nested/b.py"}
