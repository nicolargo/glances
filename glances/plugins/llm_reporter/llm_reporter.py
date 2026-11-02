# TODO add comments explaining this
import importlib
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from glances.config import GlancesConfig

_LLM_REPORTER_TIMEOUT = 30
_LLM_MAX_RETRIES = 3
_DEFAULT_MAX_TOKENS = 500
_DEFAULT_LLM_CACHE_TTL = 300
_DEFAULT_LLM_REPORTER_HISTORY_SIZE = 3


class LLMProvider(StrEnum):
    LITELLM = "litellm"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str | None
    max_tokens: int
    base_url: str | None

    @classmethod
    def from_glances_config(cls, config: GlancesConfig) -> "LLMConfig":
        provider_str = config.get("llm_reporter", "llm_provider", "")
        if not provider_str:
            raise ValueError("An LLM Provider must be provided when LLMReporterPlugin is enabled")
        provider = LLMProvider(provider_str)
        model = config.get("llm_reporter", "model", "")
        if not model or not model.strip():
            raise ValueError("LLM model must be configured when LLMReporterPlugin is enabled")
        api_key = config.get("llm_reporter", "api_key", "")
        max_tokens = config.get("llm_reporter", "max_tokens", _DEFAULT_MAX_TOKENS)
        base_url = config.get("llm_reporter", "base_url", "")
        return cls(provider, model, api_key, max_tokens, base_url)


class Reporter:
    def __init__(self, config):
        self.llm = _build_reporter(LLMConfig.from_glances_config(config))
        self.ttl = config.get("llm_reporter", "llm_cache_ttl", _DEFAULT_LLM_CACHE_TTL)
        self.history_size = config.get("llm_reporter", "history_size", _DEFAULT_LLM_REPORTER_HISTORY_SIZE)
        self.report_history = deque()

    def __call__(self, prompt: str):

        # if call
        # else
        return self.llm(prompt)


def _import_provider(m: str):
    try:
        module = importlib.import_module(m)
    except ModuleNotFoundError as e:
        if e.name != m:
            raise
        raise RuntimeError(f"The {m} package is required to enable llm reporting via {m}") from e
    return module


def _build_reporter(config: LLMConfig) -> Callable[[str], str]:

    match config.provider:
        case LLMProvider.LITELLM:
            litellm = _import_provider(LLMProvider.LITELLM)

            def _call(prompt: str):
                r = litellm.completion(
                    model=config.model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=config.api_key,
                    max_completion_tokens=config.max_tokens,
                )
                return r.choices[0].message.content

        case LLMProvider.ANTHROPIC:
            anthropic = _import_provider(LLMProvider.ANTHROPIC)
            client = anthropic.Anthropic(
                api_key=config.api_key,
                timeout=_LLM_REPORTER_TIMEOUT,
                max_retries=_LLM_MAX_RETRIES,
            )

            def _call(prompt: str) -> str:
                r = client.messages.create(
                    model=config.model,
                    max_tokens=config.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return r.content[0].text

        case LLMProvider.OPENAI:
            openai = _import_provider(LLMProvider.OPENAI)
            client = openai.OpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
                max_retries=_LLM_MAX_RETRIES,
                timeout=_LLM_REPORTER_TIMEOUT,
            )

            def _call(prompt: str) -> str:
                r = client.chat.completions.create(
                    model=config.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=config.max_tokens,
                )
                return r.choices[0].message.content

        case LLMProvider.OLLAMA:
            openai = _import_provider(LLMProvider.OPENAI)
            client = openai.OpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
                max_retries=_LLM_MAX_RETRIES,
                timeout=_LLM_REPORTER_TIMEOUT,
            )

            def _call(prompt: str) -> str:
                r = client.chat.completions.create(
                    model=config.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=config.max_tokens,
                )
                return r.choices[0].message.content

        case _:
            raise ValueError(f"Unsupported LLM Provider: {config.provider}")

    return _call
