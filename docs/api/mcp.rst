.. _api_mcp:

MCP (Model Context Protocol) server
=====================================

Glances can expose its system monitoring data through a
`Model Context Protocol <https://modelcontextprotocol.io>`_ (MCP) server,
allowing AI assistants (Claude, Cursor, VS Code Copilot, …) to query
real-time metrics and generate structured analyses directly from their chat
interface.

The MCP server is mounted alongside the standard RESTful API when the web
server is started with the ``--enable-mcp`` flag.  It uses **Server-Sent
Events** (SSE) as its transport layer, which means any MCP-compatible client
that supports SSE can connect to it.

Requirements
------------

The ``mcp`` Python package must be installed:

.. code-block:: bash

    pip install 'glances[mcp]'

Start the MCP server
--------------------

Add ``--enable-mcp`` to any Glances web-server command:

.. code-block:: bash

    glances -w --enable-mcp

The MCP server is then reachable at ``http://localhost:61208/mcp``.

The SSE endpoint used by MCP clients is:

.. code-block:: text

    http://localhost:61208/mcp/sse

To change the mount path (default: ``/mcp``):

.. code-block:: bash

    glances -w --enable-mcp --mcp-path /monitoring/mcp

Authentication
--------------

The MCP endpoint inherits the authentication policy of the web server.
When Glances is started with ``--password``, every MCP request must carry
valid credentials — either **HTTP Basic Auth** or a **JWT Bearer token**
(see :ref:`api_restful` for how to obtain a JWT token).

When no password is configured the MCP endpoint is open.

Resources
---------

MCP resources are read-only data sources that a client can list and read.

Static resources
~~~~~~~~~~~~~~~~

============================================ ================================================
URI                                          Description
============================================ ================================================
``glances://plugins``                        JSON list of all active plugin names
``glances://stats``                          JSON object of all plugins' current statistics
``glances://limits``                         JSON object of alert thresholds for all plugins
============================================ ================================================

Resource templates (parameterised)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

============================================== =====================================================
URI template                                   Description
============================================== =====================================================
``glances://stats/{plugin}``                   Current statistics for one plugin
``glances://stats/{plugin}/history``           Historical time-series for one plugin
``glances://limits/{plugin}``                  Alert thresholds for one plugin
============================================== =====================================================

Replace ``{plugin}`` with any name returned by ``glances://plugins``
(e.g. ``cpu``, ``mem``, ``network``, ``processlist``, …).

Prompts
-------

MCP prompts are pre-built analysis templates that embed live Glances data
into a system prompt ready to be sent to an LLM.

+-----------------------------+-----------------------------------------------------+-------------------+
| Prompt name                 | Description                                         | Parameters        |
+=============================+=====================================================+===================+
| ``system_health_summary``   | Overall health report: CPU, memory, swap,           | *(none)*          |
|                             | load, filesystems, network                          |                   |
+-----------------------------+-----------------------------------------------------+-------------------+
| ``alert_analysis``          | Analysis of active alerts with remediation steps    | ``level``         |
|                             |                                                     | (``warning`` /    |
|                             |                                                     | ``critical`` /    |
|                             |                                                     | ``all``)          |
+-----------------------------+-----------------------------------------------------+-------------------+
| ``top_processes_report``    | Report on the most CPU-intensive processes          | ``nb``            |
|                             |                                                     | (integer,         |
|                             |                                                     | default ``10``)   |
+-----------------------------+-----------------------------------------------------+-------------------+
| ``storage_health``          | Disk usage and I/O statistics analysis              | *(none)*          |
+-----------------------------+-----------------------------------------------------+-------------------+

Connect an MCP client
---------------------

Claude Desktop
~~~~~~~~~~~~~~

Add the following entry to your ``claude_desktop_config.json``
(``~/Library/Application Support/Claude/claude_desktop_config.json`` on macOS,
``%APPDATA%\Claude\claude_desktop_config.json`` on Windows):

.. code-block:: json

    {
      "mcpServers": {
        "glances": {
          "url": "http://localhost:61208/mcp/sse"
        }
      }
    }

For a password-protected server, use the ``headers`` field:

.. code-block:: json

    {
      "mcpServers": {
        "glances": {
          "url": "http://localhost:61208/mcp/sse",
          "headers": {
            "Authorization": "Basic <base64(user:password)>"
          }
        }
      }
    }

Python MCP client (programmatic access)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from mcp.client.sse import sse_client
    from mcp import ClientSession

    async def main():
        async with sse_client("http://localhost:61208/mcp/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List available resources
                resources = await session.list_resources()
                print([str(r.uri) for r in resources.resources])

                # Read CPU stats
                from pydantic import AnyUrl
                result = await session.read_resource(AnyUrl("glances://stats/cpu"))
                print(result.contents[0].text)

                # Run a health-summary prompt
                prompt = await session.get_prompt("system_health_summary")
                print(prompt.messages[0].content.text[:200])

    asyncio.run(main())

.. seealso::

   :ref:`api_restful` — RESTful/JSON API documentation

   :ref:`cmds` — full command-line reference
