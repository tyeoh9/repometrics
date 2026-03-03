from __future__ import annotations

import subprocess
from pathlib import Path

from repometrics.config import ScanConfig
from repometrics.models import CategoryResult, GitMetrics, Hotspot


def analyze(path: Path, config: ScanConfig) -> CategoryResult[GitMetrics]:
    try:
        check = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return CategoryResult(
            status="unavailable",
            metrics=None,
            warnings=[f"git: unavailable: {exc}"],
        )

    if check.returncode != 0:
        return CategoryResult(
            status="unavailable",
            metrics=None,
            warnings=["git: path is not inside a git work tree"],
        )

    log = subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "log",
            "--numstat",
            "--no-merges",
            f"--since={config.days} days ago",
            "--pretty=format:__COMMIT__%H",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if log.returncode != 0:
        return CategoryResult(
            status="unavailable",
            metrics=None,
            warnings=["git: failed to read git history in selected window"],
        )

    total_commits = 0
    current_commit_loc = 0
    largest_commit = 0
    commit_loc_values: list[int] = []
    file_change_frequency: dict[str, int] = {}
    seen_in_commit: set[str] = set()

    for raw_line in log.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("__COMMIT__"):
            if total_commits > 0:
                commit_loc_values.append(current_commit_loc)
                largest_commit = max(largest_commit, current_commit_loc)
            total_commits += 1
            current_commit_loc = 0
            seen_in_commit = set()
            continue

        parts = raw_line.split("\t")
        if len(parts) != 3:
            continue
        added_raw, deleted_raw, file_path = parts
        try:
            added = int(added_raw)
        except ValueError:
            added = 0
        try:
            deleted = int(deleted_raw)
        except ValueError:
            deleted = 0

        current_commit_loc += added + deleted
        if file_path not in seen_in_commit:
            file_change_frequency[file_path] = file_change_frequency.get(file_path, 0) + 1
            seen_in_commit.add(file_path)

    if total_commits > 0:
        commit_loc_values.append(current_commit_loc)
        largest_commit = max(largest_commit, current_commit_loc)

    avg_loc = (sum(commit_loc_values) / total_commits) if total_commits else 0.0
    hotspots_top10 = [
        Hotspot(path=entry[0], count=entry[1])
        for entry in sorted(
            file_change_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    ]
    metrics = GitMetrics(
        total_commits=total_commits,
        avg_loc_changed_per_commit=avg_loc,
        largest_commit_loc_changed=largest_commit,
        file_change_frequency=file_change_frequency,
        hotspots_top10=hotspots_top10,
    )
    return CategoryResult(status="ok", metrics=metrics)
