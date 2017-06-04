'use strict';

function GlancesPluginSystemController($scope) {
    var vm = this;

    vm.hostname = null;
    vm.platform = null;
    vm.humanReadableName = null;
    vm.os = {
        'name': null,
        'version': null
    };

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['system'];

      vm.hostname = stats['hostname'];
      vm.platform = stats['platform'];
      vm.os.name = stats['os_name'];
      vm.os.version = stats['os_version'];
      vm.humanReadableName = stats['hr_name'];
      vm.isDisconnected = false;
    });

    $scope.$on('is_disconnected', function() {
      vm.isDisconnected = true;
    });
}
