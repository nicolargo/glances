'use strict';

function GlancesPluginPortsController($scope, GlancesStats) {
    var vm = this;
    vm.ports = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['ports'];

        vm.ports = [];
        angular.forEach(stats, function (port) {
            vm.ports.push(port);
        }, this);
    }

    vm.getDecoration = function (port) {
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
