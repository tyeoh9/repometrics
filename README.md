# repometrics

A deterministic CLI for measuring Python repository health.

```bash
pip install repometrics
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
repometrics check [--path DIR] [--days N] [--json] [--min-score N] [--confirm-test-matches] [--no-color]
```

Important flags:
- `--json`: machine-readable output
- `--min-score`: health threshold (default `70`)
- `--no-color`: disable ANSI colors in terminal output
- `--confirm-test-matches`: interactive confirmation for ambiguous non-`test_*` matches

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
