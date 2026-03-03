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

BAR_WIDTH = 16
CATEGORY_WIDTH = 15
SCORE_WIDTH = 6
ANSI_RESET = "\033[0m"
ANSI_GREEN = "\033[32m"
ANSI_GRAY = "\033[90m"
ANSI_AMBER = "\033[33m"


def _add_common_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--days", type=int, default=30, help="Git lookback window in days.")
    parser.add_argument("--path", type=Path, default=Path("."), help="Repository path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument(
        "--confirm-test-matches",
        action="store_true",
        help="Interactively confirm ambiguous fuzzy test matches.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=70.0,
        help="Health threshold (0-100). Exit 1 when final score is below this threshold.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in text output.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full category metrics in text mode.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repometrics")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    check_parser = subparsers.add_parser(
        "check",
        help="Check repository health score and metrics.",
    )
    _add_common_scan_args(check_parser)
    scan_parser = subparsers.add_parser(
        "scan",
        help="Alias for 'check' (kept for backwards compatibility).",
    )
    _add_common_scan_args(scan_parser)
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.command not in {"check", "scan"}:
        raise ValueError("missing command; use: repometrics check")
    if args.days <= 0:
        raise ValueError("--days must be a positive integer")
    if not args.path.exists():
        raise ValueError(f"--path does not exist: {args.path}")
    if not args.path.is_dir():
        raise ValueError(f"--path is not a directory: {args.path}")
    if args.min_score < 0 or args.min_score > 100:
        raise ValueError("--min-score must be between 0 and 100")


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


def _supports_color(no_color: bool) -> bool:
    if no_color:
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _colorize(text: str, color: str, use_color: bool) -> str:
    if not use_color:
        return text
    return f"{color}{text}{ANSI_RESET}"


def _render_score_bar(score: float, use_color: bool) -> str:
    filled = max(0, min(BAR_WIDTH, int(round((score / 100.0) * BAR_WIDTH))))
    filled_part = "#" * filled
    empty_part = "-" * (BAR_WIDTH - filled)
    if not use_color:
        return f"{filled_part}{empty_part}"
    return f"{_colorize(filled_part, ANSI_GREEN, use_color)}{_colorize(empty_part, ANSI_GRAY, use_color)}"


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


def _render_score_table(score: dict, use_color: bool) -> list[str]:
    rows = [
        ("Structure", score["category_scores"].get("structure", "n/a")),
        ("Dependencies", score["category_scores"].get("dependencies", "n/a")),
        ("Git", score["category_scores"].get("git", "n/a")),
        ("Hygiene", score["category_scores"].get("hygiene", "n/a")),
        ("Final", score.get("final_score", "n/a")),
    ]
    divider_text = "---------------+-------"
    if use_color:
        header_category = _colorize("Category", ANSI_GRAY, use_color)
        header_score = _colorize("Score", ANSI_GRAY, use_color)
        divider = _colorize(divider_text, ANSI_GRAY, use_color)
    else:
        header_category = "Category"
        header_score = "Score"
        divider = divider_text
    lines = [
        f"{header_category:<{CATEGORY_WIDTH}} | {header_score:>{SCORE_WIDTH}}",
        divider,
    ]
    for name, value in rows:
        rendered = f"{value:.2f}" if isinstance(value, float) else str(value)
        lines.append(f"{name:<{CATEGORY_WIDTH}} | {rendered:>{SCORE_WIDTH}}")
    return lines


def _render_text_compact(
    metrics: dict,
    score: dict,
    min_score: float,
    healthy: bool,
    no_color: bool,
) -> str:
    final_score = float(score["final_score"])
    use_color = _supports_color(no_color)
    score_bar = _render_score_bar(final_score, use_color)
    health_state = "healthy" if healthy else "unhealthy"
    health_color = ANSI_GREEN if healthy else ANSI_AMBER
    score_value = _colorize(f"{final_score:.2f}", ANSI_GREEN, use_color)
    health_value = _colorize(health_state, health_color, use_color)

    lines = [
        "",
        f"score={score_value}  {score_bar}  health={health_value}",
        f"threshold={min_score:.2f}  path={metrics['path']}",
        "",
        *_render_score_table(score, use_color),
    ]
    warnings = metrics.get("warnings", [])
    errors = metrics.get("errors", [])
    if warnings or errors:
        lines.append("")
        lines.append(f"warnings={len(warnings)} errors={len(errors)}")
    return "\n".join(lines)


def _render_text_verbose(
    metrics: dict,
    score: dict,
    min_score: float,
    healthy: bool,
    no_color: bool,
) -> str:
    final_score = float(score["final_score"])
    use_color = _supports_color(no_color)
    score_bar = _render_score_bar(final_score, use_color)
    health_state = "healthy" if healthy else "unhealthy"
    health_color = ANSI_GREEN if healthy else ANSI_AMBER

    lines = [
        _colorize("repometrics check", ANSI_GREEN, use_color),
        f"path: {metrics['path']}",
        f"days: {metrics['days']}",
        f"final_score: {_colorize(f'{final_score:.2f}', ANSI_GREEN, use_color)}",
        f"threshold: {min_score:.2f}",
        f"health: {_colorize(health_state, health_color, use_color)}",
        f"score_bar: {score_bar}",
        "",
        _colorize("Category Metrics", ANSI_GRAY, use_color),
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
            f"  Final:        {final_score:.2f}",
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
        return 2

    metrics_payload = metrics_report.to_dict()
    score_payload = asdict(score_report)
    final_score = float(score_payload["final_score"])
    healthy = final_score >= args.min_score
    exit_code = 0 if healthy else 1
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
        "healthy": healthy,
        "min_score": args.min_score,
        "exit_code": exit_code,
        "warnings": metrics_payload["warnings"],
        "errors": metrics_payload["errors"],
    }

    if args.json:
        print(json.dumps(combined, indent=2, sort_keys=False))
    else:
        if args.verbose:
            print(
                _render_text_verbose(
                    metrics_payload,
                    score_payload,
                    args.min_score,
                    healthy,
                    args.no_color,
                )
            )
        else:
            print(
                _render_text_compact(
                    metrics_payload,
                    score_payload,
                    args.min_score,
                    healthy,
                    args.no_color,
                )
            )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
