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
gl = api.GlancesAPI(args_begin_at=2)


# Pytest functions to test the Glances API version
def test_glances_api_version():
    assert gl.__version__ == __version__.split('.')[0]


def test_glances_api_plugins():
    # Check that the plugins list is not empty
    assert len(gl.plugins()) > 0
    # Check that the cpu plugin is in the list of plugins
    assert 'cpu' in gl.plugins()
    # Check that the network plugin is in the list of plugins
    assert 'network' in gl.plugins()
    # Check that the processcount plugin is in the list of plugins
    assert 'processcount' in gl.plugins()
    # Check that the processlist plugin is in the list of plugins
    assert 'processlist' in gl.plugins()


def test_glances_api_plugin_cpu():
    # Check that the cpu plugin is available
    assert gl.cpu is not None
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
    # Get list of keys (interfaces)
    keys = gl.network.keys()
    # Check that the keys are not empty
    assert len(keys) > 0
    # Check that the first item is a dictionary
    assert isinstance(gl.network[keys[0]], dict)


def test_glances_api_plugin_process():
    # Get list of keys (processes)
    keys = gl.processcount.keys()
    # Check that the keys are not empty
    assert len(keys) > 0
    # Check that processcount total is > 0
    assert gl.processcount['total'] > 0

    # Get list of keys (processes)
    keys = gl.processlist.keys()
    # Check that first key is an integer (PID)
    assert isinstance(keys[0], int)
    # Check that the first item is a dictionary
    assert isinstance(gl.processlist[keys[0]], dict)


def test_glances_api_limits():
    assert isinstance(gl.cpu.limits, dict)
