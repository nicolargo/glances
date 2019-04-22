
export default function GlancesPluginProcesslistController($scope, GlancesStats, GlancesPluginHelper, $filter, CONFIG, ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;
    vm.processes = [];
    vm.ioReadWritePresent = false;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var processlistStats = data.stats['processlist'] || [];

        vm.processes = [];
        vm.ioReadWritePresent = false;

        for (var i = 0; i < processlistStats.length; i++) {
            var process = processlistStats[i];

            process.memvirt = "?";
            process.memres = "?";
            if (process.memory_info) {
                process.memvirt = process.memory_info[1];
                process.memres = process.memory_info[0];
            }

            process.timeplus = "?";
            process.timemillis = "?";
            if (process.cpu_times) {
                process.timeplus = $filter('timedelta')(process.cpu_times);
                process.timemillis = $filter('timemillis')(process.cpu_times);
            }

            if (process.num_threads === null) {
              process.num_threads = -1;
            }

            if (process.cpu_percent === null) {
              process.cpu_percent = -1;
            }

            if (process.memory_percent  === null) {
              process.memory_percent = -1;
            }


            process.ioRead = null;
            process.ioWrite = null;

            if (process.io_counters) {
                vm.ioReadWritePresent = true;

                process.ioRead = (process.io_counters[0] - process.io_counters[2]) / process.time_since_update;

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

            if (process.cmdline === null) {
                process.cmdline = process.name;
            }

            if (data.isWindows && process.username !== null) {
                process.username = _.last(process.username.split('\\'));
            }
 
            vm.processes.push(process);
        }
    }

    vm.getCpuPercentAlert = function (process) {
        return GlancesPluginHelper.getAlert('processlist', 'processlist_cpu_', process.cpu_percent);
    };

    vm.getMemoryPercentAlert = function (process) {
        return GlancesPluginHelper.getAlert('processlist', 'processlist_mem_', process.cpu_percent);
    };

    vm.getLimit = function () {
        return CONFIG.outputs !== undefined ? CONFIG.outputs.max_processes_display : undefined;
    };
}
