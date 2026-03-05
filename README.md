# repometrics

[![PyPI](https://img.shields.io/pypi/v/repository-metrics-cli?logo=pypi)](https://pypi.org/project/repository-metrics-cli/)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/tyeoh9/repometrics/ci.yml?branch=main&logo=githubactions)](https://github.com/tyeoh9/repometrics/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/tyeoh9/repometrics)](LICENSE)

A deterministic CLI for measuring Python repository health.

```bash
pip install repository-metrics-cli
repometrics check
```

## Quickstart

```bash
repometrics check --path /path/to/repo
repometrics check --json
```

`scan` is kept as a backward-compatible alias for `check`.

## CLI Reference

Primary command:

```bash
repometrics check [--path DIR] [--days N] [--json] [--verbose] [--min-score N] [--confirm-test-matches] [--no-color]
```

Important flags:
- `--json`: machine-readable output
- `--verbose`: full category metrics and warnings/errors
- `--min-score`: health threshold (default `70`)
- `--no-color`: disable ANSI colors in terminal output
- `--confirm-test-matches`: interactive confirmation for ambiguous non-`test_*` matches

Text modes:
- default: compact summary + small score table
- `--verbose`: full stats view
- `--json`: programmatic full detail

## What The Points Mean

- Structure: folder/file layout quality and balance.
- Dependencies: import graph health (cycles, density, isolation).
- Git: recent commit activity and contributor spread.
- Hygiene: tests coverage mapping, TODO noise, duplication, binary footprint.
- Final score: weighted average across available categories.

## Exit Codes

- `0`: healthy (`final_score >= min_score`)
- `1`: unhealthy (`final_score < min_score`)
- `2`: runtime/validation error

## Agent-Friendly Usage

- Stable JSON payload (`schema_version`, category metrics, scoring, warnings/errors)
- Additive health fields: `healthy`, `min_score`, `exit_code`
- Exit codes enable CI/agent decisions without parsing human-formatted text

Minimal JSON example:

```bash
repometrics check --json --min-score 75
```

## Development

```bash
python3 -m pytest -q
```

## License

MIT
