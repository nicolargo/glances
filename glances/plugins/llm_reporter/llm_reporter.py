#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — llm_reporter: LLM provider factory and report cache.

``_build_reporter()`` turns the ``[llm_reporter]`` configuration into a
provider-agnostic callable ``(prompt) -> report``. Each provider SDK is an
optional dependency (``pip install 'glances[llm-<provider>]'``), imported
only when that provider is configured, and every call is capped by
``max_tokens``.

``_ReportCache`` decides whether a due report is worth an LLM call: only when
the bucketed system state changed, or when the last report is older than
``cache_ttl``.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from glances.config import GlancesConfig

_LLM_REPORTER_TIMEOUT = 30
_LLM_MAX_RETRIES = 3
_DEFAULT_MAX_TOKENS = 500
_DEFAULT_CACHE_TTL = 3600.0
# Ollama is reached through its OpenAI-compatible API, which expects a key and ignores it.
_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434/v1"
_OLLAMA_PLACEHOLDER_API_KEY = "ollama"
# The cache compares CPU, memory and swap in 5% buckets.
_STATE_BUCKET_PERCENT = 5


class LLMProvider(str, Enum):
    # (str, Enum) works on Python 3.10, the minimal version.
    LITELLM = "litellm"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


# The SDK each provider is reached through.
_PROVIDER_MODULES: dict[LLMProvider, str] = {
    LLMProvider.LITELLM: "litellm",
    LLMProvider.ANTHROPIC: "anthropic",
    LLMProvider.OPENAI: "openai",
    LLMProvider.OLLAMA: "openai",
}


@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str | None
    max_tokens: int
    base_url: str | None

    @classmethod
    def from_glances_config(cls, config: GlancesConfig) -> LLMConfig:
        """Read ``[llm_reporter]``; raise ``ValueError`` on a missing or invalid key.

        Unset ``api_key`` / ``base_url`` are None, so the SDKs use their
        environment variables (``OPENAI_API_KEY``...) and default endpoint.
        """
        provider_str = config.get("llm_reporter", "provider", "").strip().lower()
        if not provider_str:
            raise ValueError("[llm_reporter] provider is not set")
        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            valid = ", ".join(p.value for p in LLMProvider)
            raise ValueError(f"[llm_reporter] provider={provider_str} is not one of: {valid}") from None
        model = config.get("llm_reporter", "model", "").strip()
        if not model:
            raise ValueError("[llm_reporter] model is not set")
        # An indented line after `model=` is read as part of its value: reported
        # without echoing it, as that line may be another key.
        if any(char.isspace() for char in model):
            raise ValueError(
                "[llm_reporter] model must not contain spaces or line breaks "
                "(check the indentation of the lines after it)"
            )
        max_tokens = config.get("llm_reporter", "max_tokens", _DEFAULT_MAX_TOKENS)
        if max_tokens < 1:
            raise ValueError(f"[llm_reporter] max_tokens={max_tokens} must be at least 1")
        api_key = config.get("llm_reporter", "api_key", "").strip() or None
        base_url = config.get("llm_reporter", "base_url", "").strip() or None
        if provider is LLMProvider.OLLAMA:
            api_key = api_key or _OLLAMA_PLACEHOLDER_API_KEY
            base_url = base_url or _OLLAMA_DEFAULT_BASE_URL
        return cls(provider, model, api_key, max_tokens, base_url)


def _import_provider(provider: LLMProvider) -> Any:
    """Import the SDK ``provider`` needs, with an actionable error when it is not installed."""
    module_name = _PROVIDER_MODULES[provider]
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:
            raise  # a dependency of the SDK itself is missing
        raise RuntimeError(
            f"provider={provider.value} needs the {module_name} package: pip install 'glances[llm-{provider.value}]'"
        ) from e


def _build_reporter(config: LLMConfig) -> Callable[[str], str]:
    """Factory: return a provider-agnostic ``(prompt) -> report`` callable.

    The SDK is imported and its client built once, here. The returned
    callable blocks for the whole HTTP round-trip: run it in a worker thread.
    """
    sdk = _import_provider(config.provider)

    match config.provider:
        case LLMProvider.LITELLM:

            def _call(prompt: str) -> str:
                r = sdk.completion(
                    model=config.model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=config.api_key,
                    base_url=config.base_url,
                    max_completion_tokens=config.max_tokens,
                    timeout=_LLM_REPORTER_TIMEOUT,
                    num_retries=_LLM_MAX_RETRIES,
                )
                return r.choices[0].message.content

        case LLMProvider.ANTHROPIC:
            client = sdk.Anthropic(
                api_key=config.api_key,
                base_url=config.base_url,
                timeout=_LLM_REPORTER_TIMEOUT,
                max_retries=_LLM_MAX_RETRIES,
            )

            def _call(prompt: str) -> str:
                r = client.messages.create(
                    model=config.model,
                    max_tokens=config.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return "".join(block.text for block in r.content if block.type == "text")

        case LLMProvider.OPENAI | LLMProvider.OLLAMA:
            client = sdk.OpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
                max_retries=_LLM_MAX_RETRIES,
                timeout=_LLM_REPORTER_TIMEOUT,
            )
            # OpenAI takes max_completion_tokens, Ollama max_tokens.
            token_limit = "max_tokens" if config.provider is LLMProvider.OLLAMA else "max_completion_tokens"

            def _call(prompt: str) -> str:
                r = client.chat.completions.create(
                    model=config.model,
                    messages=[{"role": "user", "content": prompt}],
                    **{token_limit: config.max_tokens},
                )
                return r.choices[0].message.content

        case _:
            raise ValueError(f"Unsupported LLM Provider: {config.provider}")

    return _call


def _bucket(percent: float | None) -> int | None:
    return None if percent is None else int(percent // _STATE_BUCKET_PERCENT)


def state_key(cpu: float, mem: float, swap: float | None, alert_count: int) -> tuple[Any, ...]:
    """The system state the cache compares: CPU, memory and swap buckets, and the active alert count."""
    return (_bucket(cpu), _bucket(mem), _bucket(swap), alert_count)


class _ReportCache:
    """Reuse the last report while the system state is unchanged, for up to ``ttl`` seconds.

    Consulted when a report is due, so ``ttl`` is longer than ``refresh``.
    """

    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._last_key: tuple[Any, ...] | None = None
        self._last_time: float | None = None

    def is_stale(self, key: tuple[Any, ...], now: float) -> bool:
        """True when ``key`` differs from the cached report's state or the cached report expired."""
        return self._last_time is None or key != self._last_key or now - self._last_time >= self.ttl

    def store(self, key: tuple[Any, ...], now: float) -> None:
        """Record the state and time of a successful report."""
        self._last_key = key
        self._last_time = now
