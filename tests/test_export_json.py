#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Glances contributors
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""JSON export must write the completed sample without waiting for another one."""

import json
import subprocess  # nosec B404 - exercise the real CLI with a fixed executable.
import sys


def test_json_export_writes_a_single_sample(tmp_path):
    config = tmp_path / 'glances.conf'
    config.write_text('')
    output = tmp_path / 'stats.json'
    result = subprocess.run(  # nosec B603 - fixed interpreter/arguments, no shell.
        [
            sys.executable,
            '-m',
            'glances',
            '-C',
            str(config),
            '--export',
            'json',
            '--export-json-file',
            str(output),
            '--stop-after',
            '2',  # The first iteration initializes exporters without exporting.
            '--quiet',
            '--disable-plugin',
            'all',
            '--enable-plugin',
            'cpu,mem',
        ],
        capture_output=True,
        text=True,
        timeout=40,
    )
    assert result.returncode == 0, result.stderr  # nosec B101 - pytest regression assertion.
    stats = json.loads(output.read_text())
    assert isinstance(stats['cpu'], dict)  # nosec B101 - pytest regression assertion.
    assert stats['mem']['total'] > 0  # nosec B101 - pytest regression assertion.
