'use strict';

function GlancesPluginSensorsController($scope, GlancesPluginHelper) {
    var vm = this;
    vm.sensors = [];

    $scope.$on('data_refreshed', function(event, data) {
        var stats = data.stats['sensors'];

        _.remove(stats, function(sensor) {
            return (_.isArray(sensor.value) && _.isEmpty(sensor.value)) || sensor.value === 0;
        });

        vm.sensors = data;
    });

    this.getAlert = function(sensor) {
        var current = sensor.type == 'battery' ? 100 - sensor.value : sensor.value;

        return GlancesPluginHelper.getAlert('sensors', 'sensors_' + sensor.type + '_', current);
    };
}
