glancesApp.service('GlancesPluginAmps', function() {
    var _pluginName = "amps";
    this.processes = [];

    this.setData = function(data, views) {
        var processes = data[_pluginName];

        this.processes = [];
        angular.forEach(processes, function(process) {
            if (process.result !== null) {
                this.processes.push(process);
            }
        }, this);
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
