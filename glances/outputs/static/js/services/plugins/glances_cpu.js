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
    this.ctx_switches = null;
    this.interrupts = null;
    this.soft_interrupts = null;
    this.syscalls = null;

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

        if (data.ctx_switches) {
          this.ctx_switches = Math.floor(data.ctx_switches / data.time_since_update);
        }

        if (data.interrupts) {
          this.interrupts = Math.floor(data.interrupts / data.time_since_update);
        }

        if (data.soft_interrupts) {
          this.soft_interrupts = Math.floor(data.soft_interrupts / data.time_since_update);
        }

        if (data.syscalls) {
          this.syscalls = Math.floor(data.syscalls / data.time_since_update);
        }
    }

    this.getDecoration = function(value) {
        if(_view[value] == undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    }
});
