"""The VM table's colours.

`msg_curse` in the vms plugin asks for a decoration on four columns, but no
field declared `alert`/`log` and `update_views` set none, so every one of those
reads returned 'DEFAULT': the VM table never changed colour, unlike the sibling
containers table. These pin the thresholds that make those reads mean something,
and the cases that must stay uncoloured.
"""

import pytest

from glances.plugins.vms import VmsPlugin


class _Args:
    def __getattr__(self, name):
        return False


LIMITS = {
    'vms_cpu_careful': 50,
    'vms_cpu_warning': 70,
    'vms_cpu_critical': 90,
    'vms_mem_careful': 20,
    'vms_mem_warning': 50,
    'vms_mem_critical': 70,
    'vms_load_careful': 70,
    'vms_load_warning': 100,
    'vms_load_critical': 500,
}


def vm(**overrides):
    stat = {
        'name': 'vm1',
        'id': '1',
        'status': 'running',
        'engine': 'virsh',
        'cpu_count': 2,
        'cpu_time_rate_per_sec': 5.0,
        'memory_usage': 100,
        'memory_total': 1000,
        'load_1min': 10.0,
    }
    stat.update(overrides)
    return stat


def build(stats, limits=LIMITS):
    plugin = VmsPlugin(args=_Args())
    plugin._limits = dict(limits)
    plugin.stats = stats
    plugin.update_views()
    return plugin


def decoration(plugin, name, field):
    return plugin.get_views(item=name, key=field, option='decoration')


@pytest.mark.parametrize(
    ('field', 'quiet', 'loud'),
    [
        ('cpu_time_rate_per_sec', 5.0, 95.0),
        ('memory_usage', 100, 950),
        ('load_1min', 10.0, 600.0),
    ],
)
def test_a_column_reaches_critical_from_its_own_threshold(field, quiet, loud):
    plugin = build([vm(name='quiet', **{field: quiet}), vm(name='loud', **{field: loud})])
    assert decoration(plugin, 'quiet', field) == 'OK'
    assert decoration(plugin, 'loud', field) == 'CRITICAL'


def test_memory_is_measured_against_that_vm_own_total():
    # The same byte count is fine in a large VM and critical in a small one, so
    # a test that only moved memory_usage would pass against a fixed maximum.
    plugin = build(
        [vm(name='big', memory_usage=500, memory_total=10000), vm(name='small', memory_usage=500, memory_total=600)]
    )
    assert decoration(plugin, 'big', 'memory_usage') == 'OK'
    assert decoration(plugin, 'small', 'memory_usage') == 'CRITICAL'


def test_a_missing_value_is_left_alone_rather_than_read_as_zero():
    # Engines that do not report load leave None; painting it OK would claim a
    # measurement that was never taken.
    plugin = build([vm(load_1min=None)])
    assert decoration(plugin, 'vm1', 'load_1min') == 'DEFAULT'


def test_a_vm_with_no_memory_total_does_not_divide_by_zero():
    plugin = build([vm(memory_total=0)])
    assert decoration(plugin, 'vm1', 'memory_usage') == 'DEFAULT'


def test_cpu_count_stays_uncoloured():
    # A core count is not a threshold, so it keeps the read msg_curse already
    # does and no colour.
    plugin = build([vm(cpu_count=64)])
    assert decoration(plugin, 'vm1', 'cpu_count') == 'DEFAULT'


def test_no_configured_thresholds_leaves_the_table_as_it_was():
    plugin = build([vm(cpu_time_rate_per_sec=99.0, memory_usage=999, load_1min=999.0)], limits={})
    for field in ('cpu_time_rate_per_sec', 'memory_usage', 'load_1min'):
        assert decoration(plugin, 'vm1', field) == 'DEFAULT'


def test_a_per_vm_override_wins_over_the_shared_threshold():
    # get_stat_name builds <plugin>_<action_key>_<header>, so the per-VM key
    # carries the plugin prefix too -- the conf line is `<vmname>_mem_careful`.
    limits = dict(LIMITS, vms_vm1_mem_careful=1, vms_vm1_mem_warning=2, vms_vm1_mem_critical=3)
    plugin = build(
        [vm(name='vm1', memory_usage=100, memory_total=1000), vm(name='vm2', memory_usage=100, memory_total=1000)]
    )
    plugin._limits = limits
    plugin.update_views()
    assert decoration(plugin, 'vm1', 'memory_usage') == 'CRITICAL'
    assert decoration(plugin, 'vm2', 'memory_usage') == 'OK'
