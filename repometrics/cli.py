from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from repometrics import __version__
from repometrics.scanner import scan
from repometrics.scoring import compute


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repometrics")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    scan_parser = subparsers.add_parser("scan", help="Scan repository and compute health score.")
    scan_parser.add_argument("--days", type=int, default=30, help="Git lookback window in days.")
    scan_parser.add_argument("--path", type=Path, default=Path("."), help="Repository path.")
    scan_parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    scan_parser.add_argument(
        "--confirm-test-matches",
        action="store_true",
        help="Interactively confirm ambiguous fuzzy test matches.",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.command != "scan":
        raise ValueError("missing command; use: repometrics scan")
    if args.days <= 0:
        raise ValueError("--days must be a positive integer")
    if not args.path.exists():
        raise ValueError(f"--path does not exist: {args.path}")
    if not args.path.is_dir():
        raise ValueError(f"--path is not a directory: {args.path}")


def _format_metric_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list):
        if not value:
            return "[]"
        rendered = ", ".join(str(item) for item in value[:5])
        suffix = " ..." if len(value) > 5 else ""
        return f"[{rendered}{suffix}]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = list(value.items())[:5]
        rendered = ", ".join(f"{key}={val}" for key, val in items)
        suffix = " ..." if len(value) > 5 else ""
        return f"{{{rendered}{suffix}}}"
    return str(value)


def _render_category(name: str, category: dict, score: dict) -> list[str]:
    lines = [f"{name}"]
    lines.append(f"  status: {category['status']}")
    lines.append(f"  score: {score['category_scores'].get(name.lower(), 'n/a')}")
    metrics = category.get("metrics")
    if metrics:
        lines.append("  metrics:")
        for key in sorted(metrics):
            lines.append(f"    {key}: {_format_metric_value(metrics[key])}")
    category_warnings = category.get("warnings", [])
    category_errors = category.get("errors", [])
    if category_warnings:
        lines.append("  warnings:")
        for warning in category_warnings:
            lines.append(f"    - {warning}")
    if category_errors:
        lines.append("  errors:")
        for error in category_errors:
            lines.append(f"    - {error}")
    return lines


def _render_text(metrics: dict, score: dict) -> str:
    lines = [
        "repometrics scan",
        f"path: {metrics['path']}",
        f"days: {metrics['days']}",
        "",
        "Category Metrics",
    ]
    categories = {
        "Structure": metrics["structure"],
        "Dependencies": metrics["dependencies"],
        "Git": metrics["git"],
        "Hygiene": metrics["hygiene"],
    }
    for index, (name, category) in enumerate(categories.items()):
        lines.extend(_render_category(name, category, score))
        if index < len(categories) - 1:
            lines.append("")

    lines.extend(
        [
            "",
            "Scores",
            f"  Structure:    {score['category_scores'].get('structure', 'n/a')}",
            f"  Dependencies: {score['category_scores'].get('dependencies', 'n/a')}",
            f"  Git:          {score['category_scores'].get('git', 'n/a')}",
            f"  Hygiene:      {score['category_scores'].get('hygiene', 'n/a')}",
            f"  Final:        {score['final_score']}",
        ]
    )
    warnings = metrics.get("warnings", [])
    errors = metrics.get("errors", [])
    if warnings or errors:
        lines.extend(["", "Warnings/Errors"])
        for warning in warnings:
            lines.append(f"  warning: {warning}")
        for error in errors:
            lines.append(f"  error: {error}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_args(args)
        metrics_report = scan(
            path=args.path,
            days=args.days,
            confirm_test_matches=args.confirm_test_matches,
        )
        score_report = compute(metrics_report)
    except Exception as exc:  # pragma: no cover - CLI fallback
        print(f"error: {exc}", file=sys.stderr)
        return 1

    metrics_payload = metrics_report.to_dict()
    score_payload = asdict(score_report)
    combined = {
        "schema_version": metrics_payload["schema_version"],
        "path": metrics_payload["path"],
        "days": metrics_payload["days"],
        "generated_at": metrics_payload["generated_at"],
        "categories": {
            "structure": metrics_payload["structure"],
            "dependencies": metrics_payload["dependencies"],
            "git": metrics_payload["git"],
            "hygiene": metrics_payload["hygiene"],
        },
        "scoring": score_payload,
        "warnings": metrics_payload["warnings"],
        "errors": metrics_payload["errors"],
    }

    if args.json:
        print(json.dumps(combined, indent=2, sort_keys=False))
    else:
        print(_render_text(metrics_payload, score_payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
