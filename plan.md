# repometrics — Spec (Current)

## Goal

`repometrics` is a local, read-only CLI that analyzes a Python repository and reports:
- category metrics
- deterministic category scores
- deterministic final health score
- machine-readable health status for agents/CI

No network calls. No AI inference. No auto-refactoring.

## Package Structure

```
repometrics/
  __init__.py
  cli.py
  config.py
  scanner.py
  models.py
  scoring.py
  metrics/
    common.py
    structure.py
    dependencies.py
    gitstats.py
    hygiene.py
tests/
  test_cli.py
  test_common.py
  test_structure.py
  test_dependencies.py
  test_gitstats.py
  test_hygiene.py
  test_scoring.py
  test_integration_scan.py
```

## Execution Flow

1. CLI parses command/options.
2. `scanner.scan(path, days, confirm_test_matches)` runs category analyzers.
3. `scoring.compute(report)` computes normalized category scores and final score.
4. CLI emits text or JSON and returns health-aware exit code.

Metric modules do computation only. They do not score or print.

## Commands and Flags

Primary command:

```bash
repometrics check
```

Alias:

```bash
repometrics scan
```

Supported options:
- `--path <dir>` (default: `.`)
- `--days <int>` (default: `30`)
- `--json` (machine output)
- `--verbose` (full text stats)
- `--min-score <float>` (default: `70`, range `0..100`)
- `--confirm-test-matches` (interactive hygiene fallback)
- `--no-color` (disable ANSI colors in text mode)

## Exit Code Contract

- `0`: run succeeded and healthy (`final_score >= min_score`)
- `1`: run succeeded and unhealthy (`final_score < min_score`)
- `2`: runtime/validation failure

## Output Contracts

## Text Output

- Default mode (`check`): compact summary (2 lines) + small score table
- Verbose mode (`check --verbose`): full category metrics, statuses, warnings/errors
- Minimal cool-tone ANSI styling (cyan/blue/gray with amber unhealthy state)
- ANSI auto-disabled on non-TTY, forced off by `--no-color`

## JSON Output

Top-level:
- `schema_version`
- `path`
- `days`
- `generated_at`
- `categories`
- `scoring`
- `healthy`
- `min_score`
- `exit_code`
- `warnings`
- `errors`

`categories` contains `structure`, `dependencies`, `git`, `hygiene` with:
- `status` (`ok`, `partial`, `unavailable`)
- `metrics`
- `warnings`
- `errors`

## Metrics

## Structure
- max depth / avg depth
- total `.py` files
- files over 500 LOC / 1000 LOC
- largest file path + LOC
- empty dirs
- total Python LOC

LOC is non-empty lines.

## Dependencies
- AST import parsing
- internal module resolution
- directed graph (`networkx`)
- total nodes/edges
- cycle count (SCC-based)
- most imported module
- isolated module count

Parse failures are skipped with warnings (`partial` status).

## Git
- `git log --numstat --no-merges --since=<days> days ago`
- total commits
- average LOC changed per commit
- largest commit LOC changed
- file change frequency
- top-10 hotspots

If not in a git repo, category is `unavailable`.

## Hygiene
- duplicate basenames across directories
- TODO/FIXME/XXX marker count
- test-to-code ratio
- modules without matching test file
- binary files >1MB (top-10)

Test matching:
1. strict `test_<module>.py`
2. fuzzy suggestion mode for non-`test_*` files
3. optional interactive confirmation (`--confirm-test-matches`)

## Scoring

Base weights:
- Structure: 30
- Dependencies: 30
- Git: 20
- Hygiene: 20

Category scores are normalized to `0..100`.
Final score is deterministic and rounded.
Unavailable categories are removed and weights are rebalanced to total 100.

## Performance and Constraints

- Single-threaded
- No cache
- Target: under ~2 seconds for ~1000 Python files on typical hardware

## Agent-Friendly Artifacts

- `README.md`: concise quickstart and command contract
- `llms.txt`: short orientation + quickstart
- `llms-full.txt`: full command/output contract for one-pass ingestion
