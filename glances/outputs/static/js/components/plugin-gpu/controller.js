'use strict';

function GlancesPluginGpuController($scope, ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;
    var _view = {};
    vm.gpus = [];
    vm.name = "GPU";
    vm.mean = {};

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['gpu'];
      _view = data.views['gpu'];

      if (stats.length === 0) {
          return;
      }

      vm.gpus = [];
      vm.name = "GPU";
      vm.mean = {
          proc: null,
          mem: null
      };
      var sameName = true;

      for (var i = 0; i < stats.length; i++) {
          var gpuData = stats[i];

          var gpu = gpuData;

          vm.mean.proc += gpu.proc;
          vm.mean.mem += gpu.mem;

          vm.gpus.push(gpu);
      }

      if (stats.length === 1 ) {
          vm.name = stats[0].name;
      } else if (sameName) {
          vm.name = stats.length + ' GPU ' + stats[0].name;
      }

      vm.mean.proc = vm.mean.proc / stats.length;
      vm.mean.mem = vm.mean.mem / stats.length;
    });

    vm.getDecoration = function(gpuId, value) {
        if(_view[gpuId][value] == undefined) {
            return;
        }

        return _view[gpuId][value].decoration.toLowerCase();
    };

    vm.getMeanDecoration = function(value) {
        return vm.getDecoration(0, value);
    };
}
