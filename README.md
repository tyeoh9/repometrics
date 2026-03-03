# repometrics

A CLI that measures repository health.

## Install

```bash
pip install repometrics
```

## Usage

```bash
repometrics scan
repometrics scan --days 60
repometrics scan --path /path/to/repo
repometrics scan --json
repometrics scan --confirm-test-matches
```

## JSON Output

`--json` returns a stable, versioned payload with:
- metadata (`schema_version`, `path`, `days`, `generated_at`)
- category results (`structure`, `dependencies`, `git`, `hygiene`) including status, metrics, warnings, errors
- scoring (`category_scores`, `weights_used`, `final_score`)
- top-level warnings and errors

## Development

Run tests:

```bash
python3 -m pytest -q
```

## Example

```text
Repo Health Score: 74 / 100

Structure:     68
Dependencies:  80
Git Activity:  72
Hygiene:       75
```

## Philosophy

Deterministic.  
Read-only.  
CI-friendly.  
Python-first.

## License

MIT
