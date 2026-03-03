from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.metrics.structure import analyze


def test_structure_computes_depth_loc_and_largest_file(tmp_path: Path) -> None:
    (tmp_path / "root.py").write_text("print('a')\n\nprint('b')\n", encoding="utf-8")
    nested = tmp_path / "pkg" / "inner"
    nested.mkdir(parents=True)
    big_file = nested / "big.py"
    big_file.write_text("\n".join("x=1" for _ in range(520)), encoding="utf-8")

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.status == "ok"
    assert result.metrics is not None
    assert result.metrics.total_py_files == 2
    assert result.metrics.max_depth == 2
    assert result.metrics.files_gt_500_loc == 1
    assert result.metrics.files_gt_1000_loc == 0
    assert result.metrics.largest_file_path == "pkg/inner/big.py"
    assert result.metrics.largest_file_loc == 520


def test_structure_counts_empty_dirs(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "empty_a").mkdir()
    (tmp_path / "non_empty").mkdir()
    (tmp_path / "non_empty" / "x.txt").write_text("x\n", encoding="utf-8")

    result = analyze(tmp_path, ScanConfig(days=30))

    assert result.metrics is not None
    assert result.metrics.empty_dirs >= 1
