'use strict';

function GlancesPluginProcesscountController() {
    var vm = this;

    vm.total  = null;
    vm.running = null;
    vm.sleeping = null;
    vm.stopped = null;
    vm.thread = null;

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['processcount'];

        vm.total = data['total'] || 0;
        vm.running = data['running'] || 0;
        vm.sleeping = data['sleeping'] || 0;
        vm.stopped = data['stopped'] || 0;
        vm.thread = data['thread'] || 0;

        data = undefined;
    };
}
