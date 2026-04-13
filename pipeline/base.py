"""
base.py - Pipeline infrastructure.

Design Patterns implemented here:
  - Template Method  : PipelineStage defines the fixed contract (name + run) that
                       every concrete stage must satisfy. The base class never
                       dictates *how* to run; it only dictates *that* run() exists.
  - Pipeline (arch.) : Pipeline sequences stages and passes a shared context dict
                       so each stage can read prior results and publish its own.
  - Observer         : An optional on_stage_complete callback lets callers react to
                       progress events without coupling the pipeline to any specific
                       logging or monitoring system.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """
    Template Method Pattern — abstract skeleton for a single pipeline step.

    Subclasses implement:
      - name : unique key under which the result is stored in the context dict
      - run  : domain logic that reads prior results from context and returns its own
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique result key written into the shared context after this stage runs."""

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Any:
        """Execute this stage and return the result to be stored in context[self.name]."""


class Pipeline:
    """
    Pipeline Architectural Pattern — orchestrates an ordered list of PipelineStages.

    Context dict flows through every stage so later stages can consume results
    produced by earlier ones.  The observer callback (if provided) fires after
    every stage without the pipeline knowing anything about the observer.

    Observer Pattern: on_stage_complete(stage_name: str, result: Any) -> None
    """

    def __init__(
        self,
        stages: List[PipelineStage],
        on_stage_complete: Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        self._stages = stages
        self._on_stage_complete = on_stage_complete

    def execute(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """Run all stages in order, returning the fully populated context dict."""
        context: Dict[str, Any] = dict(initial_context)
        for stage in self._stages:
            logger.debug("Pipeline: starting stage '%s'", stage.name)
            result = stage.run(context)
            context[stage.name] = result
            if self._on_stage_complete:
                self._on_stage_complete(stage.name, result)
        return context
