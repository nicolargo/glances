glancesApp.service('GlancesPluginProcessCount', function() {
    var _pluginName = "processcount";

    this.total  = null;
    this.running = null;
    this.sleeping = null;
    this.stopped = null;
    this.thread = null;

    this.setData = function(data, views) {
        data = data[_pluginName];

        this.total = data['total'] || 0;
        this.running = data['running'] || 0;
        this.sleeping = data['sleeping'] || 0;
        this.stopped = data['stopped'] || 0;
        this.thread = data['thread'] || 0;
    };
});
