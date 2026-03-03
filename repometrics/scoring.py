from __future__ import annotations

from repometrics.models import (
    DependencyMetrics,
    GitMetrics,
    HygieneMetrics,
    RepoMetricsReport,
    ScoreReport,
    StructureMetrics,
)

BASE_WEIGHTS = {
    "structure": 30.0,
    "dependencies": 30.0,
    "git": 20.0,
    "hygiene": 20.0,
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _round(value: float) -> float:
    return round(value, 2)


def _score_structure(m: StructureMetrics) -> float:
    s_depth = 100 - min(100, 4 * m.max_depth + 8 * max(0.0, m.avg_depth - 4))
    s_size = 100 - min(
        100,
        6 * m.files_gt_500_loc
        + 12 * m.files_gt_1000_loc
        + max(0, m.largest_file_loc - 1200) / 20,
    )
    s_empty = 100 - min(100, 3 * m.empty_dirs)
    score = 0.35 * s_depth + 0.50 * s_size + 0.15 * s_empty
    return _round(_clamp(score))


def _score_dependencies(m: DependencyMetrics) -> float:
    n = max(m.total_nodes, 1)
    edge_density = m.total_edges / n
    isolated_ratio = m.isolated_modules / n
    s_cycles = 100 - min(100, 15 * m.cycle_count)
    s_density = 100 - min(100, 12 * max(0.0, edge_density - 2))
    s_isolated = 100 - min(100, 100 * isolated_ratio)
    score = 0.45 * s_cycles + 0.35 * s_density + 0.20 * s_isolated
    return _round(_clamp(score))


def _score_git(m: GitMetrics) -> float:
    touches = sum(m.file_change_frequency.values())
    top1 = m.hotspots_top10[0].count if m.hotspots_top10 else 0
    hotspot_share = top1 / max(touches, 1)
    s_activity = min(100, 10 * m.total_commits)
    s_avg_size = 100 - min(100, max(0.0, m.avg_loc_changed_per_commit - 300) / 7)
    s_max_size = 100 - min(100, max(0, m.largest_commit_loc_changed - 1200) / 12)
    s_hotspot = 100 - min(100, 120 * max(0.0, hotspot_share - 0.35))
    score = (
        0.30 * s_activity
        + 0.30 * s_avg_size
        + 0.20 * s_max_size
        + 0.20 * s_hotspot
    )
    return _round(_clamp(score))


def _score_hygiene(m: HygieneMetrics) -> float:
    mod_count = max(m.code_file_count, 1)
    dup_ratio = m.duplicate_basenames_count / mod_count
    missing_test_ratio = m.modules_without_matching_test_count / mod_count
    todo_per_kloc = m.todo_markers_count / max(m.total_python_loc / 1000, 1)
    s_dup = 100 - min(100, 250 * dup_ratio)
    s_tests = 100 - min(100, 140 * missing_test_ratio)
    s_todo = 100 - min(100, 8 * todo_per_kloc)
    s_binary = 100 - min(100, 8 * m.large_binary_files_count)
    score = 0.25 * s_dup + 0.40 * s_tests + 0.20 * s_todo + 0.15 * s_binary
    return _round(_clamp(score))


def compute(report: RepoMetricsReport) -> ScoreReport:
    category_scores: dict[str, float] = {}

    if report.structure.metrics is not None and report.structure.status != "unavailable":
        category_scores["structure"] = _score_structure(report.structure.metrics)
    if (
        report.dependencies.metrics is not None
        and report.dependencies.status != "unavailable"
    ):
        category_scores["dependencies"] = _score_dependencies(report.dependencies.metrics)
    if report.git.metrics is not None and report.git.status != "unavailable":
        category_scores["git"] = _score_git(report.git.metrics)
    if report.hygiene.metrics is not None and report.hygiene.status != "unavailable":
        category_scores["hygiene"] = _score_hygiene(report.hygiene.metrics)

    if not category_scores:
        return ScoreReport(category_scores={}, weights_used={}, final_score=0.0)

    available_weight = sum(BASE_WEIGHTS[name] for name in category_scores)
    sorted_names = sorted(
        category_scores.keys(),
        key=lambda name: (-BASE_WEIGHTS[name], name),
    )
    weights_used: dict[str, float] = {}
    remainder = 100.0
    for index, name in enumerate(sorted_names):
        if index == len(sorted_names) - 1:
            weights_used[name] = _round(remainder)
            break
        normalized = _round(BASE_WEIGHTS[name] * 100.0 / available_weight)
        weights_used[name] = normalized
        remainder -= normalized
    final = 0.0
    for name, score in category_scores.items():
        final += score * (weights_used[name] / 100.0)

    return ScoreReport(
        category_scores=category_scores,
        weights_used=weights_used,
        final_score=_round(_clamp(final)),
    )
