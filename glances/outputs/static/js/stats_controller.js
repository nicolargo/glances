glancesApp.controller('statsController', function ($scope, $rootScope, $interval, GlancesStats, help, arguments) {
    $scope.help = help;
    $scope.arguments = arguments;

    $scope.sorter = {
        column: "cpu_percent",
        auto: true,
        isReverseColumn: function (column) {
            return !(column == 'username' || column == 'name');
        },
        getColumnLabel: function (column) {
            if (_.isEqual(column, ['io_read', 'io_write'])) {
                return 'io_counters';
            } else {
                return column;
            }
        }
    };

    $scope.dataLoaded = false;
    $scope.refreshData = function () {
        GlancesStats.getData().then(function (data) {

            $scope.statsAlert = GlancesStats.getPlugin('alert');
            $scope.statsCpu = GlancesStats.getPlugin('cpu');
            $scope.statsDiskio = GlancesStats.getPlugin('diskio');
            $scope.statsDocker = GlancesStats.getPlugin('docker');
            $scope.statsFs = GlancesStats.getPlugin('fs');
            $scope.statsIp = GlancesStats.getPlugin('ip');
            $scope.statsLoad = GlancesStats.getPlugin('load');
            $scope.statsMem = GlancesStats.getPlugin('mem');
            $scope.statsMemSwap = GlancesStats.getPlugin('memswap');
            $scope.statsMonitor = GlancesStats.getPlugin('monitor');
            $scope.statsNetwork = GlancesStats.getPlugin('network');
            $scope.statsPerCpu = GlancesStats.getPlugin('percpu');
            $scope.statsProcessCount = GlancesStats.getPlugin('processcount');
            $scope.statsProcessList = GlancesStats.getPlugin('processlist');
            $scope.statsQuicklook = GlancesStats.getPlugin('quicklook');
            $scope.statsRaid = GlancesStats.getPlugin('raid');
            $scope.statsSensors = GlancesStats.getPlugin('sensors');
            $scope.statsSystem = GlancesStats.getPlugin('system');
            $scope.statsUptime = GlancesStats.getPlugin('uptime');

            $rootScope.title = $scope.statsSystem.hostname + ' - Glances';

            $scope.is_disconnected = false;
            $scope.dataLoaded = true;
        }, function() {
            $scope.is_disconnected = true;
        });
    };

    $scope.refreshData();
    $interval(function () {
        $scope.refreshData();
    }, arguments.time * 1000); // in milliseconds

    $scope.onKeyDown = function ($event) {

        switch (true) {
            case !$event.shiftKey && $event.keyCode == keycodes.a:
                // a => Sort processes automatically
                $scope.sorter.column = "cpu_percent";
                $scope.sorter.auto = true;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.c:
                // c => Sort processes by CPU%
                $scope.sorter.column = "cpu_percent";
                $scope.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.m:
                // m => Sort processes by MEM%
                $scope.sorter.column = "memory_percent";
                $scope.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.u:
                // u => Sort processes by user
                $scope.sorter.column = "username";
                $scope.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.p:
                // p => Sort processes by name
                $scope.sorter.column = "name";
                $scope.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.i:
                // i => Sort processes by I/O rate
                $scope.sorter.column = ['io_read', 'io_write'];
                $scope.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.t:
                // t => Sort processes by time
                $scope.sorter.column = "timemillis";
                $scope.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.d:
                // d => Show/hide disk I/O stats
                $scope.arguments.disable_diskio = !$scope.arguments.disable_diskio;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.f:
                // f => Show/hide filesystem stats
                $scope.arguments.disable_fs = !$scope.arguments.disable_fs;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.n:
                // n => Show/hide network stats
                $scope.arguments.disable_network = !$scope.arguments.disable_network;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.s:
                // s => Show/hide sensors stats
                $scope.arguments.disable_sensors = !$scope.arguments.disable_sensors;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.TWO:
                // 2 => Show/hide left sidebar
                $scope.arguments.disable_left_sidebar = !$scope.arguments.disable_left_sidebar;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.z:
                // z => Enable/disable processes stats
                $scope.arguments.disable_process = !$scope.arguments.disable_process;
                break;
            case $event.keyCode == keycodes.SLASH:
                // SLASH => Enable/disable short processes name
                $scope.arguments.process_short_name = !$scope.arguments.process_short_name;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.D:
                // D => Enable/disable Docker stats
                $scope.arguments.disable_docker = !$scope.arguments.disable_docker;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.b:
                // b => Bytes or bits for network I/O
                $scope.arguments.byte = !$scope.arguments.byte;
               break;
            case $event.shiftKey && $event.keyCode == keycodes.b:
               // 'B' => Switch between bit/s and IO/s for Disk IO
                $scope.arguments.diskio_iops = !$scope.arguments.diskio_iops;
               break;
            case !$event.shiftKey && $event.keyCode == keycodes.l:
                // l => Show/hide alert logs
                $scope.arguments.disable_log = !$scope.arguments.disable_log;
               break;
            case $event.shiftKey && $event.keyCode == keycodes.ONE:
               // 1 => Global CPU or per-CPU stats
               $scope.arguments.percpu = !$scope.arguments.percpu;
               break;
            case !$event.shiftKey && $event.keyCode == keycodes.h:
                // h => Show/hide this help screen
                $scope.arguments.help_tag = !$scope.arguments.help_tag;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.T:
                // T => View network I/O as combination
                $scope.arguments.network_sum = !$scope.arguments.network_sum;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.u:
                // U => View cumulative network I/O
                $scope.arguments.network_cumul = !$scope.arguments.network_cumul;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.f:
                // F => Show filesystem free space
                $scope.arguments.fs_free_space = !$scope.arguments.fs_free_space;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.THREE:
                // 3 => Enable/disable quick look plugin
                $scope.arguments.disable_quicklook = !$scope.arguments.disable_quicklook;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.FIVE:
                $scope.arguments.disable_quicklook = !$scope.arguments.disable_quicklook;
                $scope.arguments.disable_cpu = !$scope.arguments.disable_cpu;
                $scope.arguments.disable_mem = !$scope.arguments.disable_mem;
                $scope.arguments.disable_swap = !$scope.arguments.disable_swap;
                $scope.arguments.disable_load = !$scope.arguments.disable_load;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.i:
                // I => Show/hide IP module
                $scope.arguments.disable_ip = !$scope.arguments.disable_ip;
                break;
        }
    };
});
