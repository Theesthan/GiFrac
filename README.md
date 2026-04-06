# AI Code Refactoring and Optimization System

An AI-powered pipeline that automatically analyzes any GitHub repository, detects code quality issues, generates LLM-powered refactoring suggestions, benchmarks performance improvements, and publishes results via GitHub Pages.

## Features

- Clone any public GitHub repository
- - Static analysis with pylint, flake8, and bandit
  - - Cyclomatic complexity evaluation and code smell detection using radon
    - - LLM-based code refactoring (OpenAI GPT-4o, Ollama, or rule-based fallback)
      - - Performance benchmarking of original vs. refactored functions
        - - Automated HTML report published to GitHub Pages
          - - Scheduled weekly analysis via GitHub Actions
           
            - ## Pipeline Architecture
           
            - ```
              repo_loader -> static_analyzer -> complexity_evaluator -> llm_refactoring_engine -> benchmark_system -> report_generator
              ```

              | Stage | Module | Purpose |
              |-------|--------|---------|
              | 1 | `repo_loader.py` | Clone repository and inventory files |
              | 2 | `static_analyzer.py` | Run pylint/flake8/bandit static analysis |
              | 3 | `complexity_evaluator.py` | Measure cyclomatic complexity and detect smells |
              | 4 | `llm_refactoring_engine.py` | Generate optimized code with LLM |
              | 5 | `benchmark_system.py` | Benchmark original vs refactored functions |
              | 6 | `report_generator.py` | Generate HTML report for GitHub Pages |

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

              ```
              python main.py <repo_url> [--branch main] [--workspace ./workspace] [--output ./docs] [--iterations 1000]
              ```

              ## LLM Configuration

              Set the `LLM_PROVIDER` environment variable to select the refactoring engine:

              | Provider | Setup |
              |----------|-------|
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

              ## Outputs

              ### Refactored Code Suggestions
              For each function with cyclomatic complexity > 10, the engine provides:
              - The original function source
              - - A refactored version with improvements applied
                - - A list of specific improvements made
                  - - A rationale explaining the changes
                   
                    - ### Performance Benchmarks
                    - For each refactored function:
                    - - Original execution time (ms)
                      - - Refactored execution time (ms)
                        - - Speedup ratio
                          - - Memory allocation delta (KB)
                           
                            - ### Maintainability Score
                            - A 0-100 score derived from radon's Maintainability Index, indicating overall code health.
                           
                            - ## Optimization Strategies
                           
                            - The LLM refactoring engine applies the following strategies:
                           
                            - **1. Extract Method**
                            - Long functions (> 30 lines) are split into smaller, single-purpose helper methods. This improves readability, testability, and reduces cognitive complexity.
                           
                            - **2. Guard Clauses**
                            - Deeply nested if-else blocks are inverted using early return statements. This flattens the code structure and reduces indentation levels.
                           
                            - **3. Named Constants**
                            - Magic numbers and string literals embedded directly in code are replaced with descriptive named constants at the module level.
                           
                            - **4. List and Dict Comprehensions**
                            - Imperative loops that build collections are converted to declarative comprehension syntax, which is faster and more Pythonic.
                           
                            - **5. Type Annotations**
                            - Missing Python type hints are added to function signatures, improving IDE support, enabling static type checking, and serving as documentation.
                           
                            - **6. Dead Code Removal**
                            - Unreachable branches (code after unconditional return, unreachable except blocks) are identified and flagged for removal.
                           
                            - **7. Dependency Injection**
                            - Hard-coded dependencies (e.g., direct instantiation inside methods) are converted to constructor parameters, enabling unit testing and loose coupling.
                           
                            - **8. Rename for Clarity**
                            - Vague identifiers (single-letter variables, abbreviations) are replaced with descriptive names that communicate intent.
                           
                            - ## GitHub Actions Workflow
                           
                            - The workflow at `.github/workflows/analyze.yml`:
                           
                            - 1. Triggers on `workflow_dispatch` (manual run) or weekly on Monday at 06:00 UTC
                              2. 2. Installs all dependencies
                                 3. 3. Runs the full pipeline against the specified repository
                                    4. 4. Uploads the report as a build artifact
                                       5. 5. Deploys the HTML report to GitHub Pages on the `gh-pages` branch
                                         
                                          6. To analyze a specific repository, go to **Actions > AI Code Refactoring Analysis > Run workflow** and provide the repository URL.
                                         
                                          7. ## GitHub Pages Report
                                         
                                          8. After a workflow run, the interactive HTML report is published at:
                                         
                                          9. ```
                                             https://Theesthan.github.io/GiFrac/
                                             ```

                                             The report includes:
                                             - Summary dashboard with key metrics
                                             - - Full static analysis issue table
                                               - - List of all detected code smells
                                                 - - Structural suggestions (missing tests, packaging, etc.)
                                                   - - Per-function refactoring cards with improvements and rationale
                                                     - - Performance benchmark comparison table
                                                      
                                                       - ## Project Structure
                                                      
                                                       - ```
                                                         GiFrac/
                                                         - pipeline/
                                                           - repo_loader.py           # Stage 1: Clone repository
                                                           - static_analyzer.py       # Stage 2: Pylint/Flake8/Bandit
                                                           - complexity_evaluator.py  # Stage 3: Radon complexity + smell detection
                                                           - llm_refactoring_engine.py # Stage 4: LLM-powered refactoring
                                                           - benchmark_system.py      # Stage 5: Performance benchmarking
                                                           - report_generator.py      # Stage 6: HTML report generation
                                                         - .github/workflows/
                                                           - analyze.yml              # GitHub Actions CI/CD pipeline
                                                         - main.py                    # Orchestrator entry point
                                                         - requirements.txt           # Python dependencies
                                                         - README.md                  # This file
                                                         - docs/                      # Generated reports (GitHub Pages)
                                                         ```

                                                         ## License

                                                         MIT License - see LICENSE file for details.
                                                         
