'use strict';

function GlancesPluginDockerController($scope) {
    var vm = this;
    vm.containers = [];
    vm.version = null;

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['docker'];
      this.containers = [];

      if(_.isEmpty(stats)) {
          return;
      }

      for (var i = 0; i < stats['containers'].length; i++) {
          var containerData = stats['containers'][i];

          var container = {
              'id': containerData.Id,
              'name': containerData.Names[0].split('/').splice(-1)[0],
              'status': containerData.Status,
              'cpu': containerData.cpu.total,
              'memory': containerData.memory.usage != undefined ? containerData.memory.usage : '?',
              'ior': containerData.io.ior != undefined ? containerData.io.ior : '?',
              'iow': containerData.io.iow != undefined ? containerData.io.iow : '?',
              'io_time_since_update': containerData.io.time_since_update,
              'rx': containerData.network.rx != undefined ? containerData.network.rx : '?',
              'tx': containerData.network.tx != undefined ? containerData.network.tx : '?',
              'net_time_since_update': containerData.network.time_since_update,
              'command': containerData.Command,
              'image': containerData.Image
          };

          vm.containers.push(container);
      }

      vm.version = stats['version']['Version'];
    });
}
