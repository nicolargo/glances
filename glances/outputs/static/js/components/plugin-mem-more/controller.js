'use strict';

function GlancesPluginMemMoreController() {
    var vm = this;

    vm.active = null;
    vm.inactive = null;
    vm.buffers = null;
    vm.cached = null;

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['mem'];

        vm.active = data['active'];
        vm.inactive = data['inactive'];
        vm.buffers = data['buffers'];
        vm.cached = data['cached'];

        data = undefined;
    };
}
