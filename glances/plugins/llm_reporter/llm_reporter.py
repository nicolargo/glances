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
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from glances.config import GlancesConfig

# Per attempt. A local reasoning model needs this long (qwen3 27B took 40-45 s on a
# laptop), and a failing report, with its retries, still ends within the default
# 300 s refresh (4 x 60 s).
_LLM_REPORTER_TIMEOUT = 60
_LLM_MAX_RETRIES = 3
_DEFAULT_MAX_TOKENS = 500
_DEFAULT_CACHE_TTL = 3600.0
# Ollama is reached through its OpenAI-compatible API, which expects a key and ignores it.
_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434/v1"
_OLLAMA_PLACEHOLDER_API_KEY = "ollama"
# LiteLLM's Ollama providers run locally and need no key.
_LITELLM_KEYLESS_PREFIXES = ("ollama/", "ollama_chat/")
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

        An unset ``base_url`` is None, so the SDKs use their default endpoint.
        ``api_key`` is required except for Ollama: the provider's own environment
        variable (``ANTHROPIC_API_KEY``...) is never used, as other tools read
        it too and would bill the API account it belongs to.
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
        elif api_key is None and not (provider is LLMProvider.LITELLM and model.startswith(_LITELLM_KEYLESS_PREFIXES)):
            raise ValueError(
                "[llm_reporter] api_key is not set: set it in the [llm_reporter] section or with the "
                "GLANCES_LLM_REPORTER__API_KEY environment variable. Glances does not read the providers' "
                "API key environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.): set globally, "
                "they can be used unintentionally by other applications, such as Claude Code, resulting "
                "in unexpected charges. For a local server that needs no key, set api_key to any value."
            )
        return cls(provider, model, api_key, max_tokens, base_url)


def _keep_litellm_off_the_terminal(litellm: Any) -> None:
    """Send LiteLLM's warnings and errors to the Glances log instead of the console."""
    # LiteLLM adds its own console handlers to its loggers, and prints a banner when
    # a call fails: in the TUI, that text lands in the curses screen and breaks it.
    # Its INFO messages, two per call, would only fill the Glances log.
    litellm.suppress_debug_info = True
    for name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
        litellm_logger = logging.getLogger(name)
        litellm_logger.setLevel(logging.WARNING)
        for handler in list(litellm_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                litellm_logger.removeHandler(handler)


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


def _answer(text: str | None, hit_limit: bool, max_tokens: int) -> str | None:
    """Return the model's answer; raise when it is empty because the model hit max_tokens."""
    # A reasoning model counts its thinking against max_tokens and can spend them all
    # before answering. The empty answer would only be logged as an empty report:
    # raise instead, so the log says why, and what to change.
    if hit_limit and not (text or "").strip():
        raise RuntimeError(
            f"max_tokens ({max_tokens}) used up by reasoning before any answer: "
            "raise max_tokens or use a model without reasoning"
        )
    return text


def _build_reporter(config: LLMConfig) -> Callable[[str], str]:
    """Factory: return a provider-agnostic ``(prompt) -> report`` callable.

    The SDK is imported and its client built once, here. The returned
    callable blocks for the whole HTTP round-trip: run it in a worker thread.
    """
    sdk = _import_provider(config.provider)

    match config.provider:
        case LLMProvider.LITELLM:
            _keep_litellm_off_the_terminal(sdk)

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
                choice = r.choices[0]
                return _answer(choice.message.content, choice.finish_reason == "length", config.max_tokens)

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
                text = "".join(block.text for block in r.content if block.type == "text")
                return _answer(text, r.stop_reason == "max_tokens", config.max_tokens)

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
                choice = r.choices[0]
                return _answer(choice.message.content, choice.finish_reason == "length", config.max_tokens)

        case _:
            raise ValueError(f"Unsupported LLM Provider: {config.provider}")

    return _call


def _bucket(percent: float | None) -> int | None:
    return None if percent is None else int(percent // _STATE_BUCKET_PERCENT)


def state_key(cpu: float, mem: float, swap: float | None, alerts: frozenset) -> tuple[Any, ...]:
    """The system state the cache compares: CPU, memory and swap buckets, and the active alerts with their levels."""
    return (_bucket(cpu), _bucket(mem), _bucket(swap), alerts)


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
