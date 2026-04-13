# AI Code Refactoring and Optimization System

An AI-powered pipeline that automatically analyzes any GitHub repository, detects code quality issues, generates LLM-powered refactoring suggestions, benchmarks performance improvements, and publishes results via GitHub Pages.

## Features

- Clone any public GitHub repository
- Static analysis with pylint, flake8, and bandit
- Cyclomatic complexity evaluation and code smell detection using radon
- LLM-based code refactoring (OpenAI GPT-4o, Ollama, or rule-based fallback)
- Performance benchmarking of original vs. refactored functions
- Automated HTML report published to GitHub Pages
- Scheduled weekly analysis via GitHub Actions

---

## Design Patterns & Principles

This project was deliberately structured to demonstrate industry-standard software design patterns and SOLID principles. Every pattern solves a concrete problem in the codebase.

### Architectural Pattern — Pipeline

**File:** [pipeline/base.py](pipeline/base.py) · [pipeline/stages.py](pipeline/stages.py)

The six analysis stages are chained into a `Pipeline` that passes a shared context dict from stage to stage. Each stage reads upstream results from the context and stores its own result under a unique key. This eliminates the brittle sequential variable wiring that was in `main.py` before, and makes the order of stages explicit and reorderable.

```text
Pipeline.execute(context={})
  │
  ├─▶ LoadRepoStage       → context["meta"]
  ├─▶ StaticAnalysisStage → context["static_report"]
  ├─▶ ComplexityStage     → context["complexity_report"]
  ├─▶ RefactoringStage    → context["refactoring_report"]
  ├─▶ BenchmarkStage      → context["benchmark_report"]
  └─▶ ReportStage         → context["report"]
```

### Behavioural Pattern — Strategy + Factory

**File:** [pipeline/strategies.py](pipeline/strategies.py)

**Problem:** The original `LLMRefactoringEngine` selected its LLM provider with a chain of `if LLM_PROVIDER == "openai"` branches scattered through the class. Adding a new provider meant editing the engine itself.

**Solution:**

- `LLMStrategy` — a `Protocol` (structural interface) that every provider must satisfy with a single `refactor(source_code) -> dict` method.
- `OpenAIStrategy`, `OllamaStrategy`, `RuleBasedStrategy` — three independent concrete implementations.
- `LLMStrategyFactory.create()` — reads `LLM_PROVIDER` once and returns the right instance. Callers never import a concrete strategy class.
- `LLMStrategyFactory.register(name, cls)` — registers a custom provider at runtime (OCP extension point).

```python
# Before: engine knew about every provider
if LLM_PROVIDER == "openai":
    return self._call_openai(source_code)
elif LLM_PROVIDER == "ollama":
    ...

# After: engine delegates to an injected strategy
response = self._strategy.refactor(source_code)
```

### Structural Pattern — Template Method

**File:** [pipeline/base.py](pipeline/base.py)

`PipelineStage` is an abstract base class that defines the contract every stage must fulfil:

| Member | Role |
| ------ | ---- |
| `name` (abstract property) | The key under which the result is stored in the context dict |
| `run(context)` (abstract method) | The actual stage logic |

The base class never dictates *how* to run — only *that* run exists and returns something. This is the Template Method pattern applied at the interface level.

### Structural Pattern — Adapter

**File:** [pipeline/stages.py](pipeline/stages.py)

Each domain service (`RepoLoader`, `StaticAnalyzer`, …) has its own API. The six `*Stage` classes are thin adapters that:

1. Accept the domain service via constructor injection.
2. Translate the `run(context)` call into the service's native API.
3. Return the result in the shape the pipeline expects.

This keeps domain services independent of the pipeline — `RepoLoader` knows nothing about `PipelineStage`.

### Behavioural Pattern — Observer

**File:** [pipeline/base.py](pipeline/base.py) · [main.py](main.py)

`Pipeline` accepts an optional `on_stage_complete(stage_name, result)` callback. After every stage the pipeline fires this callback without importing or knowing anything about logging, monitoring, or alerting. In `main.py` the observer simply logs progress; in tests it can collect results; in a future UI it could emit WebSocket events — all without changing `Pipeline`.

```python
Pipeline(stages=stages, on_stage_complete=_on_stage_complete)
```

---

## SOLID Principles Applied

| Principle | Where | How |
| --------- | ----- | --- |
| **S** — Single Responsibility | Every `*Strategy`, every `*Stage` | Each class has exactly one job; provider logic, pipeline wiring, and domain analysis are in separate files |
| **O** — Open / Closed | `StaticAnalyzer.register_tool()` | New linters can be added without touching existing methods |
| **O** — Open / Closed | `LLMStrategyFactory.register()` | New LLM providers registered at runtime without editing the factory |
| **L** — Liskov Substitution | All `PipelineStage` subclasses | Any stage can replace any other in the pipeline list without breaking `Pipeline.execute()` |
| **I** — Interface Segregation | `LLMStrategy` Protocol | One method only — consumers depend only on what they use |
| **D** — Dependency Inversion | `LLMRefactoringEngine(strategy=…)` | High-level engine depends on the `LLMStrategy` abstraction; concrete providers injected from `main.py` |

---

## Project Structure

```text
GiFrac/
├── main.py                          # Entry point; wires pipeline + DI
├── pipeline/
│   ├── base.py                      # PipelineStage ABC + Pipeline + Observer
│   ├── stages.py                    # Adapter stages (one per domain service)
│   ├── strategies.py                # LLMStrategy Protocol + 3 providers + Factory
│   ├── repo_loader.py               # Stage 1: Clone repository
│   ├── static_analyzer.py           # Stage 2: Pylint / Flake8 / Bandit (OCP)
│   ├── complexity_evaluator.py      # Stage 3: Radon complexity + smell detection
│   ├── llm_refactoring_engine.py    # Stage 4: Strategy consumer (DIP)
│   ├── benchmark_system.py          # Stage 5: Performance benchmarking
│   └── report_generator.py          # Stage 6: HTML report generation
├── .github/workflows/
│   └── analyze.yml                  # GitHub Actions CI/CD pipeline
├── requirements.txt
├── docs/                            # Generated reports (GitHub Pages)
└── README.md
```

---

## Pipeline Architecture

```text
repo_loader → static_analyzer → complexity_evaluator → llm_refactoring_engine → benchmark_system → report_generator
```

| Stage | Module | Purpose |
| ----- | ------ | ------- |
| 1 | `repo_loader.py` | Clone repository and inventory files |
| 2 | `static_analyzer.py` | Run pylint / flake8 / bandit static analysis |
| 3 | `complexity_evaluator.py` | Measure cyclomatic complexity and detect smells |
| 4 | `llm_refactoring_engine.py` | Generate optimized code via injected LLMStrategy |
| 5 | `benchmark_system.py` | Benchmark original vs refactored functions |
| 6 | `report_generator.py` | Generate HTML report for GitHub Pages |

---

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run Analysis

```bash
python main.py https://github.com/YOUR_USERNAME/YOUR_REPO
```

### Options

```text
python main.py <repo_url> [--branch main] [--workspace ./workspace] [--output ./docs] [--iterations 1000]
```

---

## LLM Configuration

Set the `LLM_PROVIDER` environment variable to select the refactoring engine:

| Provider | Setup |
| -------- | ----- |
| `mock` (default) | Rule-based analysis, no API key needed |
| `openai` | Set `OPENAI_API_KEY` environment variable |
| `ollama` | Run Ollama locally with `OLLAMA_HOST=http://localhost:11434` |

```bash
# OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
python main.py https://github.com/example/repo

# Ollama (local)
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=codellama
python main.py https://github.com/example/repo
```

### Registering a Custom LLM Provider

Thanks to the Factory + OCP design, you can add a new provider without modifying `strategies.py`:

```python
from pipeline.strategies import LLMStrategyFactory

class AnthropicStrategy:
    def refactor(self, source_code: str) -> dict:
        ...

LLMStrategyFactory.register("anthropic", AnthropicStrategy)
```

### Registering a Custom Static Analysis Tool

```python
from pathlib import Path
from pipeline.static_analyzer import StaticAnalyzer, Issue

def run_mypy(path: Path) -> list[Issue]:
    ...

analyzer = StaticAnalyzer()
analyzer.register_tool("mypy", run_mypy)
```

---

## Optimization Strategies

The LLM refactoring engine applies:

| # | Strategy | Description |
| - | -------- | ----------- |
| 1 | Extract Method | Split long functions (> 30 lines) into single-purpose helpers |
| 2 | Guard Clauses | Invert nested if-else with early returns to flatten structure |
| 3 | Named Constants | Replace magic numbers with descriptive module-level constants |
| 4 | Comprehensions | Convert imperative loops to declarative list/dict comprehensions |
| 5 | Type Annotations | Add missing Python type hints for IDE support and static checking |
| 6 | Dead Code Removal | Flag unreachable branches and unused variables |
| 7 | Dependency Injection | Replace hard-coded instantiation with constructor parameters |
| 8 | Rename for Clarity | Replace vague identifiers with names that communicate intent |

---

## Outputs

### Refactored Code Suggestions
For each function with cyclomatic complexity > 10, the engine provides:
- The original function source
- A refactored version with improvements applied
- A list of specific improvements made
- A rationale explaining the changes

### Performance Benchmarks
For each refactored function:
- Original execution time (ms)
- Refactored execution time (ms)
- Speedup ratio
- Memory allocation delta (KB)

### Maintainability Score
A 0-100 score derived from radon's Maintainability Index, indicating overall code health.

---

## GitHub Actions Workflow

The workflow at `.github/workflows/analyze.yml`:

1. Triggers on `workflow_dispatch` (manual run) or weekly on Monday at 06:00 UTC
2. Installs all dependencies
3. Runs the full pipeline against the specified repository
4. Uploads the report as a build artifact
5. Deploys the HTML report to GitHub Pages on the `gh-pages` branch

To analyze a specific repository, go to **Actions > AI Code Refactoring Analysis > Run workflow** and provide the repository URL.

## GitHub Pages Report

After a workflow run, the interactive HTML report is published at:

```
https://Theesthan.github.io/GiFrac/
```

The report includes:
- Summary dashboard with key metrics
- Full static analysis issue table
- List of all detected code smells
- Structural suggestions (missing tests, packaging, etc.)
- Per-function refactoring cards with improvements and rationale
- Performance benchmark comparison table

---

## License

MIT License — see LICENSE file for details.
