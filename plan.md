# repometrics — PRD (MVP)

## Goal

CLI tool that analyzes a Python repository and outputs:
- category metrics
- weighted deterministic health score

Read-only. Local-only. No AI. No network.

---

## Package Structure

```
repometrics/
  cli.py          # entrypoint
  scanner.py      # orchestration
  models.py       # dataclasses for results
  scoring.py      # normalization + weights
  metrics/
      structure.py
      dependencies.py
      gitstats.py
      hygiene.py
```

---

## Execution Flow

cli.py
  → parse args
  → call scanner.scan(path, days)
  → receive RepoMetrics
  → scoring.compute()
  → render (rich or json)

scanner.py
  → call each metrics module
  → aggregate results into models
  → return unified result object

No cross-calls between metric modules.

---

## Metrics Modules

Each module exposes:

```
analyze(path, config) -> CategoryResult
```

Must not print. Must not score. Pure computation.

---

### metrics/structure.py

Input:
- filesystem walk

Compute:
- max depth
- avg depth
- total .py files
- files >500 LOC
- files >1000 LOC
- largest file
- empty dirs

LOC = non-empty lines.

---

### metrics/dependencies.py

Input:
- Python AST

Steps:
- parse imports
- resolve internal modules only
- build directed graph (networkx)

Compute:
- total nodes
- total edges
- cycles (simple_cycles)
- most imported module (max in-degree)
- isolated modules (degree 0)

Ignore third-party imports.

---

### metrics/gitstats.py

Input:
- `git log --numstat` (subprocess)

Default window: last 30 days.

Compute:
- total commits
- avg LOC changed per commit
- largest commit
- file change frequency
- hotspot (max change count)

Fail gracefully if not a git repo.

---

### metrics/hygiene.py

Compute:
- duplicate basenames across dirs
- TODO count
- test-to-code ratio
- modules without matching test file
- binary files >1MB

Test detection:
- files in `/tests/`
- files starting with `test_`

No coverage tooling.

---

## models.py

Dataclasses:

- StructureMetrics
- DependencyMetrics
- GitMetrics
- HygieneMetrics

Aggregate:

```
RepoMetrics:
  structure
  dependencies
  git
  hygiene
```

No scoring fields stored here.

---

## scoring.py

Input:
- RepoMetrics

Output:
- CategoryScores
- FinalScore

Weights:
- Structure: 30
- Dependencies: 30
- Git: 20
- Hygiene: 20

Each category normalized 0–100.

Score must be deterministic.
No randomness.
No historical comparison.

---

## CLI Requirements

Command:

```
repometrics scan
```

Options:
- `--days <int>`
- `--path <dir>`
- `--json`

Terminal:
- section headers
- metrics
- per-category score
- final score

JSON:
- raw metrics
- per-category scores
- final score

---

## Performance Constraints

- <2 seconds for ~1000 Python files
- single-threaded
- no caching (MVP)

---

## Non-Goals

- auto-refactoring
- multi-language support
- persistence/history
- CI enforcement mode
- graph visualization export

---

## Done Criteria

- Works on real-world repo
- Cycles detected correctly
- Hotspot detection accurate
- Score stable across runs
- JSON output complete + valid
- Clean CLI UX