glancesApp.service('GlancesPluginUptime', function() {
    this.uptime = null;

    this.setData = function(data, views) {
        this.uptime = data['uptime'];
    };
});
