.. _llm_reporter:

LLM reporter
============

*Availability: all; requires the SDK of the chosen LLM provider*

Glances can ask a Large Language Model for a short health report of the
system. Every ``refresh`` seconds (5 minutes by default), the plugin sends
the model the current CPU, memory, swap and load, their trend over the last
interval, the active alerts and the five most CPU-hungry processes, and
publishes the answer: a 4 to 6 sentence report with an overall status (OK,
Degraded or Critical), a root cause and a recommended action. The first
report comes a few global refresh cycles after start (about 8 seconds by
default), once the trends, the process list and the alerts are available.

The plugin is disabled by default. Enable it, choose a provider and a model,
and install the SDK of that provider (only that one):

.. code-block:: console

    $ pip install 'glances[llm-litellm]'     # LiteLLM: Anthropic, OpenAI, Mistral, Ollama and many more
    $ pip install 'glances[llm-anthropic]'   # Anthropic SDK
    $ pip install 'glances[llm-openai]'      # OpenAI SDK
    $ pip install 'glances[llm-ollama]'      # local Ollama, through its OpenAI-compatible API

Configuration (``[llm_reporter]`` section):

.. code-block:: ini

    [llm_reporter]
    disable=False
    refresh=300
    provider=litellm
    model=claude-haiku-4-5
    #api_key=
    #base_url=
    max_tokens=500
    cache_ttl=3600
    trend_samples=3

- ``refresh`` — seconds between two reports (default 300).
- ``provider`` — ``litellm``, ``anthropic``, ``openai`` or ``ollama``.
- ``model`` — the model, as the provider names it.
- ``api_key`` — leave it unset to use the provider's own environment variable
  (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``, ``MISTRAL_API_KEY``...), or set
  the ``GLANCES_LLM_REPORTER__API_KEY`` environment variable. Not needed for
  Ollama. The key is never served by ``/api/5/config``.
- ``base_url`` — endpoint override, for Ollama or any OpenAI-compatible
  server (Ollama default: ``http://localhost:11434/v1``).
- ``max_tokens`` — hard cap on the output tokens of each report (default 500).
- ``cache_ttl`` — a report is reused without calling the model while CPU,
  memory and swap stay in the same 5% bucket and the number of active alerts
  is unchanged, for up to ``cache_ttl`` seconds (default 3600). It must be
  larger than ``refresh`` to save any call: an idle machine then costs one
  call per hour instead of twelve.
- ``trend_samples`` — points of each metric's trend sent to the model,
  spread over the last ``refresh`` seconds (default 3). The trends are read
  from the stats history (see ``[global] history_size``) and are left out of
  the prompt when the history is disabled or too short.

Examples:

.. code-block:: ini

    # Claude, OpenAI or Mistral through LiteLLM
    provider=litellm
    model=claude-haiku-4-5
    #model=gpt-4o-mini
    #model=mistral/mistral-large-latest

    # Direct SDKs
    provider=anthropic
    model=claude-haiku-4-5
    #provider=openai
    #model=gpt-4o-mini

    # Local Ollama: no API key, no cost, no data leaves the machine
    provider=ollama
    model=llama3.2

The report is served by the REST API (``GET /api/5/llm_reporter``) and the
MCP server (``glances://stats/llm_reporter``)::

    {"report": "1. Overall health status: Degraded ...", "status": "degraded",
     "model": "claude-haiku-4-5", "generated_at": "2026-11-02T10:05:00+01:00"}

``status`` is ``ok``, ``degraded`` or ``critical`` as stated by the report,
and ``unknown`` when the report states none. ``generated_at`` is the date of
the stats the report was generated from (ISO 8601): a report reused by the
cache, or kept after a failed call, keeps its date. All three are ``null``
(as is ``report``) until the first report. The report is not displayed by
the TUI and the WebUI, and it is not exported.

Privacy and cost: a cloud provider receives the metrics above and the names
of the top processes, never their command lines. With a 5 minute interval, a
small model such as ``claude-haiku-4-5`` or ``gpt-4o-mini`` costs about
$0.001 per report.

A configuration error or a missing SDK is logged at startup, and the plugin
then publishes empty fields. A failed call (timeout, rate limit, invalid key)
is logged as a warning, keeps the previous report, and is retried at the
next interval.
