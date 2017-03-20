'use strict';

function GlancesPluginPercpuController(GlancesPluginHelper) {
    var vm = this;
    vm.cpus = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['percpu'];

        vm.cpus = [];

        for (var i = 0; i < data.length; i++) {
            var cpuData = data[i];

            vm.cpus.push({
                'total': cpuData.total,
                'user': cpuData.user,
                'system': cpuData.system,
                'idle': cpuData.idle,
                'iowait': cpuData.iowait,
                'steal': cpuData.steal
            });
        }
    };

    vm.getUserAlert = function(cpu) {
        return GlancesPluginHelper.getAlert('percpu', 'percpu_user_', cpu.user)
    };

    vm.getSystemAlert = function(cpu) {
        return GlancesPluginHelper.getAlert('percpu', 'percpu_system_', cpu.system);
    };
}
