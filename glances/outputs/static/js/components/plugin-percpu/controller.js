import _ from "lodash";

export default function GlancesPluginPercpuController($scope, GlancesStats, GlancesPluginHelper) {
    var vm = this;
    vm.cpusChunks = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var percpuStats = data.stats['percpu'];

        var cpus = [];

        for (var i = 0; i < percpuStats.length; i++) {
            var cpuData = percpuStats[i];

            cpus.push({
                'number': cpuData.cpu_number,
                'total': cpuData.total,
                'user': cpuData.user,
                'system': cpuData.system,
                'idle': cpuData.idle,
                'iowait': cpuData.iowait,
                'steal': cpuData.steal
            });
        }

        vm.cpusChunks = _.chunk(cpus, 4);
    };

    vm.getUserAlert = function (cpu) {
        return GlancesPluginHelper.getAlert('percpu', 'percpu_user_', cpu.user)
    };

    vm.getSystemAlert = function (cpu) {
        return GlancesPluginHelper.getAlert('percpu', 'percpu_system_', cpu.system);
    };
}
