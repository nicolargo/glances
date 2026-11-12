.. _llm_reporter:

LLM reporter
============

*Availability: all; requires the SDK of the chosen LLM provider*

Glances can ask a Large Language Model for a short health report of the
system. Every ``refresh`` seconds (5 minutes by default), and soon after the
active alerts change, the plugin sends the model the current CPU, memory,
swap and load, their trend over the last interval (with the processor and
memory trend of each GPU), the active alerts and the five most CPU-hungry
processes, and publishes the answer: a 4 to 6 sentence report with an
overall status (OK, Degraded or Critical), a root cause and a recommended
action. The first report comes at least 30 seconds and 3 refresh cycles
after start, once Glances' own startup load and the alerts engine's warm-up
are over: its trends leave out the first 10 seconds, and Glances itself is
never listed among the top processes.

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
    min_interval=60
    provider=litellm
    model=claude-haiku-4-5
    #api_key=
    #base_url=
    max_tokens=500
    cache_ttl=3600
    trend_samples=3

.. warning::

    Glances does not read the providers' API key environment variables
    (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``, etc.). Setting these
    variables globally can cause other applications to use your API key
    unintentionally, resulting in unexpected charges.

    For example, Claude Code may use ``ANTHROPIC_API_KEY`` instead of your
    Claude subscription and bill you per use. Claude Pro and Max
    subscriptions do not include API usage.

    To avoid this, set the key for Glances only: ``api_key`` in the
    ``[llm_reporter]`` section, or the ``GLANCES_LLM_REPORTER__API_KEY``
    environment variable.

- ``refresh`` — seconds between two reports (default 300).
- ``min_interval`` — when the active alerts change (an alert opens, closes or
  changes level), a report is requested right away instead of waiting for
  ``refresh``, at most once every ``min_interval`` seconds (default 60). Set
  it to ``refresh`` or more to wait for ``refresh``.
- ``provider`` — ``litellm``, ``anthropic``, ``openai`` or ``ollama``.
- ``model`` — the model, as the provider names it.
- ``api_key`` — the API key of the provider, required except for Ollama. You
  can also set it with the ``GLANCES_LLM_REPORTER__API_KEY`` environment
  variable, which keeps it out of the configuration file. For a local server
  that needs no key, set any value. The key is never served by
  ``/api/5/config``.
- ``base_url`` — endpoint override, for Ollama or any OpenAI-compatible
  server (Ollama default: ``http://localhost:11434/v1``).
- ``max_tokens`` — hard cap on the output tokens of each report (default 500).
- ``cache_ttl`` — a report is reused without calling the model while CPU,
  memory and swap stay in the same 5% bucket and the active alerts are
  unchanged, for up to ``cache_ttl`` seconds (default 3600). It must be
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

    {"report": "1. Overall health status: Degraded ...",
     "short_report": "CPU is saturated by the backup job.", "status": "degraded",
     "model": "claude-haiku-4-5", "generated_at": "2026-11-02T10:05:00+01:00"}

``short_report`` is the one-sentence summary the model is asked to start
with, taken out of ``report``. The TUI and the WebUI show it at the end of
the first line of the alerts block::

    ALERTS  2 ongoing · 1 resolved · CPU is saturated by the backup job.

It is ``null`` until the first report, and when the report states none. The
summary describes the alerts the report was generated from, while the alert
counts next to it are live: when the active alerts change, a new report is
requested right away (see ``min_interval``), so the summary catches up within
about a minute.

``status`` is ``ok``, ``degraded`` or ``critical`` as stated by the report,
and ``unknown`` when the report states none. ``generated_at`` is the date of
the stats the report was generated from (ISO 8601): a report reused by the
cache, or kept after a failed call, keeps its date. Both are ``null`` (as is
``report``) until the first report; ``model`` is the configured model from
the start. The TUI displays only ``short_report``. The WebUI also shows the
full report, with its time and model, at the top of its alerts window,
opened by clicking the alert counts or the summary. None of these fields is
exported.

Privacy and cost: a cloud provider receives the metrics above and the names
of the top processes, never their command lines. With a 5 minute interval, a
small model such as ``claude-haiku-4-5`` or ``gpt-4o-mini`` costs about
$0.001 per report. Alert changes add reports, at most one every
``min_interval`` seconds.

A configuration error or a missing SDK is logged at startup, and the plugin
then publishes empty fields without calling the model. Numeric settings must
be finite; ``min_interval``, ``cache_ttl`` and ``trend_samples`` must also be
non-negative. A zero ``cache_ttl`` disables cache reuse, and setting
``trend_samples`` to zero or one omits trends. A failed call (timeout, rate
limit, invalid key) is logged as a warning, keeps the previous report, and
is retried at the next interval.
