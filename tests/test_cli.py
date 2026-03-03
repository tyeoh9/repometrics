import json
from pathlib import Path

from repometrics.cli import main


def test_cli_json_runs_for_repo_root() -> None:
    exit_code = main(["scan", "--path", str(Path.cwd()), "--days", "30", "--json"])
    assert exit_code == 0


def test_cli_rejects_invalid_days() -> None:
    exit_code = main(["scan", "--path", str(Path.cwd()), "--days", "0", "--json"])
    assert exit_code == 1


def test_cli_text_output_includes_category_sections(capsys) -> None:
    exit_code = main(["scan", "--path", str(Path.cwd()), "--days", "30"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Category Metrics" in captured.out
    assert "Structure" in captured.out
    assert "Dependencies" in captured.out
    assert "Scores" in captured.out


def test_cli_json_output_contract(capsys) -> None:
    exit_code = main(["scan", "--path", str(Path.cwd()), "--days", "30", "--json"])
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
