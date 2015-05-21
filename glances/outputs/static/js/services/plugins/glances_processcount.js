glancesApp.service('GlancesPluginProcessCount', function() {
    var _pluginName = "processcount";

    this.total  = null;
    this.running = null;
    this.sleeping = null;
    this.stopped = null;
    this.thread = null;

    this.setData = function(data, views) {
        data = data[_pluginName];

        this.total = data['total'];
        this.running = data['running'];
        this.sleeping = data['sleeping'];
        this.stopped = data['stopped'];
        this.thread = data['thread'];
    };
});
