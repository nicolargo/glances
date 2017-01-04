glancesApp.service('GlancesStats', function($http, $injector, $q, GlancesPlugin) {
    var _stats = [], _views = [], _limits = [], _config = {};

    var _plugins = {
        'alert': 'GlancesPluginAlert',
        'cpu': 'GlancesPluginCpu',
        'diskio': 'GlancesPluginDiskio',
        'irq'   : 'GlancesPluginIrq',
        'docker': 'GlancesPluginDocker',
        'ip': 'GlancesPluginIp',
        'fs': 'GlancesPluginFs',
        'folders': 'GlancesPluginFolders',
        'gpu': 'GlancesPluginGpu',
        'load': 'GlancesPluginLoad',
        'mem': 'GlancesPluginMem',
        'memswap': 'GlancesPluginMemSwap',
        'amps': 'GlancesPluginAmps',
        'network': 'GlancesPluginNetwork',
        'percpu': 'GlancesPluginPerCpu',
        'processcount': 'GlancesPluginProcessCount',
        'processlist': 'GlancesPluginProcessList',
        'quicklook': 'GlancesPluginQuicklook',
        'raid': 'GlancesPluginRaid',
        'sensors': 'GlancesPluginSensors',
        'system': 'GlancesPluginSystem',
        'uptime': 'GlancesPluginUptime',
        'ports': 'GlancesPluginPorts',
        'wifi': 'GlancesPluginWifi'
    };

    this.getData = function() {
        return $q.all([
            this.getAllStats(),
            this.getAllViews()
        ]).then(function(results) {
            return {
                'stats': results[0],
                'view': results[1]
            };
        });
    };

    this.getAllStats = function() {
        return $http.get('/api/2/all').then(function (response) {
            _stats = response.data;

            return response.data;
        });
    };

    this.getAllLimits = function() {
        return $http.get('/api/2/all/limits').then(function (response) {
            _limits = response.data;

            return response.data;
        });
    };

    this.getAllViews = function() {
        return $http.get('/api/2/all/views').then(function (response) {
            _views = response.data;

            return response.data;
        });
    };

    this.getHelp = function() {
        return $http.get('/api/2/help').then(function (response) {
            return response.data;
        });
    };

    this.getConfig = function() {
        return $http.get('/api/2/config').then(function (response) {
            _config = response.data;

            return _config;
        });
    };

    this.getArguments = function() {
        return $http.get('/api/2/args').then(function (response) {
            return response.data;
        });
    };

    this.getPlugin = function(name) {
        var plugin = _plugins[name];

        if (plugin === undefined) {
            throw "Plugin '" + name + "' not found";
        }

        plugin = $injector.get(plugin);
        plugin.setData(_stats, _views, _config);

        return plugin;
    };

    // load limits to init GlancePlugin helper
    this.getAllLimits().then(function(limits) {
        GlancesPlugin.setLimits(limits);
    });

});
