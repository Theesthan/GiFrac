"""
strategies.py - LLM provider abstraction layer.

Design Patterns implemented here:
  - Strategy  : LLMStrategy is a Protocol (structural interface). Each concrete class
                encapsulates one provider's behaviour.  The engine that uses it never
                knows which provider is active.
  - Factory   : LLMStrategyFactory centralises construction, reads env-var config once,
                and returns the correct strategy — callers never import concrete classes.
  - Open/Closed (via registry): new providers can be registered at runtime with
                LLMStrategyFactory.register() without modifying existing code.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strategy interface
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMStrategy(Protocol):
    """
    Strategy Pattern — the interface every LLM provider must satisfy.

    Keeping it to a single method (refactor) respects the Interface Segregation
    Principle: callers only depend on what they actually use.
    """

    def refactor(self, source_code: str) -> Dict:
        """
        Analyse source_code and return a dict with keys:
          - refactored_code : str
          - improvements    : list[str]
          - rationale       : str
        """
        ...


# ---------------------------------------------------------------------------
# Concrete strategies
# ---------------------------------------------------------------------------

class RuleBasedStrategy:
    """
    Concrete Strategy: deterministic rule-based analysis.
    No network calls, no API key — always available as a safe fallback.
    """

    def refactor(self, source_code: str) -> Dict:
        lines = source_code.splitlines()
        improvements: list = []

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
            "rationale": (
                "Rule-based stub. Set LLM_PROVIDER=openai or ollama for AI refactoring."
            ),
        }


class OpenAIStrategy:
    """
    Concrete Strategy: OpenAI GPT-4 provider.
    Falls back to RuleBasedStrategy on any API error.
    """

    def __init__(self, api_key: str = "", model: str = "") -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")
        self._fallback = RuleBasedStrategy()

    def refactor(self, source_code: str) -> Dict:
        try:
            import openai

            client = openai.OpenAI(api_key=self._api_key)
            prompt = (
                "You are an expert Python engineer. Refactor the function below. "
                "Return JSON with keys refactored_code, improvements (list), rationale (str).\n\n"
                f"```python\n{source_code}\n```"
            )
            response = client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as exc:
            logger.error("OpenAI error: %s", exc)
            return self._fallback.refactor(source_code)


class OllamaStrategy:
    """
    Concrete Strategy: local Ollama provider.
    Falls back to RuleBasedStrategy on any connection error.
    """

    def __init__(self, host: str = "", model: str = "") -> None:
        self._host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._model = model or os.environ.get("OLLAMA_MODEL", "codellama")
        self._fallback = RuleBasedStrategy()

    def refactor(self, source_code: str) -> Dict:
        try:
            import requests

            payload = {
                "model": self._model,
                "prompt": (
                    "Refactor the Python function below. "
                    "Return JSON with refactored_code, improvements, rationale.\n\n"
                    f"```python\n{source_code}\n```"
                ),
                "stream": False,
                "format": "json",
            }
            resp = requests.post(
                f"{self._host}/api/generate", json=payload, timeout=120
            )
            resp.raise_for_status()
            return json.loads(resp.json().get("response", "{}"))
        except Exception as exc:
            logger.error("Ollama error: %s", exc)
            return self._fallback.refactor(source_code)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class LLMStrategyFactory:
    """
    Factory Pattern — creates the correct LLMStrategy from configuration.

    Eliminates scattered if/elif chains across the codebase: callers ask for
    *a* strategy without knowing which providers exist or how to construct them.

    Open/Closed via registry: add a new provider with register() without
    touching any existing class.
    """

    _REGISTRY: Dict[str, type] = {
        "openai": OpenAIStrategy,
        "ollama": OllamaStrategy,
    }

    @classmethod
    def create(cls, provider: str = "") -> LLMStrategy:
        """Return a strategy instance for the given provider name (or LLM_PROVIDER env var)."""
        resolved = provider or os.getenv("LLM_PROVIDER", "mock")
        strategy_cls = cls._REGISTRY.get(resolved, RuleBasedStrategy)
        logger.debug("LLMStrategyFactory: using %s", strategy_cls.__name__)
        return strategy_cls()

    @classmethod
    def register(cls, name: str, strategy_cls: type) -> None:
        """Register a custom strategy provider without modifying this file (OCP)."""
        cls._REGISTRY[name] = strategy_cls
