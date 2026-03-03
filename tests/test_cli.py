import json
from pathlib import Path

from repometrics.cli import main
from repometrics.models import ScoreReport


def test_cli_json_runs_for_repo_root() -> None:
    exit_code = main(["check", "--path", str(Path.cwd()), "--days", "30", "--json"])
    assert exit_code == 0


def test_cli_rejects_invalid_days() -> None:
    exit_code = main(["check", "--path", str(Path.cwd()), "--days", "0", "--json"])
    assert exit_code == 2


def test_cli_text_output_includes_category_sections(capsys) -> None:
    exit_code = main(["check", "--path", str(Path.cwd()), "--days", "30", "--no-color"])
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert exit_code == 0
    assert lines[0] == ""
    assert lines[1].startswith("score=")
    assert "threshold=70.00  path=" in captured.out
    assert "Category         |  Score" in captured.out
    assert "----------------+-------" in captured.out
    assert "Final" in captured.out
    assert "total_py_files" not in captured.out


def test_cli_verbose_text_output_includes_full_metrics(capsys) -> None:
    exit_code = main(["check", "--path", str(Path.cwd()), "--days", "30", "--verbose", "--no-color"])
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert exit_code == 0
    assert lines[0] == ""
    assert "Category Metrics" in captured.out
    assert "Structure" in captured.out
    assert "total_py_files" in captured.out
    assert "score_bar:" in captured.out


def test_cli_json_output_contract(capsys) -> None:
    exit_code = main(["check", "--path", str(Path.cwd()), "--days", "30", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["schema_version"] == "1.0"
    assert payload["path"] == str(Path.cwd())
    assert payload["days"] == 30
    assert "generated_at" in payload
    assert set(payload["categories"].keys()) == {
        "structure",
        "dependencies",
        "git",
        "hygiene",
    }
    assert {"category_scores", "weights_used", "final_score"} <= set(payload["scoring"].keys())
    assert {"healthy", "min_score", "exit_code"} <= set(payload.keys())
    assert payload["min_score"] == 70.0
    assert payload["exit_code"] == exit_code


def test_cli_scan_alias_parity(monkeypatch, capsys) -> None:
    fixed = ScoreReport(
        category_scores={"structure": 90.0, "dependencies": 90.0, "git": 90.0, "hygiene": 90.0},
        weights_used={"structure": 30.0, "dependencies": 30.0, "git": 20.0, "hygiene": 20.0},
        final_score=90.0,
    )
    monkeypatch.setattr("repometrics.cli.compute", lambda _report: fixed)

    check_code = main(["check", "--path", str(Path.cwd()), "--days", "30", "--json"])
    check_out = capsys.readouterr().out

    scan_code = main(["scan", "--path", str(Path.cwd()), "--days", "30", "--json"])
    scan_out = capsys.readouterr().out

    assert check_code == 0
    assert scan_code == 0
    assert json.loads(check_out)["scoring"] == json.loads(scan_out)["scoring"]


def test_cli_unhealthy_exit_code(monkeypatch) -> None:
    fixed = ScoreReport(
        category_scores={"structure": 30.0, "dependencies": 30.0, "git": 30.0, "hygiene": 30.0},
        weights_used={"structure": 30.0, "dependencies": 30.0, "git": 20.0, "hygiene": 20.0},
        final_score=30.0,
    )
    monkeypatch.setattr("repometrics.cli.compute", lambda _report: fixed)

    exit_code = main(["check", "--path", str(Path.cwd()), "--days", "30", "--min-score", "70"])
    assert exit_code == 1


def test_cli_score_bar_color_and_no_color(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    main(["check", "--path", str(Path.cwd()), "--days", "30"])
    colored = capsys.readouterr().out

    main(["check", "--path", str(Path.cwd()), "--days", "30", "--no-color", "--verbose"])
    plain_verbose = capsys.readouterr().out

    assert "\x1b[" in colored
    assert "\x1b[" not in plain_verbose
