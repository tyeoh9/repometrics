# Changelog

## 0.2.0 - 2026-03-03

- Added compact default `repometrics check` terminal output.
- Added `--verbose` mode for full category metrics output.
- Added `check` as canonical command, with `scan` maintained as alias.
- Added health-gating flag `--min-score` (default `70`) and exit code contract:
  - `0` healthy
  - `1` unhealthy
  - `2` runtime/validation error
- Added `--no-color` support with TTY-aware ANSI color behavior.
- Extended JSON output with additive fields: `healthy`, `min_score`, `exit_code`.
- Added agent-oriented docs: `llms.txt` and `llms-full.txt`.
- Updated README and plan spec to match the implemented CLI and output contracts.
