glancesApp.service('GlancesPluginSensors', function(GlancesPlugin) {

    var _pluginName = "sensors";
    this.sensors = [];

    this.setData = function(data, views) {
        _.remove(data[_pluginName], function(sensor) {
            return sensor.type == "battery" && _.isArray(sensor.value) && _.isEmpty(sensor.value);
        });

        this.sensors = data[_pluginName];
    };

    this.getAlert = function(sensor) {
        var current = sensor.type == 'battery' ? 100 - sensor.value : sensor.value;

        return GlancesPlugin.getAlert(_pluginName, 'sensors_' + sensor.type + '_', current);
    };
});
