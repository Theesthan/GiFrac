"""
llm_refactoring_engine.py - Pipeline Stage 4
Uses an LLM strategy to generate refactored code suggestions.

Design Patterns applied here:
  - Strategy (consumer): LLMRefactoringEngine depends on the LLMStrategy *protocol*,
                         not any concrete provider class.  The active strategy is
                         injected via the constructor (Dependency Inversion Principle).
  - Dependency Inversion: high-level policy (engine) no longer imports or instantiates
                          low-level details (openai, requests, env vars).  Those live
                          in strategies.py and are wired up in main.py.
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from pipeline.strategies import LLMStrategy, LLMStrategyFactory

logger = logging.getLogger(__name__)


@dataclass
class RefactoringResult:
    original_file: str
    original_function: str
    original_code: str
    refactored_code: str
    improvements: List[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class RefactoringReport:
    repo_name: str
    results: List[RefactoringResult] = field(default_factory=list)
    structural_suggestions: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "repo_name": self.repo_name,
            "structural_suggestions": self.structural_suggestions,
            "refactored_functions": [
                {
                    "file": r.original_file,
                    "function": r.original_function,
                    "improvements": r.improvements,
                    "rationale": r.rationale,
                }
                for r in self.results
            ],
        }


class LLMRefactoringEngine:
    """
    Stage 4 — AI-powered code refactoring.

    Optimization strategies applied by the injected LLMStrategy:
        1. Extract Method   — decompose long functions
        2. Guard Clauses    — replace nested if-else with early returns
        3. Named Constants  — replace magic numbers
        4. Comprehensions   — replace imperative loops
        5. Type Hints       — add missing annotations
        6. Dead Code Removal
        7. Dependency Injection
        8. Rename for Clarity

    Dependency Inversion: this class depends only on LLMStrategy (an abstract
    Protocol).  Concrete providers (OpenAI, Ollama, rule-based) are injected
    from the outside, making this class fully testable without any network calls.
    """

    def __init__(self, strategy: Optional[LLMStrategy] = None) -> None:
        self._strategy: LLMStrategy = strategy or LLMStrategyFactory.create()

    def refactor(
        self, local_path: str, repo_name: str, smelly_functions: List[Dict]
    ) -> RefactoringReport:
        report = RefactoringReport(repo_name=repo_name)
        for fn_info in smelly_functions[:10]:
            try:
                result = self._refactor_function(fn_info, local_path)
                if result:
                    report.results.append(result)
            except Exception as exc:
                logger.error("Failed to refactor %s: %s", fn_info.get("name"), exc)
        report.structural_suggestions = self._suggest_structure(local_path)
        return report

    def _refactor_function(
        self, fn_info: Dict, local_path: str
    ) -> Optional[RefactoringResult]:
        source = fn_info.get("source_code") or self._extract_source(
            fn_info["file"], fn_info["line"], local_path
        )
        if not source:
            return None
        response = self._strategy.refactor(source)
        return RefactoringResult(
            original_file=fn_info["file"],
            original_function=fn_info["name"],
            original_code=source,
            refactored_code=response.get("refactored_code", source),
            improvements=response.get("improvements", []),
            rationale=response.get("rationale", ""),
        )

    def _extract_source(
        self, file: str, line: int, local_path: str
    ) -> Optional[str]:
        try:
            full_path = Path(local_path) / file
            source = full_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.lineno == line:
                        return ast.get_source_segment(source, node)
        except Exception:
            pass
        return None

    def _suggest_structure(self, local_path: str) -> List[str]:
        suggestions = []
        path = Path(local_path)
        py_files = list(path.rglob("*.py"))
        if not any("test" in f.name.lower() for f in py_files):
            suggestions.append("No tests found — add a tests/ directory with pytest")
        if not (path / "requirements.txt").exists() and not (path / "pyproject.toml").exists():
            suggestions.append("Missing requirements.txt or pyproject.toml")
        if not list(path.glob("README*")):
            suggestions.append("Add a README.md documenting setup and usage")
        return suggestions
