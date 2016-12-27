glancesApp.service('GlancesPluginProcessList', function($filter, GlancesPlugin) {
    var _pluginName = "processlist";
    var _maxProcessesToDisplay = undefined;
    this.processes = [];
    this.ioReadWritePresent = false;

    this.setData = function(data, views, config) {
        this.processes = [];
        this.ioReadWritePresent = false;
        _maxProcessesToDisplay = config.outputs !== undefined ? config.outputs.max_processes_display : undefined;;

        for (var i = 0; i < data[_pluginName].length; i++) {
            var process = data[_pluginName][i];

            process.memvirt = process.memory_info[1];
            process.memres  = process.memory_info[0];
            process.timeplus = $filter('timedelta')(process.cpu_times);
            process.timemillis = $filter('timemillis')(process.cpu_times);

            process.ioRead = null;
            process.ioWrite = null;

            if (process.io_counters) {
                this.ioReadWritePresent = true;

                process.ioRead  = (process.io_counters[0] - process.io_counters[2]) / process.time_since_update;

                if (process.ioRead != 0) {
                    process.ioRead = $filter('bytes')(process.ioRead);
                }

                process.ioWrite = (process.io_counters[1] - process.io_counters[3]) / process.time_since_update;

                if (process.ioWrite != 0) {
                    process.ioWrite = $filter('bytes')(process.ioWrite);
                }
            }

            process.isNice = process.nice !== undefined && ((data['system'].os_name === 'Windows' && process.nice != 32) || (data['system'].os_name !== 'Windows' && process.nice != 0));

            if (Array.isArray(process.cmdline)) {
                process.cmdline = process.cmdline.join(' ');
            }

            this.processes.push(process);
        }
    };

    this.getCpuPercentAlert = function(process) {
        return GlancesPlugin.getAlert(_pluginName, 'processlist_cpu_', process.cpu_percent);
    };

    this.getMemoryPercentAlert = function(process) {
        return GlancesPlugin.getAlert(_pluginName, 'processlist_mem_', process.cpu_percent);
    };

    this.getLimit = function() {
        return _maxProcessesToDisplay;
    };
});
