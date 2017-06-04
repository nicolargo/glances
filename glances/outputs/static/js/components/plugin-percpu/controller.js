'use strict';

function GlancesPluginPercpuController($scope, GlancesPluginHelper) {
    var vm = this;
    vm.cpus = [];

    $scope.$on('data_refreshed', function(event, data) {
      var percpuStats = data.stats['percpu'];

      vm.cpus = [];

      for (var i = 0; i < percpuStats.length; i++) {
          var cpuData = percpuStats[i];

          vm.cpus.push({
              'total': cpuData.total,
              'user': cpuData.user,
              'system': cpuData.system,
              'idle': cpuData.idle,
              'iowait': cpuData.iowait,
              'steal': cpuData.steal
          });
      }
    });

    vm.getUserAlert = function(cpu) {
        return GlancesPluginHelper.getAlert('percpu', 'percpu_user_', cpu.user)
    };

    vm.getSystemAlert = function(cpu) {
        return GlancesPluginHelper.getAlert('percpu', 'percpu_system_', cpu.system);
    };
}
