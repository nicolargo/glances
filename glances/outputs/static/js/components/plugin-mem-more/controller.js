'use strict';

function GlancesPluginMemMoreController($scope) {
    var vm = this;

    vm.active = null;
    vm.inactive = null;
    vm.buffers = null;
    vm.cached = null;

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['mem'];

      vm.active = stats['active'];
      vm.inactive = stats['inactive'];
      vm.buffers = stats['buffers'];
      vm.cached = stats['cached'];
    });
}
