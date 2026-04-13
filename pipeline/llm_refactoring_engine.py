"""
llm_refactoring_engine.py - Pipeline Stage 4
Uses an LLM (OpenAI GPT-4 or local Ollama) to generate refactored code.
"""

import os
import logging
import textwrap
import re
import ast
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
OPENAI_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "codellama")
OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://localhost:11434")


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
    """Stage 4 - AI-powered code refactoring.

        Optimization strategies:
            1. Extract Method  - decompose long functions
            2. Guard Clauses   - replace nested if-else with early returns
            3. Named Constants - replace magic numbers
            4. Comprehensions  - replace imperative loops
            5. Type Hints      - add missing annotations
            6. Dead Code Removal
            7. Dependency Injection
            8. Rename for Clarity
    """

    def refactor(self, local_path: str, repo_name: str, smelly_functions: List[Dict]) -> RefactoringReport:
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

    def _refactor_function(self, fn_info: Dict, local_path: str) -> Optional[RefactoringResult]:
        source = fn_info.get("source_code") or self._extract_source(
            fn_info["file"], fn_info["line"], local_path)
        if not source:
            return None
        response_json = self._call_llm(source)
        return RefactoringResult(
            original_file=fn_info["file"],
            original_function=fn_info["name"],
            original_code=source,
            refactored_code=response_json.get("refactored_code", source),
            improvements=response_json.get("improvements", []),
            rationale=response_json.get("rationale", ""),
        )

    def _call_llm(self, source_code: str) -> Dict:
        if LLM_PROVIDER == "openai":
            return self._call_openai(source_code)
        if LLM_PROVIDER == "ollama":
            return self._call_ollama(source_code)
        return self._rule_based_refactor(source_code)

    def _call_openai(self, source_code: str) -> Dict:
        import json
        try:
            import openai
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
            msg = (
                "You are an expert Python engineer. Refactor the function below. "
                "Return JSON with keys refactored_code, improvements (list), rationale (str).\n\n"
                f"```python\n{source_code}\n```"
            )
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": msg}],
                temperature=0.2,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as exc:
            logger.error("OpenAI error: %s", exc)
            return self._rule_based_refactor(source_code)

    def _call_ollama(self, source_code: str) -> Dict:
        import json, requests
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": (
                    "Refactor the Python function below. "
                    "Return JSON with refactored_code, improvements, rationale.\n\n"
                    f"```python\n{source_code}\n```"
                ),
                "stream": False,
                "format": "json",
            }
            resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
            resp.raise_for_status()
            return json.loads(resp.json().get("response", "{}"))
        except Exception as exc:
            logger.error("Ollama error: %s", exc)
            return self._rule_based_refactor(source_code)

    def _rule_based_refactor(self, source_code: str) -> Dict:
        lines = source_code.splitlines()
        improvements = []
        if "def " in source_code and "->" not in source_code:
            improvements.append("Add return type annotation")
        if re.search(r"\b\d{2,}\b", source_code):
            improvements.append("Replace magic numbers with named constants")
        if len(lines) > 30:
            improvements.append("Extract helper methods (function > 30 lines)")
        if not improvements:
            improvements.append("No critical smells detected")
        return {
            "refactored_code": source_code,
            "improvements": improvements,
            "rationale": "Rule-based stub. Set LLM_PROVIDER=openai or ollama for AI refactoring.",
        }

    def _extract_source(self, file: str, line: int, local_path: str) -> Optional[str]:
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
            suggestions.append("No tests found - add a tests/ directory with pytest")
        if not (path / "requirements.txt").exists() and not (path / "pyproject.toml").exists():
            suggestions.append("Missing requirements.txt or pyproject.toml")
        if not list(path.glob("README*")):
            suggestions.append("Add a README.md documenting setup and usage")
        return suggestions
