'use strict';

function GlancesPluginPortsController() {
    var vm = this;

    vm.ports = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['ports'];

        vm.ports = [];
        angular.forEach(data, function(port) {
            vm.ports.push(port);
        }, this);

        data = undefined;
    };

    vm.getDecoration = function(port) {
        if (port.status === null) {
            return 'careful';
        }

        if (port.status === false) {
            return 'critical';
        }

        if (port.rtt_warning !== null && port.status > port.rtt_warning) {
            return 'warning';
        }

        return 'ok';
    };
}
