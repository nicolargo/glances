glancesApp.service('GlancesPluginCpu', function() {
    var _pluginName = "cpu";
    var _view = {};
    
    this.total = null;
    this.user = null;
    this.system = null;
    this.idle = null;
    this.nice = null;
    this.irq = null;
    this.iowait = null;
    this.steal = null;

    this.setData = function(data, views) {
        data = data[_pluginName];
        _view = views[_pluginName];

        this.total = data.total;
        this.user = data.user;
        this.system = data.system;
        this.idle = data.idle;
        this.nice = data.nice;
        this.irq = data.irq;
        this.iowait = data.iowait;
        this.steal = data.steal;
    }

    this.getDecoration = function(value) {
        if(_view[value] == undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    }
});
