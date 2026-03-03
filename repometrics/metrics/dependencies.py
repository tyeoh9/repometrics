from __future__ import annotations

import ast
from pathlib import Path

import networkx as nx

from repometrics.config import ScanConfig
from repometrics.metrics.common import walk_files
from repometrics.models import CategoryResult, DependencyMetrics


def _module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_known_module(name: str, known_modules: set[str]) -> str | None:
    current = name
    while current:
        if current in known_modules:
            return current
        if "." not in current:
            break
        current = current.rsplit(".", 1)[0]
    return None


def _resolve_relative(module: str | None, level: int, current_module: str) -> str:
    base_parts = current_module.split(".")
    if level > 0:
        base_parts = base_parts[:-level]
    module_parts = module.split(".") if module else []
    all_parts = [part for part in [*base_parts, *module_parts] if part]
    return ".".join(all_parts)


def analyze(path: Path, config: ScanConfig) -> CategoryResult[DependencyMetrics]:
    del config
    py_files = [file_path for file_path in walk_files(path) if file_path.suffix == ".py"]
    modules = {file_path: _module_name(path, file_path) for file_path in py_files}
    known_modules = {name for name in modules.values() if name}

    graph = nx.DiGraph()
    graph.add_nodes_from(known_modules)

    warnings: list[str] = []
    for file_path, module_name in modules.items():
        if not module_name:
            continue
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            warnings.append(f"dependencies: skipped {file_path}: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = _resolve_known_module(alias.name, known_modules)
                    if target and target != module_name:
                        graph.add_edge(module_name, target)
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    resolved = _resolve_relative(node.module, node.level, module_name)
                else:
                    resolved = node.module or ""

                base_target = _resolve_known_module(resolved, known_modules)
                alias_targets: set[str] = set()
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    candidate = f"{resolved}.{alias.name}" if resolved else alias.name
                    target = _resolve_known_module(candidate, known_modules)
                    if target:
                        alias_targets.add(target)

                targets = alias_targets or ({base_target} if base_target else set())
                for target in targets:
                    if target != module_name:
                        graph.add_edge(module_name, target)

    cycle_count = 0
    for component in nx.strongly_connected_components(graph):
        if len(component) > 1:
            cycle_count += 1
            continue
        node = next(iter(component))
        if graph.has_edge(node, node):
            cycle_count += 1

    indegrees = dict(graph.in_degree())
    most_imported_module = ""
    if indegrees:
        max_in = max(indegrees.values())
        winners = sorted(node for node, degree in indegrees.items() if degree == max_in)
        most_imported_module = winners[0]

    isolated = sum(1 for node in graph.nodes if graph.degree(node) == 0)
    metrics = DependencyMetrics(
        total_nodes=graph.number_of_nodes(),
        total_edges=graph.number_of_edges(),
        cycle_count=cycle_count,
        most_imported_module=most_imported_module,
        isolated_modules=isolated,
    )
    status = "partial" if warnings else "ok"
    return CategoryResult(status=status, metrics=metrics, warnings=warnings)
