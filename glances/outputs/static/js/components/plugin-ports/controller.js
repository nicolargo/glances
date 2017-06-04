'use strict';

function GlancesPluginPortsController($scope) {
    var vm = this;

    vm.ports = [];

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['ports'];

      vm.ports = [];
      angular.forEach(stats, function(port) {
          vm.ports.push(port);
      }, this);
    });

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
