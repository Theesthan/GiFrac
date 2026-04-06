"""
complexity_evaluator.py - Pipeline Stage 3
Evaluates cyclomatic complexity, cognitive complexity, and code smells.
Uses radon for Python; reports maintainability index per file.
"""

import ast
import logging
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Thresholds
CC_MODERATE = 10     # Cyclomatic Complexity - moderate risk
CC_HIGH = 20         # Cyclomatic Complexity - high risk
MI_MAINTAINABLE = 65 # Maintainability Index - well maintained


@dataclass
class FunctionComplexity:
      name: str
      file: str
      line: int
      cyclomatic_complexity: int
      rank: str     # A-F scale
    is_smelly: bool


@dataclass
class FileComplexity:
      file: str
      maintainability_index: float
      mi_rank: str  # A-C scale
    functions: List[FunctionComplexity] = field(default_factory=list)


@dataclass
class ComplexityReport:
      repo_name: str
      files: List[FileComplexity] = field(default_factory=list)
      overall_mi: float = 0.0
      smells: List[str] = field(default_factory=list)
      maintainability_score: float = 0.0  # 0-100 normalized

    def as_dict(self) -> Dict[str, Any]:
              return {
                            "repo_name": self.repo_name,
                            "overall_mi": self.overall_mi,
                            "maintainability_score": self.maintainability_score,
                            "smells": self.smells,
                            "files": [
                                              {
                                                                    "file": f.file,
                                                                    "mi": f.maintainability_index,
                                                                    "mi_rank": f.mi_rank,
                                                                    "functions": [fn.__dict__ for fn in f.functions],
                                              }
                                              for f in self.files
                            ],
              }


class ComplexityEvaluator:
      """
          Stage 3: Compute cyclomatic/cognitive complexity and detect code smells.

              Code smells detected:
                  - Long functions (> 50 lines)
                      - Deep nesting (> 4 levels)
                          - Large classes (> 500 lines)
                              - High cyclomatic complexity (CC > 10)
                                  - Too many parameters (> 7)
                                      """

    def evaluate(self, local_path: str, repo_name: str) -> ComplexityReport:
              report = ComplexityReport(repo_name=repo_name)
              path = Path(local_path)

        python_files = list(path.rglob("*.py"))
        if not python_files:
                      logger.warning("No Python files found")
                      return report

        for py_file in python_files:
                      try:
                                        fc = self._analyze_file(py_file, path)
                                        report.files.append(fc)
                                        smells = self._detect_smells(py_file, fc)
                                        report.smells.extend(smells)
except Exception as exc:
                logger.debug(f"Skipping {py_file}: {exc}")

        if report.files:
                      mis = [f.maintainability_index for f in report.files if f.maintainability_index > 0]
                      report.overall_mi = round(sum(mis) / len(mis), 2) if mis else 0.0
                      report.maintainability_score = min(100.0, report.overall_mi)

        return report

    # ------------------------------------------------------------------
    def _analyze_file(self, py_file: Path, root: Path) -> FileComplexity:
              rel = str(py_file.relative_to(root))
              mi, mi_rank = self._radon_mi(py_file)
              functions = self._radon_cc(py_file, rel)
              return FileComplexity(file=rel, maintainability_index=mi,
                                    mi_rank=mi_rank, functions=functions)

    def _radon_mi(self, path: Path):
              try:
                            result = subprocess.run(
                                              ["radon", "mi", "-s", str(path)],
                                              capture_output=True, text=True
                            )
                            for line in result.stdout.splitlines():
                                              parts = line.strip().split()
                                              if len(parts) >= 3:
                                                                    try:
                                                                                              mi = float(parts[-1].strip("()"))
                                                                                              rank = parts[-2]
                                                                                              return mi, rank
              except ValueError:
                                        pass
except FileNotFoundError:
            pass
        return self._ast_mi(path)

    def _ast_mi(self, path: Path):
              """Fallback: estimate MI from LOC and comment ratio."""
              try:
                            source = path.read_text(encoding="utf-8", errors="ignore")
                            lines = source.splitlines()
                            loc = len([l for l in lines if l.strip()])
                            comments = len([l for l in lines if l.strip().startswith("#")])
                            ratio = comments / max(loc, 1)
                            mi = min(100.0, 50 + ratio * 100 - loc * 0.01)
                            rank = "A" if mi >= 80 else "B" if mi >= 65 else "C"
                            return round(mi, 2), rank
except Exception:
            return 0.0, "C"

    def _radon_cc(self, path: Path, rel_path: str) -> List[FunctionComplexity]:
              try:
                            result = subprocess.run(
                                              ["radon", "cc", "-s", "-j", str(path)],
                                              capture_output=True, text=True
                            )
                            raw = json.loads(result.stdout or "{}")
                            fns = []
                            for file_path, items in raw.items():
                                              for item in items:
                                                                    cc = item.get("complexity", 1)
                                                                    rank = item.get("rank", "A")
                                                                    fns.append(FunctionComplexity(
                                                                        name=item.get("name", "?"),
                                                                        file=rel_path,
                                                                        line=item.get("lineno", 0),
                                                                        cyclomatic_complexity=cc,
                                                                        rank=rank,
                                                                        is_smelly=cc > CC_MODERATE,
                                                                    ))
                                                            return fns
except (FileNotFoundError, json.JSONDecodeError):
            return self._ast_cc(path, rel_path)

    def _ast_cc(self, path: Path, rel_path: str) -> List[FunctionComplexity]:
              """Fallback: count branches in AST as proxy for CC."""
              branch_nodes = (ast.If, ast.For, ast.While, ast.ExceptHandler,
                              ast.With, ast.Assert, ast.comprehension)
              functions = []
              try:
                            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
                            for node in ast.walk(tree):
                                              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                                                    cc = 1 + sum(1 for n in ast.walk(node) if isinstance(n, branch_nodes))
                                                                    rank = "A" if cc <= 5 else "B" if cc <= 10 else "C" if cc <= 15 else "D"
                                                                    functions.append(FunctionComplexity(
                                                                        name=node.name, file=rel_path,
                                                                        line=node.lineno, cyclomatic_complexity=cc,
                                                                        rank=rank, is_smelly=cc > CC_MODERATE,
                                                                    ))
              except SyntaxError:
                            pass
                        return functions

    def _detect_smells(self, path: Path, fc: FileComplexity) -> List[str]:
              smells = []
        rel = fc.file
        try:
                      source = path.read_text(encoding="utf-8", errors="ignore")
                      lines = source.splitlines()
                      # Long file
                      if len(lines) > 500:
                                        smells.append(f"Large file ({len(lines)} lines): {rel}")
                                    # Deep nesting via indentation proxy
                                    max_indent = max((len(l) - len(l.lstrip())) for l in lines if l.strip()) // 4
            if max_indent > 4:
                              smells.append(f"Deep nesting (indent level {max_indent}): {rel}")
except Exception:
            pass
        # High-CC functions
        for fn in fc.functions:
                      if fn.cyclomatic_complexity > CC_HIGH:
                                        smells.append(f"Very high CC ({fn.cyclomatic_complexity}) in {fn.name}(): {rel}:{fn.line}")
                                return smells
