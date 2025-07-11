#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Multipass Extension unit for Glances' Vms plugin."""

import json
import os
from functools import cache
from typing import Any

from glances.globals import json_loads, nativestr
from glances.plugins.vms.engines import VmsExtension
from glances.secure import secure_popen

# Check if multipass binary exist
# TODO: make this path configurable from the Glances configuration file
MULTIPASS_PATH = '/snap/bin/multipass'
MULTIPASS_VERSION_OPTIONS = 'version --format json'
MULTIPASS_INFO_OPTIONS = 'info --format json'
import_multipass_error_tag = not os.path.exists(MULTIPASS_PATH) or not os.access(MULTIPASS_PATH, os.X_OK)


class VmExtension(VmsExtension):
    """Glances' Vms Plugin's Vm Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['running']

    def __init__(self):
        self.ext_name = "Multipass (Vm)"

    @cache
    def update_version(self):
        # > multipass version --format json
        # {
        #     "multipass": "1.13.1",
        #     "multipassd": "1.13.1"
        # }
        ret_cmd = secure_popen(f'{MULTIPASS_PATH} {MULTIPASS_VERSION_OPTIONS}')
        try:
            ret = json_loads(ret_cmd)
        except json.JSONDecodeError:
            return ''
        else:
            return ret.get('multipass', None)

    def update_info(self):
        ret_cmd = secure_popen(f'{MULTIPASS_PATH} {MULTIPASS_INFO_OPTIONS}')
        try:
            ret = json_loads(ret_cmd)
        except json.JSONDecodeError:
            return {}
        else:
            return ret.get('info', {})

    def update(self, all_tag) -> tuple[str, list[dict]]:
        """Update Vm stats using the input method."""
        # Can not run multipass on this system then...
        if import_multipass_error_tag:
            return '', []

        # Get the stats from the system
        version_stats = self.update_version()
        info_stats = self.update_info()
        returned_stats = []
        for k, v in info_stats.items():
            # Only display when VM in on 'running' states
            # See states list here: https://multipass.run/docs/instance-states
            if all_tag or self._want_display(v, 'state', ['Running', 'Starting', 'Restarting']):
                returned_stats.append(self.generate_stats(k, v))

        return version_stats, returned_stats

    @property
    def key(self) -> str:
        """Return the key of the list."""
        return 'name'

    def _want_display(self, vm_stats, key, values):
        return vm_stats.get(key).lower() in [v.lower() for v in values]

    def generate_stats(self, vm_name, vm_stats) -> dict[str, Any]:
        # Init the stats for the current vm
        return {
            'key': self.key,
            'name': nativestr(vm_name),
            'id': vm_stats.get('image_hash'),
            'status': vm_stats.get('state').lower() if vm_stats.get('state') else None,
            'release': vm_stats.get('release') if vm_stats.get('release') else vm_stats.get('image_release'),
            'cpu_count': int(vm_stats.get('cpu_count', 1)) if vm_stats.get('cpu_count', 1) else None,
            'cpu_time': None,  # Not available through the multipass CLI
            'memory_usage': vm_stats.get('memory').get('used') if vm_stats.get('memory') else None,
            'memory_total': vm_stats.get('memory').get('total') if vm_stats.get('memory') else None,
            'load_1min': vm_stats.get('load')[0] if vm_stats.get('load') else None,
            'load_5min': vm_stats.get('load')[1] if vm_stats.get('load') else None,
            'load_15min': vm_stats.get('load')[2] if vm_stats.get('load') else None,
            'ipv4': vm_stats.get('ipv4')[0] if vm_stats.get('ipv4') else None,
            # TODO: disk
        }
