#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the IRQ plugin."""

from glances.plugins import irq


def test_irq_rate_is_per_second(tmp_path, monkeypatch):
    interrupts = tmp_path / 'interrupts'
    monkeypatch.setattr(irq.GlancesIRQ, 'IRQ_FILE', str(interrupts))
    monkeypatch.setattr(irq, 'getTimeSinceLastUpdate', lambda key: 2)
    grabber = irq.GlancesIRQ()

    interrupts.write_text('CPU0 CPU1\nLOC: 1000 1000 Local timer interrupts\n')
    grabber.get()
    interrupts.write_text('CPU0 CPU1\nLOC: 1100 1100 Local timer interrupts\n')

    assert grabber.get()[0]['irq_rate'] == 100  # nosec B101
