glancesApp.service('GlancesPluginPerCpu', function($filter, GlancesPlugin) {
    var _pluginName = "percpu";
    this.cpus = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        this.cpus = [];

        for (var i = 0; i < data.length; i++) {
            var cpuData = data[i];

            this.cpus.push({
                'total': cpuData.total,
                'user': cpuData.user,
                'system': cpuData.system,
                'idle': cpuData.idle,
                'iowait': cpuData.iowait,
                'steal': cpuData.steal
            });
        }
    };

    this.getUserAlert = function(cpu) {
        return GlancesPlugin.getAlert(_pluginName, 'percpu_user_', cpu.user)
    };

    this.getSystemAlert = function(cpu) {
        return GlancesPlugin.getAlert(_pluginName, 'percpu_system_', cpu.system);
    };
});
