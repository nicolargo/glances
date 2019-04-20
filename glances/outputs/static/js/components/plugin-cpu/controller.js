
export default function GlancesPluginCpuController($scope, GlancesStats) {
    var vm = this;
    var _view = {};

    vm.total = null;
    vm.user = null;
    vm.system = null;
    vm.idle = null;
    vm.nice = null;
    vm.irq = null;
    vm.iowait = null;
    vm.steal = null;
    vm.ctx_switches = null;
    vm.interrupts = null;
    vm.soft_interrupts = null;
    vm.syscalls = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['cpu'];
        _view = data.views['cpu'];

        vm.isLinux = data.isLinux;

        vm.total = stats.total;
        vm.user = stats.user;
        vm.system = stats.system;
        vm.idle = stats.idle;
        vm.nice = stats.nice;
        vm.irq = stats.irq;
        vm.iowait = stats.iowait;
        vm.steal = stats.steal;

        if (stats.ctx_switches) {
            vm.ctx_switches = Math.floor(stats.ctx_switches / stats.time_since_update);
        }

        if (stats.interrupts) {
            vm.interrupts = Math.floor(stats.interrupts / stats.time_since_update);
        }

        if (stats.soft_interrupts) {
            vm.soft_interrupts = Math.floor(stats.soft_interrupts / stats.time_since_update);
        }

        if (stats.syscalls) {
            vm.syscalls = Math.floor(stats.syscalls / stats.time_since_update);
        }
    }

    vm.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
