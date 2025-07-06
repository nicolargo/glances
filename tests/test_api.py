#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances API unitary tests suite."""

from glances import __version__, api

# Global variables
# =================

# Init Glances API
# test_config = core.get_config()
# test_args = core.get_args()
gl = api.GlancesAPI()


# Pytest functions to test the Glances API version
def test_glances_api_version():
    assert gl.__version__ == __version__.split('.')[0]


def test_glances_api_plugin_cpu():
    # Check that the cpu plugin is available
    assert gl.cpu is not None
    # Update stats
    gl.cpu.update()
    # Get list of keys (cpu stat fields)
    keys = gl.cpu.keys()
    # Check that the keys are not empty
    assert len(keys) > 0
    # Check that the cpu plugin has a total item
    assert gl.cpu['total'] is not None
    # and is a float
    assert isinstance(gl.cpu['total'], float)
    # test the get method
    assert isinstance(gl.cpu.get('total'), float)


def test_glances_api_plugin_network():
    # Check that the network plugin is available
    assert gl.network is not None
    # Update stats
    gl.network.update()
    # Get list of keys (interfaces)
    keys = gl.network.keys()
    # Check that the keys are not empty
    assert len(keys) > 0
    # Check that the first item is a dictionary
    assert isinstance(gl.network[keys[0]], dict)


def test_glances_api_plugin_process():
    gl.processcount.update()
    # Get list of keys (processes)
    keys = gl.processcount.keys()
    # Check that the keys are not empty
    assert len(keys) > 0
    # Check that processcount total is > 0
    assert gl.processcount['total'] > 0

    # Note should be done after processcount update
    gl.processlist.update()
    # Get list of keys (processes)
    keys = gl.processlist.keys()
    # Check that first key is an integer (PID)
    assert isinstance(keys[0], int)
    # Check that the first item is a dictionary
    assert isinstance(gl.processlist[keys[0]], dict)
