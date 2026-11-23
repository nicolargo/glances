.. _llm_reporter:

LLM reporter
============

*Availability: all; requires the SDK of the chosen LLM provider*

Glances can ask a Large Language Model for a short health report of the
system, when you ask for one: press ``H`` in the TUI or the WebUI, or click
``AI report`` at the end of the alerts line of the WebUI. A window opens over
the stats. It shows ``Generating…`` while the model writes, then the report
with the time of the stats it describes, its age and the model. The report
is never shown while a new one is being written: Glances does not present a
report as current once the system has moved on.

The plugin sends the model the current CPU, memory, swap and load, their
trend over the whole stats history (with the processor and memory trend of
each GPU), the alert incidents (the ongoing ones first, then the last
resolved ones, 20 at most) and the five most CPU-hungry processes. The answer
is a 4 to 6 sentence report: a one-sentence summary, an overall status (OK,
Degraded or Critical) and a root cause. The model is told to describe the
system only, never to recommend an action such as killing a process.

A request during Glances' startup waits for its end: at least 30 seconds and
3 refresh cycles, once Glances' own startup load and the alerts engine's
warm-up are over. The trends leave out the first 10 seconds, and Glances
itself is never listed among the top processes.

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
    min_interval=60
    provider=litellm
    model=claude-haiku-4-5
    #api_key=
    #base_url=
    max_tokens=500
    trend_samples=12

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

- ``min_interval`` — one report at a time, and at most one every
  ``min_interval`` seconds (default 60), counted from the start of the last
  call. A request sooner is answered with the previous report and its age,
  and says when a new one can be requested. Glances is unauthenticated by
  default: this bounds what anyone who can reach it can spend.
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
- ``trend_samples`` — points of each metric's trend sent to the model,
  spread over the whole stats history (default 12; 40 minutes with the
  default ``[global] history_size`` and ``refresh``). The trends are left out
  of the prompt when the history is disabled or too short.

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

The TUI's ``H`` and the WebUI's button request a report with
``POST /api/5/llm_reporter/request``, which answers the plugin's state. A
client TUI (``glances -c``) asks its server: the API key and the calls stay
there, under the same ``min_interval``. The state is served by the REST API
(``GET /api/5/llm_reporter``) and the MCP server
(``glances://stats/llm_reporter``)::

    {"state": "idle", "report": "Summary: CPU is saturated by the backup job.\n1. Overall health status: Degraded ...",
     "status": "degraded", "model": "claude-haiku-4-5", "generated_at": "2026-11-20T10:05:00+01:00",
     "age": 25, "available_in": 35, "error": null, "revision": 4}

- ``state`` — ``idle``; ``starting`` while a request waits for the end of
  Glances' startup; ``generating`` while the model writes the report.
- ``report`` — the last report, kept while a new one is being written and
  after a failed call. ``status`` is ``ok``, ``degraded`` or ``critical`` as
  it states, and ``unknown`` when it states none. ``generated_at`` is the date
  of the stats it describes (ISO 8601) and ``age`` the seconds since then.
  All four are ``null`` until the first report; ``model`` is the configured
  model from the start.
- ``available_in`` — seconds before a new report can be requested; 0 when
  one can be requested now.
- ``error`` — why the last request brought no report (a failed call, an
  empty answer), or why the plugin can write none (a configuration error);
  ``null`` otherwise. The details are in the Glances log.
- ``revision`` — grows at each change of the state: of two copies of the
  payload, the higher revision is the newer.

None of these fields is exported.

Privacy and cost: a cloud provider receives the metrics above and the names
of the top processes, never their command lines. A small model such as
``claude-haiku-4-5`` or ``gpt-4o-mini`` costs about $0.001 per report, and
Glances never calls the model unless a report is requested.

A configuration error or a missing SDK is logged at startup, and the plugin
then answers every request with an ``error`` without calling the model.
Numeric settings must be finite and non-negative; setting ``trend_samples``
to zero or one omits trends. A failed call (timeout, rate limit, invalid key)
is logged as a warning and keeps the previous report.
