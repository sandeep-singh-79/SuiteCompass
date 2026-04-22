# V1-C Execution Plan: LLM Narrative Layer

> **Status:** DRAFT — awaiting confirmation before implementation  
> **Depends on:** V1-A (history overlay) + V1-B (diff mapper) — both complete, 406 tests passing  
> **Branch strategy:** Create `v1c-llm-narrative` from current `v1b-diff-mapper`  
> **Goal:** Add an LLM-powered mode that wraps the deterministic scoring results in a contextual narrative report, with structural repair, deterministic fallback, and comparison mode.

---

## Design Principles

1. **Deterministic core is ground truth.** The LLM does not replace scoring — it narrates the deterministic results. Every fact in the LLM output must trace back to a deterministic tier assignment or classification.
2. **Reuse-first from QEStrategyForge.** Copy-adapt proven LLM modules (Protocol, factory, config loader, provider clients, prompt builder, repair chain). Divergence from QEStrategyForge requires a written reason.
3. **Output contract preserved.** The LLM output must pass the same `validate_output()` checks: 6 headings, 7 labels, section-aware placement. The LLM adds narrative prose around the structural skeleton.
4. **Repair before fallback before failure.** Chain: LLM raw → structural repair → validate → if still invalid, deterministic fallback → if somehow that fails too, exit 3.
5. **No new external dependencies.** All HTTP via `urllib.request` (stdlib). No `openai`, `httpx`, or `requests`.
6. **API keys from env vars only.** Config files may set provider/model/base-url but never API keys. Enforced by `_FORBIDDEN_FILE_KEYS`.

---

## Domain Adaptation Decisions

| Decision | Value | Reason |
|---|---|---|
| Env var prefix | `IRO_LLM_` | Matches CLI name `iro`; short, distinct |
| Exit code for generation errors | `EXIT_GENERATION_ERROR = 3` | Extends existing 0/1/2 scheme; matches QEStrategyForge convention |
| Recommendation Mode values | `deterministic` / `llm` / `llm-repaired` / `deterministic-fallback` | User can see exactly which path produced the output |
| Prompt scenario routing key | `classifications` dict | Reuse existing `classify_context()` output — sprint_risk_level, suite_health, time_pressure |
| Scenario templates | `high_risk`, `degraded_suite`, `budget_pressure`, `balanced` | Map from classification combinations; simpler than QEStrategyForge's 4 scenarios |
| Prompt input fields | ALL fields from `normalized` + `classifications` + `tier_result` | Insight #5: silent omission is a regression |
| LLM output expectation | Markdown with same 6 headings + 7 labels + narrative prose between/around them | LLM adds value through explanation, not through different structure |
| FakeLLMClient response | Pre-computed valid SuiteCompass report with `Recommendation Mode: llm` | Enables full pipeline testing without network calls |

---

## Dependency Graph

```
C1-1 (models + protocol + fake) ──┬──→ C1-2 (provider clients) ──→ C1-3 (config + factory)
                                   │                                        │
C2-1 (template loader + templates) │                                        │
       │                           │                                        │
       ▼                           │                                        │
C2-2 (prompt builder) ◄───────────┘                                        │
       │                                                                    │
       ▼                                                                    │
C3-1 (LLM flow orchestration) ──┬──→ C3-2 (repair + fallback)             │
                                 │                                          │
                                 └──→ C3-3 (comparison reporter)           │
                                              │                             │
                                              ▼                             │
                                   C4-1 (CLI integration) ◄────────────────┘
                                              │
                                              ▼
                                   C5-1 (hardening + benchmark + docs)
```

**Parallelism opportunities:** C1-1 and C2-1 can be built simultaneously. C1-2 and C2-2 can proceed once C1-1 is done. C3-2 and C3-3 are independent of each other.

---

## Story Specifications

---

### C1-1: LLM Data Models + Protocol + FakeLLMClient

**As a** developer integrating LLM support,  
**I want** typed data models and a Protocol-based client boundary,  
**so that** all LLM clients share a common interface testable without network calls.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Yes — no dependency on other C stories; only adds to `models.py` and new `llm_client.py` |
| **N**egotiable | Implementation details (field names, dataclass vs slots) flexible within the Protocol contract |
| **V**aluable | Enables all downstream stories (clients, flow, CLI) to program against a stable interface |
| **E**stimable | Small — ~4 dataclasses + 1 Protocol + 1 FakeLLMClient; copy-adapt from QEStrategyForge |
| **S**mall | ~100-150 lines of production code + ~80-100 lines of tests |
| **T**estable | Binary: Protocol compliance checks, FakeLLMClient returns valid output, model field access |

#### Interface Specification

```python
# models.py additions
EXIT_GENERATION_ERROR: int = 3

@dataclass(slots=True)
class ProviderConfig:
    provider: str           # "openai" | "ollama" | "gemini"
    model: str              # e.g. "gpt-4o", "llama3", "gemini-pro"
    base_url: str | None    # override endpoint
    api_key: str | None     # from env var only
    temperature: float      # default 0.3
    max_tokens: int         # default 4096

@dataclass(slots=True)
class GenerationRequest:
    system_prompt: str
    user_prompt: str
    config: ProviderConfig

@dataclass(slots=True)
class GenerationResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

# llm_client.py (new file)
@runtime_checkable
class LLMClient(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...

class FakeLLMClient:
    """Deterministic client for testing. Returns a pre-computed valid report."""
    def __init__(self, response_content: str | None = None): ...
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...
```

#### Acceptance Criteria

- [ ] `ProviderConfig`, `GenerationRequest`, `GenerationResponse` are `@dataclass(slots=True)` in `models.py`
- [ ] `EXIT_GENERATION_ERROR = 3` added to `models.py`
- [ ] `LLMClient` is a `@runtime_checkable` Protocol in `llm_client.py`
- [ ] `FakeLLMClient` implements `LLMClient` and returns a pre-computed valid SuiteCompass report
- [ ] `isinstance(FakeLLMClient(), LLMClient)` returns `True`
- [ ] FakeLLMClient default response passes `validate_output()`
- [ ] All tests pass; coverage ≥ 90% on both `models.py` and `llm_client.py`

#### Files

| Action | File |
|---|---|
| Modify | `src/intelligent_regression_optimizer/models.py` |
| Create | `src/intelligent_regression_optimizer/llm_client.py` |
| Create | `tests/test_llm_client.py` |

---

### C1-2: Provider Clients (OpenAI, Ollama, Gemini)

**As a** user who wants LLM-enhanced reports,  
**I want** provider clients for OpenAI, Ollama, and Gemini,  
**so that** I can use my preferred LLM provider without changing any code.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on C1-1 (Protocol + models) only |
| **N**egotiable | Provider count negotiable; internal HTTP details flexible |
| **V**aluable | Delivers the actual LLM connectivity — central to V1-C value |
| **E**stimable | Copy-adapt from QEStrategyForge; each client is ~50-80 lines |
| **S**mall | ~200 lines production code + ~150 lines tests |
| **T**estable | Protocol compliance, HTTP request shape validation (mocked urllib), error handling |

#### Interface Specification

```python
# openai_client.py
class OpenAIClient:
    def __init__(self, config: ProviderConfig) -> None: ...
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...
    # POST to {base_url}/v1/chat/completions, Bearer auth, 300s timeout

# ollama_client.py
class OllamaClient:
    def __init__(self, config: ProviderConfig) -> None: ...
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...
    # POST to {base_url}/api/generate, no auth

# gemini_client.py
class GeminiClient:
    def __init__(self, config: ProviderConfig) -> None: ...
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...
    # POST to {base_url}/v1beta/models/{model}:generateContent?key=, API key in URL param
```

#### Acceptance Criteria

- [ ] Each client class implements `LLMClient` Protocol — `isinstance()` returns `True`
- [ ] Each client constructs the correct HTTP request shape (verified via mocked urllib)
- [ ] OpenAI: Bearer token in Authorization header, `messages` array format
- [ ] Ollama: no auth header, `prompt` field format
- [ ] Gemini: API key as URL parameter, `contents` array format
- [ ] Each client raises a descriptive error on HTTP failure (non-200 status)
- [ ] Each client raises a descriptive error on missing API key (OpenAI, Gemini)
- [ ] Timeout set to 300s for all clients
- [ ] No new external dependencies — all via `urllib.request`
- [ ] All tests pass; coverage ≥ 90% per client module

#### Files

| Action | File |
|---|---|
| Create | `src/intelligent_regression_optimizer/openai_client.py` |
| Create | `src/intelligent_regression_optimizer/ollama_client.py` |
| Create | `src/intelligent_regression_optimizer/gemini_client.py` |
| Create | `tests/test_openai_client.py` |
| Create | `tests/test_ollama_client.py` |
| Create | `tests/test_gemini_client.py` |

---

### C1-3: Config Loader + Client Factory

**As a** user configuring LLM settings,  
**I want** a layered config system that merges defaults, config file, env vars, and CLI flags,  
**so that** I can set provider defaults in a file and override per-run without editing config.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on C1-1 (ProviderConfig) and C1-2 (client classes for factory dispatch) |
| **N**egotiable | Layer count, env var names, file format (YAML) details are flexible |
| **V**aluable | Eliminates hardcoded provider settings; enables both CI and interactive use |
| **E**stimable | Copy-adapt from QEStrategyForge config_loader + client_factory |
| **S**mall | ~120 lines production + ~100 lines tests |
| **T**estable | Layer precedence tests, forbidden key enforcement, factory dispatch |

#### Interface Specification

```python
# config_loader.py
_FORBIDDEN_FILE_KEYS: frozenset[str]  # {"api_key"}

def load_llm_config(
    config_path: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> ProviderConfig:
    """4-layer resolution: defaults → config file → env vars (IRO_LLM_*) → CLI flags.

    API key resolved from env var IRO_LLM_API_KEY only. Never from config file.
    """

# client_factory.py
def create_llm_client(config: ProviderConfig) -> LLMClient:
    """Dispatch to OpenAIClient / OllamaClient / GeminiClient by config.provider."""
```

**Env var mapping:**

| Env var | Maps to |
|---|---|
| `IRO_LLM_PROVIDER` | `provider` |
| `IRO_LLM_MODEL` | `model` |
| `IRO_LLM_BASE_URL` | `base_url` |
| `IRO_LLM_API_KEY` | `api_key` |
| `IRO_LLM_TEMPERATURE` | `temperature` |
| `IRO_LLM_MAX_TOKENS` | `max_tokens` |

#### Acceptance Criteria

- [ ] 4-layer precedence: CLI > env var > config file > defaults (verified by test)
- [ ] Config file with `api_key` raises `ValueError` with clear message
- [ ] `IRO_LLM_API_KEY` env var is the only source for API key
- [ ] Default provider is `"openai"`, default model is `"gpt-4o"`, default temperature is `0.3`
- [ ] `create_llm_client()` returns correct client type for each provider name
- [ ] Unknown provider name raises `ValueError`
- [ ] Config file format is YAML (consistent with project convention)
- [ ] All tests pass; coverage ≥ 90% on `config_loader.py` and `client_factory.py`

#### Files

| Action | File |
|---|---|
| Create | `src/intelligent_regression_optimizer/config_loader.py` |
| Create | `src/intelligent_regression_optimizer/client_factory.py` |
| Create | `tests/test_config_loader.py` |
| Create | `tests/test_client_factory.py` |

---

### C2-1: Template Loader + Prompt Templates

**As a** developer building the prompt pipeline,  
**I want** a template loader and versioned prompt templates,  
**so that** prompts can be iterated independently of code and versioned for future optimization.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Yes — no dependency on C1; only creates template infrastructure |
| **N**egotiable | Template format (plain text with `{placeholders}`), directory structure flexible |
| **V**aluable | Separates prompt content from code; enables future Karpathy optimization loop |
| **E**stimable | Copy-adapt template_loader from QEStrategyForge; write domain-specific templates |
| **S**mall | ~40 lines loader + 4 template files + ~60 lines tests |
| **T**estable | Load existing template succeeds, missing template raises FileNotFoundError, template contains expected placeholders |

#### Interface Specification

```python
# template_loader.py
def load_template(
    name: str,
    version: str = "v1",
    prompt_dir: Path | None = None,
) -> str:
    """Load prompts/{version}/{name}.txt and return its content.

    Default prompt_dir is <package_root>/prompts/.
    Raises FileNotFoundError if template does not exist.
    """
```

**Template directory:**

```
src/intelligent_regression_optimizer/prompts/v1/
    system.txt              # System prompt: role, constraints, output format rules
    high_risk.txt           # Scenario: sprint_risk_level=high
    degraded_suite.txt      # Scenario: suite_health=degraded
    budget_pressure.txt     # Scenario: time_pressure=tight + budget_overflow
    balanced.txt            # Scenario: default / no special conditions
```

Each template uses `{placeholder}` syntax for variable substitution (Python `str.format()`).

#### Acceptance Criteria

- [ ] `load_template("system")` returns content of `prompts/v1/system.txt`
- [ ] `load_template("high_risk")` returns content of `prompts/v1/high_risk.txt`
- [ ] `load_template("nonexistent")` raises `FileNotFoundError`
- [ ] Custom `prompt_dir` override works
- [ ] All 5 template files exist and are non-empty
- [ ] `system.txt` includes output format rules (6 headings, 7 labels)
- [ ] Each scenario template has `{placeholders}` for all input schema fields
- [ ] All tests pass; coverage ≥ 90% on `template_loader.py`

#### Files

| Action | File |
|---|---|
| Create | `src/intelligent_regression_optimizer/template_loader.py` |
| Create | `src/intelligent_regression_optimizer/prompts/v1/system.txt` |
| Create | `src/intelligent_regression_optimizer/prompts/v1/high_risk.txt` |
| Create | `src/intelligent_regression_optimizer/prompts/v1/degraded_suite.txt` |
| Create | `src/intelligent_regression_optimizer/prompts/v1/budget_pressure.txt` |
| Create | `src/intelligent_regression_optimizer/prompts/v1/balanced.txt` |
| Create | `tests/test_template_loader.py` |

---

### C2-2: Prompt Builder with Scenario Routing

**As a** developer wiring the LLM pipeline,  
**I want** a prompt builder that selects the right scenario template and populates all fields,  
**so that** the LLM receives complete, context-appropriate input for every run.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on C2-1 (template loader) and C1-1 (TierResult model, already exists) |
| **N**egotiable | Scenario selection logic, field formatting details flexible |
| **V**aluable | Core intelligence of how the LLM is guided; directly affects output quality |
| **E**stimable | ~80-100 lines; scenario routing logic + field formatting |
| **S**mall | Single module, single public function |
| **T**estable | Correct scenario selected for each classification combo; all input fields present in prompt; output is (system_prompt, user_prompt) tuple |

#### Interface Specification

```python
# prompt_builder.py
def build_prompt(
    normalized: dict[str, Any],
    classifications: dict[str, Any],
    tier_result: TierResult,
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for LLM generation.

    Scenario routing:
    - sprint_risk_level == "high"                    → high_risk template
    - suite_health == "degraded"                     → degraded_suite template
    - time_pressure == "tight" and budget_overflow   → budget_pressure template
    - otherwise                                      → balanced template

    Priority: high_risk > degraded_suite > budget_pressure > balanced
    (first match wins)

    All fields from normalized, classifications, and tier_result are
    formatted into the user_prompt. Insight #5: no silent field omission.
    """
```

**Scenario routing table:**

| Priority | Condition | Template |
|---|---|---|
| 1 | `sprint_risk_level == "high"` | `high_risk` |
| 2 | `suite_health == "degraded"` | `degraded_suite` |
| 3 | `time_pressure == "tight"` AND `tier_result.budget_overflow` | `budget_pressure` |
| 4 | (default) | `balanced` |

#### Acceptance Criteria

- [ ] Returns `(system_prompt, user_prompt)` tuple
- [ ] System prompt loaded from `system.txt` template
- [ ] Correct scenario template selected per routing table
- [ ] Priority order respected (high_risk wins over degraded if both apply)
- [ ] User prompt contains: all test IDs with their tiers, all classification values, sprint context summary, constraint values
- [ ] No input schema field silently omitted (verify all fields from `normalized` keys appear)
- [ ] `tier_result` tier assignments are embedded verbatim in the prompt (the LLM must reflect these, not invent its own)
- [ ] All tests pass; coverage ≥ 90% on `prompt_builder.py`

#### Files

| Action | File |
|---|---|
| Create | `src/intelligent_regression_optimizer/prompt_builder.py` |
| Create | `tests/test_prompt_builder.py` |

---

### C3-1: LLM Flow Orchestration

**As a** user running in LLM mode,  
**I want** a pipeline that generates, validates, repairs, and falls back automatically,  
**so that** I always get a structurally valid report regardless of LLM output quality.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on C1-1 (LLMClient Protocol) and C2-2 (prompt builder); uses existing output_validator |
| **N**egotiable | Internal step ordering, logging approach flexible |
| **V**aluable | Core pipeline that delivers the LLM-powered user experience |
| **E**stimable | ~100-120 lines; orchestration logic with clear step sequence |
| **S**mall | Single module, two public functions |
| **T**estable | Happy path, repair path, fallback path, generation error path — all testable with FakeLLMClient |

#### Interface Specification

```python
# llm_flow.py

@dataclass(slots=True)
class LLMFlowResult:
    """Extended result carrying repair/fallback metadata."""
    flow_result: FlowResult              # standard exit_code + message + warnings
    recommendation_mode: str             # "llm" | "llm-repaired" | "deterministic-fallback"
    raw_llm_output: str | None           # original LLM text before repair
    repair_actions: list[str]            # what was repaired (empty if clean)

def run_llm_pipeline(
    normalized: dict[str, Any],
    classifications: dict[str, Any],
    tier_result: TierResult,
    client: LLMClient,
) -> LLMFlowResult:
    """Full LLM pipeline: prompt → generate → validate → repair → fallback.

    Steps:
    1. build_prompt(normalized, classifications, tier_result)
    2. client.generate(request)
    3. validate_output(raw_llm_output)
    4. If invalid: repair_output(raw_llm_output, tier_result)
    5. validate_output(repaired)
    6. If still invalid: deterministic fallback via render_report()
    7. Return LLMFlowResult with appropriate recommendation_mode
    """

def run_compare_pipeline(
    normalized: dict[str, Any],
    classifications: dict[str, Any],
    tier_result: TierResult,
    client: LLMClient,
) -> FlowResult:
    """Run both deterministic and LLM pipelines, return comparison report."""
```

#### Acceptance Criteria

- [ ] Happy path: valid LLM output → `recommendation_mode = "llm"`, empty `repair_actions`
- [ ] Repair path: invalid LLM output, repairable → `recommendation_mode = "llm-repaired"`, non-empty `repair_actions`
- [ ] Fallback path: unrepairable LLM output → `recommendation_mode = "deterministic-fallback"`, deterministic report in message
- [ ] Generation error (client raises) → `FlowResult(exit_code=3, ...)`
- [ ] `Recommendation Mode:` label in output matches `recommendation_mode`
- [ ] Final output always passes `validate_output()` (except exit_code=3)
- [ ] `raw_llm_output` preserved for debugging even when repair/fallback occurs
- [ ] All tests pass; coverage ≥ 90% on `llm_flow.py`

#### Files

| Action | File |
|---|---|
| Create | `src/intelligent_regression_optimizer/llm_flow.py` |
| Create | `tests/test_llm_flow.py` |

---

### C3-2: Structural Repair + Deterministic Fallback

**As a** pipeline operator,  
**I want** the system to auto-repair common LLM structural defects,  
**so that** minor formatting errors don't cause unnecessary fallbacks to deterministic mode.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on output_validator (existing) and renderer (for fallback); called by C3-1 |
| **N**egotiable | Repair strategies (which defects to fix) negotiable |
| **V**aluable | Directly reduces fallback rate; maximises LLM mode success |
| **E**stimable | ~80-100 lines; pattern-based string manipulation |
| **S**mall | Single module with focused responsibility |
| **T**estable | Each repair strategy independently testable: input with defect → repaired output passes validation |

#### Interface Specification

```python
# repair.py

@dataclass(slots=True)
class RepairResult:
    markdown: str
    actions: list[str]      # human-readable description of each repair applied
    is_repaired: bool       # True if any repair was applied

def repair_output(
    markdown: str,
    tier_result: TierResult,
    classifications: dict[str, Any],
) -> RepairResult:
    """Attempt structural repair of LLM-generated markdown.

    Repair strategies (applied in order):
    1. Missing headings: inject required headings with empty content
    2. Missing labels: inject required labels with values from tier_result/classifications
    3. Duplicate labels: keep first occurrence, remove subsequent
    4. Labels in wrong section: move label to correct section
    5. Recommendation Mode fixup: ensure label says "llm-repaired" after repair

    Does NOT alter narrative prose — only structural elements.
    """
```

#### Acceptance Criteria

- [ ] Missing heading → heading injected in correct position; repair recorded
- [ ] Missing label → label injected with correct value from tier_result; repair recorded
- [ ] Duplicate label → duplicates removed; repair recorded
- [ ] Label in wrong section → moved to correct section; repair recorded
- [ ] After repair, `Recommendation Mode:` says `llm-repaired`
- [ ] Repair does not alter narrative prose between structural elements
- [ ] If no defects found, `is_repaired = False`, `actions` empty, markdown unchanged
- [ ] All tests pass; coverage ≥ 90% on `repair.py`

#### Files

| Action | File |
|---|---|
| Create | `src/intelligent_regression_optimizer/repair.py` |
| Create | `tests/test_repair.py` |

---

### C3-3: Comparison Reporter

**As a** user evaluating LLM quality,  
**I want** a side-by-side comparison of deterministic and LLM outputs,  
**so that** I can assess whether LLM mode adds value before adopting it.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on C3-1 (LLMFlowResult for repair stats); uses existing renderer + output_validator |
| **N**egotiable | Report format (sections, headings, wording) flexible |
| **V**aluable | Key decision-support feature for LLM adoption |
| **E**stimable | ~60-80 lines; markdown assembly |
| **S**mall | Single module, single function |
| **T**estable | Output contains both reports, repair stats section present, comparison headings correct |

#### Interface Specification

```python
# comparison.py

def build_comparison_report(
    deterministic_md: str,
    llm_flow_result: LLMFlowResult,
) -> str:
    """Build a side-by-side comparison markdown report.

    Sections:
    1. Comparison Summary (mode used, repair count, fallback triggered)
    2. Deterministic Output (full deterministic report)
    3. LLM Output (full LLM report — repaired or fallback)
    4. Repair Log (if any repairs applied)
    """
```

#### Acceptance Criteria

- [ ] Output contains `## Comparison Summary` with mode and repair count
- [ ] Output contains `## Deterministic Output` with full deterministic report
- [ ] Output contains `## LLM Output` with full LLM/repaired/fallback report
- [ ] Repair log section present when `repair_actions` is non-empty
- [ ] Repair log section absent (or empty) when no repairs applied
- [ ] All tests pass; coverage ≥ 90% on `comparison.py`

#### Files

| Action | File |
|---|---|
| Create | `src/intelligent_regression_optimizer/comparison.py` |
| Create | `tests/test_comparison.py` |

---

### C4-1: CLI Integration (Mode / Provider / Model Flags)

**As a** command-line user,  
**I want** `--mode`, `--provider`, `--model`, and related flags on `iro run`,  
**so that** I can switch between deterministic and LLM modes without editing files.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on C1-3 (config loader), C3-1 (llm_flow), C3-3 (comparison); CLI is the composition root |
| **N**egotiable | Flag names, defaults, grouping flexible |
| **V**aluable | The user-facing surface for all V1-C functionality |
| **E**stimable | Extends existing CLI with ~8 new Click options + routing logic |
| **S**mall | ~60-80 lines of new CLI code + ~80-100 lines of tests |
| **T**estable | Flag parsing, mode routing, config file integration, error messages |

#### Interface Specification

New Click options on `iro run`:

| Flag | Type | Default | Description |
|---|---|---|---|
| `--mode` | Choice | `deterministic` | `deterministic` / `llm` / `compare` |
| `--provider` | String | (from config) | LLM provider name |
| `--model` | String | (from config) | Model identifier |
| `--base-url` | String | (from config) | Provider API endpoint |
| `--temperature` | Float | (from config) | Sampling temperature |
| `--max-tokens` | Int | (from config) | Max response tokens |
| `--config` | Path | None | Path to LLM config YAML |

#### Acceptance Criteria

- [ ] `iro run input.yaml` (no flags) → deterministic mode, identical to current behaviour
- [ ] `iro run input.yaml --mode llm --provider openai --model gpt-4o` → LLM mode
- [ ] `iro run input.yaml --mode compare` → comparison report to stdout
- [ ] `--mode llm` without `IRO_LLM_API_KEY` set → clear error message, exit 1
- [ ] `--config llm-config.yaml` loads config file, CLI flags override it
- [ ] `--mode deterministic` ignores all LLM flags (no error)
- [ ] LLM/compare mode with `--output` writes to file
- [ ] Help text for each new flag is accurate (contract triangle: help ↔ implementation ↔ test)
- [ ] All tests pass; coverage ≥ 90% on `cli.py`

#### Files

| Action | File |
|---|---|
| Modify | `src/intelligent_regression_optimizer/cli.py` |
| Modify | `tests/test_cli.py` |

---

### C5-1: Phase C Hardening + Benchmark + Documentation

**As a** project maintainer,  
**I want** comprehensive hardening before sealing Phase C,  
**so that** all new modules meet quality standards and users have accurate documentation.

#### INVEST Assessment

| Criterion | Assessment |
|---|---|
| **I**ndependent | Depends on all C1-C4 stories being complete |
| **N**egotiable | Specific edge cases and doc sections flexible |
| **V**aluable | Ensures quality bar; reduces post-release defects |
| **E**stimable | Predictable scope: coverage gaps + benchmark + doc updates |
| **S**mall | Bounded by the coverage report + known doc files |
| **T**estable | Coverage ≥ 90% per module, benchmark passes, docs updated |

#### Scope

1. **Coverage audit:** Every new module at ≥ 90% line coverage. Fix gaps.
2. **Benchmark assertions:** New assertions file for LLM output contract — headings, labels, recommendation mode values.
3. **Edge case tests:** Empty test suite, all manual tests, single test, provider timeout.
4. **Documentation updates:**
   - `USAGE-GUIDE.md`: LLM mode CLI reference, new workflow section (Workflow 6: LLM-Enhanced Report)
   - `LEARNING-GUIDE.md`: domain explanation for LLM integration concepts
   - `README.md`: Development Status table, CLI table, new features section
   - `V1-INPUT-TEMPLATE.md`: LLM config YAML schema section (if applicable)
5. **Self-review cycle:** Dead code, unused imports, over-abstraction, missing edge cases.
6. **Pre-seal branch review:** Review V1-C diff against V1-B baseline per insight #25.

#### Acceptance Criteria

- [ ] `pytest --tb=short -q` passes with all tests green
- [ ] Coverage ≥ 90% on every new module (measured individually)
- [ ] Benchmark assertions for LLM mode pass against FakeLLMClient output
- [ ] USAGE-GUIDE has Workflow 6 (LLM-Enhanced Report) section
- [ ] LEARNING-GUIDE has LLM integration concepts section
- [ ] README Development Status updated
- [ ] Self-review findings are empty or all resolved
- [ ] Pre-seal branch review written findings — all resolved or deferred with reasons

#### Files

| Action | File |
|---|---|
| Create | `benchmarks/llm-output.assertions.yaml` |
| Modify | `docs/USAGE-GUIDE.md` |
| Modify | `docs/LEARNING-GUIDE.md` |
| Modify | `README.md` |
| Modify | Various test files (gap fixes) |

---

## Execution Order

| Step | Story | Depends On | Key Deliverable |
|---|---|---|---|
| 1 | C1-1 | — | Protocol + FakeLLMClient |
| 2 | C2-1 | — | Template loader + 5 prompt templates |
| 3 | C1-2 | C1-1 | 3 provider clients |
| 4 | C2-2 | C2-1, C1-1 | Prompt builder with scenario routing |
| 5 | C1-3 | C1-1, C1-2 | Config loader + client factory |
| 6 | C3-1 | C1-1, C2-2 | LLM flow orchestration |
| 7 | C3-2 | C3-1 | Repair chain + fallback |
| 8 | C3-3 | C3-1 | Comparison reporter |
| 9 | C4-1 | C1-3, C3-1, C3-3 | CLI flags + mode routing |
| 10 | C5-1 | All above | Hardening, benchmark, docs |

**Steps 1 & 2 are parallel.** Steps 3 & 4 are parallel after step 1. Steps 7 & 8 are parallel after step 6.

---

## New Module Summary

| Module | Lines (est.) | Purpose |
|---|---|---|
| `llm_client.py` | ~60 | Protocol + FakeLLMClient |
| `openai_client.py` | ~70 | OpenAI provider |
| `ollama_client.py` | ~60 | Ollama provider |
| `gemini_client.py` | ~70 | Gemini provider |
| `config_loader.py` | ~80 | 4-layer config resolution |
| `client_factory.py` | ~30 | Provider dispatch |
| `template_loader.py` | ~30 | Template file loading |
| `prompt_builder.py` | ~100 | Scenario routing + field assembly |
| `llm_flow.py` | ~120 | Pipeline orchestration |
| `repair.py` | ~100 | Structural repair strategies |
| `comparison.py` | ~70 | Side-by-side report builder |
| **Total new** | **~790** | |

**Test modules:** ~11 new test files, estimated ~800-1000 lines of tests.

---

## Risk Register

| Risk | Mitigation |
|---|---|
| LLM output wildly divergent from expected structure | Repair chain + deterministic fallback ensures valid output always |
| Prompt templates too generic → low-value narrative | Embed deterministic tier assignments verbatim in prompt; LLM explains, not decides |
| API key leak in config file | `_FORBIDDEN_FILE_KEYS` enforcement; tests verify rejection |
| urllib timeout on slow providers | 300s timeout; generation error exit code 3; fallback path |
| Template placeholder mismatch after schema changes | Insight #5: test that all `normalized` keys appear in prompt output |
| Repair chain hides real LLM quality issues | `repair_actions` list preserved in LLMFlowResult; comparison mode surfaces raw vs repaired |
