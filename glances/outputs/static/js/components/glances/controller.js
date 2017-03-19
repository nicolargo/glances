'use strict';

function GlancesController($interval, GlancesStats) {
    var vm = this;

    vm.sorter = {
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

    vm.dataLoaded = false;
    vm.stats = {};
    vm.refreshData = function () {
        GlancesStats.getData().then(function (data) {

            data.isBsd = data.stats['system']['os_name'] === 'FreeBSD';
            data.isLinux = data.stats['system']['os_name'] === 'Linux';
            data.isMac = data.stats['system']['os_name'] === 'Darwin';
            data.isWindows = data.stats['system']['os_name'] === 'Windows';

            vm.stats = data;
            vm.is_disconnected = false;
            vm.dataLoaded = true;
        }, function() {
            vm.is_disconnected = true;
        });
    };

    vm.refreshData();
    var refreshTime = 60; // arguments.time
    $interval(function () {
        vm.refreshData();
    }, refreshTime * 1000); // in milliseconds

    vm.onKeyDown = function ($event) {
        switch (true) {
            case !$event.shiftKey && $event.keyCode == keycodes.a:
                // a => Sort processes automatically
                vm.sorter.column = "cpu_percent";
                vm.sorter.auto = true;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.A:
                // A => Enable/disable AMPs
                vm.arguments.disable_amps = !vm.arguments.disable_amps;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.c:
                // c => Sort processes by CPU%
                vm.sorter.column = "cpu_percent";
                vm.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.m:
                // m => Sort processes by MEM%
                vm.sorter.column = "memory_percent";
                vm.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.u:
                // u => Sort processes by user
                vm.sorter.column = "username";
                vm.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.p:
                // p => Sort processes by name
                vm.sorter.column = "name";
                vm.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.i:
                // i => Sort processes by I/O rate
                vm.sorter.column = ['io_read', 'io_write'];
                vm.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.t:
                // t => Sort processes by time
                vm.sorter.column = "timemillis";
                vm.sorter.auto = false;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.d:
                // d => Show/hide disk I/O stats
                vm.arguments.disable_diskio = !vm.arguments.disable_diskio;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.Q:
                // Q => Show/hide IRQ
                vm.arguments.enable_irq = !vm.arguments.enable_irq;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.f:
                // f => Show/hide filesystem stats
                vm.arguments.disable_fs = !vm.arguments.disable_fs;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.n:
                // n => Show/hide network stats
                vm.arguments.disable_network = !vm.arguments.disable_network;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.s:
                // s => Show/hide sensors stats
                vm.arguments.disable_sensors = !vm.arguments.disable_sensors;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.TWO:
                // 2 => Show/hide left sidebar
                vm.arguments.disable_left_sidebar = !vm.arguments.disable_left_sidebar;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.z:
                // z => Enable/disable processes stats
                vm.arguments.disable_process = !vm.arguments.disable_process;
                break;
            case $event.keyCode == keycodes.SLASH:
                // SLASH => Enable/disable short processes name
                vm.arguments.process_short_name = !vm.arguments.process_short_name;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.D:
                // D => Enable/disable Docker stats
                vm.arguments.disable_docker = !vm.arguments.disable_docker;
                break;
            case !$event.shiftKey && $event.keyCode == keycodes.b:
                // b => Bytes or bits for network I/O
                vm.arguments.byte = !vm.arguments.byte;
               break;
            case $event.shiftKey && $event.keyCode == keycodes.b:
               // 'B' => Switch between bit/s and IO/s for Disk IO
                vm.arguments.diskio_iops = !vm.arguments.diskio_iops;
               break;
            case !$event.shiftKey && $event.keyCode == keycodes.l:
                // l => Show/hide alert logs
                vm.arguments.disable_alert = !vm.arguments.disable_alert;
               break;
            case $event.shiftKey && $event.keyCode == keycodes.ONE:
               // 1 => Global CPU or per-CPU stats
               vm.arguments.percpu = !vm.arguments.percpu;
               break;
            case !$event.shiftKey && $event.keyCode == keycodes.h:
                // h => Show/hide this help screen
                vm.arguments.help_tag = !vm.arguments.help_tag;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.T:
                // T => View network I/O as combination
                vm.arguments.network_sum = !vm.arguments.network_sum;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.u:
                // U => View cumulative network I/O
                vm.arguments.network_cumul = !vm.arguments.network_cumul;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.f:
                // F => Show filesystem free space
                vm.arguments.fs_free_space = !vm.arguments.fs_free_space;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.THREE:
                // 3 => Enable/disable quick look plugin
                vm.arguments.disable_quicklook = !vm.arguments.disable_quicklook;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.SIX:
                // 6 => Enable/disable mean gpu
                vm.arguments.meangpu = !vm.arguments.meangpu;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.g:
                // G => Enable/disable gpu
                vm.arguments.disable_gpu = !vm.arguments.disable_gpu;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.FIVE:
                vm.arguments.disable_quicklook = !vm.arguments.disable_quicklook;
                vm.arguments.disable_cpu = !vm.arguments.disable_cpu;
                vm.arguments.disable_mem = !vm.arguments.disable_mem;
                vm.arguments.disable_memswap = !vm.arguments.disable_memswap;
                vm.arguments.disable_load = !vm.arguments.disable_load;
                vm.arguments.disable_gpu = !vm.arguments.disable_gpu;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.i:
                // I => Show/hide IP module
                vm.arguments.disable_ip = !vm.arguments.disable_ip;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.p:
                // I => Enable/disable ports module
                vm.arguments.disable_ports = !vm.arguments.disable_ports;
                break;
            case $event.shiftKey && $event.keyCode == keycodes.w:
                // 'W' > Enable/Disable Wifi plugin
                vm.arguments.disable_wifi = !vm.arguments.disable_wifi;
                break;
        }
    };
}
