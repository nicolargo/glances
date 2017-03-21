'use strict';

function GlancesPluginQuicklookController() {
    var vm = this;
    var _view = {};

    vm.mem = null;
    vm.cpu = null;
    vm.cpu_name = null;
    vm.cpu_hz_current = null;
    vm.cpu_hz = null;
    vm.swap = null;
    vm.percpus = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['quicklook'];
        _view = stats.view['quicklook'];

        vm.mem = data.mem;
        vm.cpu = data.cpu;
        vm.cpu_name = data.cpu_name;
        vm.cpu_hz_current = data.cpu_hz_current;
        vm.cpu_hz = data.cpu_hz;
        vm.swap = data.swap;
        vm.percpus = [];

        angular.forEach(data.percpu, function(cpu) {
            vm.percpus.push({
                'number': cpu.cpu_number,
                'total': cpu.total
            });
        }, this);

        data = undefined;
    };

    this.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
