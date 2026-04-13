"""
benchmark_system.py - Pipeline Stage 5
Benchmarks original vs refactored functions using timeit and tracemalloc.
"""

import timeit
import logging
import tracemalloc
import statistics
import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any

logger = logging.getLogger(__name__)

ITERATIONS = 1000
WARMUP     = 10


@dataclass
class BenchmarkResult:
    function_name: str
    file: str
    original_time_ms: float
    refactored_time_ms: float
    original_memory_kb: float
    refactored_memory_kb: float
    speedup_ratio: float = 0.0
    memory_delta_kb: float = 0.0

    def __post_init__(self):
        denom = max(self.refactored_time_ms, 0.001)
        self.speedup_ratio = round(self.original_time_ms / denom, 3)
        self.memory_delta_kb = round(self.original_memory_kb - self.refactored_memory_kb, 2)


@dataclass
class BenchmarkReport:
    repo_name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    overall_speedup: float = 0.0
    total_memory_saved_kb: float = 0.0

    def finalize(self):
        ratios = [r.speedup_ratio for r in self.results if r.speedup_ratio > 0]
        self.overall_speedup = round(statistics.mean(ratios), 3) if ratios else 1.0
        self.total_memory_saved_kb = round(sum(r.memory_delta_kb for r in self.results), 2)

    def as_dict(self) -> Dict[str, Any]:
        return {
                            "repo_name": self.repo_name,
                            "overall_speedup": self.overall_speedup,
                            "total_memory_saved_kb": self.total_memory_saved_kb,
                            "benchmarks": [
                                              {
                                                                    "function": r.function_name,
                                                                    "file": r.file,
                                                                    "original_ms": r.original_time_ms,
                                                                    "refactored_ms": r.refactored_time_ms,
                                                                    "speedup": r.speedup_ratio,
                                                                    "memory_delta_kb": r.memory_delta_kb,
                                              }
                                              for r in self.results
                            ],
              }


class BenchmarkSystem:
    """Stage 5: Performance benchmarking of original vs refactored code."""

    def __init__(self, iterations: int = ITERATIONS):
        self.iterations = iterations

    def run(self, refactoring_results: list, repo_name: str) -> BenchmarkReport:
        report = BenchmarkReport(repo_name=repo_name)
        for r in refactoring_results:
            try:
                bench = self._benchmark_pair(
                    r.original_function, r.original_file,
                    r.original_code, r.refactored_code)
                if bench:
                    report.results.append(bench)
            except Exception as exc:
                logger.warning("Benchmark failed %s: %s", r.original_function, exc)
        report.finalize()
        return report

    def _benchmark_pair(self, fn_name, file, orig_src, refac_src):
        orig_fn  = self._compile(orig_src, fn_name)
        refac_fn = self._compile(refac_src, fn_name)
        if not orig_fn or not refac_fn:
            return None
        args = self._default_args(orig_src, fn_name)
        return BenchmarkResult(
            function_name=fn_name, file=file,
            original_time_ms=self._time(orig_fn, args),
            refactored_time_ms=self._time(refac_fn, args),
            original_memory_kb=self._memory(orig_fn, args),
            refactored_memory_kb=self._memory(refac_fn, args),
        )

    def _compile(self, src: str, fn_name: str) -> Optional[Callable]:
        try:
            ns: Dict = {}
            exec(compile(src, "<string>", "exec"), ns)
            return ns.get(fn_name)
        except Exception:
            return None

    def _default_args(self, src: str, fn_name: str) -> tuple:
        type_defaults = {"str": "", "int": 0, "float": 0.0, "bool": False, "list": [], "dict": {}}
        try:
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
                    result = []
                    for arg in node.args.args[1:]:
                        hint = arg.annotation.id.lower() if (arg.annotation and isinstance(arg.annotation, ast.Name)) else ""
                        result.append(type_defaults.get(hint))
                    return tuple(result)
        except Exception:
            pass
        return ()

    def _time(self, fn: Callable, args: tuple) -> float:
        try:
            for _ in range(WARMUP):
                self._safe_call(fn, args)
            elapsed = timeit.timeit(lambda: self._safe_call(fn, args), number=self.iterations)
            return round((elapsed / self.iterations) * 1000, 4)
        except Exception:
            return 0.0

    def _memory(self, fn: Callable, args: tuple) -> float:
        try:
            tracemalloc.start()
            self._safe_call(fn, args)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return round(peak / 1024, 4)
        except Exception:
            return 0.0

    @staticmethod
    def _safe_call(fn: Callable, args: tuple) -> Any:
        try:
            return fn(*args)
        except Exception:
            return None
