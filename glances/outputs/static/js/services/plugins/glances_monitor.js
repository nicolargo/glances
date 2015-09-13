glancesApp.service('GlancesPluginMonitor', function() {
    var _pluginName = "monitor";
    this.processes = [];

    this.setData = function(data, views) {
        this.processes = data[_pluginName];
    };

    this.getDescriptionDecoration = function(process) {
        var count = process.count;
        var countMin = process.countmin;
        var countMax = process.countmax;
        var decoration = "ok";

        if (count > 0) {
            if ((countMin == null || count >= countMin) && (countMax == null || count <= countMax)) {
                decoration = 'ok';
            } else {
                decoration = 'careful';
            }
        } else {
            decoration = countMin == null ? 'ok' : 'critical';
        }

        return decoration;
    }
});
