.. _fetch:

Fetch
=====

The fetch mode is used to get and share a quick look of a machine using the
``fetch`` option. In this mode, current stats are displayed on the console in
a fancy way.

.. code-block:: console

    $ glances --fetch

Results look like this:

.. image:: _static/screenshot-fetch.png

Bars and values take the colour of their alert level (the same thresholds
as the TUI), and titles are bold. Colours are only used when the output is a
terminal and the ``NO_COLOR`` environment variable is not set. With
``--disable-unicode``, the bars and the rules are drawn in ASCII.

It is also possible to use a custom template with the ``--fetch-template </path/to/template.jinja>`` option
(it requires ``--fetch``):

.. code-block:: console

    $ glances --fetch --fetch-template conf/fetch-templates/short.jinja

Some examples are provided in the ``conf/fetch-templates/`` directory. Please feel free to
customize them or create your own template (contribution via PR are welcome).

The format of the template is based on the Jinja2 templating engine. It is rendered with two variables:

- ``gl``: all the stats available in Glances (an instance of the :ref:`Glances Python API<api>`),
  for example ``gl.mem['percent']``, ``gl.fs.keys()``, ``gl.top_process()``, ``gl.auto_unit()``;
- ``ui``: helpers drawing values in the TUI's style. ``ui.bar``, ``ui.percent`` and ``ui.number``
  take a plugin name, a field and, for a collection, the item's key (for example
  ``ui.percent('fs', 'percent', '/home')``) and colour the value by its alert level.
  ``ui.bits``, ``ui.process``, ``ui.title``, ``ui.uptime``, ``ui.rule``, ``ui.pad``, ``ui.color``,
  ``ui.level``, ``ui.value`` and ``ui.visible`` are also available.

An undefined name stops the rendering with an error instead of printing a blank.

.. warning::

    Glances v4 templates do not work with Glances v5: some field names changed
    (for example, the network rates are ``bytes_recv`` and ``bytes_sent``, not
    ``bytes_recv_rate_per_sec`` and ``bytes_sent_rate_per_sec``) and the ``ui``
    helpers are new. Check the plugin fields in the :ref:`Glances Python API<api>`
    documentation and the templates in ``conf/fetch-templates/`` to update yours.

For example, the default template is defined as:

.. code-block:: jinja

    {{ ui.rule() }}
    ✨ {{ ui.title(gl.system['hostname']) }}{{ ' | ' + gl.ip['address'] if gl.ip.get('address') else '' }} | Uptime: {{ ui.uptime() }}
    ⚙️  {{ gl.system['hr_name'] }}

    💡 {{ ui.title('LOAD') }}     {{ ui.number('load', 'min1') }}/min1 | {{ ui.number('load', 'min5') }}/min5 | {{ ui.number('load', 'min15') }}/min15
    ⚡ {{ ui.title('CPU') }}      {{ ui.bar('cpu', 'total') }} {{ ui.percent('cpu', 'total') }} of {{ gl.core['log'] }} cores
    🧠 {{ ui.title('MEM') }}      {{ ui.bar('mem', 'percent') }} {{ ui.percent('mem', 'percent') }} ({{ gl.auto_unit(gl.mem['used']) }} / {{ gl.auto_unit(gl.mem['total']) }})
    {% for fs in gl.fs.keys() %}💾 {% if loop.index == 1 %}{{ ui.title('DISK') }}{% else %}    {% endif %}     {{ ui.bar('fs', 'percent', fs) }} {{ ui.percent('fs', 'percent', fs) }} ({{ gl.auto_unit(gl.fs[fs]['used']) }} / {{ gl.auto_unit(gl.fs[fs]['size']) }}) for {{ fs }}
    {% endfor %}{% for net in ui.visible('network') %}📡 {% if loop.index == 1 %}{{ ui.title('NET') }}{% else %}   {% endif %}      ↓ {{ ui.bits('network', 'bytes_recv', net) }}/s ↑ {{ ui.bits('network', 'bytes_sent', net) }}/s for {{ net }}
    {% endfor %}
    🔥 {{ ui.title('TOP PROCESS by CPU') }}
    {% for p in gl.top_process() %}{{ loop.index }}️⃣ {{ ui.pad(p['name'], 20) }}    ⚡ {{ ui.pad(ui.process(p, 'cpu_percent') ~ '% CPU', 11) }}    🧠 {{ gl.auto_unit(p['memory_info']['rss']) }}B MEM
    {% endfor %}🔥 {{ ui.title('TOP PROCESS by MEM') }}
    {% for p in gl.top_process(sorted_by='memory_percent', sorted_by_secondary='cpu_percent') %}{{ loop.index }}️⃣ {{ ui.pad(p['name'], 20) }}    🧠 {{ ui.pad(gl.auto_unit(p['memory_info']['rss']) ~ 'B MEM', 10) }}    ⚡ {{ ui.process(p, 'cpu_percent') }}% CPU
    {% endfor %}{{ ui.rule() }}
