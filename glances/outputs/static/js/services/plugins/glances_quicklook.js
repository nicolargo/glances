glancesApp.service('GlancesPluginQuicklook', function() {
    var _pluginName = "quicklook";
    var _view = {};

    this.mem = null;
    this.cpu = null;
    this.swap = null;
    this.percpus = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        _view = views[_pluginName];

        this.mem = data.mem;
        this.cpu = data.cpu;
        this.swap = data.swap;
        this.percpus = [];

        _.forEach(data.percpu, function(cpu, key) {
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
