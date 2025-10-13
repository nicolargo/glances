#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Fetch mode interface class."""

import jinja2

from glances import api
from glances.logger import logger

DEFAULT_FETCH_TEMPLATE = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {{ gl.system['hostname'] }}{{ ' | ' + gl.ip['address'] if gl.ip['address'] else '' }} | Uptime: {{ gl.uptime }}
⚙️  {{ gl.system['hr_name'] }}

💡 LOAD     {{ '%0.2f'| format(gl.load['min1']) }}/min1 |\
 {{ '%0.2f'| format(gl.load['min5']) }}/min5 |\
 {{ '%0.2f'| format(gl.load['min15']) }}/min15
⚡ CPU      {{ gl.bar(gl.cpu['total']) }} {{ gl.cpu['total'] }}% of {{ gl.core['log'] }} cores
🧠 MEM      {{ gl.bar(gl.mem['percent']) }} {{ gl.mem['percent'] }}% ({{ gl.auto_unit(gl.mem['used']) }} /\
 {{ gl.auto_unit(gl.mem['total']) }})
{% for fs in gl.fs.keys() %}\
💾 {% if loop.index == 1 %}DISK{% else %}    {% endif %}\
     {{ gl.bar(gl.fs[fs]['percent']) }} {{ gl.fs[fs]['percent'] }}% ({{ gl.auto_unit(gl.fs[fs]['used']) }} /\
 {{ gl.auto_unit(gl.fs[fs]['size']) }}) for {{ fs }}
{% endfor %}\
{% for net in gl.network.keys() %}\
📡 {% if loop.index == 1 %}NET{% else %}   {% endif %}\
      ↓ {{ gl.auto_unit(gl.network[net]['bytes_recv_rate_per_sec']) }}b/s\
 ↑ {{ gl.auto_unit(gl.network[net]['bytes_sent_rate_per_sec']) }}b/s for {{ net }}
{% endfor %}\

🔥 TOP PROCESS by CPU
{% for process in gl.top_process() %}\
{{ loop.index }}️⃣ {{ process['name'][:20] }}{{ ' ' * (20 - process['name'][:20] | length) }}\
    ⚡ {{ process['cpu_percent'] }}% CPU\
{{ ' ' * (8 - (gl.auto_unit(process['cpu_percent']) | length)) }}\
    🧠 {{ gl.auto_unit(process['memory_info']['rss']) }}B MEM
{% endfor %}\
🔥 TOP PROCESS by MEM
{% for process in gl.top_process(sorted_by='memory_percent', sorted_by_secondary='cpu_percent') %}\
{{ loop.index }}️⃣ {{ process['name'][:20] }}{{ ' ' * (20 - process['name'][:20] | length) }}\
    🧠 {{ gl.auto_unit(process['memory_info']['rss']) }}B MEM\
{{ ' ' * (7 - (gl.auto_unit(process['memory_info']['rss']) | length)) }}\
    ⚡ {{ process['cpu_percent'] }}% CPU
{% endfor %}\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""


class GlancesStdoutFetch:
    """This class manages the Stdout JSON display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args
        self.gl = api.GlancesAPI(self.config, self.args)

    def end(self):
        pass

    def update(self, stats, duration=3, cs_status=None, return_to_browser=False):
        """Display fetch from the template file to stdout."""
        if self.args.fetch_template == "":
            fetch_template = DEFAULT_FETCH_TEMPLATE
        else:
            logger.info("Using fetch template file: " + self.args.fetch_template)
            # Load the template from the file given in the self.args.fetch_template argument
            with open(self.args.fetch_template) as f:
                fetch_template = f.read()

        # Create a Jinja2 environment
        jinja_env = jinja2.Environment(loader=jinja2.BaseLoader())
        template = jinja_env.from_string(fetch_template)
        output = template.render(gl=self.gl)
        print(output)

        # Return True to exit directly (no refresh)
        return True
