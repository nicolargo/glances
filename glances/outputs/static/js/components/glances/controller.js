
export default function GlancesController($scope, GlancesStats, hotkeys, ARGUMENTS) {
    var vm = this;
    vm.dataLoaded = false;
    vm.arguments = ARGUMENTS;

    vm.$onInit = function () {
        GlancesStats.init(vm.refreshTime);
    };

    $scope.$on('data_refreshed', function (event, data) {
        vm.hasGpu = data.stats.gpu.length > 0;
        vm.isLinux = data.isLinux;
        vm.dataLoaded = true;
    });

    // A => Enable/disable AMPs
    hotkeys.add({
        combo: 'A',
        callback: function () {
            ARGUMENTS.disable_amps = !ARGUMENTS.disable_amps;
        }
    });

    // d => Show/hide disk I/O stats
    hotkeys.add({
        combo: 'd',
        callback: function () {
            ARGUMENTS.disable_diskio = !ARGUMENTS.disable_diskio;
        }
    });

    // Q => Show/hide IRQ
    hotkeys.add({
        combo: 'Q',
        callback: function () {
            ARGUMENTS.enable_irq = !ARGUMENTS.enable_irq;
        }
    });

    // f => Show/hide filesystem stats
    hotkeys.add({
        combo: 'f',
        callback: function () {
            ARGUMENTS.disable_fs = !ARGUMENTS.disable_fs;
        }
    });

    // k => Show/hide connections stats
    hotkeys.add({
        combo: 'k',
        callback: function () {
            ARGUMENTS.disable_connections = !ARGUMENTS.disable_connections;
        }
    });

    // n => Show/hide network stats
    hotkeys.add({
        combo: 'n',
        callback: function () {
            ARGUMENTS.disable_network = !ARGUMENTS.disable_network;
        }
    });

    // s => Show/hide sensors stats
    hotkeys.add({
        combo: 's',
        callback: function () {
            ARGUMENTS.disable_sensors = !ARGUMENTS.disable_sensors;
        }
    });

    // 2 => Show/hide left sidebar
    hotkeys.add({
        combo: '2',
        callback: function () {
            ARGUMENTS.disable_left_sidebar = !ARGUMENTS.disable_left_sidebar;
        }
    });

    // z => Enable/disable processes stats
    hotkeys.add({
        combo: 'z',
        callback: function () {
            ARGUMENTS.disable_process = !ARGUMENTS.disable_process;
        }
    });

    // SLASH => Enable/disable short processes name
    hotkeys.add({
        combo: '/',
        callback: function () {
            ARGUMENTS.process_short_name = !ARGUMENTS.process_short_name;
        }
    });

    // D => Enable/disable Docker stats
    hotkeys.add({
        combo: 'D',
        callback: function () {
            ARGUMENTS.disable_docker = !ARGUMENTS.disable_docker;
        }
    });

    // b => Bytes or bits for network I/O
    hotkeys.add({
        combo: 'b',
        callback: function () {
            ARGUMENTS.byte = !ARGUMENTS.byte;
        }
    });

    // 'B' => Switch between bit/s and IO/s for Disk IO
    hotkeys.add({
        combo: 'B',
        callback: function () {
            ARGUMENTS.diskio_iops = !ARGUMENTS.diskio_iops;
        }
    });

    // l => Show/hide alert logs
    hotkeys.add({
        combo: 'l',
        callback: function () {
            ARGUMENTS.disable_alert = !ARGUMENTS.disable_alert;
        }
    });

    // 1 => Global CPU or per-CPU stats
    hotkeys.add({
        combo: '1',
        callback: function () {
            ARGUMENTS.percpu = !ARGUMENTS.percpu;
        }
    });

    // h => Show/hide this help screen
    hotkeys.add({
        combo: 'h',
        callback: function () {
            ARGUMENTS.help_tag = !ARGUMENTS.help_tag;
        }
    });

    // T => View network I/O as combination
    hotkeys.add({
        combo: 'T',
        callback: function () {
            ARGUMENTS.network_sum = !ARGUMENTS.network_sum;
        }
    });

    // U => View cumulative network I/O
    hotkeys.add({
        combo: 'U',
        callback: function () {
            ARGUMENTS.network_cumul = !ARGUMENTS.network_cumul;
        }
    });

    // F => Show filesystem free space
    hotkeys.add({
        combo: 'F',
        callback: function () {
            ARGUMENTS.fs_free_space = !ARGUMENTS.fs_free_space;
        }
    });

    // 3 => Enable/disable quick look plugin
    hotkeys.add({
        combo: '3',
        callback: function () {
            ARGUMENTS.disable_quicklook = !ARGUMENTS.disable_quicklook;
        }
    });

    // 6 => Enable/disable mean gpu
    hotkeys.add({
        combo: '6',
        callback: function () {
            ARGUMENTS.meangpu = !ARGUMENTS.meangpu;
        }
    });

    // G => Enable/disable gpu
    hotkeys.add({
        combo: 'G',
        callback: function () {
            ARGUMENTS.disable_gpu = !ARGUMENTS.disable_gpu;
        }
    });

    hotkeys.add({
        combo: '5',
        callback: function () {
            ARGUMENTS.disable_quicklook = !ARGUMENTS.disable_quicklook;
            ARGUMENTS.disable_cpu = !ARGUMENTS.disable_cpu;
            ARGUMENTS.disable_mem = !ARGUMENTS.disable_mem;
            ARGUMENTS.disable_memswap = !ARGUMENTS.disable_memswap;
            ARGUMENTS.disable_load = !ARGUMENTS.disable_load;
            ARGUMENTS.disable_gpu = !ARGUMENTS.disable_gpu;
        }
    });

    // I => Show/hide IP module
    hotkeys.add({
        combo: 'I',
        callback: function () {
            ARGUMENTS.disable_ip = !ARGUMENTS.disable_ip;
        }
    });

    // P => Enable/disable ports module
    hotkeys.add({
        combo: 'P',
        callback: function () {
            ARGUMENTS.disable_ports = !ARGUMENTS.disable_ports;
        }
    });

    // 'W' > Enable/Disable Wifi plugin
    hotkeys.add({
        combo: 'W',
        callback: function () {
            ARGUMENTS.disable_wifi = !ARGUMENTS.disable_wifi;
        }
    });
}
