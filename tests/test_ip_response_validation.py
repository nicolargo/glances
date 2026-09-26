# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""Public IP responses must not replace the shared dictionary with scalars."""

import io
import json

import pytest

from glances.plugins import ip


@pytest.mark.parametrize('payload', [False, True, 42, 'error', [], ['error'], None])
def test_invalid_response_preserves_last_public_info(monkeypatch, payload):
    worker = ip.ThreadPublicIpAddress('https://example.test/ip', None, None, 300)
    worker._public_info = {'ip': '192.0.2.1'}
    monkeypatch.setattr(ip, 'urlopen', lambda *args, **kwargs: io.BytesIO(json.dumps(payload).encode()))
    monkeypatch.setattr(worker._stopper, 'wait', lambda timeout: worker.stop())

    worker.run()

    assert worker.public_info == {'ip': '192.0.2.1'}


def test_valid_response_updates_public_info(monkeypatch):
    worker = ip.ThreadPublicIpAddress('https://example.test/ip', None, None, 300)
    monkeypatch.setattr(ip, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'{"ip":"192.0.2.2"}'))
    monkeypatch.setattr(worker._stopper, 'wait', lambda timeout: worker.stop())

    worker.run()

    assert worker.public_info == {'ip': '192.0.2.2'}
