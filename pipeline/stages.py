"""
stages.py - Concrete PipelineStage adapters.

Design Patterns implemented here:
  - Adapter   : Each class wraps an existing domain service and adapts it to the
                PipelineStage interface, decoupling domain logic from pipeline
                infrastructure.  Domain services (RepoLoader, StaticAnalyzer, …)
                remain independent of the pipeline; stages are the thin glue layer.
  - Template Method (inherited): each class satisfies the PipelineStage contract
                by providing a concrete name property and run() implementation.

Dependency flow (Dependency Inversion Principle):
  main.py  ──→  Pipeline  ──→  PipelineStage (abstract)
                                     ↑ implemented by
                              Concrete stage adapters
                                     ↓ depends on
                              Domain service instances
                              (injected via __init__)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from pipeline.base import PipelineStage
from pipeline.benchmark_system import BenchmarkSystem
from pipeline.complexity_evaluator import ComplexityEvaluator
from pipeline.llm_refactoring_engine import LLMRefactoringEngine
from pipeline.repo_loader import RepoLoader
from pipeline.report_generator import ReportGenerator
from pipeline.static_analyzer import StaticAnalyzer

logger = logging.getLogger(__name__)


class LoadRepoStage(PipelineStage):
    """Stage 1 adapter: clone the target repository."""

    def __init__(self, loader: RepoLoader, repo_url: str, branch: str) -> None:
        self._loader = loader
        self._repo_url = repo_url
        self._branch = branch

    @property
    def name(self) -> str:
        return "meta"

    def run(self, context: Dict[str, Any]) -> Any:
        meta = self._loader.load(self._repo_url, branch=self._branch)
        logger.info("Loaded %s: %d files", meta.name, meta.file_count)
        return meta


class StaticAnalysisStage(PipelineStage):
    """Stage 2 adapter: run pylint / flake8 / bandit."""

    def __init__(self, analyzer: StaticAnalyzer) -> None:
        self._analyzer = analyzer

    @property
    def name(self) -> str:
        return "static_report"

    def run(self, context: Dict[str, Any]) -> Any:
        meta = context["meta"]
        report = self._analyzer.analyze(meta.local_path, meta.name)
        logger.info("Static issues: %d | score: %.1f", len(report.issues), report.score)
        return report


class ComplexityStage(PipelineStage):
    """Stage 3 adapter: measure cyclomatic complexity and detect code smells."""

    def __init__(self, evaluator: ComplexityEvaluator) -> None:
        self._evaluator = evaluator

    @property
    def name(self) -> str:
        return "complexity_report"

    def run(self, context: Dict[str, Any]) -> Any:
        meta = context["meta"]
        report = self._evaluator.evaluate(meta.local_path, meta.name)
        logger.info(
            "Maintainability: %.1f | smells: %d",
            report.maintainability_score,
            len(report.smells),
        )
        return report


class RefactoringStage(PipelineStage):
    """Stage 4 adapter: LLM-powered refactoring of smelly functions."""

    def __init__(self, engine: LLMRefactoringEngine) -> None:
        self._engine = engine

    @property
    def name(self) -> str:
        return "refactoring_report"

    def run(self, context: Dict[str, Any]) -> Any:
        meta = context["meta"]
        complexity_report = context["complexity_report"]
        smelly_fns = [
            {"file": fn.file, "name": fn.name, "line": fn.line, "source_code": None}
            for fc in complexity_report.files
            for fn in fc.functions
            if fn.is_smelly
        ]
        report = self._engine.refactor(meta.local_path, meta.name, smelly_fns)
        logger.info("Refactored: %d functions", len(report.results))
        return report


class BenchmarkStage(PipelineStage):
    """Stage 5 adapter: benchmark original vs refactored functions."""

    def __init__(self, system: BenchmarkSystem) -> None:
        self._system = system

    @property
    def name(self) -> str:
        return "benchmark_report"

    def run(self, context: Dict[str, Any]) -> Any:
        meta = context["meta"]
        refactoring_report = context["refactoring_report"]
        report = self._system.run(refactoring_report.results, meta.name)
        logger.info("Speedup: %.2fx", report.overall_speedup)
        return report


class ReportStage(PipelineStage):
    """Stage 6 adapter: generate HTML + JSON reports."""

    def __init__(self, generator: ReportGenerator, output_dir: str) -> None:
        self._generator = generator
        self._output_dir = Path(output_dir)

    @property
    def name(self) -> str:
        return "report"

    def run(self, context: Dict[str, Any]) -> Any:
        meta = context["meta"]
        static_report = context["static_report"]
        complexity_report = context["complexity_report"]
        refactoring_report = context["refactoring_report"]
        benchmark_report = context["benchmark_report"]

        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._generator.generate(
            meta=meta,
            static_report=static_report,
            complexity_report=complexity_report,
            refactoring_report=refactoring_report,
            benchmark_report=benchmark_report,
        )

        (self._output_dir / "report.json").write_text(
            json.dumps(
                {
                    "repo": meta.__dict__,
                    "static": static_report.as_dict(),
                    "complexity": complexity_report.as_dict(),
                    "refactoring": refactoring_report.as_dict(),
                    "benchmarks": benchmark_report.as_dict(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        logger.info("Reports saved to %s", self._output_dir)
        return str(self._output_dir)
