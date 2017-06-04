'use strict';

function GlancesPluginUptimeController($scope) {
    var vm = this;
    vm.value = null;

    $scope.$on('data_refreshed', function(event, data) {
      vm.value = data.stats['uptime'];
    });
}
