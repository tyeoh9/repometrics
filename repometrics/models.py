from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Generic, Optional, TypeVar

CategoryStatus = str
T = TypeVar("T")


@dataclass(slots=True)
class Hotspot:
    path: str
    count: int


@dataclass(slots=True)
class BinaryFile:
    path: str
    size_bytes: int


@dataclass(slots=True)
class StructureMetrics:
    total_py_files: int
    max_depth: int
    avg_depth: float
    files_gt_500_loc: int
    files_gt_1000_loc: int
    largest_file_path: str
    largest_file_loc: int
    empty_dirs: int
    total_python_loc: int


@dataclass(slots=True)
class DependencyMetrics:
    total_nodes: int
    total_edges: int
    cycle_count: int
    most_imported_module: str
    isolated_modules: int


@dataclass(slots=True)
class GitMetrics:
    total_commits: int
    avg_loc_changed_per_commit: float
    largest_commit_loc_changed: int
    file_change_frequency: dict[str, int] = field(default_factory=dict)
    hotspots_top10: list[Hotspot] = field(default_factory=list)


@dataclass(slots=True)
class HygieneMetrics:
    duplicate_basenames_count: int
    todo_markers_count: int
    test_to_code_ratio: float
    modules_without_matching_test_count: int
    large_binary_files_count: int
    large_binary_files_top10: list[BinaryFile] = field(default_factory=list)
    code_file_count: int = 0
    test_file_count: int = 0
    total_python_loc: int = 0


@dataclass(slots=True)
class CategoryResult(Generic[T]):
    status: CategoryStatus
    metrics: Optional[T] = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RepoMetricsReport:
    schema_version: str
    path: str
    days: int
    generated_at: str
    structure: CategoryResult[StructureMetrics]
    dependencies: CategoryResult[DependencyMetrics]
    git: CategoryResult[GitMetrics]
    hygiene: CategoryResult[HygieneMetrics]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ScoreReport:
    category_scores: dict[str, float]
    weights_used: dict[str, float]
    final_score: float

    def to_dict(self) -> dict:
        return asdict(self)
