'use strict';

function GlancesPluginCloudController($scope) {
    var vm = this;

    vm.provider = null;
    vm.instance = null;

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['cloud'];

      if (stats['ami-id'] !== undefined) {
          vm.provider = 'AWS EC2';
          vm.instance =  stats['instance-type'] + ' instance ' + stats['instance-id'] + ' (' + stats['region'] + ')';
      }
    });
}
