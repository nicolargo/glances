#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Virsh (QEMU/KVM) Extension unit for Glances' Vms plugin."""

import os
import re
from functools import cache
from typing import Any

from glances.globals import nativestr
from glances.plugins.vms.engines import VmsExtension
from glances.secure import secure_popen

# Check if virsh binary exist
# TODO: make this path configurable from the Glances configuration file
VIRSH_PATH = '/usr/bin/virsh'
VIRSH_VERSION_OPTIONS = 'version'
VIRSH_INFO_OPTIONS = 'list --all'
VIRSH_DOMAIN_STATS_OPTIONS = 'domstats'
VIRSH_DOMAIN_TITLE_OPTIONS = 'desc --title'
import_virsh_error_tag = not os.path.exists(VIRSH_PATH) or not os.access(VIRSH_PATH, os.X_OK)


class VmExtension(VmsExtension):
    """Glances' Virsh Plugin's Vm Extension unit"""

    CONTAINER_ACTIVE_STATUS = ['running']

    def __init__(self):
        self.ext_name = "Virsh (Vm)"

    @cache
    def update_version(self):
        # > virsh version
        # Compiled against library: libvirt 10.0.0
        # Using library: libvirt 10.0.0
        # Using API: QEMU 10.0.0
        # Running hypervisor: QEMU 8.2.2
        ret_cmd = secure_popen(f'{VIRSH_PATH} {VIRSH_VERSION_OPTIONS}')
        try:
            ret = ret_cmd.splitlines()[3].split(':')[1].lstrip()
        except IndexError:
            return ''
        return ret

    def update_domains(self):
        # ❯ virsh list --all
        #  Id   Name              State
        # ----------------------------------
        #  4    win11             paused
        #  -    Kali_Linux_2024   shut off
        ret_cmd = secure_popen(f'{VIRSH_PATH} {VIRSH_INFO_OPTIONS}')

        try:
            # Ignore first two lines (header) and the last one (empty)
            lines = ret_cmd.splitlines()[2:-1]
        except IndexError:
            return {}

        ret = {}
        for line in lines:
            domain = re.split(r'\s{2,}', line)
            ret[domain[1]] = {
                'id': domain[0],
                'state': domain[2],
            }

        return ret

    def update_stats(self, domain):
        # ❯ virsh domstats win11
        # Domain: 'win11'
        #   state.state=1
        #   state.reason=1
        #   cpu.time=1702145606000
        #   cpu.user=1329954143000
        #   cpu.system=372191462000
        #   cpu.cache.monitor.count=0
        #   cpu.haltpoll.success.time=60243506159
        #   cpu.haltpoll.fail.time=34398762096
        #   balloon.current=8388608
        #   balloon.maximum=8388608
        #   balloon.last-update=0
        #   balloon.rss=8439116
        #   vcpu.current=4
        #   vcpu.maximum=4
        #   vcpu.0.state=1
        #   vcpu.0.time=955260000000
        #   vcpu.0.wait=0
        #   vcpu.0.delay=1305744538
        #   vcpu.0.halt_wakeup.sum=701415
        #   vcpu.0.halt_successful_poll.sum=457799
        #   vcpu.0.pf_mmio_spte_created.sum=38376
        #   vcpu.0.pf_emulate.sum=38873
        #   vcpu.0.fpu_reload.sum=8252258
        #   vcpu.0.insn_emulation.sum=6544119
        #   vcpu.0.signal_exits.sum=144
        #   vcpu.0.invlpg.sum=0
        #   vcpu.0.request_irq_exits.sum=0
        #   vcpu.0.preemption_reported.sum=25322
        #   vcpu.0.l1d_flush.sum=0
        #   vcpu.0.guest_mode.cur=no
        #   vcpu.0.halt_poll_fail_ns.sum=8369146975
        #   vcpu.0.pf_taken.sum=11455007
        #   vcpu.0.notify_window_exits.sum=0
        #   vcpu.0.directed_yield_successful.sum=0
        #   vcpu.0.host_state_reload.sum=8982225
        #   vcpu.0.nested_run.sum=0
        #   vcpu.0.nmi_injections.sum=1
        #   vcpu.0.pf_spurious.sum=7
        #   vcpu.0.halt_exits.sum=1173865
        #   vcpu.0.exits.sum=28094008
        #   vcpu.0.mmio_exits.sum=6536664
        #   vcpu.0.pf_fixed.sum=11410566
        #   vcpu.0.insn_emulation_fail.sum=0
        #   vcpu.0.io_exits.sum=1723037
        #   vcpu.0.halt_attempted_poll.sum=610576
        #   vcpu.0.req_event.sum=3245967
        #   vcpu.0.irq_exits.sum=1265655
        #   vcpu.0.blocking.cur=yes
        #   vcpu.0.irq_injections.sum=594
        #   vcpu.0.preemption_other.sum=11312
        #   vcpu.0.pf_fast.sum=5377009
        #   vcpu.0.hypercalls.sum=4799
        #   vcpu.0.nmi_window_exits.sum=0
        #   vcpu.0.directed_yield_attempted.sum=0
        #   vcpu.0.tlb_flush.sum=286197
        #   vcpu.0.halt_wait_ns.sum=872563463627
        #   vcpu.0.irq_window_exits.sum=0
        #   vcpu.0.pf_guest.sum=0
        #   vcpu.0.halt_poll_success_ns.sum=13527499051
        #   vcpu.0.halt_poll_invalid.sum=0
        #   vcpu.1...
        #   net.count=1
        #   net.0.name=vnet3
        #   net.0.rx.bytes=418454563
        #   net.0.rx.pkts=291468
        #   net.0.rx.errs=0
        #   net.0.rx.drop=7
        #   net.0.tx.bytes=3884562
        #   net.0.tx.pkts=35405
        #   net.0.tx.errs=0
        #   net.0.tx.drop=0
        #   block.count=2
        #   block.0.name=sda
        #   block.0.path=/var/lib/libvirt/images/win11.qcow2
        #   block.0.backingIndex=2
        #   block.0.rd.reqs=246802
        #   block.0.rd.bytes=18509028864
        #   block.0.rd.times=83676206416
        #   block.0.wr.reqs=471370
        #   block.0.wr.bytes=28260229120
        #   block.0.wr.times=158585666809
        #   block.0.fl.reqs=46269
        #   block.0.fl.times=181262854634
        #   block.0.allocation=137460187136
        #   block.0.capacity=137438953472
        #   block.0.physical=13457760256
        #   block.1...
        #   dirtyrate.calc_status=0
        #   dirtyrate.calc_start_time=0
        #   dirtyrate.calc_period=0
        #   dirtyrate.calc_mode=page-sampling
        #   vm.remote_tlb_flush.sum=436456
        #   vm.nx_lpage_splits.cur=0
        #   vm.pages_1g.cur=0
        #   vm.pages_2m.cur=859
        #   vm.pages_4k.cur=1196897
        #   vm.max_mmu_page_hash_collisions.max=0
        #   vm.mmu_pde_zapped.sum=0
        #   vm.max_mmu_rmap_size.max=0
        #   vm.mmu_cache_miss.sum=0
        #   vm.mmu_recycled.sum=0
        #   vm.mmu_unsync.cur=0
        #   vm.mmu_shadow_zapped.sum=0
        #   vm.mmu_flooded.sum=0
        #   vm.mmu_pte_write.sum=0
        #   vm.remote_tlb_flush_requests.sum=609455
        ret_cmd = secure_popen(f'{VIRSH_PATH} {VIRSH_DOMAIN_STATS_OPTIONS} {domain}')

        try:
            # Ignore first line (domain name already know) and last line (empty)
            lines = ret_cmd.splitlines()[1:-1]
        except IndexError:
            return {}

        ret = {}
        for line in lines:
            k, v = re.split(r'\s*=\s*', line.lstrip())
            ret[k] = v

        return ret

    @cache
    def update_title(self, domain):
        # ❯ virsh desc --title Kali_Linux_2024
        # Kali Linux 2024
        ret_cmd = secure_popen(f'{VIRSH_PATH} {VIRSH_DOMAIN_TITLE_OPTIONS} {domain}')

        return ret_cmd.rstrip()

    def update(self, all_tag) -> tuple[dict, list[dict]]:
        """Update Vm stats using the input method."""
        # Can not run virsh on this system then...
        if import_virsh_error_tag:
            return '', []

        # Update VM stats
        version_stats = self.update_version()
        domains_stats = self.update_domains()
        returned_stats = []
        for k, v in domains_stats.items():
            # Only display when VM in on 'running' and 'paused' states
            # Why paused ? Because a paused VM consume memory
            if all_tag or self._want_display(v, 'state', ['running', 'paused']):
                returned_stats.append(self.generate_stats(k, v))

        return version_stats, returned_stats

    @property
    def key(self) -> str:
        """Return the key of the list."""
        return 'name'

    def _want_display(self, domain_stats, key, values):
        return domain_stats.get(key).lower() in [v.lower() for v in values]

    def generate_stats(self, domain_name, domain_stats) -> dict[str, Any]:
        # Update stats and title for the domain
        vm_stats = self.update_stats(domain_name)
        vm_title = self.update_title(domain_name)

        return {
            'key': self.key,
            'name': nativestr(domain_name),
            'id': domain_stats.get('id'),
            'status': domain_stats.get('state').lower() if domain_stats.get('state') else None,
            'release': nativestr(vm_title),
            'cpu_count': int(vm_stats.get('vcpu.current', 1)) if vm_stats.get('vcpu.current', 1) else None,
            'cpu_time': int(vm_stats.get('cpu.time', 0)) / 1000000000 * 100,
            'memory_usage': int(vm_stats.get('balloon.rss')) * 1024 if vm_stats.get('balloon.rss') else None,
            'memory_total': int(vm_stats.get('balloon.maximum')) * 1024 if vm_stats.get('balloon.maximum') else None,
            'load_1min': None,
            'load_5min': None,
            'load_15min': None,
            'ipv4': None,
            # TODO: disk
        }
