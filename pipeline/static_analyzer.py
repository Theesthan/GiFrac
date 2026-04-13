"""
static_analyzer.py - Pipeline Stage 2
Runs static analysis tools (pylint, flake8, bandit) on the cloned repository.
"""

import json
import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    file: str
    line: int
    column: int
    code: str
    message: str
    severity: str
    tool: str


@dataclass
class StaticAnalysisReport:
    repo_name: str
    issues: List[Issue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    score: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "repo_name": self.repo_name,
            "score": self.score,
            "summary": self.summary,
            "issues": [i.__dict__ for i in self.issues],
        }


class StaticAnalyzer:
    """Stage 2: Run pylint, flake8, and bandit; aggregate findings."""

    def analyze(self, local_path: str, repo_name: str) -> StaticAnalysisReport:
        report = StaticAnalysisReport(repo_name=repo_name)
        path = Path(local_path)

        for tool, runner in [("pylint", self._run_pylint),
                             ("flake8", self._run_flake8),
                             ("bandit", self._run_bandit)]:
            try:
                issues = runner(path)
                report.issues.extend(issues)
                logger.info(f"{tool}: {len(issues)} issues")
            except FileNotFoundError:
                logger.warning(f"{tool} not installed, skipping")

        report.summary = {"error": 0, "warning": 0, "info": 0}
        for i in report.issues:
            report.summary[i.severity] = report.summary.get(i.severity, 0) + 1
        report.score = self._pylint_score(path)
        return report

    def _run_pylint(self, path: Path) -> List[Issue]:
        r = subprocess.run(["python", "-m", "pylint", "--output-format=json", "--recursive=y", str(path)],
                           capture_output=True, text=True)
        try:
            raw = json.loads(r.stdout or "[]")
        except json.JSONDecodeError:
            return []
        return [Issue(file=i["path"], line=i["line"], column=i["column"],
                      code=i["message-id"], message=i["message"],
                      severity="error" if i["type"] in ("error", "fatal") else "warning",
                      tool="pylint") for i in raw]

    def _run_flake8(self, path: Path) -> List[Issue]:
        r = subprocess.run(
            ["python", "-m", "flake8", "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
             "--max-line-length=120", str(path)],
            capture_output=True, text=True)
        issues = []
        for line in r.stdout.splitlines():
            parts = line.split(":", 4)
            if len(parts) == 5:
                f, row, col, code, msg = parts
                issues.append(Issue(file=f, line=int(row), column=int(col),
                                    code=code, message=msg.strip(),
                                    severity="error" if code.startswith("E") else "warning",
                                    tool="flake8"))
        return issues

    def _run_bandit(self, path: Path) -> List[Issue]:
        r = subprocess.run(["python", "-m", "bandit", "-r", str(path), "-f", "json", "-q"],
                           capture_output=True, text=True)
        try:
            raw = json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            return []
        return [Issue(file=i["filename"], line=i["line_number"], column=0,
                      code=i["test_id"], message=i["issue_text"],
                      severity="error" if i["issue_severity"] == "HIGH" else "warning",
                      tool="bandit") for i in raw.get("results", [])]

    def _pylint_score(self, path: Path) -> float:
        try:
            r = subprocess.run(["python", "-m", "pylint", "--recursive=y", str(path)],
                               capture_output=True, text=True)
            for line in r.stdout.splitlines():
                if "Your code has been rated at" in line:
                    try:
                        return float(line.split("at ")[1].split("/")[0])
                    except Exception:
                        pass
        except FileNotFoundError:
            pass
        return 0.0
