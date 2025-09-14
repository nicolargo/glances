import json

from glances.outputs.glances_curses import _GlancesCurses

print(json.dumps({"leftMenu": [p for p in _GlancesCurses._left_sidebar if p != "now"]}, indent=4))
