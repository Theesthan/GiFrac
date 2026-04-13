"""
main.py - AI Code Refactoring and Optimization System
Entry point that wires together the pipeline infrastructure and domain services.

Design Patterns / Principles wired here:
  - Pipeline (arch.)   : Pipeline.execute() sequences all stages.
  - Observer           : on_stage_complete logs progress without coupling stages to logging.
  - Factory            : LLMStrategyFactory.create() picks the right LLM provider.
  - Dependency Inversion: domain services are constructed here and injected into stages;
                          stages never instantiate their own dependencies.
"""

import sys
import logging
import argparse
from pathlib import Path

from pipeline.base import Pipeline
from pipeline.benchmark_system import BenchmarkSystem
from pipeline.complexity_evaluator import ComplexityEvaluator
from pipeline.llm_refactoring_engine import LLMRefactoringEngine
from pipeline.repo_loader import RepoLoader
from pipeline.report_generator import ReportGenerator
from pipeline.stages import (
    BenchmarkStage,
    ComplexityStage,
    LoadRepoStage,
    RefactoringStage,
    ReportStage,
    StaticAnalysisStage,
)
from pipeline.static_analyzer import StaticAnalyzer
from pipeline.strategies import LLMStrategyFactory

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def _on_stage_complete(stage_name: str, result: object) -> None:
    """Observer callback: fired by Pipeline after each stage completes."""
    logger.info("Stage '%s' complete", stage_name)


def build_pipeline(args: argparse.Namespace) -> Pipeline:
    """
    Factory / wiring function — constructs every domain service and stage adapter,
    then assembles them into a Pipeline.

    All dependencies flow inward (DIP): services are created here and injected
    into stages via constructor arguments.
    """
    output_dir = Path(args.output)
    strategy = LLMStrategyFactory.create()

    stages = [
        LoadRepoStage(
            loader=RepoLoader(workspace=args.workspace),
            repo_url=args.repo_url,
            branch=args.branch,
        ),
        StaticAnalysisStage(analyzer=StaticAnalyzer()),
        ComplexityStage(evaluator=ComplexityEvaluator()),
        RefactoringStage(engine=LLMRefactoringEngine(strategy=strategy)),
        BenchmarkStage(system=BenchmarkSystem(iterations=args.iterations)),
        ReportStage(
            generator=ReportGenerator(str(output_dir)),
            output_dir=str(output_dir),
        ),
    ]

    return Pipeline(stages=stages, on_stage_complete=_on_stage_complete)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Code Refactoring System")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--workspace", default="./workspace")
    parser.add_argument("--output", default="./docs")
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()

    logger.info("Target: %s", args.repo_url)

    pipeline = build_pipeline(args)
    pipeline.execute(initial_context={})


if __name__ == "__main__":
    main()
