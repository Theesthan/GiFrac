"""
main.py - AI Code Refactoring and Optimization System
Pipeline orchestrator: runs all 5 stages in sequence.
"""

import sys
import json
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))

from repo_loader import RepoLoader
from static_analyzer import StaticAnalyzer
from complexity_evaluator import ComplexityEvaluator
from llm_refactoring_engine import LLMRefactoringEngine
from benchmark_system import BenchmarkSystem
from report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO,
                                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")


def main():
      parser = argparse.ArgumentParser(description="AI Code Refactoring System")
      parser.add_argument("repo_url", help="GitHub repository URL")
      parser.add_argument("--branch", default="main")
      parser.add_argument("--workspace", default="./workspace")
      parser.add_argument("--output", default="./docs")
      parser.add_argument("--iterations", type=int, default=1000)
      args = parser.parse_args()

    logger.info("Target: %s", args.repo_url)

    # Stage 1
    meta = RepoLoader(workspace=args.workspace).load(args.repo_url, branch=args.branch)
    logger.info("Loaded %s: %d files", meta.name, meta.file_count)

    # Stage 2
    static_report = StaticAnalyzer().analyze(meta.local_path, meta.name)
    logger.info("Static issues: %d | score: %.1f", len(static_report.issues), static_report.score)

    # Stage 3
    complexity_report = ComplexityEvaluator().evaluate(meta.local_path, meta.name)
    logger.info("Maintainability: %.1f | smells: %d",
                                complexity_report.maintainability_score, len(complexity_report.smells))

    # Stage 4
    smelly_fns = [
              {"file": fn.file, "name": fn.name, "line": fn.line, "source_code": None}
              for fc in complexity_report.files for fn in fc.functions if fn.is_smelly
    ]
    refactoring_report = LLMRefactoringEngine().refactor(meta.local_path, meta.name, smelly_fns)
    logger.info("Refactored: %d functions", len(refactoring_report.results))

    # Stage 5
    benchmark_report = BenchmarkSystem(iterations=args.iterations).run(
              refactoring_report.results, meta.name)
    logger.info("Speedup: %.2fx", benchmark_report.overall_speedup)

    # Stage 6 - Report
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    ReportGenerator(str(output_dir)).generate(
              meta=meta, static_report=static_report,
              complexity_report=complexity_report,
              refactoring_report=refactoring_report,
              benchmark_report=benchmark_report,
    )
    (output_dir / "report.json").write_text(json.dumps({
              "repo": meta.__dict__,
              "static": static_report.as_dict(),
              "complexity": complexity_report.as_dict(),
              "refactoring": refactoring_report.as_dict(),
              "benchmarks": benchmark_report.as_dict(),
    }, indent=2))
    logger.info("Reports saved to %s", output_dir)


if __name__ == "__main__":
      main()
  
