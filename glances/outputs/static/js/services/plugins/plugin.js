glancesApp.service('GlancesPlugin', function () {

    var plugin = {
        'limits': {},
        'limitSuffix': ['critical', 'careful', 'warning']
    };

    plugin.setLimits = function(limits){
        this.limits = limits;
    };

    plugin.getAlert = function (pluginName, limitNamePrefix, current, maximum, log) {
        current = current || 0;
        maximum = maximum || 100;
        log = log || false;

        var log_str = log ? '_log' : '';
        var value = (current * 100) / maximum;

        if (this.limits[pluginName] != undefined) {
            for (var i = 0; i < this.limitSuffix.length; i++) {
                var limitName = limitNamePrefix + this.limitSuffix[i];
                var limit = this.limits[pluginName][limitName];

                if (value >= limit) {
                    var pos = limitName.lastIndexOf("_");
                    var className = limitName.substring(pos + 1);

                    return className + log_str;
                }
            }
        }

        return "ok" + log_str;
    };

    plugin.getAlertLog = function (pluginName, limitNamePrefix, current, maximum) {
        return this.getAlert(pluginName, limitNamePrefix, current, maximum, true);
    };

    return plugin;
});
