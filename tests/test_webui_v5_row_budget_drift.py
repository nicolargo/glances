"""Behavioural drift guard for the row-budget solver.

The other WebUI drift tests compare constant LISTS -- an ordering, a set of
widths. This one cannot: `plan_right_column` is an algorithm, and a textual
comparison of two languages' source would prove nothing. So it runs both
solvers over a case matrix and requires identical output dicts.

One `node` invocation for the whole matrix: JSON in, JSON out.

Two adaptations from the original brief, both required by this environment,
neither weakening what is checked -- the full matrix is still compared:

1. `process.argv` indexing: with `node -e <script> <args...>`, there is no
   script-path entry in `argv` (unlike running a `.js` file), so the brief's
   `argv[2]` is off by one. Verified empirically against the `node` on this
   box (v24.16.0): `node --input-type=module -e 'console.log(process.argv)'
   foo` prints `[nodePath, "foo"]` -- the extra arg is `argv[1]`.
2. Passing the whole case matrix as a single argv string hits the OS's
   `E2BIG` (`OSError: [Errno 7] Argument list too long`) once the matrix
   is a few thousand cases. The matrix is instead written to the child's
   stdin and read with `fs.readFileSync(0, "utf-8")`, which has no such
   limit.
"""

from __future__ import annotations

import itertools
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.curses_renderer_v5 import plan_right_column

_MODULE = Path("glances/outputs/static/js/v5/row_budget.js").resolve()

_BODY_HEIGHTS = (4, 8, 10, 20, 24, 30, 40, 60, 100)
_VMS = (0, 1, 3, 12)
_CONTAINERS = (0, 1, 3, 30)
_PROCESSES = (0, 5, 20, 200)
_ALERTS = (0, 1, 5, 12)
_ONGOING = (0, 1, 3, 8)
_AMPS = (0, 3, 9)


def _cases():
    for body, vms, containers, procs, alerts, ongoing, amps in itertools.product(
        _BODY_HEIGHTS, _VMS, _CONTAINERS, _PROCESSES, _ALERTS, _ONGOING, _AMPS
    ):
        # `n_ongoing` counts a SUBSET of `n_alerts` -- an impossible pair would
        # test a state the engine cannot produce.
        if ongoing > alerts:
            continue
        yield {
            "bodyHeight": body,
            "staticHeights": {"processcount": 1},
            "ampsHeight": amps,
            "nVms": vms,
            "nContainers": containers,
            "nProcesses": procs,
            "nAlerts": alerts,
            "nOngoing": ongoing,
        }


_RUNNER = """
import {{ readFileSync }} from "node:fs";
import {{ planRightColumn }} from {module};
const cases = JSON.parse(readFileSync(0, "utf-8"));
process.stdout.write(JSON.stringify(cases.map((c) => planRightColumn(c))));
"""


def test_the_js_solver_matches_the_python_one():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not available")
    cases = list(_cases())
    assert len(cases) > 1000, "a shrunken matrix would make this guard vacuous"

    script = _RUNNER.format(module=json.dumps(_MODULE.as_uri()))
    out = subprocess.run(
        [node, "--input-type=module", "-e", script],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
    )
    js_results = json.loads(out.stdout)

    for case, js in zip(cases, js_results, strict=True):
        py = plan_right_column(
            body_height=case["bodyHeight"],
            static_heights=case["staticHeights"],
            amps_height=case["ampsHeight"],
            n_vms=case["nVms"],
            n_containers=case["nContainers"],
            n_processes=case["nProcesses"],
            n_alerts=case["nAlerts"],
            n_ongoing=case["nOngoing"],
        )
        assert py == js, f"divergence on {case}: python={py} js={js}"
