glancesApp.service('GlancesPluginQuicklook', function() {
    var _pluginName = "quicklook";
    var _view = {};

    this.mem = null;
    this.cpu = null;
    this.cpu_name = null;
    this.cpu_hz_current = null;
    this.cpu_hz = null;
    this.swap = null;
    this.percpus = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        _view = views[_pluginName];

        this.mem = data.mem;
        this.cpu = data.cpu;
        this.cpu_name = data.cpu_name;
        this.cpu_hz_current = data.cpu_hz_current;
        this.cpu_hz = data.cpu_hz;
        this.swap = data.swap;
        this.percpus = [];

        angular.forEach(data.percpu, function(cpu) {
            this.percpus.push({
                'number': cpu.cpu_number,
                'total': cpu.total
            });
        }, this);
    }

    this.getDecoration = function(value) {
        if(_view[value] == undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    }
});
