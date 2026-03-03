from repometrics.models import (
    CategoryResult,
    DependencyMetrics,
    GitMetrics,
    HygieneMetrics,
    RepoMetricsReport,
    StructureMetrics,
)
from repometrics.scoring import compute


def _base_report() -> RepoMetricsReport:
    return RepoMetricsReport(
        schema_version="1.0",
        path="/tmp/repo",
        days=30,
        generated_at="2026-03-03T00:00:00-08:00",
        structure=CategoryResult(
            status="ok",
            metrics=StructureMetrics(
                total_py_files=10,
                max_depth=2,
                avg_depth=1.2,
                files_gt_500_loc=1,
                files_gt_1000_loc=0,
                largest_file_path="a.py",
                largest_file_loc=800,
                empty_dirs=0,
                total_python_loc=2000,
            ),
        ),
        dependencies=CategoryResult(
            status="ok",
            metrics=DependencyMetrics(
                total_nodes=10,
                total_edges=15,
                cycle_count=1,
                most_imported_module="pkg.core",
                isolated_modules=1,
            ),
        ),
        git=CategoryResult(
            status="ok",
            metrics=GitMetrics(
                total_commits=8,
                avg_loc_changed_per_commit=230.0,
                largest_commit_loc_changed=700,
                file_change_frequency={"a.py": 5, "b.py": 2},
                hotspots_top10=[],
            ),
        ),
        hygiene=CategoryResult(
            status="ok",
            metrics=HygieneMetrics(
                duplicate_basenames_count=1,
                todo_markers_count=3,
                test_to_code_ratio=0.8,
                modules_without_matching_test_count=2,
                large_binary_files_count=0,
                code_file_count=10,
                test_file_count=8,
                total_python_loc=2000,
            ),
        ),
    )


def test_compute_rebalances_unavailable_category() -> None:
    report = _base_report()
    report.git = CategoryResult(status="unavailable", metrics=None, warnings=["not git repo"])

    result = compute(report)

    assert "git" not in result.category_scores
    assert sum(result.weights_used.values()) == 100.0
    assert result.weights_used == {
        "structure": 37.5,
        "dependencies": 37.5,
        "hygiene": 25.0,
    }


def test_compute_scores_in_range() -> None:
    result = compute(_base_report())

    assert 0 <= result.final_score <= 100
    assert set(result.category_scores) == {"structure", "dependencies", "git", "hygiene"}
    assert sum(result.weights_used.values()) == 100.0


def test_compute_weights_sum_exactly_to_hundred() -> None:
    report = _base_report()
    report.structure = CategoryResult(status="unavailable", metrics=None, warnings=["skip"])
    report.git = CategoryResult(status="unavailable", metrics=None, warnings=["skip"])

    result = compute(report)

    assert result.weights_used == {"dependencies": 60.0, "hygiene": 40.0}
    assert sum(result.weights_used.values()) == 100.0
