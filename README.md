# SuiteCompass

Deterministic regression suite optimizer for sprint-scoped delivery.

## Problem

Sprint delivery teams carry oversized regression suites that burn CI time and delay releases. Manual triage is ad-hoc and inconsistent. SuiteCompass analyses sprint context and test-suite metadata to recommend which tests to **run**, **defer**, or **retire** for a given sprint — and surfaces suite health signals.

## Key Capabilities

- **Deterministic scoring** — formula-based, reproducible prioritisation with no LLM dependency
- **Tiered recommendations** — must-run / should-run / defer / retire with override support
- **NFR elevation** — automatic promotion of performance and security tests in high-risk sprints
- **Budget-aware** — respects time budgets with overflow demotion logic
- **Excel import** — teams can feed existing spreadsheets instead of hand-writing YAML
- **Binary validation** — machine-checkable output contract with section-aware assertions

## Repo Layout

| Path | Purpose |
|---|---|
| `src/intelligent_regression_optimizer/` | Core package — loader, classifier, scorer, renderer, validator, CLI |
| `tests/` | 228+ pytest tests (98%+ coverage) |
| `benchmarks/` | Benchmark input YAMLs + assertion files + sample Excel |
| `templates/` | Excel import template (13 columns) |
| `docs/` | Full documentation (see index below) |
| `claude-memory/` | Development memory layer |
| `plan.md` | Planning and phase tracking |

## Quick Start

```bash
# Clone and install
git clone git@github.com:sandeep-singh-79/SuiteCompass.git
cd SuiteCompass
pip install -e .

# Run on a sample input
iro run tests/fixtures/valid_input.yaml

# Import from Excel
iro import-tests templates/test_suite_template.xlsx --output test_suite.yaml
# Then merge test_suite.yaml with your sprint_context + constraints YAML and run:
# iro run combined.yaml
```

## CLI Reference

| Command | Purpose | Key Flags | Exit Codes |
|---|---|---|---|
| `iro run <input.yaml>` | Run optimisation pipeline, print report | `--output, -o <path>` | 0 = success, 1 = validation error, 2 = input error |
| `iro run --tests <t.yaml> --sprint <s.yaml>` | Merge separate test suite + sprint context files and run | `--output, -o <path>` | 0 = success, 2 = input error |
| `iro benchmark <input.yaml> <assertions.yaml>` | Run pipeline + validate against assertions | — | 0 = pass, 1 = fail, 2 = input error |
| `iro import-tests <file.xlsx>` | Import Excel test inventory as test_suite YAML | `--output, -o <path>`, `--sheet, -s <name>` | 0 = success, 2 = input error |

## Documentation

| Document | Description |
|---|---|
| [USAGE-GUIDE](docs/USAGE-GUIDE.md) | End-to-end usage instructions, workflows, error handling |
| [V1-INPUT-TEMPLATE](docs/V1-INPUT-TEMPLATE.md) | Full input schema with field-level annotations |
| [V1-OUTPUT-TEMPLATE](docs/V1-OUTPUT-TEMPLATE.md) | Annotated sample output report |
| [DECISION-RULES](docs/DECISION-RULES.md) | Scoring formula, tier logic, override and retire rules |
| [SCENARIO-LIBRARY](docs/SCENARIO-LIBRARY.md) | Named scenarios with expected behaviour and tradeoffs |
| [VALIDATION-HARNESS](docs/VALIDATION-HARNESS.md) | Benchmark system guide — how to run and add assertions |
| [LEARNING-GUIDE](docs/LEARNING-GUIDE.md) | Tutorial: regression prioritisation thinking |
| [SCORING-FORMULA](docs/SCORING-FORMULA.md) | Full formula derivation with weights, examples, and edge cases |
| [BENCHMARK-AUTHORING](docs/BENCHMARK-AUTHORING.md) | How to write and validate new benchmark scenarios |
| [PHASED-IMPLEMENTATION](docs/PHASED-IMPLEMENTATION.md) | Architecture retrospective and decision log |

## Development Status

| Metric | Value |
|---|---|
| Phase 1 (Deterministic Core) | Complete |
| Phase 3 (Excel Adapter — all tracks A1–A6) | Complete |
| Phase 2 (Documentation) | Complete |
| Tests | 248 |
| Coverage | 97.7% |
| Python | ≥ 3.13 |

## License

AGPL-3.0-or-later
