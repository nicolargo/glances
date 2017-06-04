'use strict';

function GlancesPluginProcesslistController($scope, GlancesPluginHelper, $filter, CONFIG, ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;

    vm.processes = [];
    vm.ioReadWritePresent = false;

    $scope.$on('data_refreshed', function(event, data) {
      var processlistStats = data.stats['processlist'];

      vm.processes = [];
      vm.ioReadWritePresent = false;

      for (var i = 0; i < processlistStats.length; i++) {
          var process = processlistStats[i];

          process.memvirt = process.memory_info[1];
          process.memres  = process.memory_info[0];
          process.timeplus = $filter('timedelta')(process.cpu_times);
          process.timemillis = $filter('timemillis')(process.cpu_times);

          process.ioRead = null;
          process.ioWrite = null;

          if (process.io_counters) {
              vm.ioReadWritePresent = true;

              process.ioRead  = (process.io_counters[0] - process.io_counters[2]) / process.time_since_update;

              if (process.ioRead != 0) {
                  process.ioRead = $filter('bytes')(process.ioRead);
              }

              process.ioWrite = (process.io_counters[1] - process.io_counters[3]) / process.time_since_update;

              if (process.ioWrite != 0) {
                  process.ioWrite = $filter('bytes')(process.ioWrite);
              }
          }

          process.isNice = process.nice !== undefined && ((data.stats.isWindows && process.nice != 32) || (!data.stats.isWindows && process.nice != 0));

          if (Array.isArray(process.cmdline)) {
              process.cmdline = process.cmdline.join(' ');
          }

          vm.processes.push(process);
      }
    });

    vm.getCpuPercentAlert = function(process) {
        return GlancesPluginHelper.getAlert('processlist', 'processlist_cpu_', process.cpu_percent);
    };

    vm.getMemoryPercentAlert = function(process) {
        return GlancesPluginHelper.getAlert('processlist', 'processlist_mem_', process.cpu_percent);
    };

    vm.getLimit = function() {
        return CONFIG.outputs !== undefined ? CONFIG.outputs.max_processes_display : undefined;
    };
}
