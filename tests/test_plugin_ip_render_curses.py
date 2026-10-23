#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the ip curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer import ColorRole
from glances.plugins.ip.render_curses import render


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_returns_nothing():
    assert render({}) == []
    assert render({"address": None}) == []


def test_private_only():
    rows = render({"address": "192.168.1.10", "mask_cidr": 24})
    flat = _flat(rows)
    assert "IP" in flat
    assert "192.168.1.10/24" in flat
    assert len(rows) == 1


def test_private_no_cidr():
    # issue #842 — VPN/no-internet: mask_cidr present as 0, must still render.
    rows = render({"address": "10.0.0.2", "mask_cidr": 0})
    flat = _flat(rows)
    assert "10.0.0.2/0" in flat


def test_with_public():
    rows = render({"address": "192.168.1.10", "mask_cidr": 24, "public_address": "1.2.3.4"})
    flat = _flat(rows)
    assert "Pub" in flat
    assert "1.2.3.4" in flat


def test_with_public_info_human():
    rows = render(
        {
            "address": "192.168.1.10",
            "mask_cidr": 24,
            "public_address": "1.2.3.4",
            "public_info_human": "Wonderland",
        }
    )
    flat = _flat(rows)
    assert "Wonderland" in flat


def test_hide_ip_location_drops_only_the_geolocation():
    """Header cascade step 1: the geolocation string goes, both addresses stay."""
    payload = {
        "address": "192.168.1.10",
        "mask_cidr": 24,
        "public_address": "1.2.3.4",
        "public_info_human": "Wonderland",
    }
    flat = _flat(render(payload, None, view={"hide_ip_location": True}))
    assert "Wonderland" not in flat
    assert "192.168.1.10/24" in flat
    assert "1.2.3.4" in flat


def test_hide_ip_location_is_independent_of_hide_public_info():
    """`hide_ip_location` (header degradation) drops the geolocation string
    alone; `--hide-public-info` masks the public address octets AND drops the
    geolocation string, which is rendered from the same document and repeats
    the address with a `{ip}` template (GHSA-vg43-q6xr-hp92)."""
    payload = {
        "address": "192.168.1.10",
        "mask_cidr": 24,
        "public_address": "1.2.3.4",
        "public_info_human": "Wonderland",
    }
    located = _flat(render(payload, None, view={"hide_ip_location": True}))
    assert "1.2.3.4" in located
    assert "Wonderland" not in located

    masked = _flat(render(payload, None, view={"hide_public_info": True}))
    assert "1.2.*.*" in masked
    assert "Wonderland" not in masked

    both = _flat(render(payload, None, view={"hide_public_info": True, "hide_ip_location": True}))
    assert "1.2.*.*" in both
    assert "Wonderland" not in both


def test_public_absent_no_pub_segment():
    rows = render({"address": "192.168.1.10", "mask_cidr": 24})
    flat = _flat(rows)
    assert "Pub" not in flat


def test_hide_public_info_masks():
    rows = render(
        {"address": "192.168.1.10", "mask_cidr": 24, "public_address": "1.2.3.4"},
        None,
        view={"hide_public_info": True},
    )
    flat = _flat(rows)
    assert "1.2.*.*" in flat
    assert "1.2.3.4" not in flat


def test_hide_public_info_off_shows_full():
    rows = render(
        {"address": "192.168.1.10", "mask_cidr": 24, "public_address": "1.2.3.4"},
        None,
        view={},
    )
    flat = _flat(rows)
    assert "1.2.3.4" in flat


def test_header_cells_coloured():
    rows = render({"address": "192.168.1.10", "mask_cidr": 24, "public_address": "1.2.3.4"})
    header_cells = [c for r in rows for c in r.cells if c.text in ("IP", "Pub")]
    assert header_cells
    assert all(c.color == ColorRole.HEADER for c in header_cells)
