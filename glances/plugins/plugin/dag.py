#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

# Glances DAG (direct acyclic graph) for plugins dependencies.
# It allows to define DAG dependencies between plugins
# For the moment, it will be used only for Restful API interface

_plugins_graph = {
    '*': ['alert'],  # All plugins depend on alert plugin
    'cpu': ['core'],
    'load': ['core'],
    'processlist': ['core', 'processcount'],
    'programlist': ['processcount'],
    'quicklook': ['fs', 'load'],
    'vms': ['processcount'],
}


def get_plugin_dependencies(plugin_name, _graph=_plugins_graph):
    """Return all transitive dependencies for a given plugin (including global ones)."""
    seen = set()

    def _resolve(plugin):
        if plugin in seen:
            return
        seen.add(plugin)

        # Get direct dependencies of this plugin
        deps = _graph.get(plugin, [])
        for dep in deps:
            _resolve(dep)

    # Resolve dependencies for this plugin
    _resolve(plugin_name)

    # Add global ("*") dependencies
    for dep in _graph.get('*', []):
        _resolve(dep)

    # Remove the plugin itself if present
    seen.discard(plugin_name)

    # Preserve order of discovery (optional, for deterministic results)
    result = []
    added = set()
    for dep in _graph.get(plugin_name, []) + _graph.get('*', []):
        for d in _dfs_order(dep, _graph, set()):
            if d not in added and d != plugin_name:
                result.append(d)
                added.add(d)
    return [plugin_name] + result


def _dfs_order(plugin, graph, seen):
    """Helper to preserve depth-first order."""
    if plugin in seen:
        return []
    seen.add(plugin)
    order = []
    for dep in graph.get(plugin, []):
        order.extend(_dfs_order(dep, graph, seen))
    order.append(plugin)
    return order
