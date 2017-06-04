'use strict';

function GlancesPluginIpController($scope, ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;

    vm.address = null;
    vm.gateway = null;
    vm.mask = null;
    vm.maskCidr = null;
    vm.publicAddress = null;

    $scope.$on('data_refreshed', function(event, data) {
      var ipStats = data.stats['ip'];

      vm.address = ipStats.address;
      vm.gateway = ipStats.gateway;
      vm.mask = ipStats.mask;
      vm.maskCidr = ipStats.mask_cidr;
      vm.publicAddress = ipStats.public_address
    });
}
