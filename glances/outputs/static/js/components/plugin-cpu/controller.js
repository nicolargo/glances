'use strict';

function GlancesPluginCpuController() {
    var vm = this;
    var _view = {};

    vm.total = null;
    vm.user = null;
    vm.system = null;
    vm.idle = null;
    vm.nice = null;
    vm.irq = null;
    vm.iowait = null;
    vm.steal = null;
    vm.ctx_switches = null;
    vm.interrupts = null;
    vm.soft_interrupts = null;
    vm.syscalls = null;

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['cpu'];
        _view = stats.view['cpu'];

        vm.total = data.total;
        vm.user = data.user;
        vm.system = data.system;
        vm.idle = data.idle;
        vm.nice = data.nice;
        vm.irq = data.irq;
        vm.iowait = data.iowait;
        vm.steal = data.steal;

        if (data.ctx_switches) {
            vm.ctx_switches = Math.floor(data.ctx_switches / data.time_since_update);
        }

        if (data.interrupts) {
            vm.interrupts = Math.floor(data.interrupts / data.time_since_update);
        }

        if (data.soft_interrupts) {
            vm.soft_interrupts = Math.floor(data.soft_interrupts / data.time_since_update);
        }

        if (data.syscalls) {
            vm.syscalls = Math.floor(data.syscalls / data.time_since_update);
        }

        data = undefined;
    };

    this.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
