glancesApp.service('GlancesPluginSensors', function(GlancesPlugin) {

    var _pluginName = "sensors";
    this.sensors = [];

    this.setData = function(data, views) {
        data = data[_pluginName];

        _.remove(data, function(sensor) {
            return (_.isArray(sensor.value) && _.isEmpty(sensor.value)) || sensor.value === 0;
        });

        this.sensors = data;
    };

    this.getAlert = function(sensor) {
        var current = sensor.type == 'battery' ? 100 - sensor.value : sensor.value;

        return GlancesPlugin.getAlert(_pluginName, 'sensors_' + sensor.type + '_', current);
    };
});
